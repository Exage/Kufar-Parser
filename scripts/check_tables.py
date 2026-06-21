import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не найден в .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """))

    tables = [row[0] for row in result]

if not tables:
    print("Таблиц нет")
else:
    for table in tables:
        print(table)