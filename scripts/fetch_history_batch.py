import os
import sys
import argparse
import time
from datetime import datetime

import tushare as ts

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from app.db import get_setting
from data_ingestion.data_collector import RealTimeDataCollector


def parse_args():
    p = argparse.ArgumentParser(prog="fetch_history_batch", description="Batch fetch history data into SQLite")
    p.add_argument("--universe", choices=["hs300", "all", "file", "list"], default="hs300")
    p.add_argument("--file", type=str, default="")
    p.add_argument("--symbols", type=str, default="")
    p.add_argument("--start", type=str, default="20220101")
    p.add_argument("--end", type=str, default=datetime.now().strftime("%Y%m%d"))
    p.add_argument("--db", type=str, default="data/tushare/db/quant_data.db")
    p.add_argument("--sleep", type=float, default=0.2)
    p.add_argument("--batch-size", type=int, default=500)
    p.add_argument("--state-file", type=str, default="data/tushare/state/fetch_state.txt")
    p.add_argument("--log-file", type=str, default="BATCH_INGEST_DOCUMENTATION.md")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def get_token(db_path: str) -> str:
    app = Flask("fetch_history_batch")
    app.config["DATABASE"] = db_path
    with app.app_context():
        return get_setting("tushare_token")


def resolve_universe(universe: str, file_path: str, symbols: str, token: str, end_date: str):
    if universe == "file":
        if not file_path or not os.path.exists(file_path):
            raise RuntimeError("file not found for universe=file")
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    if universe == "list":
        parts = [s.strip() for s in symbols.split(",") if s.strip()]
        if not parts:
            raise RuntimeError("symbols is empty for universe=list")
        return parts
    pro = ts.pro_api(token)
    if universe == "hs300":
        trade_date = end_date
        try:
            df = pro.index_weight(index_code="000300.SH", trade_date=trade_date)
            codes = sorted(df["con_code"].dropna().unique().tolist())
            return codes
        except Exception:
            df = pro.index_weight(index_code="000300.SH")
            codes = sorted(df["con_code"].dropna().unique().tolist())
            return codes
    if universe == "all":
        df = pro.stock_basic(exchange="", list_status="L", fields="ts_code")
        return sorted(df["ts_code"].dropna().unique().tolist())
    raise RuntimeError("unknown universe")


def main():
    args = parse_args()
    start_ts = time.time()
    token = get_token(args.db)
    if not token:
        print("no tushare token found in settings")
        sys.exit(1)

    symbols = resolve_universe(args.universe, args.file, args.symbols, token, args.end)
    # 断点续传：读取已完成列表
    done_set = set()
    if args.state_file and os.path.exists(args.state_file):
        try:
            with open(args.state_file, "r", encoding="utf-8") as f:
                done_set = set([line.strip() for line in f if line.strip()])
        except Exception:
            done_set = set()
    symbols = [s for s in symbols if s not in done_set]
    total = len(symbols)
    print(f"universe size: {total}")

    if args.dry_run:
        for i, s in enumerate(symbols[:10], 1):
            print(f"[{i}/{total}] {s}")
        print("dry-run only, exit")
        return

    collector = RealTimeDataCollector(args.db)
    collector.set_token(token)

    fetched = 0
    for i, s in enumerate(symbols, 1):
        try:
            df = collector.collect_history_data(s, args.start, args.end)
            ok = df is not None and not df.empty
            fetched += 1 if ok else 0
            print(f"[{i}/{total}] {s} -> {'OK' if ok else 'NO DATA'}")
            # 记录断点
            if args.state_file:
                os.makedirs(os.path.dirname(args.state_file), exist_ok=True)
                with open(args.state_file, "a", encoding="utf-8") as f:
                    f.write(s + "\n")
        except Exception as e:
            print(f"[{i}/{total}] {s} -> ERROR {e}")
        if args.sleep > 0:
            time.sleep(args.sleep)
        if args.batch_size > 0 and i % args.batch_size == 0:
            time.sleep(2.0)
    print(f"done. fetched OK: {fetched}/{total}")

    if not args.dry_run and args.log_file:
        try:
            ts_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            elapsed = int(time.time() - start_ts)
            with open(args.log_file, "a", encoding="utf-8") as lf:
                lf.write(f"\n### {ts_str}\n")
                lf.write(f"- 执行方式：fetch_history_batch.py\n")
                lf.write(f"- 参数：universe={args.universe}, start={args.start}, end={args.end}, db={args.db}, sleep={args.sleep}, batch_size={args.batch_size}\n")
                lf.write(f"- 结果：fetched_ok={fetched}/total={total}, 用时={elapsed}s\n")
        except Exception as e:
            print(f"append log failed: {e}")


if __name__ == "__main__":
    main()
