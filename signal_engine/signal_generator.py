import pandas as pd
import numpy as np
from typing import Dict, Any
from app.utils import logger


class SignalGenerator:
    def __init__(self, signal_thresholds: Dict[str, float] = None):
        if signal_thresholds is None:
            self.signal_thresholds = {
                'buy_score': 8.0,
                'sell_score': 3.0,
                'buy_prob': 0.7,
                'sell_prob': 0.7
            }
        else:
            self.signal_thresholds = signal_thresholds
        
        logger.info(f"信号生成器初始化完成，阈值: {self.signal_thresholds}")
    
    def generate_signal(self, factors: Dict[str, Any], ml_prediction: Dict[str, float] = None) -> Dict[str, Any]:
        if factors is None:
            logger.warning("因子数据为空，无法生成信号")
            return {
                'signal': 'hold',
                'reason': '数据不足',
                'confidence': 0.0
            }
        
        try:
            total_score = factors.get('total_score', 0.5)
            
            signal = self._determine_signal(total_score, ml_prediction)
            
            result = {
                'signal': signal,
                'total_score': total_score,
                'valuation_score': factors.get('valuation_score', 0.5),
                'trend_score': factors.get('trend_score', 0.5),
                'fund_score': factors.get('fund_score', 0.5),
                'ml_buy_prob': ml_prediction.get('buy_prob', 0.5) if ml_prediction else None,
                'ml_sell_prob': ml_prediction.get('sell_prob', 0.5) if ml_prediction else None,
                'reason': self._get_signal_reason(signal, total_score, ml_prediction),
                'confidence': self._calculate_confidence(signal, total_score, ml_prediction),
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
            logger.info(f"生成信号: {signal}, 总分={total_score:.2f}, 置信度={result['confidence']:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"信号生成失败: {e}")
            return {
                'signal': 'hold',
                'reason': f'生成失败: {str(e)}',
                'confidence': 0.0
            }
    
    def _determine_signal(self, total_score: float, ml_prediction: Dict[str, float] = None) -> str:
        buy_score_threshold = self.signal_thresholds['buy_score']
        sell_score_threshold = self.signal_thresholds['sell_score']
        
        if ml_prediction is not None:
            buy_prob_threshold = self.signal_thresholds['buy_prob']
            sell_prob_threshold = self.signal_thresholds['sell_prob']
            
            if total_score >= buy_score_threshold and ml_prediction.get('buy_prob', 0.5) >= buy_prob_threshold:
                return 'buy'
            elif total_score <= sell_score_threshold and ml_prediction.get('sell_prob', 0.5) >= sell_prob_threshold:
                return 'sell'
            else:
                return 'hold'
        else:
            if total_score >= buy_score_threshold:
                return 'buy'
            elif total_score <= sell_score_threshold:
                return 'sell'
            else:
                return 'hold'
    
    def _get_signal_reason(self, signal: str, total_score: float, ml_prediction: Dict[str, float] = None) -> str:
        if signal == 'buy':
            if ml_prediction is not None:
                return f'综合评分{total_score:.2f}≥{self.signal_thresholds["buy_score"]}且ML买入概率{ml_prediction.get("buy_prob", 0.5):.2f}≥{self.signal_thresholds["buy_prob"]}'
            else:
                return f'综合评分{total_score:.2f}≥{self.signal_thresholds["buy_score"]}'
        elif signal == 'sell':
            if ml_prediction is not None:
                return f'综合评分{total_score:.2f}≤{self.signal_thresholds["sell_score"]}且ML卖出概率{ml_prediction.get("sell_prob", 0.5):.2f}≥{self.signal_thresholds["sell_prob"]}'
            else:
                return f'综合评分{total_score:.2f}≤{self.signal_thresholds["sell_score"]}'
        else:
            return '综合评分在持有区间'
    
    def _calculate_confidence(self, signal: str, total_score: float, ml_prediction: Dict[str, float] = None) -> float:
        if signal == 'hold':
            return 0.5
        
        if signal == 'buy':
            score_confidence = min(1.0, (total_score - self.signal_thresholds['buy_score']) / (10.0 - self.signal_thresholds['buy_score']) + 0.5)
            
            if ml_prediction is not None:
                ml_confidence = ml_prediction.get('buy_prob', 0.5)
                return (score_confidence + ml_confidence) / 2
            else:
                return score_confidence
        
        elif signal == 'sell':
            score_confidence = min(1.0, (self.signal_thresholds['sell_score'] - total_score) / self.signal_thresholds['sell_score'] + 0.5)
            
            if ml_prediction is not None:
                ml_confidence = ml_prediction.get('sell_prob', 0.5)
                return (score_confidence + ml_confidence) / 2
            else:
                return score_confidence
        
        return 0.5
    
    def generate_batch_signals(self, data_list: list, ml_predictions: list = None) -> list:
        if not data_list:
            logger.warning("数据列表为空，无法批量生成信号")
            return []
        
        try:
            signals = []
            
            for i, data in enumerate(data_list):
                ml_pred = ml_predictions[i] if ml_predictions and i < len(ml_predictions) else None
                signal = self.generate_signal(data, ml_pred)
                signals.append(signal)
            
            logger.info(f"批量生成信号完成: {len(signals)}条")
            return signals
            
        except Exception as e:
            logger.error(f"批量信号生成失败: {e}")
            return []
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        for key, value in new_thresholds.items():
            if key in self.signal_thresholds:
                self.signal_thresholds[key] = value
        
        logger.info(f"信号阈值已更新: {self.signal_thresholds}")
    
    def get_current_thresholds(self) -> Dict[str, float]:
        return self.signal_thresholds.copy()
