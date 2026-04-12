"""
メルカリ 商品検索スクレーパー（公開検索ページ）
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = "https://jp.mercari.com/search?keyword={keyword}&status=on_sale&sort=price&order=desc"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9",
}


def search_mercari_selenium(keyword: str, max_results: int = 5) -> list[dict]:
    """Selenium でメルカリを検索する（JS動的ページ対応）"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--lang=ja-JP")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        url = SEARCH_URL.format(keyword=keyword.replace(" ", "+"))
        driver.get(url)
        time.sleep(5)

        results = []
        items = driver.find_elements(
            By.CSS_SELECTOR,
            "[data-testid='item-cell'], [class*='item-cell'], li[class*='merList']"
        )
        logger.info("メルカリ '%s' → %d 件", keyword, len(items))

        for item in items[:max_results]:
            try:
                title_el = item.find_element(
                    By.CSS_SELECTOR, "[class*='itemName'], [class*='item-name'], span"
                )
                title = title_el.text.strip()

                price_el = item.find_element(
                    By.CSS_SELECTOR, "[class*='price'], [class*='Price']"
                )
                price_text = re.sub(r"[^\d]", "", price_el.text)
                price_jpy = int(price_text) if price_text else 0

                link_el = item.find_element(By.TAG_NAME, "a")
                url_item = link_el.get_attribute("href") or ""

                if title and price_jpy > 0:
                    results.append({
                        "title":     title[:80],
                        "price_jpy": price_jpy,
                        "url":       url_item,
                        "shop":      "メルカリ出品者",
                        "source":    "メルカリ",
                    })
            except Exception:
                pass

        driver.quit()
        return results

    except Exception as e:
        logger.error("メルカリ Selenium エラー: %s", e)
        return []


def get_max_price(keyword: str) -> int:
    items = search_mercari_selenium(keyword, max_results=3)
    if not items:
        return 0
    return max(i["price_jpy"] for i in items)
