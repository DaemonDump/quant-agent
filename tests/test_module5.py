import unittest
import sys
import os
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest_engine import BacktestEngine, ParameterOptimizer, RiskTester, OverfittingChecker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestModule5(unittest.TestCase):
    def setUp(self):
        self.db_path = 'test_quant_data.db'
        self.symbol = '000001.SZ'
        self.start_date = '20230101'
        self.end_date = '20231231'
        self.engine = BacktestEngine(self.db_path)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
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
        base = datetime(2023, 1, 1)
        for i in range(100):
            trade_date = (base + timedelta(days=i)).strftime('%Y%m%d')
            cursor.execute('''
                INSERT OR IGNORE INTO stock_history_data
                    (symbol, trade_date, open_price, high_price, low_price,
                     close_price, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.symbol, trade_date,
                  100 + i, 102 + i, 99 + i, 100 + i,
                  1000000, 100000000))
        conn.commit()
        conn.close()

    def tearDown(self):
        self.engine.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_backtest_engine(self):
        result = self.engine.run_simple_backtest(self.symbol, self.start_date, self.end_date)
        self.assertTrue(result.get('success'), msg=result.get('message'))

    def test_parameter_optimizer(self):
        optimizer = ParameterOptimizer(self.engine)
        param_grid = {
            'valuation_weight': [0.2, 0.3],
            'trend_weight': [0.3, 0.4],
            'fund_weight': [0.3, 0.4]
        }

        def evaluate_fn(params):
            return self.engine.run_simple_backtest(self.symbol, self.start_date, self.end_date)

        result = optimizer.grid_search(evaluate_fn, param_grid, metric='sharpe_ratio')
        self.assertIsNotNone(result.get('best_params'))

if __name__ == '__main__':
    unittest.main()
