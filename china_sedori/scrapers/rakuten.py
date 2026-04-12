"""
楽天市場 商品検索（楽天商品検索API 使用）
無料APIキー取得: https://webservice.rakuten.co.jp/
"""

import logging
import requests

logger = logging.getLogger(__name__)

API_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"


def search_rakuten(keyword: str, app_id: str, max_results: int = 5) -> list[dict]:
    """
    楽天市場でキーワード検索し、最高値・最安値・平均値を返す。

    Returns:
        list of {title, price_jpy, url, shop, source}
    """
    if not app_id or app_id == "YOUR_RAKUTEN_APP_ID":
        logger.warning("楽天 App ID が未設定のためスキップします")
        return []

    params = {
        "applicationId": app_id,
        "keyword":        keyword,
        "hits":           max_results,
        "sort":           "-itemPrice",  # 高い順
        "availability":   1,
    }

    try:
        resp = requests.get(API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("Items", [])

        results = []
        for item_wrap in items:
            item = item_wrap.get("Item", {})
            results.append({
                "title":     item.get("itemName", "")[:80],
                "price_jpy": int(item.get("itemPrice", 0)),
                "url":       item.get("itemUrl", ""),
                "shop":      item.get("shopName", ""),
                "source":    "楽天市場",
            })

        logger.info("楽天 '%s' → %d 件", keyword, len(results))
        return results

    except Exception as e:
        logger.error("楽天APIエラー: %s", e)
        return []


def get_max_price(keyword: str, app_id: str) -> int:
    """楽天市場での最高値（円）を返す"""
    items = search_rakuten(keyword, app_id, max_results=3)
    if not items:
        return 0
    return max(i["price_jpy"] for i in items)
