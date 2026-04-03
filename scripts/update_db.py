import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

def add_columns(db_path: str = None):
    if db_path is None:
        db_path = Config.DATABASE
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    new_cols = {
        'pe': 'REAL',
        'pb': 'REAL',
        'turnover_rate': 'REAL',
        'total_mv': 'REAL',
        'circ_mv': 'REAL',
        'buy_lg_amount': 'REAL',
        'net_mf_amount': 'REAL',
        'net_amount_rate': 'REAL',
        'adj_type': 'TEXT',
        'pre_close': 'REAL',
        'change_pct': 'REAL',
    }

    cursor.execute("PRAGMA table_info(stock_history_data)")
    existing = {row[1] for row in cursor.fetchall()}

    for col, col_type in new_cols.items():
        if col not in existing:
            try:
                cursor.execute(f"ALTER TABLE stock_history_data ADD COLUMN {col} {col_type}")
                print(f"Added column: {col}")
            except sqlite3.OperationalError as e:
                print(f"Skipped {col}: {e}")
        else:
            print(f"Column already exists: {col}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_columns()
