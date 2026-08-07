from datetime import datetime, date as date_type

from pydantic import BaseModel, ConfigDict, Field


# ---------- Менеджеры ----------
class ManagerCreate(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class ManagerStatusUpdate(BaseModel):
    status: str  # active | blocked


class ManagerOut(BaseModel):
    id: int
    login: str
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Рисунки ----------
class PictureCreate(BaseModel):
    image_path: str
    history: str = ""
    time: datetime | None = None
    price: float = Field(default=0.0, ge=0)
    status: str = "available"


class PictureUpdate(BaseModel):
    image_path: str | None = None
    history: str | None = None
    time: datetime | None = None
    price: float | None = Field(default=None, ge=0)
    status: str | None = None


class PictureOut(BaseModel):
    id: int
    image_path: str
    history: str
    time: datetime
    price: float
    status: str
    model_config = ConfigDict(from_attributes=True)


# ---------- Пожертвования ----------
class OrderItem(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    img: str
    story: str = ""
    price: float = Field(ge=0)
    qty: int = Field(default=1, ge=1)


class OrderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    items: list[OrderItem] = Field(min_length=1)


class DonationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    card: str = Field(min_length=12, max_length=25)
    price: float = Field(gt=0)
    date: date_type | None = None


class DonationStatusUpdate(BaseModel):
    status: str  # pending | confirmed | rejected


class DonationOut(BaseModel):
    id: int
    date: date_type
    name: str
    card: str
    price: float
    time: datetime
    status: str
    model_config = ConfigDict(from_attributes=True)


# ---------- Лог ----------
class LogOut(BaseModel):
    id: int
    text: str
    time: datetime
    url: str
    request: str
    response: str
    model_config = ConfigDict(from_attributes=True)
