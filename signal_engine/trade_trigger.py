import pandas as pd
import numpy as np
from typing import Dict, Any, List
from app.utils import logger


class TradeTrigger:
    def __init__(self, position_limits: Dict[str, Any] = None, targets: Dict[str, float] = None, risk_preference: float = 0.5):
        if position_limits is None:
            self.position_limits = {
                'single_max': 0.1,
                'total_max': 0.8,
                'daily_trades': 10,
                'weekly_trades': 50,
                'symbol_daily_trades': 2
            }
        else:
            self.position_limits = position_limits
        
        if targets is None:
            self.targets = {
                'annual_return': 0.20,
                'max_drawdown': 0.10,
                'single_loss': 0.05,
                'daily_loss': 0.02
            }
        else:
            self.targets = targets
        self.risk_preference = max(0.0, min(1.0, float(risk_preference or 0.5)))
        
        self.trade_records = []
        logger.info(f"交易触发器初始化完成，仓位限制: {self.position_limits}, 目标: {self.targets}")
    
    def check_buy_trigger(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]], 
                       current_price: float, available_capital: float) -> Dict[str, Any]:
        if signal is None or signal['signal'] != 'buy':
            return {
                'triggered': False,
                'reason': '非买入信号',
                'action': 'none'
            }
        
        try:
            checks = {}
            
            position_check = self._check_position_limits(current_positions, current_price, available_capital)
            checks['position'] = position_check
            
            trade_count_check = self._check_trade_count('buy')
            checks['trade_count'] = trade_count_check
            
            risk_check = self._check_risk_limits(current_price, available_capital)
            checks['risk'] = risk_check
            
            triggered = all([
                position_check['passed'],
                trade_count_check['passed'],
                risk_check['passed']
            ])
            
            if triggered:
                action = 'buy'
                reason = '所有买入条件满足'
                suggested_quantity = self._calculate_buy_quantity(signal, current_price, available_capital)
                if suggested_quantity <= 0:
                    triggered = False
                    action = 'hold'
                    reason = '风险偏好与信号强度较低，建议暂不买入'
                    suggested_price_range = None
                else:
                    suggested_price_range = self._get_suggested_price_range(current_price, 'buy')
            else:
                action = 'hold'
                reason = self._get_block_reason(checks)
                suggested_quantity = 0
                suggested_price_range = None
            
            result = {
                'triggered': triggered,
                'action': action,
                'reason': reason,
                'checks': checks,
                'suggested_quantity': suggested_quantity,
                'suggested_price_range': suggested_price_range,
                'current_price': current_price,
                'available_capital': available_capital,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
            if triggered:
                logger.info(f"买入触发: 数量={suggested_quantity}, 价格范围={suggested_price_range}")
            else:
                logger.info(f"买入未触发: {reason}")
            
            return result
            
        except Exception as e:
            logger.error(f"买入触发检查失败: {e}")
            return {
                'triggered': False,
                'reason': f'检查失败: {str(e)}',
                'action': 'none'
            }
    
    def check_sell_trigger(self, signal: Dict[str, Any], position: Dict[str, Any], 
                        current_price: float) -> Dict[str, Any]:
        if position is None or position.get('quantity', 0) == 0:
            return {
                'triggered': False,
                'reason': '无持仓',
                'action': 'none'
            }
        
        try:
            checks = {}
            
            signal_check = self._check_sell_signal(signal)
            checks['signal'] = signal_check
            
            profit_loss_check = self._check_profit_loss(position, current_price)
            checks['profit_loss'] = profit_loss_check
            
            risk_check = self._check_position_risk(position, current_price)
            checks['risk'] = risk_check
            
            triggered = False
            action = 'hold'
            reason = '无卖出条件'
            
            if risk_check['triggered']:
                triggered = True
                action = 'sell'
                reason = f'止损触发: {risk_check["reason"]}'
            elif profit_loss_check['triggered']:
                triggered = True
                action = 'sell'
                reason = f'止盈触发: {profit_loss_check["reason"]}'
            elif signal_check['triggered']:
                triggered = True
                action = 'sell'
                reason = f'信号触发: {signal_check["reason"]}'
            
            if triggered:
                suggested_price_range = self._get_suggested_price_range(current_price, 'sell')
                suggested_quantity = self._calculate_sell_quantity(signal, position)
            else:
                suggested_price_range = None
                suggested_quantity = 0
            
            result = {
                'triggered': triggered,
                'action': action,
                'reason': reason,
                'checks': checks,
                'suggested_quantity': suggested_quantity,
                'suggested_price_range': suggested_price_range,
                'current_price': current_price,
                'position': position,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
            if triggered:
                logger.info(f"卖出触发: 原因={reason}, 价格范围={suggested_price_range}")
            else:
                logger.info(f"卖出未触发: {reason}")
            
            return result
            
        except Exception as e:
            logger.error(f"卖出触发检查失败: {e}")
            return {
                'triggered': False,
                'reason': f'检查失败: {str(e)}',
                'action': 'none'
            }
    
    def _check_position_limits(self, current_positions: List[Dict[str, Any]], 
                           current_price: float, available_capital: float) -> Dict[str, Any]:
        total_value = sum(pos.get('market_value', 0) for pos in current_positions)
        total_capital = total_value + available_capital
        
        total_position_ratio = total_value / total_capital if total_capital > 0 else 0
        
        passed = total_position_ratio < self.position_limits['total_max']
        
        return {
            'passed': passed,
            'total_position_ratio': total_position_ratio,
            'total_limit': self.position_limits['total_max'],
            'reason': f'总仓位{total_position_ratio:.2%}，限制{self.position_limits["total_max"]:.2%}' if not passed else '仓位检查通过'
        }
    
    def _check_trade_count(self, action: str) -> Dict[str, Any]:
        today = pd.Timestamp.now().date()
        
        today_trades = [t for t in self.trade_records if pd.Timestamp(t['timestamp']).date() == today]
        
        today_count = len(today_trades)
        
        week_start = today - pd.Timedelta(days=today.weekday())
        week_trades = [t for t in self.trade_records if pd.Timestamp(t['timestamp']).date() >= week_start]
        week_count = len(week_trades)
        
        daily_passed = today_count < self.position_limits['daily_trades']
        weekly_passed = week_count < self.position_limits['weekly_trades']
        
        passed = daily_passed and weekly_passed
        
        return {
            'passed': passed,
            'today_count': today_count,
            'daily_limit': self.position_limits['daily_trades'],
            'week_count': week_count,
            'weekly_limit': self.position_limits['weekly_trades'],
            'reason': f'今日交易{today_count}次，限制{self.position_limits["daily_trades"]}次' if not daily_passed else '交易次数检查通过'
        }
    
    def _check_risk_limits(self, current_price: float, available_capital: float) -> Dict[str, Any]:
        single_max_capital = available_capital * self.position_limits['single_max']
        single_max_shares = int(single_max_capital / current_price)
        
        passed = single_max_shares > 0
        
        return {
            'passed': passed,
            'single_max_capital': single_max_capital,
            'single_max_shares': single_max_shares,
            'reason': '风险检查通过' if passed else '资金不足'
        }
    
    def _check_sell_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        if signal is None:
            return {
                'triggered': False,
                'reason': '无信号'
            }
        
        triggered = signal['signal'] == 'sell'
        
        return {
            'triggered': triggered,
            'signal': signal['signal'],
            'confidence': signal.get('confidence', 0.5),
            'reason': f'卖出信号，置信度{signal.get("confidence", 0.5):.2f}' if triggered else '非卖出信号'
        }
    
    def _check_profit_loss(self, position: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        avg_price = position.get('avg_price', 0)
        quantity = position.get('quantity', 0)
        
        if avg_price == 0 or quantity == 0:
            return {
                'triggered': False,
                'reason': '无有效持仓'
            }
        
        profit_pct = (current_price - avg_price) / avg_price
        
        profit_target = 0.10
        loss_limit = -self.targets['single_loss']
        
        triggered = profit_pct >= profit_target or profit_pct <= loss_limit
        
        if profit_pct >= profit_target:
            reason = f'盈利{profit_pct:.2%}，达到止盈目标{profit_target:.2%}'
        elif profit_pct <= loss_limit:
            reason = f'亏损{profit_pct:.2%}，达到止损限制{loss_limit:.2%}'
        else:
            reason = f'盈亏{profit_pct:.2%}，未达到触发条件'
        
        return {
            'triggered': triggered,
            'profit_pct': profit_pct,
            'profit_target': profit_target,
            'loss_limit': loss_limit,
            'reason': reason
        }
    
    def _check_position_risk(self, position: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        avg_price = position.get('avg_price', 0)
        quantity = position.get('quantity', 0)
        
        if avg_price == 0 or quantity == 0:
            return {
                'triggered': False,
                'reason': '无有效持仓'
            }
        
        loss_pct = (current_price - avg_price) / avg_price
        loss_limit = -self.targets['single_loss']
        
        triggered = loss_pct <= loss_limit
        
        return {
            'triggered': triggered,
            'loss_pct': loss_pct,
            'loss_limit': loss_limit,
            'reason': f'亏损{loss_pct:.2%}，达到止损限制{loss_limit:.2%}' if triggered else '风险检查通过'
        }
    
    def _shape_strength(self, strength: float) -> float:
        s = max(0.0, min(1.0, float(strength or 0.0)))
        # 偏好越小，曲线越陡：多数小单，少量大单；偏好越大，曲线越平：更容易出现大单
        gamma = 2.2 - (1.7 * self.risk_preference)  # [2.2, 0.5]
        return max(0.0, min(1.0, s ** gamma))

    def _calculate_buy_quantity(self, signal: Dict[str, Any], current_price: float, available_capital: float) -> int:
        lot_size = 100
        single_max_capital = available_capital * self.position_limits['single_max']
        confidence = float((signal or {}).get('confidence', 0.5) or 0.5)
        ml_buy_prob = (signal or {}).get('ml_buy_prob', None)
        if ml_buy_prob is None:
            base_strength = confidence
        else:
            base_strength = 0.5 * confidence + 0.5 * float(ml_buy_prob)
        shaped = self._shape_strength(base_strength)
        budget = single_max_capital * shaped
        shares = int((budget / max(float(current_price or 0.0), 1e-9)) // lot_size) * lot_size
        return max(0, shares)

    def _calculate_sell_quantity(self, signal: Dict[str, Any], position: Dict[str, Any]) -> int:
        lot_size = 100
        qty = int(position.get('quantity', 0) or 0)
        if qty <= 0:
            return 0
        confidence = float((signal or {}).get('confidence', 0.5) or 0.5)
        ml_sell_prob = (signal or {}).get('ml_sell_prob', None)
        if ml_sell_prob is None:
            base_strength = confidence
        else:
            base_strength = 0.5 * confidence + 0.5 * float(ml_sell_prob)
        shaped = self._shape_strength(base_strength)
        desired = int((qty * shaped) // lot_size) * lot_size
        if desired <= 0:
            desired = lot_size if qty >= lot_size else qty
        return min(qty, desired)
    
    def _get_suggested_price_range(self, current_price: float, action: str) -> Dict[str, float]:
        if action == 'buy':
            return {
                'min_price': current_price * 0.995,
                'max_price': current_price * 1.005,
                'suggested_price': current_price
            }
        else:
            return {
                'min_price': current_price * 0.995,
                'max_price': current_price * 1.005,
                'suggested_price': current_price
            }
    
    def _get_block_reason(self, checks: Dict[str, Any]) -> str:
        reasons = []
        
        for check_name, check_result in checks.items():
            if isinstance(check_result, dict) and not check_result.get('passed', True):
                reasons.append(check_result.get('reason', ''))
        
        return '; '.join(reasons) if reasons else '未知原因'
    
    def record_trade(self, trade: Dict[str, Any]):
        self.trade_records.append(trade)
        
        if len(self.trade_records) > 1000:
            self.trade_records = self.trade_records[-1000:]
        
        logger.info(f"记录交易: {trade.get('action', '')} {trade.get('symbol', '')} {trade.get('quantity', 0)}股")
    
    def get_trade_history(self, days: int = 30) -> List[Dict[str, Any]]:
        cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days)
        
        recent_trades = [
            t for t in self.trade_records 
            if pd.Timestamp(t['timestamp']) >= cutoff_date
        ]
        
        return recent_trades
    
    def update_position_limits(self, new_limits: Dict[str, Any]):
        for key, value in new_limits.items():
            if key in self.position_limits:
                self.position_limits[key] = value
        
        logger.info(f"仓位限制已更新: {self.position_limits}")
    
    def update_targets(self, new_targets: Dict[str, float]):
        for key, value in new_targets.items():
            if key in self.targets:
                self.targets[key] = value
        
        logger.info(f"目标已更新: {self.targets}")
    
    def get_current_limits(self) -> Dict[str, Any]:
        return {
            'position_limits': self.position_limits.copy(),
            'targets': self.targets.copy()
        }
