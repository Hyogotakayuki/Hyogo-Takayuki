"""
AliExpress 商品検索スクレーパー
Selenium で検索結果ページから商品名・価格・URLを取得する
"""

import time
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.aliexpress.com/wholesale?SearchText={keyword}&SortType=total_tranpro_desc"


def get_driver(headless: bool = True) -> webdriver.Chrome:
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ja-JP,ja")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def search_aliexpress(keyword: str, max_results: int = 20, headless: bool = True) -> list[dict]:
    """
    AliExpress でキーワード検索し、商品リストを返す。

    Returns:
        list of {title, price_cny, url, image_url, sales_count}
    """
    driver = get_driver(headless=headless)
    results = []

    try:
        url = SEARCH_URL.format(keyword=keyword.replace(" ", "+"))
        logger.info("AliExpress 検索: %s", keyword)
        driver.get(url)
        time.sleep(5)  # JS読み込み待ち

        # 商品カードを取得
        card_selectors = [
            "[class*='product-snippet']",
            "[class*='list--gallery--']",
            "a[href*='/item/']",
        ]

        cards = []
        for sel in card_selectors:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                break

        logger.info("  → %d 件のカードを取得", len(cards))

        for card in cards[:max_results]:
            try:
                item = _extract_card(card)
                if item:
                    results.append(item)
            except Exception as e:
                logger.debug("カード抽出エラー: %s", e)

    except TimeoutException:
        logger.error("AliExpress タイムアウト")
    finally:
        driver.quit()

    return results


def _extract_card(card) -> dict | None:
    """カード要素から商品情報を抽出する"""
    try:
        # タイトル
        title = ""
        for sel in ["[class*='title']", "h1", "h3", "span"]:
            try:
                title = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                if title and len(title) > 3:
                    break
            except NoSuchElementException:
                pass

        # 価格（元）
        price_cny = None
        for sel in ["[class*='price']", "[class*='Price']"]:
            try:
                price_text = card.find_element(By.CSS_SELECTOR, sel).text
                nums = re.findall(r"[\d,.]+", price_text.replace(",", "."))
                if nums:
                    price_cny = float(nums[0])
                    break
            except (NoSuchElementException, ValueError):
                pass

        # URL
        url = None
        try:
            url = card.get_attribute("href")
            if not url:
                url = card.find_element(By.TAG_NAME, "a").get_attribute("href")
        except NoSuchElementException:
            pass

        # 販売数
        sales = 0
        try:
            sales_text = card.find_element(
                By.CSS_SELECTOR, "[class*='sold'], [class*='trade']"
            ).text
            sales_nums = re.findall(r"\d+", sales_text.replace(",", ""))
            sales = int(sales_nums[0]) if sales_nums else 0
        except NoSuchElementException:
            pass

        if not title or not price_cny:
            return None

        return {
            "title":       title[:80],
            "price_cny":   round(price_cny, 2),
            "url":         url or "",
            "sales_count": sales,
            "source":      "AliExpress",
        }

    except Exception as e:
        logger.debug("_extract_card エラー: %s", e)
        return None
