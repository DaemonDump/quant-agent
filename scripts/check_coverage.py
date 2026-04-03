import os
import sys
import argparse
from datetime import datetime
import sqlite3
import csv

import tushare as ts

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from app.db import get_setting


def parse_args():
    p = argparse.ArgumentParser(prog="check_coverage", description="Check local DB coverage and export report")
    p.add_argument("--universe", choices=["hs300", "all", "file", "list", "db"], default="hs300")
    p.add_argument("--file", type=str, default="")
    p.add_argument("--symbols", type=str, default="")
    p.add_argument("--start", type=str, required=True, help="YYYYMMDD")
    p.add_argument("--end", type=str, required=True, help="YYYYMMDD")
    p.add_argument("--db", type=str, default="data/tushare/db/quant_data.db")
    p.add_argument("--output", type=str, default="")
    return p.parse_args()


def get_token(db_path: str) -> str:
    app = Flask("check_coverage")
    app.config["DATABASE"] = db_path
    with app.app_context():
        return get_setting("tushare_token")


def resolve_universe(universe: str, file_path: str, symbols: str, token: str, db_path: str):
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
    if universe == "db":
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM stock_history_data")
        items = [row[0] for row in cur.fetchall()]
        conn.close()
        return items
    token = token or ""
    pro = ts.pro_api(token) if token else None
    if universe == "hs300":
        if not pro:
            raise RuntimeError("tushare token missing for hs300 universe")
        try:
            df = pro.index_weight(index_code="000300.SH")
            codes = sorted(df["con_code"].dropna().unique().tolist())
            return codes
        except Exception:
            df = pro.index_weight(index_code="000300.SH")
            codes = sorted(df["con_code"].dropna().unique().tolist())
            return codes
    if universe == "all":
        if not pro:
            raise RuntimeError("tushare token missing for all universe")
        df = pro.stock_basic(exchange="", list_status="L", fields="ts_code")
        return sorted(df["ts_code"].dropna().unique().tolist())
    raise RuntimeError("unknown universe")


def ensure_reports_path(path: str) -> str:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    return path


def main():
    args = parse_args()
    token = None
    if args.universe in ("hs300", "all"):
        token = get_token(args.db)
    syms = resolve_universe(args.universe, args.file, args.symbols, token, args.db)
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(DISTINCT trade_date) FROM stock_history_data WHERE trade_date BETWEEN ? AND ?",
        (args.start, args.end),
    )
    total_days_row = cur.fetchone()
    total_days = int(total_days_row[0] or 0)
    if total_days == 0:
        print("no baseline trading days in DB for window; coverage ratio will be 0/NA")

    rows = []
    full, partial, missing = 0, 0, 0
    for s in syms:
        cur.execute(
            "SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM stock_history_data WHERE symbol=?",
            (s,),
        )
        r = cur.fetchone()
        min_d, max_d, cnt_all = r if r else (None, None, 0)
        cur.execute(
            "SELECT COUNT(*) FROM stock_history_data WHERE symbol=? AND trade_date BETWEEN ? AND ?",
            (s, args.start, args.end),
        )
        cnt_win = int(cur.fetchone()[0] or 0)
        ratio = (cnt_win / total_days) if total_days > 0 else 0.0
        if cnt_win == 0:
            status = "missing"
            missing += 1
        elif min_d and min_d <= args.start and max_d and max_d >= args.end and cnt_win >= total_days * 0.95:
            status = "full"
            full += 1
        else:
            status = "partial"
            partial += 1
        rows.append([s, min_d or "", max_d or "", cnt_all, cnt_win, args.start, args.end, f"{ratio:.3f}", status])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_csv = args.output or os.path.join("data", "tushare", "reports", f"coverage_{args.universe}_{args.start}_{args.end}_{timestamp}.csv")
    out_csv = ensure_reports_path(out_csv)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "min_date", "max_date", "rows_total", "rows_in_window", "window_start", "window_end", "coverage_ratio", "status"])
        w.writerows(rows)

    out_md = out_csv.replace(".csv", ".md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(f"# 覆盖率统计报告\n\n")
        f.write(f"- 标的集合：{args.universe}\n")
        f.write(f"- 时间窗口：{args.start} ~ {args.end}\n")
        f.write(f"- 基线交易日数（DB）：{total_days}\n")
        f.write(f"- 统计时间：{timestamp}\n\n")
        f.write(f"## 汇总\n\n")
        f.write(f"- 完整覆盖：{full}\n")
        f.write(f"- 部分覆盖：{partial}\n")
        f.write(f"- 缺失：{missing}\n\n")
        f.write(f"## 明细\n\n")
        f.write(f"见 CSV 明细：{out_csv}\n")

    conn.close()
    print(f"report written: {out_csv}")
    print(f"summary: full={full}, partial={partial}, missing={missing}, baseline_days={total_days}")


if __name__ == "__main__":
    main()
