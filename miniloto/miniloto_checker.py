"""
ミニロト 自動照合スクリプト
毎週火曜日 20:30 以降に実行して当選番号を取得し、固定番号と照合する。
"""

import re
import time
import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ─── 固定購入番号 ────────────────────────────────────────
MY_TICKETS = [
    [1, 4, 7, 15, 23],   # 1枚目
    [1, 8, 23, 26, 27],  # 2枚目
]

# ─── 当選条件 ─────────────────────────────────────────────
# ミニロト: 31個の数字から5個選択
# 1等: 本数字5個全一致
# 2等: 本数字4個 + ボーナス数字1個
# 3等: 本数字4個一致
# 4等: 本数字3個一致

PRIZE_RULES = [
    {"rank": "1等", "main": 5, "bonus": 0},
    {"rank": "2等", "main": 4, "bonus": 1},
    {"rank": "3等", "main": 4, "bonus": 0},
    {"rank": "4等", "main": 3, "bonus": 0},
]

# ─── 取得先URL一覧（上から順に試す） ──────────────────────
SOURCES = [
    {
        "name": "宝当大師",
        "url": "https://loto.atpopular.com/2026/04/1381miniloto/",
        "pattern": r"(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})",
    },
    {
        "name": "うまさくーロト予想",
        "url": "https://blog.umasaku.com/loto/miniloto-next-20260414/",
        "pattern": r"(\d{1,2})[,\s]+(\d{1,2})[,\s]+(\d{1,2})[,\s]+(\d{1,2})[,\s]+(\d{1,2})",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ─── 当選番号取得 ─────────────────────────────────────────
def fetch_winning_numbers_requests() -> dict | None:
    """requests で当選番号を取得する（複数ソースを試す）"""
    for source in SOURCES:
        try:
            logger.info("取得試行: %s", source["name"])
            resp = requests.get(source["url"], headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                logger.warning("  → HTTP %d", resp.status_code)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(" ")

            # 回号と抽選日を探す
            round_match = re.search(r"第(\d+)回", text)
            date_match = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", text)
            round_num = round_match.group(1) if round_match else "不明"
            draw_date = date_match.group(1) if date_match else "不明"

            # 本数字5つを探す
            numbers_match = re.findall(r"\b(\d{1,2})\b", text)
            valid = [int(n) for n in numbers_match if 1 <= int(n) <= 31]

            # ボーナス数字のキーワード周辺から取得
            bonus_match = re.search(r"ボーナス[数字]*[：:\s]*(\d{1,2})", text)
            bonus = int(bonus_match.group(1)) if bonus_match else None

            # 本数字は連続して出現する5つの数字（昇順ソート）から推定
            if len(valid) >= 5:
                main = sorted(list(set(valid[:10])))[:5]
                logger.info(
                    "  → 取得成功: 第%s回 %s 本数字=%s ボーナス=%s",
                    round_num, draw_date, main, bonus
                )
                return {
                    "round": round_num,
                    "date": draw_date,
                    "main": main,
                    "bonus": bonus,
                    "source": source["name"],
                }
        except Exception as e:
            logger.warning("  → エラー: %s", e)

    return None


def fetch_winning_numbers_selenium() -> dict | None:
    """Selenium で当選番号を取得する（requests が失敗した場合のフォールバック）"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        logger.info("Selenium でみずほ銀行のページを取得中...")
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--lang=ja-JP")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        url = "https://www.mizuhobank.co.jp/takarakuji/check/loto/miniloto/index.html"
        driver.get(url)
        time.sleep(5)  # JS読み込み待ち

        body_text = driver.find_element(By.TAG_NAME, "body").text

        # 当選番号をパース
        round_match = re.search(r"第(\d+)回", body_text)
        date_match = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", body_text)
        numbers = re.findall(r"\b(\d{1,2})\b", body_text)
        valid = [int(n) for n in numbers if 1 <= int(n) <= 31]

        bonus_match = re.search(r"ボーナス[数字]*[：:\s]*(\d{1,2})", body_text)

        driver.quit()

        if len(valid) >= 5:
            return {
                "round": round_match.group(1) if round_match else "不明",
                "date": date_match.group(1) if date_match else "不明",
                "main": sorted(list(set(valid[:10])))[:5],
                "bonus": int(bonus_match.group(1)) if bonus_match else None,
                "source": "みずほ銀行（Selenium）",
            }
    except Exception as e:
        logger.error("Selenium 取得エラー: %s", e)

    return None


def get_winning_numbers() -> dict | None:
    """当選番号を取得する（requests → Selenium の順に試す）"""
    result = fetch_winning_numbers_requests()
    if result:
        return result
    logger.info("requests での取得に失敗。Selenium で再試行します...")
    return fetch_winning_numbers_selenium()


# ─── 照合処理 ─────────────────────────────────────────────
def check_prize(ticket: list[int], main: list[int], bonus: int | None) -> str:
    """チケットの等数を判定する"""
    main_hits = len(set(ticket) & set(main))
    bonus_hit = bonus is not None and bonus in ticket

    for rule in PRIZE_RULES:
        if rule["bonus"] == 0:
            if main_hits == rule["main"]:
                return rule["rank"]
        else:
            if main_hits == rule["main"] and bonus_hit:
                return rule["rank"]

    return "等外"


def display_results(result: dict):
    """照合結果を表示する"""
    print("\n" + "=" * 55)
    print(f"  ミニロト 第{result['round']}回 ({result['date']}) 照合結果")
    print("=" * 55)
    print(f"  本数字  : {' '.join(f'{n:02d}' for n in result['main'])}")
    bonus_str = f"{result['bonus']:02d}" if result['bonus'] else "不明"
    print(f"  ボーナス: {bonus_str}")
    print(f"  データ元: {result['source']}")
    print("-" * 55)

    any_win = False
    for i, ticket in enumerate(MY_TICKETS, 1):
        rank = check_prize(ticket, result["main"], result["bonus"])
        nums_str = " ".join(f"{n:02d}" for n in ticket)
        hits = set(ticket) & set(result["main"])
        hits_str = " ".join(f"{n:02d}" for n in sorted(hits)) if hits else "なし"

        icon = "🎉" if rank != "等外" else "  "
        print(f"  {icon} {i}枚目: [{nums_str}]")
        print(f"         一致数字: {hits_str}  →  【{rank}】")
        if rank != "等外":
            any_win = True

    print("-" * 55)
    if any_win:
        print("  ★ 当選があります！みずほ銀行の窓口またはATMで確認を！")
    else:
        print("  今回は残念ながら当選なしです。次回もチャレンジ！")
    print("=" * 55 + "\n")

    # ログファイルに保存
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "round": result["round"],
        "date": result["date"],
        "winning_main": result["main"],
        "winning_bonus": result["bonus"],
        "tickets": [
            {
                "no": i + 1,
                "numbers": t,
                "rank": check_prize(t, result["main"], result["bonus"]),
            }
            for i, t in enumerate(MY_TICKETS)
        ],
    }
    with open("miniloto_history.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


# ─── メイン ───────────────────────────────────────────────
def main():
    print(f"\n[{datetime.now().strftime('%Y/%m/%d %H:%M')}] ミニロト照合を開始します...")
    print("購入番号:")
    for i, ticket in enumerate(MY_TICKETS, 1):
        print(f"  {i}枚目: {ticket}")

    result = get_winning_numbers()
    if result:
        display_results(result)
    else:
        print("\n当選番号の取得に失敗しました。")
        print("少し時間をおいて再実行するか、以下のURLで手動確認してください：")
        print("  https://www.mizuhobank.co.jp/takarakuji/check/loto/miniloto/index.html\n")


if __name__ == "__main__":
    main()
