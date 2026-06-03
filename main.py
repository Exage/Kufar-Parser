import json
import logging
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytz
from sqlalchemy import select
from apscheduler.schedulers.blocking import BlockingScheduler

from config.settings import DATABASE_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, POLL_INTERVAL_MINUTES
from database.db import get_session, init_db
from database.models import Notification, Product
from parser import parse_kufar_ads
from parser.filters import passes_filters
from telegram import send_product_notification
from telegram.bot import send_message


CONFIG_PATH = Path(__file__).resolve().parent / "config" / "categories.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def load_rules(path: Path = CONFIG_PATH) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def upsert_new_products(items: List[Dict[str, Any]], rule_name: str) -> List[Dict[str, Any]]:
    if not items:
        return []

    session = get_session()
    created_products: List[Product] = []

    try:
        kufar_ids = [item["kufar_id"] for item in items]

        existing = set(
            session.execute(
                select(Product.kufar_id).where(Product.kufar_id.in_(kufar_ids))
            ).scalars()
        )

        for item in items:
            kufar_id = item["kufar_id"]

            if kufar_id in existing:
                continue

            product = Product(
                kufar_id=kufar_id,
                title=item.get("title") or "Без названия",
                price=item.get("price"),
                url=item["url"],
                rule_name=rule_name,
            )

            session.add(product)
            created_products.append(product)
            existing.add(kufar_id)

        session.flush()

        created_data = [
            {
                "id": product.id,
                "title": product.title,
                "price": product.price,
                "url": product.url,
                "rule_name": product.rule_name,
            }
            for product in created_products
        ]

        session.commit()
        return created_data

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def get_unnotified_products(rule_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Возвращает товары, которые есть в таблице products,
    но для которых ещё нет записи в таблице notifications.

    Это нужно для ситуации:
    1. товар сохранился в БД;
    2. Telegram дал 429 Too Many Requests;
    3. уведомление не записалось;
    4. при следующем запуске товар надо попробовать отправить повторно.
    """

    session = get_session()

    try:
        query = (
            select(Product)
            .outerjoin(Notification, Notification.product_id == Product.id)
            .where(Notification.id.is_(None))
            .order_by(Product.created_at.asc(), Product.id.asc())
        )

        if rule_name:
            query = query.where(Product.rule_name == rule_name)

        products = session.execute(query).scalars().all()

        return [
            {
                "id": product.id,
                "title": product.title,
                "price": product.price,
                "url": product.url,
                "rule_name": product.rule_name,
            }
            for product in products
        ]

    finally:
        session.close()


def send_notifications_for_products(products: List[Dict[str, Any]]) -> int:
    if not products:
        return 0

    session = get_session()
    sent_count = 0

    try:
        product_ids = [product["id"] for product in products]

        notified_product_ids = set(
            session.execute(
                select(Notification.product_id).where(Notification.product_id.in_(product_ids))
            ).scalars()
        )

        for product in products:
            if product["id"] in notified_product_ids:
                continue

            send_product_notification(
                title=product["title"],
                price=product["price"],
                url=product["url"],
                rule_name=product["rule_name"],
            )

            session.add(
                Notification(
                    product_id=product["id"],
                    rule_name=product["rule_name"],
                )
            )

            session.commit()

            notified_product_ids.add(product["id"])
            sent_count += 1

        return sent_count

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def run() -> None:
    init_db()
    rules = load_rules()

    logger.info("Loaded rules: %s", len(rules))

    for rule in rules:
        name = rule.get("name", "Без имени")
        url = rule.get("categoryUrl")

        if not url:
            logger.warning("[%s] skipped: empty categoryUrl", name)
            continue

        try:
            logger.info("[%s] parsing: %s", name, url)

            items = parse_kufar_ads(url, max_pages=rule.get("maxPages"))
            filtered_items = [item for item in items if passes_filters(item, rule)]
            new_products = upsert_new_products(filtered_items, name)

            # ВАЖНО:
            # Отправляем не только товары, которые появились в текущем запуске.
            # Отправляем все товары этой категории, которые есть в products,
            # но ещё не имеют записи в notifications.
            #
            # Это исправляет проблему, когда товар уже записался в БД,
            # но Telegram не принял сообщение из-за лимита 429.
            products_to_notify = get_unnotified_products(rule_name=name)
            notified_count = send_notifications_for_products(products_to_notify)

            logger.info(
                "[%s] parsed=%s | passed_filters=%s | saved_new=%s | pending_notifications=%s | notified=%s",
                name,
                len(items),
                len(filtered_items),
                len(new_products),
                len(products_to_notify),
                notified_count,
            )

        except Exception:
            logger.exception("[%s] failed, moving to next rule", name)


def validate_env() -> None:
    missing: List[str] = []

    if not DATABASE_URL:
        missing.append("DATABASE_URL")

    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")

    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        raise RuntimeError(
            f"Не заданы обязательные переменные окружения: {', '.join(missing)}"
        )

    if not DATABASE_URL.startswith(("postgresql://", "mysql://", "sqlite:///")):
        raise RuntimeError(
            "DATABASE_URL должен начинаться с postgresql://, mysql:// или sqlite:///"
        )

    if ":" not in TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN выглядит невалидным: ожидается формат <id>:<token>"
        )

    if not str(TELEGRAM_CHAT_ID).lstrip("-").isdigit():
        raise RuntimeError(
            "TELEGRAM_CHAT_ID должен быть числом, например -1001234567890"
        )


def run_scheduler() -> None:
    scheduler = BlockingScheduler(timezone=pytz.UTC)

    scheduler.add_job(
        run,
        "interval",
        minutes=POLL_INTERVAL_MINUTES,
        max_instances=1,
        coalesce=True,
    )

    logger.info("Scheduler started: every %s minute(s)", POLL_INTERVAL_MINUTES)

    run()
    scheduler.start()


if __name__ == "__main__":
    try:
        validate_env()

        if "--schedule" in sys.argv:
            run_scheduler()
        else:
            run()

    except Exception as error:
        logger.exception("Программа упала с необработанной ошибкой.")

        try:
            error_text = "".join(
                traceback.format_exception(
                    type(error),
                    error,
                    error.__traceback__,
                )
            )

            send_message(
                "🚨 ПРИЛОЖЕНИЕ УПАЛО.\n"
                "Программа упала с ошибкой:\n"
                f"{error}\n\n"
                f"{error_text[:2500]}"
            )

        except Exception:
            logger.exception("Не удалось отправить аварийное сообщение в Telegram.")

        raise