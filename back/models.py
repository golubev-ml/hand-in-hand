from datetime import datetime, date

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Date

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
    """Рисунки: путь картинки, история, время, цена, статус."""
    __tablename__ = "pictures"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String(500), nullable=False)     # например /uploads/abc.jpg
    history = Column(Text, default="")
    time = Column(DateTime, default=datetime.now)
    price = Column(Float, default=0.0)
    status = Column(String(20), default="available")     # available | sold | archive


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