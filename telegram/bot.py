import time
from decimal import Decimal
from typing import Optional

import requests

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from telegram.formatter import format_product_message


def send_message(text: str, retries: int = 5, delay_seconds: float = 1.5) -> None:
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
                    "disable_web_page_preview": False,
                },
                timeout=20,
            )

            # Telegram возвращает 429, если бот отправляет слишком много сообщений.
            # В ответе Telegram обычно есть parameters.retry_after.
            if response.status_code == 429:
                retry_after = delay_seconds * attempt

                try:
                    data = response.json()
                    retry_after = data.get(
                        "parameters",
                        {},
                    ).get(
                        "retry_after",
                        retry_after,
                    )
                except ValueError:
                    pass

                print(f"Telegram rate limit: ждём {retry_after} секунд...")
                time.sleep(float(retry_after) + 1)
                continue

            response.raise_for_status()

            # Маленькая пауза после успешной отправки,
            # чтобы не упереться в лимиты Telegram.
            time.sleep(1.2)
            return

        except requests.RequestException as error:
            last_error = error

            if attempt < retries:
                time.sleep(delay_seconds * attempt)

    raise RuntimeError(
        f"Не удалось отправить сообщение в Telegram после {retries} попыток."
    ) from last_error


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