"""Отправка почты через SMTP.

Пока почта на сервере не настроена, письма уходят в MailHog (тестовый сервер,
никуда реально не отправляет). Параметры — через переменные окружения:
SMTP_HOST, SMTP_PORT, MAIL_FROM, BASE_URL.
"""
import os
import smtplib
from pathlib import Path
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
MAIL_FROM = os.getenv("MAIL_FROM", "noreply@kraski-detstva.ru")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"


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
      <img src="{BASE_URL}/logo.png" alt="" width="44" height="44" style="border-radius:50%;" />
      <div style="font-size:20px;font-weight:bold;color:#4A7C59;">Краски детства</div>
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

    <div style="border-top:1px solid #E8DCC8;padding-top:16px;font-size:14px;
                color:#6B5B42;line-height:1.9;">
      Остались вопросы? Мы всегда на связи:<br />
      Email: hello@kraskiland.ru<br />
      Телефон: +7 (495) 123-45-67<br />
      Адрес: Москва, ул. Творческая, 12, офис 3
    </div>
  </div>
</div>
"""


def send_email(to: str, subject: str, html: str, items: list[dict] | None = None) -> None:
    """Отправляет HTML-письмо через SMTP (MailHog или реальный сервер)."""
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = to
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alternative)

    for index, item in enumerate(items or []):
        image_path = item.get("img", "")
        if not image_path.startswith("/uploads/"):
            continue
        path = UPLOAD_DIR / Path(image_path).name
        if not path.is_file():
            raise FileNotFoundError(f"Order image not found: {image_path}")
        subtype = path.suffix.lower().lstrip(".")
        if subtype == "jpg":
            subtype = "jpeg"
        image = MIMEImage(path.read_bytes(), _subtype=subtype)
        image.add_header("Content-ID", f"<order-image-{index}>")
        image.add_header("Content-Disposition", "inline", filename=path.name)
        msg.attach(image)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.send_message(msg)
