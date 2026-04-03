DROP TABLE IF EXISTS settings;
DROP TABLE IF EXISTS positions;
DROP TABLE IF EXISTS trade_records;
DROP TABLE IF EXISTS strategy_status;
DROP TABLE IF EXISTS stock_realtime_data;
DROP TABLE IF EXISTS stock_history_data;
DROP TABLE IF EXISTS monitored_symbols;

CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT
);

CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    name TEXT,
    quantity INTEGER DEFAULT 0,
    avg_price REAL DEFAULT 0.0,
    current_price REAL DEFAULT 0.0,
    market_value REAL DEFAULT 0.0,
    profit_loss REAL DEFAULT 0.0,
    profit_loss_pct REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trade_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    amount REAL NOT NULL,
    fee REAL DEFAULT 0.0,
    trade_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE strategy_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    is_running INTEGER DEFAULT 0,
    active_positions INTEGER DEFAULT 0,
    daily_pnl REAL DEFAULT 0.0,
    total_pnl REAL DEFAULT 0.0,
    signals_today INTEGER DEFAULT 0,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stock_realtime_data (
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
);

CREATE TABLE stock_history_data (
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
);

CREATE TABLE monitored_symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    symbol_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

CREATE INDEX idx_realtime_symbol ON stock_realtime_data(symbol);
CREATE INDEX idx_realtime_timestamp ON stock_realtime_data(timestamp);
CREATE INDEX idx_history_symbol ON stock_history_data(symbol);
CREATE INDEX idx_history_date ON stock_history_data(trade_date);
