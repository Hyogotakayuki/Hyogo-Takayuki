"""
Amazon.co.jp 商品検索スクレーパー
Selenium で検索結果から価格を取得する
"""

import logging
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.amazon.co.jp/s?k={keyword}&s=price-desc-rank"


def _get_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ja-JP")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def search_amazon(keyword: str, max_results: int = 5) -> list[dict]:
    """
    Amazon.co.jp でキーワード検索（高い順）。

    Returns:
        list of {title, price_jpy, url, source}
    """
    driver = _get_driver()
    results = []

    try:
        url = SEARCH_URL.format(keyword=keyword.replace(" ", "+"))
        logger.info("Amazon 検索: %s", keyword)
        driver.get(url)
        time.sleep(4)

        # 商品カードを取得
        cards = driver.find_elements(
            By.CSS_SELECTOR,
            "[data-component-type='s-search-result']"
        )
        logger.info("  → %d 件のカードを取得", len(cards))

        for card in cards[:max_results]:
            try:
                # タイトル
                title_el = card.find_element(
                    By.CSS_SELECTOR, "h2 span, [class*='a-size-medium']"
                )
                title = title_el.text.strip()

                # 価格（整数部）
                price_jpy = 0
                for price_sel in [
                    ".a-price-whole",
                    "[class*='price-whole']",
                    ".a-offscreen",
                ]:
                    try:
                        price_text = card.find_element(
                            By.CSS_SELECTOR, price_sel
                        ).text.replace(",", "").replace(".", "").replace("￥", "")
                        nums = re.findall(r"\d+", price_text)
                        if nums:
                            price_jpy = int(nums[0])
                            break
                    except NoSuchElementException:
                        pass

                # URL
                item_url = ""
                try:
                    link = card.find_element(By.CSS_SELECTOR, "h2 a, a[class*='s-link']")
                    item_url = link.get_attribute("href") or ""
                except NoSuchElementException:
                    pass

                if title and price_jpy > 0:
                    results.append({
                        "title":     title[:80],
                        "price_jpy": price_jpy,
                        "url":       item_url,
                        "shop":      "Amazon.co.jp",
                        "source":    "Amazon",
                    })

            except Exception as e:
                logger.debug("Amazon カード抽出エラー: %s", e)

    except Exception as e:
        logger.error("Amazon 検索エラー: %s", e)
    finally:
        driver.quit()

    return results


def get_max_price(keyword: str) -> int:
    items = search_amazon(keyword, max_results=3)
    if not items:
        return 0
    return max(i["price_jpy"] for i in items)
