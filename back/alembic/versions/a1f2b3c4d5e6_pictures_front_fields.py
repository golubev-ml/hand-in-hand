"""pictures: поля витрины и стартовые рисунки

Revision ID: a1f2b3c4d5e6
Revises: 843f932f5e85
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

revision = "a1f2b3c4d5e6"
down_revision = "843f932f5e85"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pictures", sa.Column("title", sa.String(200), nullable=False, server_default=""))
    op.add_column("pictures", sa.Column("author", sa.String(100), nullable=False, server_default=""))
    op.add_column("pictures", sa.Column("age", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("pictures", sa.Column("category", sa.String(50), nullable=False, server_default="painting"))
    op.add_column("pictures", sa.Column("description", sa.Text(), nullable=False, server_default=""))
    op.add_column("pictures", sa.Column("is_new", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("pictures", sa.Column("is_featured", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("pictures", sa.Column("popularity", sa.Integer(), nullable=False, server_default="0"))

    pictures = sa.table(
        "pictures",
        sa.column("image_path", sa.String),
        sa.column("history", sa.Text),
        sa.column("price", sa.Float),
        sa.column("status", sa.String),
        sa.column("title", sa.String),
        sa.column("author", sa.String),
        sa.column("age", sa.Integer),
        sa.column("category", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_new", sa.Integer),
        sa.column("is_featured", sa.Integer),
        sa.column("popularity", sa.Integer),
    )
    op.bulk_insert(pictures, [
        {"image_path": "https://images.unsplash.com/photo-1560421683-6856ea585c78?w=700&h=560&fit=crop&auto=format", "history": "Маша нарисовала этот лес после прогулки с мамой в парке. Она сказала: «Я хочу, чтобы люди тоже почувствовали этот запах травы».", "price": 2500, "status": "available", "title": "Весенний лес", "author": "Маша К.", "age": 8, "category": "painting", "description": "Акварельный пейзаж с яркими весенними красками. Маша передала настроение первых тёплых дней через нежные переходы зелёного и голубого.", "is_new": 1, "is_featured": 1, "popularity": 95},
        {"image_path": "https://images.unsplash.com/photo-1573020568125-d15af9c3e777?w=700&h=560&fit=crop&auto=format", "history": "Артём из небольшого городка в Ярославской области. Это его первый рисунок, который он решился показать другим людям. Участие в выставке изменило его.", "price": 1800, "status": "available", "title": "Мой дом", "author": "Артём С.", "age": 7, "category": "drawing", "description": "Простой и трогательный рисунок цветными карандашами. Дом, семья и солнце — главное, что важно в жизни.", "is_new": 0, "is_featured": 1, "popularity": 88},
        {"image_path": "https://images.unsplash.com/photo-1597863881769-8d8ff8ab8b2a?w=700&h=560&fit=crop&auto=format", "history": "Дима хочет стать архитектором. Он несколько месяцев учился рисовать на планшете и создал этот удивительный мир из нуля.", "price": 3500, "status": "available", "title": "Город будущего", "author": "Дима Р.", "age": 12, "category": "digital", "description": "Цифровая иллюстрация с детальным изображением фантастического города с летающими машинами и зелёными башнями.", "is_new": 1, "is_featured": 1, "popularity": 92},
        {"image_path": "https://images.unsplash.com/photo-1666710988451-ba4450498967?w=700&h=560&fit=crop&auto=format", "history": "Аня увлекается энтомологией. Она знает названия сотен бабочек и мечтает нарисовать их всех.", "price": 2200, "status": "available", "title": "Бабочка в саду", "author": "Аня Л.", "age": 9, "category": "painting", "description": "Гуашь на картоне. Яркая бабочка среди цветов — воплощение детской радости и свободы.", "is_new": 0, "is_featured": 0, "popularity": 75},
        {"image_path": "https://images.unsplash.com/photo-1510832842230-87253f48d74f?w=700&h=560&fit=crop&auto=format", "history": "Лена живёт в маленьком городке в Сибири. Снег для неё — это тишина и покой, которые она передаёт в своих работах.", "price": 3000, "status": "available", "title": "Зимний вечер", "author": "Лена В.", "age": 11, "category": "painting", "description": "Пастель на тонированной бумаге. Тихий зимний вечер, фонари и следы на снегу.", "is_new": 1, "is_featured": 0, "popularity": 81},
        {"image_path": "https://images.unsplash.com/photo-1614712201488-9942af86b87b?w=700&h=560&fit=crop&auto=format", "history": "Миша — самый младший участник нашей программы. Он рисует каждый день и хочет стать художником, «как Ван Гог».", "price": 1500, "status": "available", "title": "Радужный конь", "author": "Миша Ф.", "age": 6, "category": "drawing", "description": "Фломастеры на бумаге. Самый радостный конь на свете, нарисованный самым весёлым автором.", "is_new": 0, "is_featured": 0, "popularity": 70},
        {"image_path": "https://images.unsplash.com/photo-1597116868150-099875391584?w=700&h=560&fit=crop&auto=format", "history": "Катя говорит, что бабушка — её самый важный человек. «Я хочу, чтобы она видела себя такой, какой вижу её я».", "price": 2800, "status": "available", "title": "Портрет бабушки", "author": "Катя Н.", "age": 10, "category": "drawing", "description": "Простой карандаш, сложное чувство. Катя нарисовала портрет бабушки с такой нежностью, что он выглядит как настоящее произведение искусства.", "is_new": 0, "is_featured": 0, "popularity": 90},
        {"image_path": "https://images.unsplash.com/photo-1536221993589-9edbbca2c7fc?w=700&h=560&fit=crop&auto=format", "history": "Саша никогда не видел моря. Он создаёт его из фантазии и книг — и оно получается невероятным.", "price": 4200, "status": "available", "title": "Океан мечты", "author": "Саша П.", "age": 13, "category": "digital", "description": "Цифровая живопись с глубоким синим морем, светящимися медузами и загадочными глубинами.", "is_new": 1, "is_featured": 0, "popularity": 86},
    ])


def downgrade() -> None:
    for col in ("popularity", "is_featured", "is_new", "description", "category", "age", "author", "title"):
        op.drop_column("pictures", col)
