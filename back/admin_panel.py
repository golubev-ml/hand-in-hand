import json
"""Админка сайта: /admin. Чистый FastAPI, без сторонних админок."""
import html
import os
import uuid
from pathlib import Path
from PIL import Image

from datetime import datetime
import jwt
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from jwt.exceptions import PyJWTError
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY, create_token, verify_password
from database import get_db
from models import Donation, Log, Manager, Order, Picture

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


router = APIRouter(prefix="/admin", include_in_schema=False)


@router.get("", include_in_schema=False)
def admin_root_redirect():
    return RedirectResponse("/admin/", status_code=302)


def current_admin(request: Request) -> str:
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return payload.get("login", "")


TEMPLATE = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>@TITLE@</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#f6f7f9;color:#111}
header{background:#111827;color:#fff;padding:12px 20px;display:flex;gap:16px;align-items:center}
header a{color:#93c5fd;text-decoration:none}
main{padding:20px;max-width:1100px;margin:0 auto}
table{border-collapse:collapse;width:100%;background:#fff}
td,th{border:1px solid #e5e7eb;padding:8px 10px;text-align:left;font-size:14px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:16px}
input,select,button,textarea{padding:8px 10px;margin:4px 0;font-size:14px}
button{cursor:pointer}
img.thumb{width:60px;height:60px;object-fit:cover}

[contenteditable]{outline:none;cursor:text}
[contenteditable]:focus{background:#eef6ff;box-shadow:0 0 0 2px #93c5fd inset}
.flash-ok{background:#d1fae5 !important;transition:background 0.3s}
.flash-err{background:#fee2e2 !important;transition:background 0.3s}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;z-index:999}
.modal{background:#fff;border-radius:10px;padding:24px;max-width:600px;width:90%;max-height:90vh;overflow-y:auto}
.modal h3{margin-top:0}
.modal img{width:120px;height:120px;object-fit:cover;border-radius:8px;float:left;margin:0 16px 12px 0}
.modal textarea{width:100%;min-height:140px;font-family:inherit}
.modal .meta{color:#6b7280;font-size:12px;margin-top:4px}
.btn-icon{padding:4px 8px !important;margin:0 !important;font-size:12px}
.btn-warn{background:#f59e0b;color:#fff}
.btn-danger{background:#ef4444;color:#fff}
.col-actions{white-space:nowrap}
</style></head><body>
<header><b>Админка</b>
<a href="/admin/">Статистика</a>
<a href="/admin/pictures">Рисунки</a>
<a href="/admin/pictures/upload">+ Картинка</a>
<a href="/admin/orders">Заказы</a>
<a href="/admin/donations">Пожертвования</a>
<a href="/admin/logs">Лог</a>
<span style="margin-left:auto">@LOGIN@ · <a href="/admin/logout">выйти</a></span>
</header><main>@BODY@</main></body></html>"""


def page(title: str, body: str, login: str) -> str:
    return TEMPLATE.replace("@TITLE@", title).replace("@BODY@", body).replace("@LOGIN@", login)


LOGIN_PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Вход</title>
<style>body{font-family:system-ui,sans-serif;background:#f6f7f9;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
form{background:#fff;padding:24px 28px;border:1px solid #e5e7eb;border-radius:10px;display:flex;flex-direction:column}
input{margin:6px 0;padding:9px 10px}button{margin-top:10px;padding:10px;cursor:pointer}</style></head>
<body><form method="post" action="/admin/login"><h2>Вход в админку</h2>
<input name="login" placeholder="Логин" required>
<input name="password" type="password" placeholder="Пароль" required>
<button>Войти</button></form></body></html>"""


# ---------- вход / выход ----------
@router.get("/login", response_class=HTMLResponse)
def login_page():
    return LOGIN_PAGE


@router.post("/login")
def do_login(login: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    manager = db.query(Manager).filter(Manager.login == login).first()
    if not manager or manager.status != "active" or not verify_password(password, manager.password_hash):
        return HTMLResponse(
            LOGIN_PAGE.replace("<button>", "<p style='color:#b91c1c'>Неверный логин или пароль</p><button>"),
            status_code=401,
        )
    response = RedirectResponse("/admin/", status_code=302)
    response.set_cookie(
        "admin_token",
        create_token(manager.id, manager.login),
        httponly=True,
        max_age=12 * 3600,
        samesite="lax",
        secure=os.getenv("BASE_URL", "").startswith("https://"),
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie("admin_token")
    return response


# ---------- статистика ----------
@router.get("/", response_class=HTMLResponse)
def dashboard(login: str = Depends(current_admin), db: Session = Depends(get_db)):
    pic_total = db.query(func.count(Picture.id)).scalar() or 0
    pic_avail = db.query(func.count(Picture.id)).filter(Picture.status == "available").scalar() or 0
    pic_sold = db.query(func.count(Picture.id)).filter(Picture.status == "sold").scalar() or 0
    don_total = db.query(func.count(Donation.id)).scalar() or 0
    don_sum = db.query(func.sum(Donation.price)).filter(Donation.status == "confirmed").scalar() or 0
    man_total = db.query(func.count(Manager.id)).scalar() or 0
    log_total = db.query(func.count(Log.id)).scalar() or 0
    body = f"""<h2>Статистика</h2><div class="card"><table>
    <tr><th>Рисунков всего</th><td>{pic_total}</td></tr>
    <tr><th>Доступно / продано</th><td>{pic_avail} / {pic_sold}</td></tr>
    <tr><th>Пожертвований</th><td>{don_total}</td></tr>
    <tr><th>Сумма подтверждённых пожертвований</th><td>{don_sum} ₽</td></tr>
    <tr><th>Менеджеров</th><td>{man_total}</td></tr>
    <tr><th>Записей в логе</th><td>{log_total}</td></tr>
    </table></div>"""
    return page("Статистика", body, login)


# ---------- рисунки ----------
@router.get("/pictures", response_class=HTMLResponse)
def pictures(login: str = Depends(current_admin), db: Session = Depends(get_db)):
    rows = db.query(Picture).order_by(Picture.time.desc()).all()
    # HIH-3: собираем данные заказов для колонки "Продано за" и отмены
    order_ids = [p.order_id for p in rows if p.order_id]
    orders = {o.id: o for o in db.query(Order).filter(Order.id.in_(order_ids)).all()} if order_ids else {}
    tr = ""
    for p in rows:
        title = html.escape(getattr(p, "title", "") or f"#{p.id}")
        author = html.escape(getattr(p, "author", "") or "—")
        age = getattr(p, "age", 0) or "—"
        min_price = getattr(p, "min_price", 500) or 500
        # "Продано за" — ищем цену по picture.id в items snapshot заказа
        sold_for = "—"
        status_changed = p.sold_at.strftime('%d.%m %H:%M') if p.sold_at else '—'
        cancel_btn = ""
        if p.order_id:
            o = orders.get(p.order_id)
            if o:
                if o.cancelled_at:
                    sold_for = f'<span style="color:#9ca3af">отменено</span>'
                    status_changed = o.cancelled_at.strftime('%d.%m %H:%M')
                else:
                    for item in (o.items or []):
                        if item.get("id") == p.id:
                            sold_for = f'{int(item.get("price", 0))} ₽'
                            break
                    status_changed = o.created_at.strftime('%d.%m %H:%M')
            cancel_btn = f'<button type="button" class="btn-icon btn-warn" onclick="cancelOrder({p.id})">⤺</button>'
        elif p.status == "sold":
            sold_for = "ручной"
        history_short = html.escape((getattr(p, "history", "") or "")[:40])
        if len(getattr(p, "history", "") or "") > 40:
            history_short += "…"
        tr += f"""<tr data-id="{p.id}">
        <td><img class="thumb" src="{p.image_path}"></td>
        <td contenteditable="true" data-field="title">{title}</td>
        <td contenteditable="true" data-field="author">{author}</td>
        <td contenteditable="true" data-field="age" style="max-width:60px">{age}</td>
        <td contenteditable="true" data-field="min_price" style="max-width:80px">{int(min_price)}</td>
        <td><form method="post" action="/admin/pictures/{p.id}/status" style="margin:0">
            <select name="status" onchange="this.form.submit()">
                <option {'selected' if p.status == 'available' else ''}>available</option>
                <option {'selected' if p.status == 'sold' else ''}>sold</option>
                <option {'selected' if p.status == 'archive' else ''}>archive</option>
            </select></form></td>
        <td>{status_changed}</td>
        <td>{sold_for}</td>
        <td class="col-actions">
            <button type="button" class="btn-icon" onclick="openHistory({p.id}, {json.dumps(title)}, {json.dumps(history_short)}, {json.dumps(getattr(p, 'history', '') or '')}, {json.dumps(p.image_path)})">📖</button>
            {cancel_btn}
            <form method="post" action="/admin/pictures/{p.id}/delete" style="margin:0;display:inline" onsubmit="return confirm('Удалить картину?')">
                <button type="submit" class="btn-icon btn-danger">✕</button>
            </form>
        </td>
        </tr>"""
    body = f"""<h2>Рисунки</h2><div class="card"><table>
    <tr><th>Превью</th><th>Название</th><th>Имя</th><th>Возраст</th><th>Мин.</th><th>Статус</th><th>Смена</th><th>Продано за</th><th></th></tr>{tr}</table></div>
<script>
document.querySelectorAll('td[contenteditable]').forEach(td => {{
    let orig = td.textContent;
    td.addEventListener('blur', save);
    td.addEventListener('keydown', e => {{
        if (e.key === 'Enter') {{ e.preventDefault(); td.blur(); }}
        if (e.key === 'Escape') {{ td.textContent = orig; td.blur(); }}
    }});
    td.addEventListener('focus', () => {{ orig = td.textContent; }});
    async function save() {{
        const id = td.parentElement.dataset.id;
        const field = td.dataset.field;
        const value = td.textContent.trim();
        if (value === orig) return;
        try {{
            const r = await fetch(`/admin/pictures/${{id}}/update`, {{
                method: 'POST', headers: {{'Content-Type':'application/json'}},
                body: JSON.stringify({{[field]: value}})
            }});
            if (!r.ok) {{
                const j = await r.json().catch(() => ({{detail: 'Ошибка'}}));
                throw new Error(j.detail || 'Ошибка');
            }}
            td.classList.add('flash-ok');
            setTimeout(() => td.classList.remove('flash-ok'), 1000);
            orig = td.textContent;
        }} catch (e) {{
            alert('Не удалось: ' + e.message);
            td.textContent = orig;
            td.classList.add('flash-err');
            setTimeout(() => td.classList.remove('flash-err'), 1500);
        }}
    }}
}});
async function cancelOrder(id) {{
    if (!confirm('Отменить заказ? Картина вернётся в продажу, заказ будет помечен как отменённый.')) return;
    const r = await fetch(`/admin/pictures/${{id}}/cancel_order`, {{method: 'POST'}});
    if (r.ok) location.reload();
    else {{ const j = await r.json().catch(() => ({{detail: 'Ошибка'}})); alert('Ошибка: ' + j.detail); }}
}}
function openHistory(id, title, short, full, img) {{
    document.querySelectorAll('.modal-bg').forEach(e => e.remove());
    const bg = document.createElement('div');
    bg.className = 'modal-bg';
    bg.onclick = e => {{ if (e.target === bg) bg.remove(); }};
    bg.innerHTML = `<div class="modal">
        <img src="${{img}}">
        <h3>${{title}}</h3>
        <textarea id="h-text">${{full.replace(/</g,'&lt;')}}</textarea>
        <div class="meta">Минимальная цена: 500 ₽ (редактируется в таблице)</div>
        <div style="margin-top:12px;text-align:right">
            <button type="button" onclick="this.closest('.modal-bg').remove()">Отмена</button>
            <button type="button" onclick="saveHistory(${{id}})">Сохранить</button>
        </div>
    </div>`;
    document.body.appendChild(bg);
}}
async function saveHistory(id) {{
    const t = document.querySelector('#h-text').value;
    const r = await fetch(`/admin/pictures/${{id}}/update`, {{
        method: 'POST', headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{history: t}})
    }});
    if (r.ok) location.reload();
    else {{ const j = await r.json().catch(() => ({{detail: 'Ошибка'}})); alert('Ошибка: ' + j.detail); }}
}}
document.addEventListener('keydown', e => {{
    if (e.key === 'Escape') document.querySelectorAll('.modal-bg').forEach(e => e.remove());
}});
</script>"""
    return page("Рисунки", body, login)


@router.post("/pictures/{picture_id}/update")
async def picture_update(picture_id: int, request: Request, login: str = Depends(current_admin), db: Session = Depends(get_db)):
    """HIH-3: inline-редактирование полей картины (whitelist)."""
    data = await request.json()
    p = db.query(Picture).filter(Picture.id == picture_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Картина не найдена")
    for k, v in data.items():
        if k in ("title", "author"):
            v = str(v).strip()
            if not v:
                raise HTTPException(status_code=400, detail="Поле не может быть пустым")
            if len(v) > 200:
                raise HTTPException(status_code=400, detail="Слишком длинно")
            setattr(p, k, v)
        elif k == "age":
            try:
                v = int(str(v).strip())
            except ValueError:
                raise HTTPException(status_code=400, detail="Возраст — число")
            if not 1 <= v <= 18:
                raise HTTPException(status_code=400, detail="Возраст 1–18")
            p.age = v
        elif k == "min_price":
            try:
                v = float(str(v).strip().replace(",", "."))
            except ValueError:
                raise HTTPException(status_code=400, detail="Цена — число")
            if v < 0:
                raise HTTPException(status_code=400, detail="Цена ≥ 0")
            p.min_price = v
        elif k == "history":
            p.history = str(v)
        else:
            raise HTTPException(status_code=400, detail=f"Поле '{k}' нельзя редактировать")
    db.commit()
    return {"ok": True}


@router.post("/pictures/{picture_id}/cancel_order")
async def picture_cancel_order(picture_id: int, login: str = Depends(current_admin), db: Session = Depends(get_db)):
    """HIH-3: отмена заказа — картина возвращается в продажу."""
    p = db.query(Picture).filter(Picture.id == picture_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Картина не найдена")
    if p.order_id is None:
        raise HTTPException(status_code=400, detail="У картины нет заказа (ручной sold — меняй статус списком)")
    order = db.query(Order).filter(Order.id == p.order_id).first()
    if order:
        order.cancelled_at = datetime.now()
    p.order_id = None
    p.sold_at = None
    p.status = "available"
    db.commit()
    return {"ok": True}


@router.get("/pictures/upload", response_class=HTMLResponse)
def upload_form(login: str = Depends(current_admin)):
    body = """<h2>Загрузка рисунка</h2><div class="card">
    <form method="post" action="/admin/pictures/upload" enctype="multipart/form-data">
    <input type="file" name="file" accept="image/*" required><br>
    <input name="title" placeholder="Название" style="width:100%"><br>
    <input name="author" placeholder="Имя ребёнка" maxlength="100" required style="width:100%"><br>
    <input name="age" type="number" min="1" max="18" placeholder="Возраст" required style="width:100%"><br>
    <textarea name="history" placeholder="История рисунка" style="width:100%" rows="3"></textarea><br>
    <input name="price" type="number" step="0.01" value="0"><br>
    <button>Сохранить</button></form></div>"""
    return page("Загрузка", body, login)


@router.post("/pictures/upload")
async def upload_save(
    file: UploadFile = File(...),
    title: str = Form(""),
    author: str = Form(...),
    age: int = Form(..., ge=1, le=18),
    history: str = Form(""),
    price: float = Form(0.0),
    min_price: float = Form(500.0),
    login: str = Depends(current_admin),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        return HTMLResponse("Формат не поддерживается. <a href='/admin/pictures/upload'>назад</a>", status_code=400)
    
    file_data = await file.read()
    if len(file_data) > MAX_FILE_SIZE:
        return HTMLResponse(f"Файл слишком большой (макс {MAX_FILE_SIZE // (1024*1024)} МБ). <a href='/admin/pictures/upload'>назад</a>", status_code=400)
    
    base = uuid.uuid4().hex
    orig_name = f"{base}{ext}"
    orig_path = UPLOAD_DIR / orig_name
    orig_path.write_bytes(file_data)
    
    # Pillow: ориентация и версии
    orientation = "landscape"
    gallery = mail = mobile = ""
    try:
        with Image.open(orig_path) as img:
            img = Image.open(orig_path)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            w, h = img.size
            orientation = "portrait" if h > w else "landscape"
            
            def save_version(max_dim, suffix):
                ratio = min(max_dim / w, max_dim / h, 1.0)
                if ratio >= 1.0:
                    new = img.copy()
                else:
                    new = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                vname = f"{base}_{suffix}.webp"
                new.save(UPLOAD_DIR / vname, "WEBP", quality=85)
                return f"/uploads/{vname}"
            
            gallery = save_version(800, "gallery")
            mail    = save_version(600, "mail")
            mobile  = save_version(480, "mobile")
    except Exception as e:
        print(f"[upload] Pillow failed: {e}; using original only")
    
    fields = {
        "image_path": f"/uploads/{orig_name}",
        "history": history,
        "price": price,
        "min_price": min_price,
        "author": author.strip(),
        "age": age,
        "orientation": orientation,
        "image_path_gallery": gallery,
        "image_path_mail": mail,
        "image_path_mobile": mobile,
    }
    if hasattr(Picture, "title"):
        fields["title"] = title
    db.add(Picture(**fields))
    db.commit()
    return RedirectResponse("/admin/pictures", status_code=302)


@router.post("/pictures/{picture_id}/status")
async def picture_status(picture_id: int, request: Request, login: str = Depends(current_admin), db: Session = Depends(get_db)):
    form = await request.form()
    picture = db.get(Picture, picture_id)
    if picture:
        new_status = form.get("status", picture.status)
        # HIH-1: реально проданную (с заказом) нельзя вернуть в продажу
        if picture.order_id is not None and new_status == "available":
            return HTMLResponse("Картина продана через заказ — вернуть в продажу нельзя", status_code=400)
        if new_status == "sold" and picture.status != "sold":
            picture.sold_at = datetime.now()
        if new_status == "available" and picture.status == "sold":
            picture.sold_at = None
        picture.status = new_status
        db.commit()
    return RedirectResponse("/admin/pictures", status_code=302)


@router.post("/pictures/{picture_id}/delete")
def picture_delete(picture_id: int, login: str = Depends(current_admin), db: Session = Depends(get_db)):
    picture = db.get(Picture, picture_id)
    if picture:
        db.delete(picture)
        db.commit()
    return RedirectResponse("/admin/pictures", status_code=302)


# ---------- заказы ----------
@router.get("/orders", response_class=HTMLResponse)
def orders(login: str = Depends(current_admin), db: Session = Depends(get_db)):
    rows = db.query(Order).order_by(Order.created_at.desc()).all()
    tr = ""
    for o in rows:
        tr += f"""<tr>
        <td>{o.created_at:%m-%d %H:%M}</td>
        <td>{html.escape(o.customer_name)}</td>
        <td>{html.escape(o.customer_email)}</td>
        <td>{html.escape(o.customer_phone)}</td>
        <td>{o.total} ₽</td>
        <td><span style="background:#{'#dcfce7' if o.payment_status == 'paid' else '#fee2e2'};padding:2px 6px;border-radius:3px">{o.payment_status}</span></td>
        <td><span style="background:#{'#dcfce7' if o.email_status == 'sent' else '#fef3c7'};padding:2px 6px;border-radius:3px">{o.email_status}</span></td>
        </tr>"""
    body = f"""<h2>Заказы</h2><div class="card"><table>
    <tr><th>Дата</th><th>Имя</th><th>Email</th><th>Телефон</th><th>Сумма</th><th>Оплата</th><th>Email</th></tr>{tr}</table></div>"""
    return page("Заказы", body, login)


# ---------- пожертвования ----------
@router.get("/donations", response_class=HTMLResponse)
def donations(login: str = Depends(current_admin), db: Session = Depends(get_db)):
    rows = db.query(Donation).order_by(Donation.time.desc()).all()
    tr = ""
    for d in rows:
        tr += f"""<tr><td>{d.date}</td><td>{html.escape(d.name)}</td><td>{d.price} ₽</td><td>{d.card}</td>
        <td><form method="post" action="/admin/donations/{d.id}/status" style="margin:0">
            <select name="status" onchange="this.form.submit()">
                <option {'selected' if d.status == 'pending' else ''}>pending</option>
                <option {'selected' if d.status == 'confirmed' else ''}>confirmed</option>
                <option {'selected' if d.status == 'rejected' else ''}>rejected</option>
            </select></form></td></tr>"""
    body = f"""<h2>Пожертвования</h2><div class="card"><table>
    <tr><th>Дата</th><th>Имя</th><th>Сумма</th><th>Карта</th><th>Статус</th></tr>{tr}</table></div>"""
    return page("Пожертвования", body, login)


@router.post("/donations/{donation_id}/status")
async def donation_status(donation_id: int, request: Request, login: str = Depends(current_admin), db: Session = Depends(get_db)):
    form = await request.form()
    donation = db.get(Donation, donation_id)
    if donation:
        donation.status = form.get("status", donation.status)
        db.commit()
    return RedirectResponse("/admin/donations", status_code=302)


# ---------- лог ----------
@router.get("/logs", response_class=HTMLResponse)
def logs(login: str = Depends(current_admin), db: Session = Depends(get_db)):
    rows = db.query(Log).order_by(Log.time.desc()).limit(200).all()
    tr = "".join(
        f"<tr><td>{l.time:%m-%d %H:%M}</td><td>{html.escape(l.text)}</td><td>{html.escape(l.url)}</td></tr>"
        for l in rows
    )
    body = f"""<h2>Лог запросов</h2><div class="card"><table>
    <tr><th>Время</th><th>Запрос</th><th>URL</th></tr>{tr}</table></div>"""
    return page("Лог", body, login)
