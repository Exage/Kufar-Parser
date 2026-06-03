from typing import Any, Dict, Iterable, List


def normalize_text(value: Any) -> str:
    """Нормализует текст для стабильного сравнения названий."""
    if value is None:
        return ""
    return " ".join(str(value).casefold().replace("ё", "е").split())


def normalize_keywords(values: Iterable[Any]) -> List[str]:
    return [keyword for keyword in (normalize_text(value) for value in values) if keyword]


def contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def passes_filters(item: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    title = normalize_text(item.get("title"))
    price = item.get("price")

    min_price = rule.get("minPrice", -1)
    max_price = rule.get("maxPrice", -1)

    # titleKeywords — явный фильтр по названию товара.
    # keywords оставлен как старое имя того же include-фильтра для совместимости.
    title_keywords = normalize_keywords(rule.get("titleKeywords") or rule.get("keywords") or [])
    exclude_keywords = normalize_keywords(rule.get("excludeKeywords") or [])
    title_exclude_keywords = normalize_keywords(rule.get("titleExcludeKeywords") or [])

    price_filter_enabled = (
        (min_price is not None and min_price >= 0)
        or (max_price is not None and max_price >= 0)
    )

    # Если в правиле задан фильтр цены, объявления без цены лучше не отправлять:
    # иначе в Telegram попадут товары, которые невозможно проверить по бюджету.
    if price is None and price_filter_enabled:
        return False

    # -1 означает "фильтр цены отключен".
    if price is not None:
        if min_price is not None and min_price >= 0 and price < min_price:
            return False
        if max_price is not None and max_price >= 0 and price > max_price:
            return False

    # Если указан titleKeywords/keywords, в названии должен быть хотя бы один вариант.
    if title_keywords and not contains_any(title, title_keywords):
        return False

    # excludeKeywords — общие стоп-слова, titleExcludeKeywords — точечные исключения модели.
    if exclude_keywords and contains_any(title, exclude_keywords):
        return False
    if title_exclude_keywords and contains_any(title, title_exclude_keywords):
        return False

    return True
