import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from app.utils import logger


class IterationOptimizer:
    def __init__(self):
        self.optimization_history = []
        self.parameter_history = []
        self.model_update_history = []
        
        logger.info("迭代优化器初始化完成")
    
    def analyze_performance(self, performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析策略表现"""
        try:
            if not performance_data:
                return {
                    'total_return': 0,
                    'annual_return': 0,
                    'max_drawdown': 0,
                    'sharpe_ratio': 0,
                    'win_rate': 0,
                    'profit_loss_ratio': 0,
                    'volatility': 0
                }
            
            df = pd.DataFrame(performance_data)
            
            daily_returns = df['pnl_pct'].values / 100
            total_return = df['pnl'].sum()
            annual_return = total_return / len(df) * 252 if len(df) > 0 else 0
            
            max_drawdown = df['max_drawdown'].max() if 'max_drawdown' in df.columns else 0
            
            volatility = np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 1 else 0
            sharpe_ratio = annual_return / volatility if volatility > 0 else 0
            
            win_days = df[df['pnl'] > 0]
            win_rate = len(win_days) / len(df) * 100 if len(df) > 0 else 0
            
            profit_days = win_days['pnl'].sum() if len(win_days) > 0 else 0
            loss_days = df[df['pnl'] < 0]['pnl'].sum() if len(df[df['pnl'] < 0]) > 0 else 0
            profit_loss_ratio = abs(profit_days / loss_days) if loss_days < 0 else 0
            
            analysis = {
                'total_return': total_return,
                'annual_return': annual_return,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'win_rate': win_rate,
                'profit_loss_ratio': profit_loss_ratio,
                'volatility': volatility,
                'analysis_date': pd.Timestamp.now().isoformat()
            }
            
            logger.info(f"绩效分析完成: 年化收益{annual_return:.2f}, 夏普比率{sharpe_ratio:.2f}, 胜率{win_rate:.1f}%")
            
            return analysis
            
        except Exception as e:
            logger.error(f"绩效分析失败: {e}")
            return None
    
    def suggest_parameter_adjustments(self, current_params: Dict[str, Any], 
                                  performance: Dict[str, Any]) -> Dict[str, Any]:
        """建议参数调整"""
        try:
            suggestions = {}
            
            if performance['win_rate'] < 40:
                suggestions['signal_thresholds'] = {
                    'buy_score': max(5.0, current_params.get('buy_score', 8.0) - 1.0),
                    'sell_score': max(2.0, current_params.get('sell_score', 3.0) - 0.5),
                    'reason': '胜率偏低，降低信号阈值以增加交易机会'
                }
            elif performance['win_rate'] > 70:
                suggestions['signal_thresholds'] = {
                    'buy_score': min(10.0, current_params.get('buy_score', 8.0) + 0.5),
                    'sell_score': min(5.0, current_params.get('sell_score', 3.0) + 0.5),
                    'reason': '胜率较高，提高信号阈值以提高交易质量'
                }
            
            if performance['max_drawdown'] > 0.15:
                suggestions['position_limits'] = {
                    'single_max': max(0.05, current_params.get('single_max', 0.1) - 0.02),
                    'total_max': max(0.6, current_params.get('total_max', 0.8) - 0.1),
                    'reason': '最大回撤过大，降低仓位限制'
                }
            
            if performance['sharpe_ratio'] < 1.0:
                suggestions['factor_weights'] = {
                    'valuation': 0.25,
                    'trend': 0.50,
                    'fund': 0.25,
                    'reason': '夏普比率偏低，增加趋势因子权重'
                }
            
            if not suggestions:
                suggestions['no_change'] = {
                    'reason': '当前表现良好，无需调整参数'
                }
            
            logger.info(f"参数调整建议: {suggestions}")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"参数调整建议失败: {e}")
            return None
    
    def optimize_parameters(self, current_params: Dict[str, Any], 
                        performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """优化参数"""
        try:
            performance = self.analyze_performance(performance_data)
            
            if performance is None:
                return current_params
            
            suggestions = self.suggest_parameter_adjustments(current_params, performance)
            
            if suggestions is None:
                return current_params
            
            optimized_params = current_params.copy()
            
            if 'signal_thresholds' in suggestions:
                optimized_params.update(suggestions['signal_thresholds'])
            
            if 'position_limits' in suggestions:
                optimized_params.update(suggestions['position_limits'])
            
            if 'factor_weights' in suggestions:
                optimized_params.update(suggestions['factor_weights'])
            
            optimization_record = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'old_params': current_params,
                'new_params': optimized_params,
                'performance': performance,
                'suggestions': suggestions
            }
            
            self.optimization_history.append(optimization_record)
            
            logger.info(f"参数优化完成: {optimized_params}")
            
            return optimized_params
            
        except Exception as e:
            logger.error(f"参数优化失败: {e}")
            return current_params
    
    def should_update_model(self, performance_data: List[Dict[str, Any]], 
                         last_update_date: str = None) -> Tuple[bool, str]:
        """判断是否需要更新模型"""
        try:
            if not performance_data:
                return False, "无绩效数据"
            
            if last_update_date is None:
                return True, "首次运行，需要训练模型"
            
            last_update = datetime.fromisoformat(last_update_date)
            days_since_update = (datetime.now() - last_update).days
            
            if days_since_update >= 30:
                return True, f"距离上次更新已过{days_since_update}天，需要重新训练"
            
            df = pd.DataFrame(performance_data)
            recent_performance = df.tail(10)
            
            if len(recent_performance) > 0:
                recent_win_rate = len(recent_performance[recent_performance['pnl'] > 0]) / len(recent_performance)
                
                if recent_win_rate < 0.4:
                    return True, "近期胜率偏低，需要重新训练模型"
            
            return False, "模型表现良好，无需更新"
            
        except Exception as e:
            logger.error(f"判断模型更新失败: {e}")
            return False, "判断失败"
    
    def update_model(self, training_data: pd.DataFrame, 
                   model_type: str = 'random_forest') -> Dict[str, Any]:
        """更新机器学习模型"""
        try:
            logger.info(f"开始更新{model_type}模型...")
            
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score
            
            features = ['valuation_score', 'trend_score', 'fund_score']
            target = 'future_return_positive'
            
            if target not in training_data.columns:
                training_data[target] = (training_data['future_return'] > 0).astype(int)
            
            X = training_data[features]
            y = training_data[target]
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            feature_importance = dict(zip(features, model.feature_importances_))
            
            model_update_record = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'model_type': model_type,
                'accuracy': accuracy,
                'feature_importance': feature_importance,
                'training_samples': len(training_data)
            }
            
            self.model_update_history.append(model_update_record)
            
            logger.info(f"模型更新完成: 准确率{accuracy:.2%}, 特征重要性{feature_importance}")
            
            return {
                'success': True,
                'model': model,
                'accuracy': accuracy,
                'feature_importance': feature_importance,
                'training_samples': len(training_data)
            }
            
        except Exception as e:
            logger.error(f"更新模型失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_optimization_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取优化历史"""
        return self.optimization_history[-limit:] if self.optimization_history else []
    
    def get_model_update_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取模型更新历史"""
        return self.model_update_history[-limit:] if self.model_update_history else []
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """获取优化汇总"""
        if not self.optimization_history:
            return {
                'total_optimizations': 0,
                'last_optimization': None,
                'parameter_changes': {}
            }
        
        latest = self.optimization_history[-1]
        
        param_changes = {}
        for key in latest['old_params']:
            if key in latest['new_params']:
                old_val = latest['old_params'][key]
                new_val = latest['new_params'][key]
                if old_val != new_val:
                    param_changes[key] = {
                        'old_value': old_val,
                        'new_value': new_val,
                        'change': new_val - old_val,
                        'change_pct': ((new_val - old_val) / old_val * 100) if old_val != 0 else 0
                    }
        
        return {
            'total_optimizations': len(self.optimization_history),
            'last_optimization': latest['timestamp'],
            'last_performance': latest['performance'],
            'parameter_changes': param_changes
        }
    
    def get_model_summary(self) -> Dict[str, Any]:
        """获取模型汇总"""
        if not self.model_update_history:
            return {
                'total_updates': 0,
                'last_update': None,
                'best_accuracy': 0,
                'avg_accuracy': 0
            }
        
        accuracies = [u['accuracy'] for u in self.model_update_history]
        
        return {
            'total_updates': len(self.model_update_history),
            'last_update': self.model_update_history[-1]['timestamp'],
            'best_accuracy': max(accuracies),
            'avg_accuracy': sum(accuracies) / len(accuracies),
            'latest_accuracy': self.model_update_history[-1]['accuracy']
        }
    
    def clear_old_history(self, days: int = 90):
        """清理旧历史记录"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            self.optimization_history = [
                o for o in self.optimization_history 
                if datetime.fromisoformat(o['timestamp']) >= cutoff_date
            ]
            
            self.model_update_history = [
                m for m in self.model_update_history 
                if datetime.fromisoformat(m['timestamp']) >= cutoff_date
            ]
            
            logger.info(f"清理{days}天前的旧优化历史完成")
            
        except Exception as e:
            logger.error(f"清理旧优化历史失败: {e}")
