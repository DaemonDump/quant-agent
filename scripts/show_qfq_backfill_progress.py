import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.fetch_history_batch import get_token, resolve_universe


def parse_args():
    p = argparse.ArgumentParser(prog="show_qfq_backfill_progress", description="Show qfq history backfill progress")
    p.add_argument("--universe", choices=["hs300", "all", "file", "list"], default="all")
    p.add_argument("--file", type=str, default="")
    p.add_argument("--symbols", type=str, default="")
    p.add_argument("--end", type=str, default=datetime.now().strftime("%Y%m%d"))
    p.add_argument("--db", type=str, default="data/tushare/db/quant_data.db")
    p.add_argument("--state-file", type=str, default="data/tushare/state/fetch_state_qfq_all_v2.txt")
    p.add_argument("--watch", action="store_true")
    p.add_argument("--interval", type=int, default=5)
    return p.parse_args()


def read_state_count(state_file: str) -> int:
    if not state_file or not os.path.exists(state_file):
        return 0
    with open(state_file, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def load_db_stats(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT
                COUNT(1),
                COUNT(DISTINCT symbol),
                MAX(trade_date)
            FROM stock_history_data
            WHERE turnover_rate IS NOT NULL
              AND buy_lg_amount IS NOT NULL
              AND net_mf_amount IS NOT NULL
              AND net_amount_rate IS NOT NULL
              AND adj_type = 'qfq'
            """
        ).fetchone()
        return {
            "rows_with_new_fields": int(row[0] or 0),
            "symbols_with_new_fields": int(row[1] or 0),
            "latest_trade_date": row[2] or ""
        }
    finally:
        conn.close()


def render(total: int, state_count: int, stats: dict):
    db_done = stats["symbols_with_new_fields"]
    total = max(total, 1)
    state_pct = round(state_count / total * 100, 2)
    db_pct = round(db_done / total * 100, 2)
    print("=" * 64)
    print(f"补采总股票数: {total}")
    print(f"状态文件已处理: {state_count} ({state_pct}%)")
    print(f"数据库已补新字段股票数: {db_done} ({db_pct}%)")
    print(f"数据库已补新字段行数: {stats['rows_with_new_fields']}")
    print(f"最新补采交易日: {stats['latest_trade_date'] or '暂无'}")
    print(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    args = parse_args()
    token = get_token(args.db)
    if not token:
        raise RuntimeError("数据库中未找到 tushare_token")
    universe = resolve_universe(args.universe, args.file, args.symbols, token, args.end)
    total = len(universe)

    while True:
        state_count = read_state_count(args.state_file)
        stats = load_db_stats(args.db)
        render(total, state_count, stats)
        if not args.watch:
            break
        time.sleep(max(args.interval, 1))


if __name__ == "__main__":
    main()
