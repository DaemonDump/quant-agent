import sqlite3
import logging

logger = logging.getLogger(__name__)


def _migrate_history_columns(cursor):
    """为已存在的 stock_history_data 表补充缺失列"""
    cursor.execute("PRAGMA table_info(stock_history_data)")
    existing = {row[1] for row in cursor.fetchall()}
    new_cols = {
        'pre_close': 'REAL',
        'change_pct': 'REAL',
        'pe': 'REAL',
        'pb': 'REAL',
        'turnover_rate': 'REAL',
        'total_mv': 'REAL',
        'circ_mv': 'REAL',
        'buy_lg_amount': 'REAL',
        'net_mf_amount': 'REAL',
        'net_amount_rate': 'REAL',
        'adj_type': 'TEXT',
    }
    for col, col_type in new_cols.items():
        if col not in existing:
            cursor.execute(f'ALTER TABLE stock_history_data ADD COLUMN {col} {col_type}')
            logger.info(f"stock_history_data 补充列: {col}")


def init_database(db_path: str = 'quant_data.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_realtime_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            price REAL NOT NULL,
            volume REAL NOT NULL,
            amount REAL NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timestamp)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_history_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            pre_close REAL,
            change_pct REAL,
            volume REAL,
            amount REAL,
            pe REAL,
            pb REAL,
            turnover_rate REAL,
            total_mv REAL,
            circ_mv REAL,
            buy_lg_amount REAL,
            net_mf_amount REAL,
            net_amount_rate REAL,
            adj_type TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, trade_date)
        )
    ''')
    
    _migrate_history_columns(cursor)
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitored_symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            symbol_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_realtime_symbol ON stock_realtime_data(symbol)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_realtime_timestamp ON stock_realtime_data(timestamp)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_history_symbol ON stock_history_data(symbol)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_history_date ON stock_history_data(trade_date)
    ''')
    
    conn.commit()
    conn.close()
    logger.info("数据库表结构初始化完成")


def add_monitored_symbol(db_path: str, symbol: str, symbol_name: str = None):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO monitored_symbols (symbol, symbol_name, is_active)
            VALUES (?, ?, 1)
        ''', (symbol, symbol_name))
        
        conn.commit()
        conn.close()
        logger.info(f"添加监控标的: {symbol}")
        return True
    except Exception as e:
        logger.error(f"添加监控标的失败: {e}")
        return False


def remove_monitored_symbol(db_path: str, symbol: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE monitored_symbols SET is_active = 0 WHERE symbol = ?
        ''', (symbol,))
        
        conn.commit()
        conn.close()
        logger.info(f"移除监控标的: {symbol}")
        return True
    except Exception as e:
        logger.error(f"移除监控标的失败: {e}")
        return False


def get_monitored_symbols(db_path: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, symbol_name FROM monitored_symbols WHERE is_active = 1
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [{'symbol': row[0], 'name': row[1]} for row in results]
    except Exception as e:
        logger.error(f"获取监控标的失败: {e}")
        return []


if __name__ == '__main__':
    import os
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _db = os.path.join(_root, 'data', 'tushare', 'db', 'quant_data.db')
    init_database(_db)
    
    add_monitored_symbol(_db, '000001.SZ', '平安银行')
    add_monitored_symbol(_db, '000002.SZ', '万科A')
    add_monitored_symbol(_db, '600000.SH', '浦发银行')
    
    symbols = get_monitored_symbols(_db)
    logger.info(f"当前监控标的: {symbols}")
