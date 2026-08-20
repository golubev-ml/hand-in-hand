"""Отправка почты через SMTP.

Пока почта на сервере не настроена, письма уходят в MailHog (тестовый сервер,
никуда реально не отправляет). Параметры — через переменные окружения:
SMTP_HOST, SMTP_PORT, MAIL_FROM, BASE_URL.
"""
import os
import re
import smtplib
from pathlib import Path
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
MAIL_FROM = os.getenv("MAIL_FROM", "noreply@kraski-detstva.ru")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _abs(url: str) -> str:
    """Абсолютный URL для картинок внутри письма."""
    return url if url.startswith("http") else f"{BASE_URL}{url}"


def _fmt(price: float) -> str:
    return f"{price:,.0f} ₽".replace(",", " ")


def build_order_html(name: str, items: list[dict], total: float) -> str:
    """Письмо о покупке: рисунок + рассказ + спасибо за пожертвование + контакты."""
    rows = ""
    for index, it in enumerate(items):
        image_src = (
            f"cid:order-image-{index}"
            if it["img"].startswith("/uploads/")
            else _abs(it["img"])
        )
        rows += f"""
      <tr>
        <td style="padding:16px 0;border-bottom:1px solid #E8DCC8;">
          <img src="{image_src}" alt="{it['title']}" width="240"
               style="border-radius:12px;display:block;margin-bottom:10px;" />
          <div style="font-size:18px;font-weight:bold;color:#2C2416;">
            {it['title']} <span style="color:#4A7C59;">— {_fmt(it['price'] * it['qty'])}</span>
          </div>
          <div style="color:#6B5B42;font-size:14px;margin-top:6px;line-height:1.6;">
            «{it['story']}»
          </div>
        </td>
      </tr>"""

    return f"""
<div style="background:#FEFAF4;padding:24px 0;font-family:Georgia,'Times New Roman',serif;">
  <div style="max-width:600px;margin:0 auto;background:#FFFCF7;border:1px solid #E8DCC8;
              border-radius:16px;padding:32px;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
      <img src="cid:logo" alt="" width="44" height="44" style="border-radius:50%;" />
      <div style="font-size:20px;font-weight:bold;color:#4A7C59;">Искусство чтобы жить</div>
    </div>

    <h1 style="font-size:26px;margin:0 0 10px;color:#2C2416;">
      {name}, спасибо за вашу покупку!
    </h1>
    <p style="color:#6B5B42;font-size:15px;line-height:1.6;margin:0 0 16px;">
      Ваш заказ принят и будет обработан в течение одного рабочего дня.
      Ниже — ваши рисунки и их истории.
    </p>

    <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>

    <div style="text-align:right;font-size:18px;font-weight:bold;
                color:#2C2416;padding:14px 0;">
      Итого: {_fmt(total)}
    </div>

    <div style="background:#E8F2EB;border-radius:12px;padding:14px;
                font-size:14px;color:#4A7C59;margin-bottom:20px;">
      🌱 <b>30%</b> от суммы заказа поступят в фонд. Спасибо за ваше
      пожертвование юным художникам!
    </div>

    <div style="background:#FFF7E0;border-radius:12px;padding:14px;font-size:14px;
                color:#8A6D3B;margin-bottom:20px;">
      🖨 Оригиналы рисунков прикреплены к письму в нескольких форматах —
      их можно распечатать в хорошем качестве.
    </div>

    <div style="border-top:1px solid #E8DCC8;padding-top:16px;font-size:14px;
                color:#6B5B42;line-height:1.9;">
      Остались вопросы? Мы всегда на связи:<br />
      Email: ahmadeeva.alina97@gmail.com<br />
      Телефон: +7 (919) 633-72-25<br />
      Адрес: 420043, Республика Татарстан, г Казань, Бойничная ул, д. 5, помещ. 6
    </div>
  </div>
</div>
"""


def _mime_subtype(path: Path) -> str:
    st = path.suffix.lower().lstrip(".")
    return {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}.get(st, "octet-stream")


def _safe_title(t: str) -> str:
    t = re.sub(r"[^\wа-яёА-ЯЁ\- ]+", "", t or "").strip().replace(" ", "_")[:40]
    return t or "picture"


def send_email(to: str, subject: str, html: str, items: list[dict] | None = None) -> None:
    """HIH-6: письмо с inline-картинками (cid) + вложениями для печати."""
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = to

    # HTML
    msg.attach(MIMEText(html, "html", "utf-8"))

    # лого — inline через cid
    logo = STATIC_DIR / "logo.png"
    if logo.is_file():
        li = MIMEImage(logo.read_bytes(), _subtype="png")
        li.add_header("Content-ID", "<logo>")
        li.add_header("Content-Disposition", "inline", filename="logo.png")
        msg.attach(li)

    # картинки заказа — inline для показа
    for index, item in enumerate(items or []):
        image_path = item.get("img", "")
        if not image_path.startswith("/uploads/"):
            continue
        path = UPLOAD_DIR / Path(image_path).name
        if not path.is_file():
            raise FileNotFoundError(f"Order image not found: {image_path}")
        image = MIMEImage(path.read_bytes(), _subtype=_mime_subtype(path))
        image.add_header("Content-ID", f"<order-image-{index}>")
        image.add_header("Content-Disposition", "inline", filename=path.name)
        msg.attach(image)

    # HIH-6: вложения для печати — оригинал + gallery-версия
    for index, item in enumerate(items or []):
        image_path = item.get("img", "")
        if not image_path.startswith("/uploads/"):
            continue
        path = UPLOAD_DIR / Path(image_path).name
        if not path.is_file():
            continue
        base = f"{index + 1:02d}_{_safe_title(item.get('title', ''))}"
        att = MIMEApplication(path.read_bytes(), _subtype=_mime_subtype(path))
        att.add_header("Content-Disposition", "attachment", filename=f"{base}_print{path.suffix.lower()}")
        msg.attach(att)
        gal = UPLOAD_DIR / (path.stem + "_gallery.webp")
        if gal.is_file():
            att2 = MIMEApplication(gal.read_bytes(), _subtype="webp")
            att2.add_header("Content-Disposition", "attachment", filename=f"{base}_gallery.webp")
            msg.attach(att2)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.send_message(msg)
