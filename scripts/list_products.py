from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_session
from database.models import Product


def run(limit: int = 50) -> None:
    session = get_session()
    try:
        rows = (
            session.query(Product)
            .order_by(Product.created_at.desc())
            .limit(limit)
            .all()
        )
        if not rows:
            print("Товаров в БД пока нет.")
            return

        for p in rows:
            print(
                f"id={p.id} | kufar_id={p.kufar_id} | price={p.price} | "
                f"rule={p.rule_name} | title={p.title}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    run()
