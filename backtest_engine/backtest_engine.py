import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
import os

logger = logging.getLogger(__name__)


class BacktestEngine:
    def __init__(self, db_path: str = None):
        if db_path is None:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(root, 'data', 'tushare', 'db', 'quant_data.db')
        self.db_path = db_path
        self.transaction_cost = 0.000085  # 万零点八五佣金
        self.stamp_duty = 0.001  # 印花税千一（仅卖出）
        self.initial_capital = 100000  # 初始资金10万
        self.conn = sqlite3.connect(self.db_path)
        logger.info(f"数据库连接已打开: {self.db_path}")

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")

    def load_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从数据库加载历史数据"""
        try:
            query = '''
                SELECT symbol, trade_date, open_price, high_price, low_price,
                       close_price, volume, amount, pe, pb,
                       turnover_rate, total_mv, circ_mv,
                       buy_lg_amount, net_mf_amount, net_amount_rate, adj_type
                FROM stock_history_data
                WHERE symbol = ? AND trade_date >= ? AND trade_date <= ?
                ORDER BY trade_date ASC
            '''
            df = pd.read_sql_query(query, self.conn, params=(symbol, start_date, end_date))
            return df
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return pd.DataFrame()
    
    def split_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """划分数据集：预热集70%（提供历史上下文）、验证集0%、测试集30%"""
        if df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        n = len(df)
        train_end = int(n * 0.7)
        
        train_df = df.iloc[:train_end].copy()
        val_df = pd.DataFrame()
        test_df = df.iloc[train_end:].copy()
        
        logger.info(f"数据划分: 预热集{len(train_df)}, 测试集{len(test_df)}")
        return train_df, val_df, test_df
    
    def calculate_returns(self, df: pd.DataFrame) -> pd.Series:
        """计算收益率"""
        df = df.copy()
        df['returns'] = df['close_price'].pct_change()
        return df['returns'].fillna(0)
    
    def calculate_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """计算绩效指标"""
        if len(returns) == 0:
            return {}
        
        returns = returns.dropna()
        
        # 总收益率
        total_return = (1 + returns).prod() - 1
        
        # 年化收益率
        trading_days = len(returns)
        annual_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 else 0
        
        # 波动率
        volatility = returns.std() * np.sqrt(252)

        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 夏普比率（年化无风险利率 3%，日化后扣除）
        risk_free_daily = 0.03 / 252
        if returns.std() > 0:
            sharpe_ratio = (returns.mean() - risk_free_daily) / returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # 胜率
        win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
        
        # 盈亏比
        avg_win = returns[returns > 0].mean() if (returns > 0).sum() > 0 else 0
        avg_loss = returns[returns < 0].mean() if (returns < 0).sum() > 0 else 0
        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        metrics = {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'volatility': volatility,
            'trading_days': trading_days
        }
        
        return metrics
    
    def run_simple_backtest(self, symbol: str, start_date: str, end_date: str) -> Dict[str, any]:
        """执行简单回测（买入持有策略）"""
        df = self.load_data(symbol, start_date, end_date)
        
        if df.empty:
            return {
                'success': False,
                'message': '无数据'
            }
        
        train_df, val_df, test_df = self.split_data(df)
        
        # 在测试集上执行买入持有策略
        if len(test_df) > 0:
            returns = self.calculate_returns(test_df)
            metrics = self.calculate_metrics(returns)

            buy_row = test_df.iloc[0]
            sell_row = test_df.iloc[-1]
            buy_price = float(buy_row['close_price'])
            sell_price = float(sell_row['close_price'])

            shares = int((self.initial_capital / buy_price) // 100) * 100
            if shares <= 0:
                return {
                    'success': False,
                    'message': '资金不足，无法按100股一手买入'
                }

            buy_amount = shares * buy_price
            buy_cost = buy_amount * self.transaction_cost
            buy_total = buy_amount + buy_cost

            sell_amount = shares * sell_price
            sell_cost = sell_amount * (self.transaction_cost + self.stamp_duty)
            sell_total = sell_amount - sell_cost

            profit = sell_total - buy_total

            trades = [
                {
                    'date': str(buy_row['trade_date']),
                    'action': 'buy',
                    'price': buy_price,
                    'hands': int(shares / 100),
                    'shares': int(shares),
                    'amount': float(buy_amount),
                    'cost': float(buy_cost)
                },
                {
                    'date': str(sell_row['trade_date']),
                    'action': 'sell',
                    'price': sell_price,
                    'hands': int(shares / 100),
                    'shares': int(shares),
                    'amount': float(sell_amount),
                    'cost': float(sell_cost),
                    'profit': float(profit)
                }
            ]
            
            return {
                'success': True,
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date,
                'train_size': len(train_df),
                'val_size': len(val_df),
                'test_size': len(test_df),
                'metrics': metrics,
                'trades': trades
            }
        else:
            return {
                'success': False,
                'message': '测试集数据不足'
            }
    
    def run_strategy_backtest(self, symbol: str, start_date: str, end_date: str,
                          strategy_func: callable, max_test_rows: Optional[int] = None,
                          single_position_limit: float = 0.2,
                          commission: float = None,
                          slippage: float = 0.001,
                          daily_trades_limit: Optional[int] = None,
                          symbol_daily_trades_limit: Optional[int] = None,
                          daily_loss_limit: Optional[float] = None,
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> Dict[str, any]:
        """执行策略回测"""
        df = self.load_data(symbol, start_date, end_date)
        
        if df.empty:
            return {
                'success': False,
                'message': '无数据'
            }
        
        train_df, val_df, test_df = self.split_data(df)
        
        # 在测试集上执行策略
        if len(test_df) > 0:
            if max_test_rows is not None and max_test_rows > 0 and len(test_df) > max_test_rows:
                test_df = test_df.iloc[-max_test_rows:].copy()
            warmup_df = train_df.copy()
            warmup_len = len(warmup_df)
            full_df = pd.concat([warmup_df, test_df], ignore_index=True)
            signals = []
            for i in range(len(test_df)):
                hist_slice = full_df.iloc[: warmup_len + i + 1]
                signals.append(strategy_func(hist_slice))
            test_df = test_df.copy()
            test_df['signal'] = signals

            effective_commission = commission if commission is not None else self.transaction_cost
            effective_stamp_duty = self.stamp_duty
            clamp_limit = max(0.0, min(1.0, single_position_limit))
            lot_size = 100

            # 初始化
            capital = self.initial_capital
            position = 0  # 持仓数量
            trades = []  # 交易记录
            equity_curve = []  # 资金曲线
            holding_days = 0
            # 用于部分卖出时的成本归集（按持仓数量等比例折算）
            cost_basis_total = 0.0

            try:
                _stop_loss_pct = abs(float(stop_loss)) if stop_loss is not None else None
                if _stop_loss_pct is not None and _stop_loss_pct <= 0:
                    _stop_loss_pct = None
            except Exception:
                _stop_loss_pct = None
            try:
                _take_profit_pct = abs(float(take_profit)) if take_profit is not None else None
                if _take_profit_pct is not None and _take_profit_pct <= 0:
                    _take_profit_pct = None
            except Exception:
                _take_profit_pct = None

            try:
                _dt_limit = int(daily_trades_limit) if daily_trades_limit is not None else None
            except Exception:
                _dt_limit = None
            try:
                _sdt_limit = int(symbol_daily_trades_limit) if symbol_daily_trades_limit is not None else None
            except Exception:
                _sdt_limit = None
            _effective_buy_limit = None
            if _dt_limit is not None and _dt_limit >= 0:
                _effective_buy_limit = _dt_limit
            if _sdt_limit is not None and _sdt_limit >= 0:
                _effective_buy_limit = _sdt_limit if _effective_buy_limit is None else min(_effective_buy_limit, _sdt_limit)
            try:
                _dl = float(daily_loss_limit) if daily_loss_limit is not None else None
                _daily_loss_abs = abs(_dl) if _dl is not None else None
                if _daily_loss_abs is not None and _daily_loss_abs <= 0:
                    _daily_loss_abs = None
            except Exception:
                _daily_loss_abs = None
            _cur_day = None
            _buy_trades_today = 0
            _start_equity_today = None
            
            # 执行策略
            for i, row in test_df.iterrows():
                price = row['close_price']
                signal = row['signal']
                
                price = float(price)
                total_assets = capital + position * price
                current_fraction = (position * price) / total_assets if total_assets > 0 else 0.0

                _day = str(row.get('trade_date'))
                if _day != _cur_day:
                    _cur_day = _day
                    _buy_trades_today = 0
                    _start_equity_today = total_assets
                _allow_buy = True
                if _effective_buy_limit is not None and _buy_trades_today >= _effective_buy_limit:
                    _allow_buy = False
                if _daily_loss_abs is not None and _start_equity_today is not None and _start_equity_today > 0:
                    _day_return = (total_assets - _start_equity_today) / _start_equity_today
                    if _day_return <= -_daily_loss_abs:
                        _allow_buy = False

                if position > 0 and cost_basis_total > 0:
                    avg_cost = cost_basis_total / position
                    pnl_pct = (price - avg_cost) / avg_cost
                    if _stop_loss_pct is not None and pnl_pct <= -_stop_loss_pct:
                        signal = 0.0
                    elif _take_profit_pct is not None and pnl_pct >= _take_profit_pct:
                        signal = 0.0

                # 允许 strategy_func 返回：
                # - 字符串: 'buy'/'sell'/'hold'（保持原行为）
                # - 数值: 目标持仓占比（0~1，表示期望市值占总资产比例）
                desired_fraction = current_fraction
                if isinstance(signal, str):
                    if signal == 'buy':
                        desired_fraction = clamp_limit
                    elif signal == 'sell':
                        desired_fraction = 0.0
                    else:  # 'hold'
                        desired_fraction = current_fraction
                elif isinstance(signal, (int, float)):
                    desired_fraction = float(signal)
                else:
                    desired_fraction = current_fraction

                desired_fraction = max(0.0, min(clamp_limit, desired_fraction))

                # 兼容旧策略：仅当字符串信号时保留“最大持有30天后清仓”逻辑
                # 数值目标仓位（机器学习调仓）完全由目标占比驱动，不额外强制清仓。
                if position > 0 and isinstance(signal, str):
                    holding_days += 1
                    if holding_days >= 30:
                        desired_fraction = 0.0

                # 根据目标占比计算目标股数（按A股一手=100股取整）
                desired_value = total_assets * desired_fraction
                desired_shares = int((desired_value / price) // lot_size) * lot_size
                desired_shares = max(0, desired_shares)

                if not _allow_buy and desired_shares > position:
                    desired_shares = position

                if desired_shares > position:
                    # 买入补到目标仓位
                    actual_buy_price = price * (1 + slippage)
                    buy_shares = desired_shares - position
                    max_affordable = int((capital / actual_buy_price) // lot_size) * lot_size
                    buy_shares = int(min(buy_shares, max_affordable))
                    if buy_shares > 0:
                        buy_amount = float(buy_shares) * actual_buy_price
                        buy_cost = buy_amount * effective_commission
                        buy_total = buy_amount + buy_cost
                        if buy_total > capital:
                            # 边界保护：由于四舍五入/滑点导致可能超买
                            affordable = int((capital / actual_buy_price) // lot_size) * lot_size
                            buy_shares = int(min(buy_shares, affordable))
                            if buy_shares <= 0:
                                buy_shares = 0
                        if buy_shares > 0:
                            buy_amount = float(buy_shares) * actual_buy_price
                            buy_cost = buy_amount * effective_commission
                            buy_total = buy_amount + buy_cost
                            capital -= buy_total
                            position += buy_shares
                            cost_basis_total += buy_total
                            holding_days = 0  # 从空仓/调整到非空仓视作重新开始持有计时
                            post_assets = capital + position * price
                            post_fraction = (position * price) / post_assets if post_assets > 0 else 0.0
                            trades.append({
                                'date': row['trade_date'],
                                'action': 'buy',
                                'price': price,
                                'hands': int(buy_shares / lot_size),
                                'shares': int(buy_shares),
                                'amount': float(buy_amount),
                                'cost': float(buy_cost),
                                'target_position': float(desired_fraction),
                                'position_after_shares': int(position),
                                'position_after_fraction': float(post_fraction)
                            })
                            _buy_trades_today += 1

                elif desired_shares < position and position > 0:
                    # 卖出补到目标仓位
                    sell_shares = position - desired_shares
                    if sell_shares > 0:
                        actual_sell_price = price * (1 - slippage)
                        # 对应旧逻辑：sell_amount 用实际成交价（含滑点）
                        sell_amount = float(sell_shares) * actual_sell_price
                        sell_cost = sell_amount * (effective_commission + effective_stamp_duty)
                        sell_total = sell_amount - sell_cost

                        # 成本归集：按卖出的份额等比例减少持仓成本
                        proportion = sell_shares / position if position > 0 else 0.0
                        cost_basis_reduce = cost_basis_total * proportion
                        profit = sell_total - float(cost_basis_reduce)

                        capital += sell_total
                        position -= sell_shares
                        cost_basis_total -= cost_basis_reduce
                        if position <= 0:
                            position = 0
                            cost_basis_total = 0.0
                            holding_days = 0
                        post_assets = capital + position * price
                        post_fraction = (position * price) / post_assets if post_assets > 0 else 0.0

                        trades.append({
                            'date': row['trade_date'],
                            'action': 'sell',
                            'price': price,
                            'hands': int(sell_shares / lot_size),
                            'shares': int(sell_shares),
                            'amount': float(sell_amount),
                            'cost': float(sell_cost),
                            'profit': float(profit),
                            'target_position': float(desired_fraction),
                            'position_after_shares': int(position),
                            'position_after_fraction': float(post_fraction)
                        })
                
                # 记录资金曲线
                current_value = capital + position * price
                equity_curve.append({
                    'date': row['trade_date'],
                    'value': current_value
                })
            
            # 计算绩效
            equity_df = pd.DataFrame(equity_curve)
            if len(equity_df) > 1:
                equity_df['returns'] = equity_df['value'].pct_change()
                returns = equity_df['returns'].fillna(0)
                metrics = self.calculate_metrics(returns)
                
                return {
                    'success': True,
                    'symbol': symbol,
                    'start_date': start_date,
                    'end_date': end_date,
                    'train_size': len(train_df),
                    'val_size': len(val_df),
                    'test_size': len(test_df),
                    'metrics': metrics,
                    'trades': trades,
                    'equity_curve': equity_curve,
                    'price_series': [
                        {'date': str(d), 'close': float(c)}
                        for d, c in zip(
                            test_df['trade_date'].tolist(),
                            test_df['close_price'].tolist()
                        )
                    ]
                }
            else:
                return {
                    'success': False,
                    'message': '数据不足'
                }
        else:
            return {
                'success': False,
                'message': '测试集数据不足'
            }
    
    def calculate_attribution(self, trades: List[Dict]) -> Dict[str, any]:
        """归因分析"""
        if not trades:
            return {}
        
        sell_trades = [t for t in trades if t['action'] == 'sell']
        
        if not sell_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit': 0,
                'total_loss': 0,
                'net_profit': 0,
                'avg_profit_per_trade': 0
            }

        total_trades = len(sell_trades)
        winning_trades = sum(1 for t in sell_trades if t.get('profit', 0) > 0)
        losing_trades = total_trades - winning_trades
        
        total_profit = sum(t.get('profit', 0) for t in sell_trades if t.get('profit', 0) > 0)
        total_loss = sum(t.get('profit', 0) for t in sell_trades if t.get('profit', 0) < 0)
        
        attribution = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': total_profit + total_loss,
            'avg_profit_per_trade': (total_profit + total_loss) / total_trades if total_trades > 0 else 0
        }
        
        return attribution
