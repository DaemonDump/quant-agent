import pandas as pd
import numpy as np
from typing import Dict, Any, List
from app.utils import logger


class SignalFilter:
    def __init__(self):
        self.filter_rules = {
            'trend_enabled': True,
            'risk_enabled': True,
            'time_validity_enabled': True,
            'signal_validity_minutes': 10
        }
        logger.info(f"信号过滤器初始化完成，规则: {self.filter_rules}")
    
    def filter_signal(self, signal: Dict[str, Any], market_data: Dict[str, Any] = None, 
                    stock_data: Dict[str, Any] = None) -> Dict[str, Any]:
        if signal is None:
            logger.warning("信号为空，无法过滤")
            return {
                'filtered': True,
                'signal': 'hold',
                'reason': '信号为空',
                'filters': {}
            }
        
        try:
            filters = {}
            original_signal = signal['signal']
            filtered_signal = original_signal
            
            if self.filter_rules['trend_enabled']:
                trend_result = self._apply_trend_filter(signal, market_data, stock_data)
                filters['trend'] = trend_result
                if trend_result['blocked']:
                    filtered_signal = 'hold'
            
            if self.filter_rules['risk_enabled'] and stock_data is not None:
                risk_result = self._apply_risk_filter(signal, stock_data)
                filters['risk'] = risk_result
                if risk_result['blocked']:
                    filtered_signal = 'hold'
            
            if self.filter_rules['time_validity_enabled']:
                time_result = self._apply_time_validity_filter(signal)
                filters['time_validity'] = time_result
                if time_result['blocked']:
                    filtered_signal = 'hold'
            
            result = {
                'original_signal': original_signal,
                'filtered_signal': filtered_signal,
                'filtered': original_signal != filtered_signal,
                'reason': self._get_filter_reason(filters, original_signal, filtered_signal),
                'filters': filters,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
            if result['filtered']:
                logger.info(f"信号被过滤: {original_signal} -> {filtered_signal}, 原因: {result['reason']}")
            else:
                logger.info(f"信号通过过滤: {original_signal}")
            
            return result
            
        except Exception as e:
            logger.error(f"信号过滤失败: {e}")
            return {
                'original_signal': signal.get('signal', 'hold'),
                'filtered_signal': 'hold',
                'filtered': True,
                'reason': f'过滤失败: {str(e)}',
                'filters': {},
                'timestamp': pd.Timestamp.now().isoformat()
            }
    
    def _apply_trend_filter(self, signal: Dict[str, Any], market_data: Dict[str, Any] = None, 
                         stock_data: Dict[str, Any] = None) -> Dict[str, Any]:
        if market_data is None and stock_data is None:
            return {
                'blocked': False,
                'reason': '无趋势数据'
            }
        
        try:
            blocked = False
            reasons = []
            
            if market_data is not None:
                market_trend = market_data.get('trend', 'neutral')
                if market_trend == 'bear' and signal['signal'] == 'buy':
                    blocked = True
                    reasons.append('大盘处于熊市')
                elif market_trend == 'bull' and signal['signal'] == 'sell':
                    blocked = True
                    reasons.append('大盘处于牛市')
            
            if stock_data is not None:
                stock_trend = stock_data.get('trend_score', 0.5)
                if stock_trend < 0.3 and signal['signal'] == 'buy':
                    blocked = True
                    reasons.append('个股趋势向下')
                elif stock_trend > 0.7 and signal['signal'] == 'sell':
                    blocked = True
                    reasons.append('个股趋势向上')
            
            return {
                'blocked': blocked,
                'reason': '; '.join(reasons) if reasons else '趋势检查通过',
                'market_trend': market_data.get('trend', 'neutral') if market_data else None,
                'stock_trend': stock_data.get('trend_score', 0.5) if stock_data else None
            }
            
        except Exception as e:
            logger.error(f"趋势过滤失败: {e}")
            return {
                'blocked': False,
                'reason': f'趋势过滤失败: {str(e)}'
            }
    
    def _apply_risk_filter(self, signal: Dict[str, Any], stock_data: Dict[str, Any]) -> Dict[str, Any]:
        if stock_data is None:
            return {
                'blocked': False,
                'reason': '无股票数据'
            }
        
        try:
            blocked = False
            reasons = []
            
            symbol = stock_data.get('symbol', '')
            
            if 'ST' in symbol or 'st' in symbol:
                blocked = True
                reasons.append('ST股票')
            
            is_suspended = stock_data.get('is_suspended', False)
            if is_suspended:
                blocked = True
                reasons.append('停牌')
            
            is_limit_up = stock_data.get('is_limit_up', False)
            is_limit_down = stock_data.get('is_limit_down', False)
            
            if is_limit_up and signal['signal'] == 'buy':
                blocked = True
                reasons.append('涨停板')
            elif is_limit_down and signal['signal'] == 'sell':
                blocked = True
                reasons.append('跌停板')
            
            avg_volume = stock_data.get('avg_volume', 0)
            if avg_volume < 50000000 and signal['signal'] == 'buy':
                blocked = True
                reasons.append('流动性不足')
            
            return {
                'blocked': blocked,
                'reason': '; '.join(reasons) if reasons else '风险检查通过',
                'is_st': 'ST' in symbol or 'st' in symbol,
                'is_suspended': is_suspended,
                'is_limit_up': is_limit_up,
                'is_limit_down': is_limit_down,
                'avg_volume': avg_volume
            }
            
        except Exception as e:
            logger.error(f"风险过滤失败: {e}")
            return {
                'blocked': False,
                'reason': f'风险过滤失败: {str(e)}'
            }
    
    def _apply_time_validity_filter(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        try:
            signal_time = signal.get('timestamp')
            if signal_time is None:
                return {
                    'blocked': False,
                    'reason': '无时间戳'
                }
            
            signal_timestamp = pd.Timestamp(signal_time)
            current_time = pd.Timestamp.now()
            time_diff = (current_time - signal_timestamp).total_seconds() / 60
            
            validity_minutes = self.filter_rules['signal_validity_minutes']
            
            if time_diff > validity_minutes:
                return {
                    'blocked': True,
                    'reason': f'信号已过期{time_diff:.1f}分钟（有效期{validity_minutes}分钟）',
                    'time_diff_minutes': time_diff,
                    'validity_minutes': validity_minutes
                }
            else:
                return {
                    'blocked': False,
                    'reason': f'信号有效（已过{time_diff:.1f}分钟，有效期{validity_minutes}分钟）',
                    'time_diff_minutes': time_diff,
                    'validity_minutes': validity_minutes
                }
                
        except Exception as e:
            logger.error(f"时效性过滤失败: {e}")
            return {
                'blocked': False,
                'reason': f'时效性过滤失败: {str(e)}'
            }
    
    def _get_filter_reason(self, filters: Dict[str, Any], original_signal: str, 
                        filtered_signal: str) -> str:
        if original_signal == filtered_signal:
            return '信号通过所有过滤'
        
        reasons = []
        
        for filter_name, filter_result in filters.items():
            if isinstance(filter_result, dict) and filter_result.get('blocked', False):
                reasons.append(filter_result.get('reason', ''))
        
        return '; '.join(reasons) if reasons else '未知原因'
    
    def filter_batch_signals(self, signals: List[Dict[str, Any]], 
                         market_data: Dict[str, Any] = None,
                         stock_data_list: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not signals:
            logger.warning("信号列表为空，无法批量过滤")
            return []
        
        try:
            filtered_signals = []
            
            for i, signal in enumerate(signals):
                stock_data = stock_data_list[i] if stock_data_list and i < len(stock_data_list) else None
                filtered_signal = self.filter_signal(signal, market_data, stock_data)
                filtered_signals.append(filtered_signal)
            
            logger.info(f"批量信号过滤完成: {len(filtered_signals)}条")
            return filtered_signals
            
        except Exception as e:
            logger.error(f"批量信号过滤失败: {e}")
            return []
    
    def update_filter_rules(self, new_rules: Dict[str, Any]):
        for key, value in new_rules.items():
            if key in self.filter_rules:
                self.filter_rules[key] = value
        
        logger.info(f"过滤规则已更新: {self.filter_rules}")
    
    def get_current_rules(self) -> Dict[str, Any]:
        return self.filter_rules.copy()
