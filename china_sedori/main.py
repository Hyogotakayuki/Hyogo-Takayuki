"""
中国せどり 価格差リサーチツール
AliExpress の商品を日本マーケット（Amazon・楽天・Yahoo・メルカリ）の
高値と比較し、利益が出る商品をCSVスプレッドシートに出力する。

使い方:
  pip install -r requirements.txt
  python main.py

設定:
  config.json を編集してキーワード・APIキー・フィルター条件を調整
"""

import json
import logging
import os
import time
from datetime import datetime

import pandas as pd

from calculator import calc_total_cost, find_best_platform
from scrapers.aliexpress import search_aliexpress
from scrapers.rakuten import get_max_price as rakuten_max
from scrapers.yahoo_shopping import get_max_price as yahoo_max
from scrapers.mercari import get_max_price as mercari_max
from scrapers.amazon_jp import get_max_price as amazon_max

# ─── 設定読み込み ────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# ─── ログ設定 ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("sedori_research.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ─── 定数 ────────────────────────────────────────────────
RATE        = CONFIG["exchange_rate"]["CNY_to_JPY"]
COSTS       = CONFIG["costs"]
FEES        = CONFIG["platform_fees"]
FILTERS     = CONFIG["filters"]
APIS        = CONFIG["apis"]
OUTPUT_PATH = CONFIG["output"]["csv_path"]
MAX_RESULTS = CONFIG["output"]["max_results_per_keyword"]


def research_keyword(keyword: str) -> list[dict]:
    """1キーワードについて AliExpress を仕入れ先として調査する"""
    logger.info("=" * 60)
    logger.info("キーワード: 【%s】", keyword)

    # ─── AliExpress 仕入れ価格取得 ──────────────────────
    ali_items = search_aliexpress(keyword, max_results=MAX_RESULTS)
    if not ali_items:
        logger.warning("  AliExpress: 商品が取得できませんでした")
        return []

    rows = []

    for item in ali_items:
        price_cny = item["price_cny"]
        if price_cny > CONFIG["filters"]["max_china_price_cny"]:
            continue

        # ─── 総仕入れコスト計算 ────────────────────────
        total_cost = calc_total_cost(
            price_cny=price_cny,
            exchange_rate=RATE,
            shipping_china_jpy=COSTS["shipping_from_china_jpy"],
            import_duty_rate=COSTS["import_duty_rate"],
            domestic_ship_jpy=COSTS["domestic_shipping_jpy"],
        )

        # ─── 日本各プラットフォームの最高値取得 ──────────
        logger.info("  商品: %s (%.0f元 / 仕入れ %d円)", item["title"], price_cny, total_cost)

        prices = {}
        prices["amazon"]  = amazon_max(item["title"])
        prices["rakuten"] = rakuten_max(item["title"], APIS["rakuten_app_id"])
        prices["yahoo"]   = yahoo_max(item["title"], APIS["yahoo_app_id"])
        prices["mercari"] = mercari_max(item["title"])

        logger.info(
            "    市場価格 → Amazon:%d 楽天:%d Yahoo:%d メルカリ:%d",
            prices["amazon"], prices["rakuten"], prices["yahoo"], prices["mercari"]
        )

        # ─── 最適プラットフォームで利益計算 ───────────────
        best = find_best_platform(total_cost, prices, FEES)
        if best is None:
            continue

        # ─── フィルター適用 ───────────────────────────────
        if best.profit_jpy < FILTERS["min_profit_jpy"]:
            logger.info("    → 利益 %d円（フィルター未満）", best.profit_jpy)
            continue
        if best.roi_pct < FILTERS["min_roi_pct"]:
            logger.info("    → ROI %.1f%%（フィルター未満）", best.roi_pct)
            continue

        row = {
            "商品名（AliExpress）":  item["title"],
            "仕入れ価格（元）":       price_cny,
            "仕入れ価格（円換算）":   int(price_cny * RATE),
            "総仕入れコスト（円）":   total_cost,
            "Amazon最高値（円）":    prices["amazon"],
            "楽天最高値（円）":       prices["rakuten"],
            "Yahoo最高値（円）":     prices["yahoo"],
            "メルカリ最高値（円）":   prices["mercari"],
            "最適販売先":            best.platform,
            "推奨販売価格（円）":     best.sell_price_jpy,
            "純利益（円）":           best.profit_jpy,
            "ROI（%）":              best.roi_pct,
            "AliExpress販売数":      item.get("sales_count", 0),
            "AliExpress URL":        item.get("url", ""),
            "検索キーワード":         keyword,
            "調査日時":              datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        rows.append(row)
        logger.info(
            "    ✓ 追加 → %s販売 利益%d円 ROI%.1f%%",
            best.platform, best.profit_jpy, best.roi_pct
        )

        time.sleep(1)  # サーバー負荷軽減

    return rows


def main():
    logger.info("中国せどり リサーチ開始")
    all_rows = []

    for keyword in CONFIG["keywords"]:
        rows = research_keyword(keyword)
        all_rows.extend(rows)
        time.sleep(3)

    if not all_rows:
        logger.warning("条件に合う商品が見つかりませんでした。フィルター条件を緩めてください。")
        return

    # ─── CSV出力 ─────────────────────────────────────────
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df = pd.DataFrame(all_rows)
    df = df.sort_values("ROI（%）", ascending=False)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    # ─── Excel出力（任意） ──────────────────────────────
    excel_path = OUTPUT_PATH.replace(".csv", ".xlsx")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="せどりリスト")
        ws = writer.sheets["せどりリスト"]

        # 列幅自動調整
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    # ─── サマリー表示 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("  中国せどり リサーチ結果")
    print("=" * 60)
    print(f"  条件適合商品数: {len(df)} 件")
    if len(df) > 0:
        print(f"  最高ROI: {df['ROI（%）'].max():.1f}%")
        print(f"  最高純利益: {df['純利益（円）'].max():,} 円")
        print(f"\n  TOP 5 商品（ROI順）:")
        for _, row in df.head(5).iterrows():
            print(
                f"    [{row['ROI（%）']:.0f}%] {row['商品名（AliExpress）'][:30]} "
                f"→ {row['最適販売先']} {row['純利益（円）']:,}円利益"
            )
    print(f"\n  CSV保存: {OUTPUT_PATH}")
    print(f"  Excel保存: {excel_path}")
    print("=" * 60 + "\n")

    logger.info("完了 → %s", OUTPUT_PATH)


if __name__ == "__main__":
    main()
