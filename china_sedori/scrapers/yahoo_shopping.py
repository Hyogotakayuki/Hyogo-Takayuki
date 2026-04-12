"""
Yahoo!ショッピング 商品検索（Yahoo! Shopping API 使用）
無料APIキー取得: https://developer.yahoo.co.jp/start/
"""

import logging
import requests

logger = logging.getLogger(__name__)

API_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"


def search_yahoo(keyword: str, app_id: str, max_results: int = 5) -> list[dict]:
    """
    Yahoo!ショッピングでキーワード検索。

    Returns:
        list of {title, price_jpy, url, shop, source}
    """
    if not app_id or app_id == "YOUR_YAHOO_CLIENT_ID":
        logger.warning("Yahoo App ID が未設定のためスキップします")
        return []

    params = {
        "appid":   app_id,
        "query":   keyword,
        "results": max_results,
        "sort":    "-price",
    }

    try:
        resp = requests.get(API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("hits", [])

        results = []
        for item in items:
            results.append({
                "title":     item.get("name", "")[:80],
                "price_jpy": int(item.get("price", 0)),
                "url":       item.get("url", ""),
                "shop":      item.get("seller", {}).get("name", ""),
                "source":    "Yahoo!ショッピング",
            })

        logger.info("Yahoo! '%s' → %d 件", keyword, len(results))
        return results

    except Exception as e:
        logger.error("Yahoo!APIエラー: %s", e)
        return []


def get_max_price(keyword: str, app_id: str) -> int:
    items = search_yahoo(keyword, app_id, max_results=3)
    if not items:
        return 0
    return max(i["price_jpy"] for i in items)
