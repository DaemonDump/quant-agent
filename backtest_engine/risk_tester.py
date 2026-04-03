import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class RiskTester:
    def __init__(self, backtest_engine):
        self.backtest_engine = backtest_engine
        
    def calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """计算风险价值（VaR）"""
        if len(returns) == 0:
            return 0.0
        return np.percentile(returns, (1 - confidence) * 100)
    
    def calculate_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """计算条件风险价值（CVaR）"""
        if len(returns) == 0:
            return 0.0
        var = self.calculate_var(returns, confidence)
        return returns[returns <= var].mean()
    
    def calculate_max_consecutive_losses(self, returns: pd.Series) -> int:
        """计算最大连续亏损次数"""
        if len(returns) == 0:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for ret in returns:
            if ret < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def calculate_volatility(self, returns: pd.Series, window: int = 20) -> pd.Series:
        """计算波动率"""
        return returns.rolling(window=window).std() * np.sqrt(252)
    
    def stress_test(self, symbol: str, start_date: str, end_date: str) -> Dict[str, any]:
        """极端场景压力测试"""
        logger.info("开始极端场景压力测试")
        
        df = self.backtest_engine.load_data(symbol, start_date, end_date)
        
        if df.empty:
            return {
                'success': False,
                'message': '无数据'
            }
        
        # 计算收益率
        returns = self.backtest_engine.calculate_returns(df)
        
        # 场景1：市场暴跌（单日跌幅超过5%）
        crash_days = returns[returns < -0.05]
        crash_count = len(crash_days)
        crash_avg_loss = crash_days.mean() if crash_count > 0 else 0
        
        # 场景2：连续下跌（连续5天下跌）
        consecutive_losses = self.calculate_max_consecutive_losses(returns)
        
        # 场景3：高波动期（波动率超过均值2倍）
        volatility = self.calculate_volatility(returns)
        high_vol_periods = volatility[volatility > volatility.mean() * 2]
        high_vol_count = len(high_vol_periods)
        
        # 场景4：极端损失（单日跌幅超过8%）
        extreme_losses = returns[returns < -0.08]
        extreme_loss_count = len(extreme_losses)
        extreme_loss_avg = extreme_losses.mean() if extreme_loss_count > 0 else 0
        
        # 风险指标
        var_95 = self.calculate_var(returns, 0.95)
        var_99 = self.calculate_var(returns, 0.99)
        cvar_95 = self.calculate_cvar(returns, 0.95)
        cvar_99 = self.calculate_cvar(returns, 0.99)
        
        stress_results = {
            'success': True,
            'symbol': symbol,
            'crash_scenarios': {
                'count': crash_count,
                'avg_loss': float(crash_avg_loss) if crash_count > 0 else 0
            },
            'consecutive_losses': consecutive_losses,
            'high_volatility_periods': high_vol_count,
            'extreme_losses': {
                'count': extreme_loss_count,
                'avg_loss': float(extreme_loss_avg) if extreme_loss_count > 0 else 0
            },
            'risk_metrics': {
                'var_95': float(var_95),
                'var_99': float(var_99),
                'cvar_95': float(cvar_95),
                'cvar_99': float(cvar_99)
            }
        }
        
        logger.info(f"压力测试完成：暴跌{crash_count}次，最大连续亏损{consecutive_losses}次")
        
        return stress_results
    
    def market_regime_test(self, symbol: str, start_date: str, end_date: str) -> Dict[str, any]:
        """市场环境测试（牛市、震荡市、熊市）"""
        logger.info("开始市场环境测试")
        
        df = self.backtest_engine.load_data(symbol, start_date, end_date)
        
        if df.empty:
            return {
                'success': False,
                'message': '无数据'
            }
        
        # 计算收益率和移动平均
        returns = self.backtest_engine.calculate_returns(df)
        ma20 = df['close_price'].rolling(window=20).mean()
        ma60 = df['close_price'].rolling(window=60).mean()
        
        # 判断市场环境
        regimes = []
        for i in range(len(df)):
            if i < 60:
                regimes.append('unknown')
                continue
            
            price = df['close_price'].iloc[i]
            ma20_val = ma20.iloc[i]
            ma60_val = ma60.iloc[i]
            
            # 牛市：价格 > MA20 > MA60
            if price > ma20_val and ma20_val > ma60_val:
                regimes.append('bull')
            # 熊市：价格 < MA20 < MA60
            elif price < ma20_val and ma20_val < ma60_val:
                regimes.append('bear')
            # 震荡市：其他情况
            else:
                regimes.append('sideways')
        
        # 统计各环境表现
        df['regime'] = regimes
        df['returns'] = returns
        
        regime_performance = {}
        for regime in ['bull', 'bear', 'sideways']:
            regime_data = df[df['regime'] == regime]
            if len(regime_data) > 0:
                regime_returns = regime_data['returns'].dropna()
                if len(regime_returns) > 0:
                    regime_performance[regime] = {
                        'days': len(regime_data),
                        'total_return': float((1 + regime_returns).prod() - 1),
                        'avg_return': float(regime_returns.mean()),
                        'volatility': float(regime_returns.std()),
                        'win_rate': float((regime_returns > 0).sum() / len(regime_returns))
                    }
        
        logger.info(f"市场环境测试完成：牛市{len(df[df['regime']=='bull'])}天，熊市{len(df[df['regime']=='bear'])}天，震荡市{len(df[df['regime']=='sideways'])}天")
        
        return {
            'success': True,
            'symbol': symbol,
            'regime_performance': regime_performance
        }
    
    def liquidity_test(self, symbol: str, start_date: str, end_date: str) -> Dict[str, any]:
        """流动性测试"""
        logger.info("开始流动性测试")
        
        df = self.backtest_engine.load_data(symbol, start_date, end_date)
        
        if df.empty:
            return {
                'success': False,
                'message': '无数据'
            }
        
        # 流动性指标
        avg_volume = df['volume'].mean()
        avg_amount = df['amount'].mean()
        volume_std = df['volume'].std()
        
        # 低流动性天数（成交量低于均值的50%）
        low_liquidity_days = df[df['volume'] < avg_volume * 0.5]
        
        # 高流动性天数（成交量超过均值的150%）
        high_liquidity_days = df[df['volume'] > avg_volume * 1.5]
        
        liquidity_results = {
            'success': True,
            'symbol': symbol,
            'avg_volume': float(avg_volume),
            'avg_amount': float(avg_amount),
            'volume_std': float(volume_std),
            'volume_cv': float(volume_std / avg_volume) if avg_volume > 0 else 0,
            'low_liquidity_days': len(low_liquidity_days),
            'high_liquidity_days': len(high_liquidity_days),
            'liquidity_ratio': float(len(high_liquidity_days) / len(low_liquidity_days)) if len(low_liquidity_days) > 0 else 0
        }
        
        logger.info(f"流动性测试完成：平均成交量{avg_volume:.0f}，低流动性{len(low_liquidity_days)}天")
        
        return liquidity_results
    
    def comprehensive_risk_test(self, symbol: str, start_date: str, end_date: str) -> Dict[str, any]:
        """综合风险测试"""
        logger.info("开始综合风险测试")
        
        # 压力测试
        stress_result = self.stress_test(symbol, start_date, end_date)
        
        # 市场环境测试
        regime_result = self.market_regime_test(symbol, start_date, end_date)
        
        # 流动性测试
        liquidity_result = self.liquidity_test(symbol, start_date, end_date)
        
        # 综合评分
        risk_score = 0
        risk_factors = []
        
        if stress_result.get('success'):
            # 暴跌次数过多
            if stress_result['crash_scenarios']['count'] > 5:
                risk_score += 20
                risk_factors.append('暴跌风险')
            
            # 连续亏损过多
            if stress_result['consecutive_losses'] > 10:
                risk_score += 15
                risk_factors.append('连续亏损风险')
            
            # VaR过大
            if abs(stress_result['risk_metrics']['var_95']) > 0.05:
                risk_score += 15
                risk_factors.append('下行风险')
        
        if regime_result.get('success'):
            # 熊市表现差
            if 'bear' in regime_result['regime_performance']:
                bear_return = regime_result['regime_performance']['bear']['total_return']
                if bear_return < -0.2:
                    risk_score += 20
                    risk_factors.append('熊市风险')
        
        if liquidity_result.get('success'):
            # 流动性差
            if liquidity_result['liquidity_ratio'] < 0.5:
                risk_score += 15
                risk_factors.append('流动性风险')
        
        # 风险等级
        if risk_score < 20:
            risk_level = '低'
        elif risk_score < 50:
            risk_level = '中'
        else:
            risk_level = '高'
        
        comprehensive_results = {
            'success': True,
            'symbol': symbol,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'stress_test': stress_result,
            'regime_test': regime_result,
            'liquidity_test': liquidity_result
        }
        
        logger.info(f"综合风险测试完成：风险评分{risk_score}，风险等级{risk_level}")
        
        return comprehensive_results
