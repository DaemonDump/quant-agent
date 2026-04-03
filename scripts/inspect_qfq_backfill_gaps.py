import os
import sys
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scripts.fetch_history_batch import get_token, resolve_universe


def main():
    db_path = r"data/tushare/db/quant_data.db"
    out_path = r"data/tushare/state/inspect_qfq_backfill_gaps_report.txt"
    token = get_token(db_path)
    universe = resolve_universe("all", "", "", token, "20260330")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT symbol,
                   COUNT(1) AS total_rows,
                   SUM(CASE WHEN turnover_rate IS NOT NULL
                             AND buy_lg_amount IS NOT NULL
                             AND net_mf_amount IS NOT NULL
                             AND net_amount_rate IS NOT NULL
                             AND adj_type = 'qfq'
                       THEN 1 ELSE 0 END) AS complete_rows,
                   MIN(trade_date) AS min_date,
                   MAX(trade_date) AS max_date
            FROM stock_history_data
            WHERE trade_date >= '20220101' AND trade_date <= '20260330'
            GROUP BY symbol
            """
        ).fetchall()
        db_map = {row["symbol"]: dict(row) for row in rows}

        missing_symbols = []
        partial_symbols = []
        for symbol in universe:
            info = db_map.get(symbol)
            if not info:
                missing_symbols.append(symbol)
                continue
            if int(info["complete_rows"] or 0) == 0:
                partial_symbols.append({
                    "symbol": symbol,
                    "total_rows": int(info["total_rows"] or 0),
                    "min_date": info["min_date"],
                    "max_date": info["max_date"],
                    "complete_rows": int(info["complete_rows"] or 0)
                })

        lines = [
            f"全市场股票数: {len(universe)}",
            f"数据库有区间记录股票数: {len(db_map)}",
            f"完全没有记录的股票数: {len(missing_symbols)}",
            f"有记录但新字段完整行数为0的股票数: {len(partial_symbols)}",
            f"前20只无记录股票: {missing_symbols[:20]}",
            "前20只有记录但未形成完整新字段行的股票:"
        ]
        for row in partial_symbols[:20]:
            lines.append(str(row))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(out_path)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
