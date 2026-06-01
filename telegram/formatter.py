from decimal import Decimal, InvalidOperation
from typing import Optional, Union


def _format_price(price: Optional[Union[Decimal, float, int]]) -> str:
    if price is None:
        return "Не указана"
    try:
        amount = Decimal(str(price))
        if amount == amount.to_integral():
            formatted = f"{int(amount):,}".replace(",", " ")
        else:
            formatted = format(amount.normalize(), "f").rstrip("0").rstrip(".")
        return f"{formatted} BYN"
    except (InvalidOperation, ValueError):
        return f"{price} BYN"


def format_product_message(
    title: str,
    price: Optional[Union[Decimal, float, int]],
    url: str,
    rule_name: str,
) -> str:
    return (
        "Новое объявление на Kufar\n\n"
        f"Категория: {rule_name}\n"
        f"Название: {title}\n"
        f"Цена: {_format_price(price)}\n\n"
        f"Ссылка:\n{url}"
    )
