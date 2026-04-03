import json
import sqlite3
import pandas as pd
from app.routes.backtest import run_simple_backtest
from app import create_app

app = create_app()
with app.app_context():
    with app.test_request_context(json={
        'symbol': '000001.SZ',
        'start_date': '20230101',
        'end_date': '20240101',
        'commission_rate': 0.003,
        'slippage': 0.001,
        'initial_capital': 100000,
        'max_position': 100
    }):
        resp = run_simple_backtest()
        data = json.loads(resp.get_data(as_text=True))
        if data.get('success'):
            trades = data.get('trades', [])
            print(f"Total trades: {len(trades)}")
            if trades:
                total_cost = sum(t.get('cost', 0) for t in trades)
                print(f"Total friction cost: {total_cost:.2f}")
                print(f"Final return: {data.get('total_return', 0)*100:.2f}%")
                
                # 打印前 5 笔交易看看频率
                for i, t in enumerate(trades[:5]):
                    print(f"Trade {i}: {t['date']} {t['action']} shares={t.get('shares')} target={t.get('target_position', 0):.2f}")
        else:
            print(data)
