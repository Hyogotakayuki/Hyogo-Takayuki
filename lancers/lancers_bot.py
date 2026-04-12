"""
Lancers 自動化ボット
仕事（タスク）の検索・受注・完了を自動化するスクリプト
"""

import json
import logging
import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


# ─── 設定読み込み ────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# ─── ログ設定 ─────────────────────────────────────────────
log_level = getattr(logging, CONFIG["logging"]["level"], logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["logging"]["file"], encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ─── 定数 ────────────────────────────────────────────────
BASE_URL = "https://www.lancers.jp"
LOGIN_URL = f"{BASE_URL}/login"
TASK_LIST_URL = f"{BASE_URL}/work/search/task"
WAIT_TIMEOUT = 15


class LancersBot:
    """Lancers 自動化ボットのメインクラス"""

    def __init__(self):
        self.driver = self._init_driver()
        self.wait = WebDriverWait(self.driver, WAIT_TIMEOUT)
        self.applied_tasks = []
        self.completed_tasks = []

    # ─── ブラウザ初期化 ──────────────────────────────────
    def _init_driver(self) -> webdriver.Chrome:
        options = Options()
        if CONFIG["browser"]["headless"]:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--user-agent={CONFIG['browser']['user_agent']}")
        options.add_argument("--lang=ja-JP")
        options.add_argument("--window-size=1280,800")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("ブラウザを起動しました")
        return driver

    # ─── ログイン ─────────────────────────────────────────
    def login(self) -> bool:
        """Lancers にログインする"""
        try:
            logger.info("ログインを試みています...")
            self.driver.get(LOGIN_URL)
            time.sleep(2)

            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "LoginEmail"))
            )
            email_field.clear()
            email_field.send_keys(CONFIG["credentials"]["email"])

            password_field = self.driver.find_element(By.ID, "LoginPassword")
            password_field.clear()
            password_field.send_keys(CONFIG["credentials"]["password"])

            login_button = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"
            )
            login_button.click()

            # ログイン成功の確認（マイページへリダイレクト）
            self.wait.until(EC.url_changes(LOGIN_URL))
            if "login" not in self.driver.current_url:
                logger.info("ログイン成功: %s", self.driver.current_url)
                return True
            else:
                logger.error("ログイン失敗: メールアドレスまたはパスワードを確認してください")
                return False

        except TimeoutException:
            logger.error("ログインページの読み込みがタイムアウトしました")
            return False

    # ─── タスク検索 ───────────────────────────────────────
    def search_tasks(self) -> list[dict]:
        """条件に合うタスクを検索して一覧を返す"""
        tasks = []
        search_cfg = CONFIG["search"]

        for keyword in search_cfg["keywords"]:
            logger.info("キーワード '%s' でタスクを検索中...", keyword)
            url = (
                f"{TASK_LIST_URL}"
                f"?keyword={keyword}"
                f"&price_from={search_cfg['min_reward']}"
                f"&price_to={search_cfg['max_reward']}"
                f"&sort=new"
            )
            self.driver.get(url)
            time.sleep(2)

            try:
                task_cards = self.driver.find_elements(
                    By.CSS_SELECTOR, ".p-list-job__item, .work-list__item, [class*='job-item']"
                )
                logger.info("  → %d 件のタスクが見つかりました", len(task_cards))

                for card in task_cards:
                    task_info = self._extract_task_info(card)
                    if task_info and task_info not in tasks:
                        tasks.append(task_info)

            except NoSuchElementException:
                logger.warning("タスク一覧の取得に失敗しました（セレクタを確認してください）")

        logger.info("合計 %d 件のタスクを取得しました", len(tasks))
        return tasks

    def _extract_task_info(self, card_element) -> dict | None:
        """タスクカードから情報を抽出する"""
        try:
            title_el = card_element.find_element(
                By.CSS_SELECTOR, "h3, .work-title, [class*='title']"
            )
            title = title_el.text.strip()

            try:
                link_el = card_element.find_element(By.CSS_SELECTOR, "a[href*='/work/detail']")
                url = link_el.get_attribute("href")
            except NoSuchElementException:
                try:
                    url = card_element.find_element(By.TAG_NAME, "a").get_attribute("href")
                except NoSuchElementException:
                    url = None

            try:
                reward_el = card_element.find_element(
                    By.CSS_SELECTOR, ".price, [class*='price'], [class*='reward']"
                )
                reward_text = reward_el.text.strip().replace(",", "").replace("円", "")
                reward = int("".join(filter(str.isdigit, reward_text))) if reward_text else 0
            except (NoSuchElementException, ValueError):
                reward = 0

            return {"title": title, "url": url, "reward": reward, "applied": False}

        except (NoSuchElementException, Exception) as e:
            logger.debug("タスク情報の抽出に失敗: %s", e)
            return None

    # ─── タスク受注（応募） ───────────────────────────────
    def apply_for_task(self, task: dict) -> bool:
        """タスクに応募（受注）する"""
        if not task.get("url"):
            return False

        try:
            logger.info("タスクに応募中: %s", task["title"])
            self.driver.get(task["url"])
            time.sleep(2)

            # 「受注する」「応募する」ボタンを探す
            apply_selectors = [
                "button[class*='apply']",
                "a[class*='apply']",
                "button[class*='order']",
                "a[class*='order']",
                "//button[contains(text(), '受注')]",
                "//a[contains(text(), '受注')]",
                "//button[contains(text(), '応募')]",
                "//a[contains(text(), '応募')]",
            ]

            apply_button = None
            for selector in apply_selectors:
                try:
                    if selector.startswith("//"):
                        apply_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        apply_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue

            if apply_button is None:
                logger.warning("  → 応募ボタンが見つかりませんでした: %s", task["title"])
                return False

            apply_button.click()
            time.sleep(2)

            # 確認ダイアログがある場合
            try:
                confirm_button = self.driver.find_element(
                    By.XPATH, "//button[contains(text(), '確認') or contains(text(), 'OK')]"
                )
                confirm_button.click()
                time.sleep(1)
            except (NoSuchElementException, ElementClickInterceptedException):
                pass

            task["applied"] = True
            self.applied_tasks.append(task)
            logger.info("  → 応募完了: %s (報酬: %d円)", task["title"], task["reward"])

            if CONFIG["task_completion"]["screenshot_on_complete"]:
                self._take_screenshot(f"applied_{len(self.applied_tasks)}")

            return True

        except Exception as e:
            logger.error("  → 応募中にエラーが発生しました: %s", e)
            return False

    # ─── タスク完了 ───────────────────────────────────────
    def complete_task(self, task: dict) -> bool:
        """受注済みタスクを完了する（タスク種別ごとに処理）"""
        if not task.get("url"):
            return False

        logger.info("タスクを完了処理中: %s", task["title"])
        self.driver.get(task["url"])
        time.sleep(2)

        # タスクの種別を判定して処理
        page_text = self.driver.find_element(By.TAG_NAME, "body").text

        success = False
        if "アンケート" in page_text or "質問" in page_text:
            success = self._complete_survey_task()
        elif "データ入力" in page_text or "入力" in page_text:
            success = self._complete_data_entry_task()
        elif "検索" in page_text or "リサーチ" in page_text:
            success = self._complete_research_task()
        else:
            success = self._complete_generic_task()

        if success:
            self.completed_tasks.append(task)
            logger.info("  → タスク完了: %s", task["title"])

        return success

    def _complete_survey_task(self) -> bool:
        """アンケートタスクを完了する"""
        try:
            # ラジオボタンを最初の選択肢で選択
            radio_buttons = self.driver.find_elements(
                By.CSS_SELECTOR, "input[type='radio']"
            )
            answered = set()
            for radio in radio_buttons:
                name = radio.get_attribute("name")
                if name and name not in answered:
                    try:
                        radio.click()
                        answered.add(name)
                        time.sleep(0.3)
                    except Exception:
                        pass

            # テキストエリアがあれば入力
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            for textarea in textareas:
                if not textarea.get_attribute("value"):
                    textarea.send_keys("ご回答ありがとうございます。")
                    time.sleep(0.3)

            return self._submit_task()

        except Exception as e:
            logger.error("アンケートタスク処理エラー: %s", e)
            return False

    def _complete_data_entry_task(self) -> bool:
        """データ入力タスクを完了する"""
        try:
            text_inputs = self.driver.find_elements(
                By.CSS_SELECTOR, "input[type='text']:not([readonly])"
            )
            for inp in text_inputs:
                if not inp.get_attribute("value"):
                    placeholder = inp.get_attribute("placeholder") or ""
                    inp.send_keys(placeholder if placeholder else "入力済み")
                    time.sleep(0.2)

            return self._submit_task()

        except Exception as e:
            logger.error("データ入力タスク処理エラー: %s", e)
            return False

    def _complete_research_task(self) -> bool:
        """リサーチ・調査タスクを完了する"""
        try:
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            for textarea in textareas:
                if not textarea.get_attribute("value"):
                    textarea.send_keys("調査が完了しました。詳細はご確認ください。")
                    time.sleep(0.3)

            return self._submit_task()

        except Exception as e:
            logger.error("リサーチタスク処理エラー: %s", e)
            return False

    def _complete_generic_task(self) -> bool:
        """汎用タスク完了処理"""
        logger.info("  → 汎用タスク完了処理を実行")
        return self._submit_task()

    def _submit_task(self) -> bool:
        """タスク送信ボタンをクリックする"""
        submit_selectors = [
            "//button[contains(text(), '送信')]",
            "//button[contains(text(), '完了')]",
            "//button[contains(text(), '提出')]",
            "//input[@type='submit']",
            "button[type='submit']",
        ]

        for selector in submit_selectors:
            try:
                if selector.startswith("//"):
                    btn = self.driver.find_element(By.XPATH, selector)
                else:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                time.sleep(2)
                logger.info("  → 送信ボタンをクリックしました")
                return True
            except (NoSuchElementException, ElementClickInterceptedException):
                continue

        logger.warning("  → 送信ボタンが見つかりませんでした")
        return False

    # ─── ユーティリティ ───────────────────────────────────
    def _take_screenshot(self, name: str):
        """スクリーンショットを保存する"""
        os.makedirs("screenshots", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"screenshots/{timestamp}_{name}.png"
        self.driver.save_screenshot(path)
        logger.debug("スクリーンショット保存: %s", path)

    def print_summary(self):
        """実行結果のサマリーを表示する"""
        print("\n" + "=" * 50)
        print("  Lancers ボット 実行サマリー")
        print("=" * 50)
        print(f"  応募済みタスク数 : {len(self.applied_tasks)} 件")
        print(f"  完了タスク数     : {len(self.completed_tasks)} 件")
        total_reward = sum(t.get("reward", 0) for t in self.completed_tasks)
        print(f"  獲得報酬（見込み）: {total_reward:,} 円")
        print("=" * 50)
        if self.applied_tasks:
            print("\n応募したタスク:")
            for t in self.applied_tasks:
                mark = "✓" if t in self.completed_tasks else "→"
                print(f"  {mark} {t['title']} ({t['reward']:,}円)")
        print()

    def close(self):
        """ブラウザを閉じる"""
        if self.driver:
            self.driver.quit()
            logger.info("ブラウザを閉じました")


# ─── メイン処理 ───────────────────────────────────────────
def main():
    logger.info("=" * 50)
    logger.info("Lancers ボット 開始")
    logger.info("=" * 50)

    bot = LancersBot()
    max_applications = CONFIG["search"]["max_applications_per_run"]
    wait_seconds = CONFIG["task_completion"]["wait_seconds_between_tasks"]

    try:
        # 1. ログイン
        if not bot.login():
            logger.error("ログインに失敗したため処理を中断します")
            return

        # 2. タスク検索
        tasks = bot.search_tasks()
        if not tasks:
            logger.info("応募可能なタスクが見つかりませんでした")
            return

        # 3. 応募 & 完了処理
        applied_count = 0
        for task in tasks:
            if applied_count >= max_applications:
                logger.info("最大応募数 (%d件) に達しました", max_applications)
                break

            if bot.apply_for_task(task):
                applied_count += 1
                time.sleep(wait_seconds)

                # 応募直後にタスク完了を試みる
                if CONFIG["task_completion"]["auto_submit"]:
                    bot.complete_task(task)
                    time.sleep(wait_seconds)

        # 4. サマリー表示
        bot.print_summary()

    except KeyboardInterrupt:
        logger.info("ユーザーによって中断されました")
    except Exception as e:
        logger.exception("予期しないエラーが発生しました: %s", e)
    finally:
        bot.close()


if __name__ == "__main__":
    main()
