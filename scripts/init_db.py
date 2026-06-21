import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не найден в .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    category_name TEXT NOT NULL,
    category_url TEXT NOT NULL,
    min_price INTEGER,
    max_price INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    kufar_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    price INTEGER,
    url TEXT NOT NULL,
    location TEXT,
    created_at TIMESTAMP,
    parsed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sent_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(product_id)
);
"""

with engine.begin() as conn:
    conn.execute(text(SQL))

print("Таблицы созданы")