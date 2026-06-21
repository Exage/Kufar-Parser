from pathlib import Path
import sys

from sqlalchemy import func, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_session
from database.models import Product, Notification


def main():
    session = get_session()

    try:
        products_count = session.execute(
            select(func.count(Product.id))
        ).scalar_one()

        notifications_count = session.execute(
            select(func.count(Notification.id))
        ).scalar_one()

        print(f"products: {products_count}")
        print(f"notifications: {notifications_count}")

    finally:
        session.close()


if __name__ == "__main__":
    main()