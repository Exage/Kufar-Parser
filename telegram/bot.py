from decimal import Decimal
from typing import Optional

import requests
import time

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from telegram.formatter import format_product_message


def send_message(text: str, retries: int = 3, delay_seconds: float = 1.5) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы в переменных окружения."
        )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                url,
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": text,
                },
                timeout=20,
            )
            response.raise_for_status()
            return
        except requests.RequestException as error:
            last_error = error
            if attempt < retries:
                time.sleep(delay_seconds * attempt)

    raise RuntimeError(f"Не удалось отправить сообщение в Telegram после {retries} попыток.") from last_error


def send_product_notification(
    title: str,
    price: Optional[Decimal],
    url: str,
    rule_name: str,
) -> None:
    message = format_product_message(
        title=title,
        price=price,
        url=url,
        rule_name=rule_name,
    )
    send_message(message)
