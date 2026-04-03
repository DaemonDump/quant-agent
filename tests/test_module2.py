import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_ingestion import init_database, add_monitored_symbol, remove_monitored_symbol, get_monitored_symbols
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestModule2(unittest.TestCase):
    def setUp(self):
        self.db_path = 'test_quant_data_module2.db'
        init_database(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_and_get_monitored_symbols(self):
        add_monitored_symbol(self.db_path, '000001.SZ', '平安银行')
        add_monitored_symbol(self.db_path, '000002.SZ', '万科A')
        symbols = get_monitored_symbols(self.db_path)
        self.assertEqual(len(symbols), 2)
        codes = [s['symbol'] for s in symbols]
        self.assertIn('000001.SZ', codes)
        self.assertIn('000002.SZ', codes)

    def test_remove_monitored_symbol(self):
        add_monitored_symbol(self.db_path, '600000.SH', '浦发银行')
        symbols_before = get_monitored_symbols(self.db_path)
        self.assertEqual(len(symbols_before), 1)
        remove_monitored_symbol(self.db_path, '600000.SH')
        symbols_after = get_monitored_symbols(self.db_path)
        self.assertEqual(len(symbols_after), 0)

    def test_duplicate_symbol_not_added_twice(self):
        add_monitored_symbol(self.db_path, '000001.SZ', '平安银行')
        add_monitored_symbol(self.db_path, '000001.SZ', '平安银行')
        symbols = get_monitored_symbols(self.db_path)
        self.assertEqual(len(symbols), 1)

if __name__ == '__main__':
    unittest.main()
