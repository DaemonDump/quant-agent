import sqlite3
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime
from app.utils import logger


def _get_db_connection():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(root, 'data', 'tushare', 'db', 'quant_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


class EmergencyHandler:
    def __init__(self):
        self.emergency_rules = {
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.10,
            'max_daily_loss_pct': 0.02,
            'max_total_loss_pct': 0.10
        }
        self.emergency_history = []
        self.active_emergencies = {}
        
        logger.info(f"紧急处理器初始化完成，规则: {self.emergency_rules}")
    
    def check_stop_loss(self, position: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """检查止损"""
        try:
            if not position or not current_price:
                return {
                    'triggered': False,
                    'reason': '数据不足'
                }
            
            avg_price = position.get('avg_price', 0)
            quantity = position.get('quantity', 0)
            
            if avg_price <= 0 or quantity <= 0:
                return {
                    'triggered': False,
                    'reason': '持仓数据异常'
                }
            
            current_pnl = (current_price - avg_price) * quantity
            current_pnl_pct = (current_price - avg_price) / avg_price * 100
            
            stop_loss_pct = self.emergency_rules['stop_loss_pct'] * 100
            
            if current_pnl_pct <= -stop_loss_pct:
                result = {
                    'triggered': True,
                    'type': 'stop_loss',
                    'symbol': position['symbol'],
                    'current_price': current_price,
                    'avg_price': avg_price,
                    'pnl': current_pnl,
                    'pnl_pct': current_pnl_pct,
                    'reason': f'触发止损：亏损{abs(current_pnl_pct):.2f}%，超过阈值{stop_loss_pct:.1f}%',
                    'action': 'sell',
                    'suggested_price': current_price,
                    'quantity': quantity
                }
                
                logger.warning(f"止损触发: {result['reason']}")
                self.record_emergency(result)
                
                return result
            
            return {
                'triggered': False,
                'current_pnl_pct': current_pnl_pct,
                'stop_loss_threshold': stop_loss_pct
            }
            
        except Exception as e:
            logger.error(f"检查止损失败: {e}")
            return {
                'triggered': False,
                'reason': f'检查失败: {str(e)}'
            }
    
    def check_take_profit(self, position: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """检查止盈"""
        try:
            if not position or not current_price:
                return {
                    'triggered': False,
                    'reason': '数据不足'
                }
            
            avg_price = position.get('avg_price', 0)
            quantity = position.get('quantity', 0)
            
            if avg_price <= 0 or quantity <= 0:
                return {
                    'triggered': False,
                    'reason': '持仓数据异常'
                }
            
            current_pnl = (current_price - avg_price) * quantity
            current_pnl_pct = (current_price - avg_price) / avg_price * 100
            
            take_profit_pct = self.emergency_rules['take_profit_pct'] * 100
            
            if current_pnl_pct >= take_profit_pct:
                result = {
                    'triggered': True,
                    'type': 'take_profit',
                    'symbol': position['symbol'],
                    'current_price': current_price,
                    'avg_price': avg_price,
                    'pnl': current_pnl,
                    'pnl_pct': current_pnl_pct,
                    'reason': f'触发止盈：盈利{current_pnl_pct:.2f}%，达到阈值{take_profit_pct:.1f}%',
                    'action': 'sell',
                    'suggested_price': current_price,
                    'quantity': quantity
                }
                
                logger.info(f"止盈触发: {result['reason']}")
                self.record_emergency(result)
                
                return result
            
            return {
                'triggered': False,
                'current_pnl_pct': current_pnl_pct,
                'take_profit_threshold': take_profit_pct
            }
            
        except Exception as e:
            logger.error(f"检查止盈失败: {e}")
            return {
                'triggered': False,
                'reason': f'检查失败: {str(e)}'
            }
    
    def check_daily_loss_limit(self, daily_pnl: float, initial_capital: float) -> Dict[str, Any]:
        """检查日亏损限制"""
        try:
            if initial_capital <= 0:
                return {
                    'triggered': False,
                    'reason': '初始资金异常'
                }
            
            daily_pnl_pct = daily_pnl / initial_capital * 100
            max_daily_loss_pct = self.emergency_rules['max_daily_loss_pct'] * 100
            
            if daily_pnl_pct <= -max_daily_loss_pct:
                result = {
                    'triggered': True,
                    'type': 'daily_loss_limit',
                    'daily_pnl': daily_pnl,
                    'daily_pnl_pct': daily_pnl_pct,
                    'initial_capital': initial_capital,
                    'reason': f'触发日亏损限制：亏损{abs(daily_pnl_pct):.2f}%，超过阈值{max_daily_loss_pct:.1f}%',
                    'action': 'stop_trading',
                    'suggestion': '停止今日交易，平仓所有持仓'
                }
                
                logger.warning(f"日亏损限制触发: {result['reason']}")
                self.record_emergency(result)
                
                return result
            
            return {
                'triggered': False,
                'daily_pnl_pct': daily_pnl_pct,
                'max_daily_loss_threshold': max_daily_loss_pct
            }
            
        except Exception as e:
            logger.error(f"检查日亏损限制失败: {e}")
            return {
                'triggered': False,
                'reason': f'检查失败: {str(e)}'
            }
    
    def check_total_loss_limit(self, total_pnl: float, initial_capital: float) -> Dict[str, Any]:
        """检查总亏损限制"""
        try:
            if initial_capital <= 0:
                return {
                    'triggered': False,
                    'reason': '初始资金异常'
                }
            
            total_pnl_pct = total_pnl / initial_capital * 100
            max_total_loss_pct = self.emergency_rules['max_total_loss_pct'] * 100
            
            if total_pnl_pct <= -max_total_loss_pct:
                result = {
                    'triggered': True,
                    'type': 'total_loss_limit',
                    'total_pnl': total_pnl,
                    'total_pnl_pct': total_pnl_pct,
                    'initial_capital': initial_capital,
                    'reason': f'触发总亏损限制：亏损{abs(total_pnl_pct):.2f}%，超过阈值{max_total_loss_pct:.1f}%',
                    'action': 'emergency_stop',
                    'suggestion': '紧急停止交易，平仓所有持仓，暂停策略'
                }
                
                logger.error(f"总亏损限制触发: {result['reason']}")
                self.record_emergency(result)
                
                return result
            
            return {
                'triggered': False,
                'total_pnl_pct': total_pnl_pct,
                'max_total_loss_threshold': max_total_loss_pct
            }
            
        except Exception as e:
            logger.error(f"检查总亏损限制失败: {e}")
            return {
                'triggered': False,
                'reason': f'检查失败: {str(e)}'
            }
    
    def execute_emergency_action(self, emergency: Dict[str, Any]) -> bool:
        """执行紧急操作"""
        try:
            action_type = emergency.get('action', '')
            
            if action_type == 'sell':
                return self._execute_sell(emergency)
            elif action_type == 'stop_trading':
                return self._execute_stop_trading(emergency)
            elif action_type == 'emergency_stop':
                return self._execute_emergency_stop(emergency)
            else:
                logger.warning(f"未知的紧急操作类型: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"执行紧急操作失败: {e}")
            return False
    
    def _execute_sell(self, emergency: Dict[str, Any]) -> bool:
        """执行卖出操作"""
        try:
            conn = _get_db_connection()
            
            trade_data = {
                'symbol': emergency['symbol'],
                'direction': '卖出',
                'price': emergency['suggested_price'],
                'quantity': emergency['quantity'],
                'amount': emergency['suggested_price'] * emergency['quantity'],
                'status': 'executed',
                'reason': emergency['reason']
            }
            
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trade_records (symbol, direction, price, quantity, amount, fee, trade_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data['symbol'],
                trade_data['direction'],
                trade_data['price'],
                trade_data['quantity'],
                trade_data['amount'],
                0.0,
                datetime.now().isoformat()
            ))
            
            cursor.execute('''
                DELETE FROM positions WHERE symbol = ?
            ''', (emergency['symbol'],))
            
            conn.commit()
            conn.close()
            
            logger.info(f"紧急卖出执行成功: {emergency['symbol']}")
            
            return True
            
        except Exception as e:
            logger.error(f"执行紧急卖出失败: {e}")
            return False
    
    def _execute_stop_trading(self, emergency: Dict[str, Any]) -> bool:
        """执行停止交易操作"""
        try:
            conn = _get_db_connection()
            
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE strategy_status
                SET is_running = 0
                WHERE id = 1
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"停止交易执行成功: {emergency['reason']}")
            
            return True
            
        except Exception as e:
            logger.error(f"执行停止交易失败: {e}")
            return False
    
    def _execute_emergency_stop(self, emergency: Dict[str, Any]) -> bool:
        """执行紧急停止操作"""
        try:
            conn = _get_db_connection()
            
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE strategy_status
                SET is_running = 0
                WHERE id = 1
            ''')
            
            positions_df = pd.read_sql_query('SELECT * FROM positions', conn)
            
            if not positions_df.empty:
                for _, position in positions_df.iterrows():
                    cursor.execute('''
                        INSERT INTO trade_records (symbol, direction, price, quantity, amount, fee, trade_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        position['symbol'],
                        '卖出',
                        position['current_price'],
                        position['quantity'],
                        position['market_value'],
                        0.0,
                        datetime.now().isoformat()
                    ))
                
                cursor.execute('DELETE FROM positions')
            
            conn.commit()
            conn.close()
            
            logger.info(f"紧急停止执行成功: {emergency['reason']}")
            
            return True
            
        except Exception as e:
            logger.error(f"执行紧急停止失败: {e}")
            return False
    
    def record_emergency(self, emergency: Dict[str, Any]):
        """记录紧急事件"""
        emergency_record = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'type': emergency.get('type', ''),
            'reason': emergency.get('reason', ''),
            'action': emergency.get('action', ''),
            'resolved': False
        }
        
        self.emergency_history.append(emergency_record)
        
        emergency_id = f"{emergency['type']}_{len(self.emergency_history)}"
        self.active_emergencies[emergency_id] = emergency_record
        
        if len(self.emergency_history) > 1000:
            self.emergency_history = self.emergency_history[-1000:]
    
    def resolve_emergency(self, emergency_id: str, resolution: str):
        """解决紧急事件"""
        try:
            if emergency_id in self.active_emergencies:
                self.active_emergencies[emergency_id]['resolved'] = True
                self.active_emergencies[emergency_id]['resolution'] = resolution
                self.active_emergencies[emergency_id]['resolved_time'] = pd.Timestamp.now().isoformat()
                
                logger.info(f"紧急事件已解决: {emergency_id} - {resolution}")
                
        except Exception as e:
            logger.error(f"解决紧急事件失败: {e}")
    
    def get_emergency_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取紧急事件历史"""
        return self.emergency_history[-limit:] if self.emergency_history else []
    
    def get_active_emergencies(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃的紧急事件"""
        return {k: v for k, v in self.active_emergencies.items() if not v['resolved']}
    
    def update_emergency_rules(self, new_rules: Dict[str, float]):
        """更新紧急规则"""
        try:
            for key, value in new_rules.items():
                if key in self.emergency_rules:
                    self.emergency_rules[key] = value
            
            logger.info(f"紧急规则已更新: {self.emergency_rules}")
            
        except Exception as e:
            logger.error(f"更新紧急规则失败: {e}")
    
    def get_current_rules(self) -> Dict[str, float]:
        """获取当前紧急规则"""
        return self.emergency_rules.copy()
    
    def get_emergency_summary(self) -> Dict[str, Any]:
        """获取紧急事件汇总"""
        if not self.emergency_history:
            return {
                'total_emergencies': 0,
                'active_emergencies': 0,
                'resolved_emergencies': 0,
                'by_type': {}
            }
        
        total_emergencies = len(self.emergency_history)
        active_emergencies = len(self.get_active_emergencies())
        resolved_emergencies = total_emergencies - active_emergencies
        
        by_type = {}
        for emergency in self.emergency_history:
            emergency_type = emergency['type']
            by_type[emergency_type] = by_type.get(emergency_type, 0) + 1
        
        return {
            'total_emergencies': total_emergencies,
            'active_emergencies': active_emergencies,
            'resolved_emergencies': resolved_emergencies,
            'by_type': by_type,
            'current_rules': self.emergency_rules
        }
