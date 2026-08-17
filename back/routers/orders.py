"""Заказы: покупка рисунков с отправкой письма покупателю."""
import json
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
from mail import build_order_html, send_email
from models import Order, Picture, Log
from schemas import PictureOrderCreate, OrderOut

router = APIRouter(prefix="/api/orders", tags=["Заказы"])


@router.post("", response_model=OrderOut)
def create_order(data: PictureOrderCreate, response: Response, db: Session = Depends(get_db)):
    """Создание заказа картин с проверкой оплаты по телефону."""
    
    # Получаем картины и проверяем их существование
    pictures = db.query(Picture).filter(Picture.id.in_(data.picture_ids)).all()
    
    if len(pictures) != len(data.picture_ids):
        raise HTTPException(status_code=400, detail="Одна или более картин не найдены")
    
    # Проверяем что картины доступны (не проданы и не в другом заказе)
    for picture in pictures:
        if picture.status == "sold" or picture.order_id is not None:
            raise HTTPException(
                status_code=400, 
                detail=f"Картина '{picture.title}' уже продана или недоступна"
            )
    
    # Считаем total из цен картин в БД
    total = sum(p.price for p in pictures)
    
    # Определяем статус оплаты по телефону
    payment_status = "failed" if data.customer_phone == "78889990002" else "paid"
    
    # Создаём снапшот картин для заказа
    items_snapshot = [
        {
            "id": p.id,
            "title": p.title,
            "author": p.author,
            "age": p.age,
            "price": p.price,
            "description": p.description,
        }
        for p in pictures
    ]
    
    # Попытаемся отправить письмо при успешной оплате
    email_status = "not_sent"
    if payment_status == "paid":
        try:
            # Подготавливаем данные для письма в формате совместимом с build_order_html
            mail_items = [
                {
                    "img": p.image_path,
                    "title": p.title,
                    "story": p.history,
                    "price": p.price,
                    "qty": 1,
                }
                for p in pictures
            ]
            html = build_order_html(
                name=data.customer_name,
                items=mail_items,
                total=total,
            )
            send_email(
                data.customer_email,
                "Искусство чтобы жить — спасибо за вашу покупку!",
                html,
                items=mail_items,
            )
            email_status = "sent"
        except Exception as e:
            print(f">>> Не удалось отправить письмо: {e}")
            email_status = "failed"
    
    # Создаём заказ в БД
    order = Order(
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        customer_phone=data.customer_phone,
        total=total,
        payment_status=payment_status,
        email_status=email_status,
        items=items_snapshot,
    )
    db.add(order)
    db.flush()  # Получаем ID заказа
    
    # При успешной оплате отмечаем картины как проданные
    if payment_status == "paid":
        for picture in pictures:
            picture.status = "sold"
            picture.order_id = order.id
    
    # Логируем
    db.add(Log(
        text=f"ORDER → {data.customer_email} ({payment_status})",
        url="/api/orders",
        request=f"items={len(pictures)}, total={total}, phone={data.customer_phone}",
        response=f"payment_status={payment_status}, email_status={email_status}",
    ))
    
    db.commit()

    if payment_status == "failed":
        response.status_code = 402
    
    return OrderOut(
        order_id=order.id,
        payment_status=payment_status,
        email_status=email_status,
        total=total,
    )
