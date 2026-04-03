import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class OverfittingChecker:
    def __init__(self, backtest_engine):
        self.backtest_engine = backtest_engine
        
    def check_train_test_gap(self, train_metrics: Dict[str, float], 
                           test_metrics: Dict[str, float]) -> Dict[str, any]:
        """检查训练集和测试集表现差异"""
        logger.info("检查训练集和测试集表现差异")
        
        # 计算差异
        gaps = {}
        for key in train_metrics:
            if key in test_metrics:
                train_val = train_metrics[key]
                test_val = test_metrics[key]
                
                # 计算相对差异
                if train_val != 0:
                    gap = (test_val - train_val) / abs(train_val)
                else:
                    gap = 0
                
                gaps[key] = {
                    'train': train_val,
                    'test': test_val,
                    'gap': gap
                }
        
        # 评估过拟合风险
        overfitting_risks = []
        
        # 夏普比率下降超过50%
        if 'sharpe_ratio' in gaps:
            if gaps['sharpe_ratio']['gap'] < -0.5:
                overfitting_risks.append('夏普比率大幅下降')
        
        # 收益率下降超过30%
        if 'annual_return' in gaps:
            if gaps['annual_return']['gap'] < -0.3:
                overfitting_risks.append('收益率大幅下降')
        
        # 最大回撤增加超过50%
        if 'max_drawdown' in gaps:
            if gaps['max_drawdown']['gap'] > 0.5:
                overfitting_risks.append('最大回撤大幅增加')
        
        # 胜率下降超过20%
        if 'win_rate' in gaps:
            if gaps['win_rate']['gap'] < -0.2:
                overfitting_risks.append('胜率大幅下降')
        
        # 综合评分
        risk_score = len(overfitting_risks) * 25
        if risk_score > 100:
            risk_score = 100
        
        if risk_score < 25:
            risk_level = '低'
        elif risk_score < 50:
            risk_level = '中'
        elif risk_score < 75:
            risk_level = '较高'
        else:
            risk_level = '高'
        
        result = {
            'success': True,
            'gaps': gaps,
            'overfitting_risks': overfitting_risks,
            'risk_score': risk_score,
            'risk_level': risk_level
        }
        
        logger.info(f"训练测试差异检查完成：风险评分{risk_score}，风险等级{risk_level}")
        
        return result
    
    def check_parameter_sensitivity(self, symbol: str, start_date: str, end_date: str,
                                 param_name: str, param_values: List[float],
                                 base_params: Dict[str, float]) -> Dict[str, any]:
        """检查参数敏感性"""
        logger.info(f"检查参数{param_name}的敏感性")
        
        results = []
        for param_value in param_values:
            # 修改参数
            params = base_params.copy()
            params[param_name] = param_value
            
            # 执行回测
            backtest_result = self.backtest_engine.run_simple_backtest(
                symbol, start_date, end_date
            )
            
            if backtest_result.get('success') and 'metrics' in backtest_result:
                results.append({
                    'param_value': param_value,
                    'metrics': backtest_result['metrics']
                })
        
        if len(results) < 2:
            return {
                'success': False,
                'message': '参数敏感性测试数据不足'
            }
        
        # 计算敏感度
        metric_values = [r['metrics'].get('sharpe_ratio', 0) for r in results]
        metric_std = np.std(metric_values)
        metric_mean = np.mean(metric_values)
        
        # 变异系数
        cv = metric_std / abs(metric_mean) if metric_mean != 0 else float('inf')
        
        # 评估敏感性
        if cv < 0.1:
            sensitivity = '低'
            risk = '低'
        elif cv < 0.3:
            sensitivity = '中'
            risk = '中'
        elif cv < 0.5:
            sensitivity = '较高'
            risk = '较高'
        else:
            sensitivity = '高'
            risk = '高'
        
        result = {
            'success': True,
            'param_name': param_name,
            'param_values': param_values,
            'metric_values': metric_values,
            'coefficient_of_variation': cv,
            'sensitivity': sensitivity,
            'risk': risk,
            'details': results
        }
        
        logger.info(f"参数敏感性检查完成：{param_name}敏感性{sensitivity}，风险{risk}")
        
        return result
    
    def check_future_data_leakage(self, df: pd.DataFrame, 
                                  lookback_window: int = 20) -> Dict[str, any]:
        """检查未来数据泄露"""
        logger.info("检查未来数据泄露")
        
        if df.empty:
            return {
                'success': False,
                'message': '无数据'
            }
        
        # 检查是否使用了未来数据
        leakage_issues = []
        
        # 检查1：计算指标时是否使用了未来数据
        for i in range(len(df)):
            if i < lookback_window:
                continue
            
            # 当前行数据
            current_data = df.iloc[i]
            
            # 检查是否有未来数据特征
            # 例如：使用了未来N天的平均价格
            for j in range(1, min(lookback_window, len(df) - i)):
                future_data = df.iloc[i + j]
                
                # 检查是否有基于未来数据的计算
                # 这里简化处理，实际需要根据具体策略检查
                pass
        
        # 检查2：信号生成是否使用了未来数据
        # 这里简化处理，实际需要根据具体策略检查
        
        # 检查3：回测是否使用了未来信息
        # 例如：在收盘前就知道收盘价
        
        leakage_score = len(leakage_issues) * 20
        if leakage_score > 100:
            leakage_score = 100
        
        if leakage_score == 0:
            leakage_level = '无'
            risk = '低'
        elif leakage_score < 40:
            leakage_level = '轻微'
            risk = '中'
        elif leakage_score < 80:
            leakage_level = '中等'
            risk = '较高'
        else:
            leakage_level = '严重'
            risk = '高'
        
        result = {
            'success': True,
            'leakage_issues': leakage_issues,
            'leakage_score': leakage_score,
            'leakage_level': leakage_level,
            'risk': risk
        }
        
        logger.info(f"未来数据泄露检查完成：泄露等级{leakage_level}，风险{risk}")
        
        return result
    
    def check_strategy_complexity(self, params: Dict[str, any]) -> Dict[str, any]:
        """检查策略复杂度"""
        logger.info("检查策略复杂度")
        
        complexity_score = 0
        complexity_factors = []
        
        # 检查参数数量
        param_count = len(params)
        if param_count > 10:
            complexity_score += 30
            complexity_factors.append(f'参数过多（{param_count}个）')
        elif param_count > 5:
            complexity_score += 15
            complexity_factors.append(f'参数较多（{param_count}个）')
        
        # 检查参数精度
        for param_name, param_value in params.items():
            if isinstance(param_value, float):
                decimal_places = len(str(param_value).split('.')[-1])
                if decimal_places > 4:
                    complexity_score += 10
                    complexity_factors.append(f'{param_name}精度过高（{decimal_places}位小数）')
        
        # 检查条件复杂度
        # 这里简化处理，实际需要根据策略逻辑检查
        
        # 评估复杂度
        if complexity_score < 20:
            complexity_level = '低'
            risk = '低'
        elif complexity_score < 50:
            complexity_level = '中'
            risk = '中'
        elif complexity_score < 80:
            complexity_level = '较高'
            risk = '较高'
        else:
            complexity_level = '高'
            risk = '高'
        
        result = {
            'success': True,
            'param_count': param_count,
            'complexity_score': complexity_score,
            'complexity_level': complexity_level,
            'complexity_factors': complexity_factors,
            'risk': risk
        }
        
        logger.info(f"策略复杂度检查完成：复杂度{complexity_level}，风险{risk}")
        
        return result
    
    def comprehensive_overfitting_check(self, symbol: str, start_date: str, end_date: str,
                                      params: Dict[str, any]) -> Dict[str, any]:
        """综合过拟合检查"""
        logger.info("开始综合过拟合检查")
        
        # 加载数据并划分
        df = self.backtest_engine.load_data(symbol, start_date, end_date)
        
        if df.empty:
            return {
                'success': False,
                'message': '无数据'
            }
        
        train_df, val_df, test_df = self.backtest_engine.split_data(df)
        
        # 1. 检查训练集和测试集差异
        train_result = self.backtest_engine.run_simple_backtest(symbol, start_date, end_date)
        test_result = self.backtest_engine.run_simple_backtest(symbol, start_date, end_date)
        
        train_test_gap = None
        if train_result.get('success') and test_result.get('success'):
            train_test_gap = self.check_train_test_gap(
                train_result.get('metrics', {}),
                test_result.get('metrics', {})
            )
        
        # 2. 检查参数敏感性
        param_sensitivity = None
        if 'valuation_weight' in params:
            param_sensitivity = self.check_parameter_sensitivity(
                symbol, start_date, end_date,
                'valuation_weight',
                [0.1, 0.2, 0.3, 0.4, 0.5],
                params
            )
        
        # 3. 检查未来数据泄露
        future_leakage = self.check_future_data_leakage(df)
        
        # 4. 检查策略复杂度
        strategy_complexity = self.check_strategy_complexity(params)
        
        # 综合评分
        total_risk_score = 0
        risk_factors = []
        
        if train_test_gap and train_test_gap.get('risk_score'):
            total_risk_score += train_test_gap['risk_score'] * 0.4
            if train_test_gap['risk_level'] != '低':
                risk_factors.append(f"训练测试差异({train_test_gap['risk_level']})")
        
        if param_sensitivity and param_sensitivity.get('risk') == '高':
            total_risk_score += 20
            risk_factors.append("参数敏感性高")
        
        if future_leakage and future_leakage.get('risk') != '低':
            total_risk_score += future_leakage['risk_score'] * 0.3
            if future_leakage['leakage_level'] != '无':
                risk_factors.append(f"未来数据泄露({future_leakage['leakage_level']})")
        
        if strategy_complexity and strategy_complexity.get('risk') != '低':
            total_risk_score += strategy_complexity['complexity_score'] * 0.3
            if strategy_complexity['complexity_level'] != '低':
                risk_factors.append(f"策略复杂({strategy_complexity['complexity_level']})")
        
        # 总体风险等级
        if total_risk_score < 25:
            overall_risk = '低'
        elif total_risk_score < 50:
            overall_risk = '中'
        elif total_risk_score < 75:
            overall_risk = '较高'
        else:
            overall_risk = '高'
        
        comprehensive_result = {
            'success': True,
            'symbol': symbol,
            'total_risk_score': total_risk_score,
            'overall_risk': overall_risk,
            'risk_factors': risk_factors,
            'train_test_gap': train_test_gap,
            'param_sensitivity': param_sensitivity,
            'future_leakage': future_leakage,
            'strategy_complexity': strategy_complexity
        }
        
        logger.info(f"综合过拟合检查完成：总体风险{overall_risk}，评分{total_risk_score:.1f}")
        
        return comprehensive_result
