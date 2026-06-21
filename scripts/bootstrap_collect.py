from pathlib import Path
import sys
import logging

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import load_rules, upsert_new_products
from parser import parse_kufar_ads
from parser.filters import passes_filters
from database.db import get_session, init_db
from database.models import Product, Notification


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def mark_unnotified_as_notified(rule_name: str) -> int:
    session = get_session()

    try:
        products = (
            session.execute(
                select(Product)
                .outerjoin(Notification, Notification.product_id == Product.id)
                .where(Notification.id.is_(None))
                .where(Product.rule_name == rule_name)
                .order_by(Product.created_at.asc(), Product.id.asc())
            )
            .scalars()
            .all()
        )

        for product in products:
            session.add(
                Notification(
                    product_id=product.id,
                    rule_name=product.rule_name,
                )
            )

        session.commit()
        return len(products)

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def main():
    init_db()

    rules = load_rules()

    logger.info("Bootstrap started. Loaded rules: %s", len(rules))

    total_parsed = 0
    total_passed = 0
    total_saved_new = 0
    total_marked_notified = 0

    for rule in rules:
        name = rule.get("name", "Без имени")
        url = rule.get("categoryUrl")

        if not url:
            logger.warning("[%s] skipped: empty categoryUrl", name)
            continue

        logger.info("[%s] parsing: %s", name, url)

        try:
            items = parse_kufar_ads(url, max_pages=rule.get("maxPages"))
            filtered_items = [item for item in items if passes_filters(item, rule)]

            new_products = upsert_new_products(filtered_items, name)
            marked_notified = mark_unnotified_as_notified(name)

            total_parsed += len(items)
            total_passed += len(filtered_items)
            total_saved_new += len(new_products)
            total_marked_notified += marked_notified

            logger.info(
                "[%s] parsed=%s | passed_filters=%s | saved_new=%s | marked_notified=%s",
                name,
                len(items),
                len(filtered_items),
                len(new_products),
                marked_notified,
            )

        except Exception:
            logger.exception("[%s] bootstrap failed, moving to next rule", name)

    logger.info(
        "Bootstrap finished: parsed=%s | passed_filters=%s | saved_new=%s | marked_notified=%s",
        total_parsed,
        total_passed,
        total_saved_new,
        total_marked_notified,
    )

    print("Bootstrap завершён. Telegram ничего не отправлял.")


if __name__ == "__main__":
    main()