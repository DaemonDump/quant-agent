import pandas as pd
import numpy as np
from typing import Dict, Any
from app.utils import logger

try:
    import talib
    TALIB_ENABLED = True
except ImportError:
    TALIB_ENABLED = False
    logger.warning("TA-Lib未安装，趋势因子计算将受限")


class FactorCalculator:
    def __init__(self, factor_weights: Dict[str, float] = None):
        if factor_weights is None:
            self.factor_weights = {
                'valuation': 0.3,
                'trend': 0.4,
                'fund': 0.3
            }
        else:
            self.factor_weights = factor_weights
        
        logger.info(f"因子计算器初始化完成，权重: {self.factor_weights}")
    
    def _validate_data(self, data: pd.DataFrame) -> bool:
        if data is None or data.empty:
            logger.warning("输入数据为空")
            return False
        
        if len(data) < 20:
            logger.warning(f"数据长度不足20，无法计算所有因子: {len(data)}")
            return False
        
        required_columns = ['close', 'volume', 'amount']
        if not all(col in data.columns for col in required_columns):
            logger.warning(f"缺少必要的列: {required_columns}")
            return False
            
        return True

    def calculate_all_factors(self, data: pd.DataFrame) -> Dict[str, Any]:
        if not self._validate_data(data):
            return None
        
        try:
            factors = {}
            
            factors['valuation'] = self._calculate_valuation_factors(data)
            if TALIB_ENABLED:
                factors['trend'] = self._calculate_trend_factors(data)
            else:
                factors['trend'] = {'score': 0.5, 'details': 'TA-Lib未安装'}
                
            factors['fund'] = self._calculate_fund_factors(data)
            
            factors['valuation_score'] = float(self._normalize_score(factors['valuation'].get('score', 0.5)))
            factors['trend_score'] = float(self._normalize_score(factors['trend'].get('score', 0.5)))
            factors['fund_score'] = float(self._normalize_score(factors['fund'].get('score', 0.5)))
            
            factors['total_score'] = float(self._calculate_total_score(factors))
            
            # 确保内部字典中的 score 也是 float 而非 numpy float，以防序列化问题
            for key in ['valuation', 'trend', 'fund']:
                if 'score' in factors[key]:
                    factors[key]['score'] = float(factors[key]['score'])
                # 把可能存在的其他 numpy float 类型也转掉
                for sub_k, sub_v in factors[key].items():
                    if isinstance(sub_v, (np.floating, np.integer, np.ndarray)):
                        if isinstance(sub_v, np.ndarray) and sub_v.size == 1:
                            factors[key][sub_k] = float(sub_v.item())
                        elif isinstance(sub_v, np.ndarray):
                            factors[key][sub_k] = sub_v.tolist()
                        else:
                            factors[key][sub_k] = float(sub_v)
            
            logger.info(f"因子计算完成: 估值={factors['valuation_score']:.2f}, 趋势={factors['trend_score']:.2f}, 资金={factors['fund_score']:.2f}, 总分={factors['total_score']:.2f}")
            return factors
            
        except Exception as e:
            logger.error(f"因子计算失败: {e}")
            return None
    
    def _calculate_valuation_factors(self, data: pd.DataFrame) -> Dict[str, Any]:
        try:
            factors = {}
            if 'pe' not in data.columns or 'pb' not in data.columns:
                return {'score': 0.5, 'pe': np.nan, 'pb': np.nan, 'details': '缺少PE/PB列'}
                
            latest = data.iloc[-1]
            pe_ratio = latest.get('pe', np.nan)
            pb_ratio = latest.get('pb', np.nan)

            if pd.isna(pe_ratio) or pd.isna(pb_ratio):
                return {'score': 0.5, 'pe': pe_ratio, 'pb': pb_ratio, 'details': 'PE或PB数据为空'}

            pe_score = self._normalize_pe(pe_ratio)
            pb_score = self._normalize_pb(pb_ratio)
            factors['score'] = (pe_score + pb_score) / 2
            factors['pe'] = pe_ratio
            factors['pb'] = pb_ratio
            factors['pe_score'] = pe_score
            factors['pb_score'] = pb_score
            factors['details'] = f'PE={pe_ratio:.2f}, PB={pb_ratio:.2f}'
            
            return factors
        except Exception as e:
            logger.error(f"估值因子计算失败: {e}")
            return {'score': 0.5, 'details': str(e)}
    
    def _calculate_trend_factors(self, data: pd.DataFrame) -> Dict[str, Any]:
        try:
            factors = {}
            
            close_prices = data['close'].values
            
            if len(close_prices) < 20:
                factors['score'] = 0.5
                factors['details'] = '数据不足'
                return factors
            
            ma5 = talib.MA(close_prices, 5)[-1]
            ma10 = talib.MA(close_prices, 10)[-1]
            ma20 = talib.MA(close_prices, 20)[-1]
            
            latest_price = close_prices[-1]
            
            ma5_score = self._normalize_trend(latest_price, ma5)
            ma10_score = self._normalize_trend(latest_price, ma10)
            ma20_score = self._normalize_trend(latest_price, ma20)
            
            momentum_score = self._calculate_momentum(close_prices)
            
            factors['score'] = (ma5_score + ma10_score + ma20_score + momentum_score) / 4
            factors['ma5'] = ma5
            factors['ma10'] = ma10
            factors['ma20'] = ma20
            factors['ma5_score'] = ma5_score
            factors['ma10_score'] = ma10_score
            factors['ma20_score'] = ma20_score
            factors['momentum_score'] = momentum_score
            factors['details'] = f'MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}, 动量={momentum_score:.2f}'
            
            return factors
        except Exception as e:
            logger.error(f"趋势因子计算失败: {e}")
            return {'score': 0.5, 'details': str(e)}
    
    def _calculate_fund_factors(self, data: pd.DataFrame) -> Dict[str, Any]:
        try:
            factors = {}
            
            latest_volume = data['volume'].iloc[-1]
            rolling_window = min(20, len(data) - 1) if len(data) > 1 else 1
            avg_volume = data['volume'].iloc[-rolling_window - 1:-1].mean() if rolling_window > 0 else data['volume'].mean()
            latest_amount = data['amount'].iloc[-1]
            avg_amount = data['amount'].iloc[-rolling_window - 1:-1].mean() if rolling_window > 0 else data['amount'].mean()
            
            if avg_volume == 0 or avg_amount == 0 or pd.isna(avg_volume) or pd.isna(avg_amount):
                factors['score'] = 0.5
                factors['details'] = '数据不足'
                return factors
            
            volume_ratio = latest_volume / avg_volume
            amount_ratio = latest_amount / avg_amount
            
            volume_score = self._normalize_volume_ratio(volume_ratio)
            amount_score = self._normalize_amount_ratio(amount_ratio)
            
            factors['score'] = (volume_score + amount_score) / 2
            factors['volume_ratio'] = volume_ratio
            factors['amount_ratio'] = amount_ratio
            factors['volume_score'] = volume_score
            factors['amount_score'] = amount_score
            factors['details'] = f'成交量比率={volume_ratio:.2f}, 成交额比率={amount_ratio:.2f}'
            
            return factors
        except Exception as e:
            logger.error(f"资金因子计算失败: {e}")
            return {'score': 0.5, 'details': str(e)}
    
    def _normalize_pe(self, pe: float) -> float:
        conditions = [pe <= 0, pe <= 10, pe <= 20, pe <= 30, pe <= 50]
        choices = [0.3, 1.0, 0.8, 0.6, 0.4]
        return float(np.select(conditions, choices, default=0.2))

    def _normalize_pb(self, pb: float) -> float:
        conditions = [pb <= 0, pb <= 1.0, pb <= 1.5, pb <= 2.0, pb <= 3.0]
        choices = [0.3, 1.0, 0.8, 0.6, 0.4]
        return float(np.select(conditions, choices, default=0.2))

    def _normalize_trend(self, price: float, ma: float) -> float:
        if ma == 0:
            return 0.5
        ratio = (price - ma) / ma
        conditions = [ratio > 0.1, ratio > 0.05, ratio > 0, ratio > -0.05, ratio > -0.1]
        choices = [1.0, 0.8, 0.6, 0.4, 0.2]
        return float(np.select(conditions, choices, default=0.0))

    def _calculate_momentum(self, prices: np.ndarray) -> float:
        if len(prices) < 5:
            return 0.5
        momentum = (prices[-1] - prices[-5]) / prices[-5]
        conditions = [momentum > 0.05, momentum > 0.02, momentum > 0, momentum > -0.02, momentum > -0.05]
        choices = [1.0, 0.8, 0.6, 0.4, 0.2]
        return float(np.select(conditions, choices, default=0.0))

    def _normalize_volume_ratio(self, ratio: float) -> float:
        conditions = [ratio > 2.0, ratio > 1.5, ratio > 1.0, ratio > 0.5]
        choices = [1.0, 0.8, 0.6, 0.4]
        return float(np.select(conditions, choices, default=0.2))

    def _normalize_amount_ratio(self, ratio: float) -> float:
        conditions = [ratio > 2.0, ratio > 1.5, ratio > 1.0, ratio > 0.5]
        choices = [1.0, 0.8, 0.6, 0.4]
        return float(np.select(conditions, choices, default=0.2))
    
    def _normalize_score(self, score: float) -> float:
        return max(0.0, min(1.0, score))
    
    def _calculate_total_score(self, factors: Dict[str, Any]) -> float:
        total_score = (
            factors['valuation_score'] * self.factor_weights['valuation'] +
            factors['trend_score'] * self.factor_weights['trend'] +
            factors['fund_score'] * self.factor_weights['fund']
        )
        return self._normalize_score(total_score) * 10.0
    
    def update_weights(self, new_weights: Dict[str, float]):
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"因子权重总和不为1.0，当前为{total:.2f}")
        
        self.factor_weights = new_weights
        logger.info(f"因子权重已更新: {self.factor_weights}")
