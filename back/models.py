from datetime import datetime, date

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Date, JSON, ForeignKey

from database import Base


class Manager(Base):
    """Менеджер: логин, пароль, статус."""
    __tablename__ = "managers"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # хеш, не пароль!
    status = Column(String(20), default="active")        # active | blocked
    created_at = Column(DateTime, default=datetime.now)


class Picture(Base):
    """Рисунок: картинка, автор, цена, статус + поля витрины."""
    __tablename__ = "pictures"
    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String(500), nullable=False)     # /uploads/abc.jpg или внешний URL
    history = Column(Text, default="")                   # на фронте отдаётся как story
    time = Column(DateTime, default=datetime.now)
    price = Column(Float, default=0.0)
    status = Column(String(20), default="available")     # available | sold | archive
    # поля витрины (раньше жили в хардкоде App.tsx)
    title = Column(String(200), default="")
    author = Column(String(100), default="")
    age = Column(Integer, default=0)
    category = Column(String(50), default="painting")
    description = Column(Text, default="")
    is_new = Column(Integer, default=0)
    is_featured = Column(Integer, default=0)
    popularity = Column(Integer, default=0)
    orientation = Column(String(20), default="landscape")
    image_path_gallery = Column(String(500), default="")
    image_path_mail = Column(String(500), default="")
    image_path_mobile = Column(String(500), default="")
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)


class Order(Base):
    """Заказ: покупка картин с контактами и статусом оплаты."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    customer_name = Column(String(100), nullable=False)
    customer_email = Column(String(254), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    total = Column(Float, nullable=False)
    payment_status = Column(String(20), default="pending")   # paid | failed
    email_status = Column(String(20), default="not_sent")    # sent | failed | not_sent
    items = Column(JSON, nullable=False)                     # JSON-снапшот: [{title, author, age, price, description}, ...]


class Donation(Base):
    """Пожертвования: дата, имя, карта, цена, время, статус."""
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today)
    name = Column(String(100), nullable=False)
    card = Column(String(30), nullable=False)            # только маска: **** 1234
    price = Column(Float, nullable=False)
    time = Column(DateTime, default=datetime.now)
    status = Column(String(20), default="pending")       # pending | confirmed | rejected


class Log(Base):
    """Лог: текст, время, URL, запрос, ответ."""
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(500), default="")               # например "GET → 200"
    time = Column(DateTime, default=datetime.now)
    url = Column(String(500), default="")
    request = Column(Text, default="")
    response = Column(Text, default="")
