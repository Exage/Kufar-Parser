import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


NEXT_PAGE_TESTID = "generalist-pagination-next-link"
AD_TESTID = "kufar-ad"
KUFAR_ID_RE = re.compile(r"/item/(\d+)")


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.split()).strip()


def _extract_price(card: BeautifulSoup) -> Optional[float]:
    price_block = card.select_one("div.styles_price_block__Ql9um")
    if not price_block:
        return None

    # Берем самую актуальную цену: сначала скидочную (если есть), иначе обычную.
    preferred = price_block.select_one("span.styles_price__vIwzP")
    fallback = price_block.select_one("p.styles_price__aVxZc span")
    raw_price = _clean_text((preferred or fallback).get_text()) if (preferred or fallback) else ""
    if not raw_price:
        return None

    normalized = (
        raw_price.replace("\xa0", "")
        .replace("р.", "")
        .replace("р", "")
        .replace(",", ".")
        .replace(" ", "")
        .strip()
    )
    match = re.search(r"\d+(?:\.\d+)?", normalized)
    if not match:
        return None
    return float(match.group(0))


def _parse_page(html: str, page_url: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    cards = soup.find_all("a", attrs={"data-testid": AD_TESTID})
    items: List[Dict] = []

    for card in cards:
        href = card.get("href")
        if not href:
            continue

        absolute_url = urljoin(page_url, href)
        kufar_id_match = KUFAR_ID_RE.search(absolute_url)
        if not kufar_id_match:
            continue

        title = _clean_text(card.select_one("h3.styles_title__F3uIe").get_text() if card.select_one("h3.styles_title__F3uIe") else "")
        location = _clean_text(card.select_one("p.styles_region__qCRbf").get_text() if card.select_one("p.styles_region__qCRbf") else "")
        published_at = _clean_text(card.select_one("div.styles_secondary__MzdEb span").get_text() if card.select_one("div.styles_secondary__MzdEb span") else "")
        price = _extract_price(card)

        items.append(
            {
                "kufar_id": kufar_id_match.group(1),
                "title": title,
                "price": price,
                "url": absolute_url,
                "location": location,
                "published_at": published_at,
            }
        )

    return items


def _find_next_page_url(html: str, page_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    next_link = soup.find("a", attrs={"data-testid": NEXT_PAGE_TESTID})

    # Если это disabled span (или нет href), считаем что страниц больше нет.
    if not next_link:
        return None

    href = next_link.get("href")
    if not href:
        return None

    return urljoin(page_url, href)


def parse_kufar_ads(start_url: str, max_pages: Optional[int] = None, timeout: int = 20) -> List[Dict]:
    """
    Парсит объявления Kufar, переходя по неклассической пагинации.

    Переход на следующую страницу выполняется только если найден
    <a data-testid="generalist-pagination-next-link" href="...">.
    Если элемент следующей страницы не ссылка (например disabled <span>),
    парсинг останавливается.
    """
    session = requests.Session()
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        }
    )

    current_url = start_url
    visited_urls = set()
    all_items: List[Dict] = []
    page_count = 0

    while current_url and current_url not in visited_urls:
        if max_pages is not None and page_count >= max_pages:
            break

        visited_urls.add(current_url)
        response = session.get(current_url, timeout=timeout)
        response.raise_for_status()

        html = response.text
        all_items.extend(_parse_page(html, current_url))

        current_url = _find_next_page_url(html, current_url)
        page_count += 1

    return all_items
