#!/bin/bash
# ミニロト 毎週火曜日 20:35 自動実行スクリプト
# cron設定例: 35 20 * * 2 /bin/bash /path/to/run_tuesday.sh

cd "$(dirname "$0")"
echo "[$(date '+%Y/%m/%d %H:%M')] ミニロト照合を開始します..."
python3 miniloto_checker.py
