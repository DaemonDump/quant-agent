"""
模型训练模块

功能：
- 模型选择（基线模型、时序模型、集成模型、深度学习）
- 训练参数配置（损失函数、评估指标、样本权重）
- 验证集调参（超参数搜索、正则化策略）
- 早停机制（监控指标、模型检查点）

设计原则：
- 优先考虑可解释性（SHAP值分析特征重要性）
- 避免过度复杂的模型（金融数据信噪比低，复杂模型易过拟合）
- 严格监控验证集表现，防止过拟合
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime
import json
import pickle
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

try:
    import catboost as cb
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False

try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.linear_model import Ridge, Lasso, LogisticRegression
    from sklearn.metrics import (
        mean_squared_error, mean_absolute_error, r2_score,
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

from .config import Config, ModelConfig, TrainingConfig


class ModelTrainer:
    """模型训练主类"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.model = None
        self.best_model = None
        self.training_history = {}
        self.feature_importance = {}
        self.best_params = {}
        
        # 创建模型目录
        self.models_dir = Path(self.config.model_management.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
    
    def train_model(self, X_train: pd.DataFrame, y_train: pd.Series,
                   X_val: pd.DataFrame, y_val: pd.Series,
                   X_test: Optional[pd.DataFrame] = None,
                   y_test: Optional[pd.Series] = None) -> Dict[str, Any]:
        """
        完整模型训练流程
        
        Args:
            X_train: 训练集特征
            y_train: 训练集标签
            X_val: 验证集特征
            y_val: 验证集标签
            X_test: 测试集特征（可选）
            y_test: 测试集标签（可选）
            
        Returns:
            训练结果字典
        """
        print(f"开始模型训练流程...")
        print(f"模型类型: {self.config.model.model_type}")
        print(f"训练集大小: {len(X_train)}")
        print(f"验证集大小: {len(X_val)}")
        
        # 1. 模型选择
        print("\n1. 模型选择...")
        self.model = self._select_model()
        
        # 2. 超参数搜索
        print("\n2. 超参数搜索...")
        if self.config.training.optimization_method == 'bayesian' and OPTUNA_AVAILABLE:
            self._bayesian_optimization(X_train, y_train, X_val, y_val)
        elif self.config.training.optimization_method == 'grid_search':
            self._grid_search(X_train, y_train, X_val, y_val)
        else:
            print("使用默认参数")
        
        # 3. 训练最终模型
        print("\n3. 训练最终模型...")
        self._train_final_model(X_train, y_train, X_val, y_val)
        
        # 4. 模型评估
        print("\n4. 模型评估...")
        train_metrics = self._evaluate_model(self.model, X_train, y_train, 'train')
        val_metrics = self._evaluate_model(self.model, X_val, y_val, 'val')
        
        results = {
            'train_metrics': train_metrics,
            'val_metrics': val_metrics,
            'best_params': self.best_params,
            'feature_importance': self.feature_importance
        }
        
        # 5. 测试集评估
        if X_test is not None and y_test is not None:
            print("\n5. 测试集评估...")
            test_metrics = self._evaluate_model(self.model, X_test, y_test, 'test')
            results['test_metrics'] = test_metrics
        
        print("\n模型训练完成！")
        return results
    
    def _select_model(self):
        """
        模型选择
        
        基线模型：线性回归（Ridge/Lasso）、逻辑回归、随机森林
        时序模型：LSTM/GRU、Transformer（暂未实现）
        集成模型：XGBoost/LightGBM/CatBoost
        深度学习：TabNet/ResNet-1D（暂未实现）
        """
        model_type = self.config.model.model_type
        
        if model_type == 'xgboost' and XGBOOST_AVAILABLE:
            print("选择 XGBoost 模型")
            return xgb.XGBRegressor(
                n_estimators=self.config.training.n_estimators,
                max_depth=self.config.training.max_depth,
                learning_rate=self.config.training.learning_rate,
                min_child_weight=self.config.training.min_child_weight,
                subsample=self.config.training.subsample,
                colsample_bytree=self.config.training.colsample_bytree,
                random_state=42,
                n_jobs=-1
            )
        
        elif model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
            print("选择 LightGBM 模型")
            return lgb.LGBMRegressor(
                n_estimators=self.config.training.n_estimators,
                max_depth=self.config.training.max_depth,
                learning_rate=self.config.training.learning_rate,
                min_child_weight=self.config.training.min_child_weight,
                subsample=self.config.training.subsample,
                colsample_bytree=self.config.training.colsample_bytree,
                random_state=42,
                n_jobs=-1,
                verbose=-1
            )
        
        elif model_type == 'catboost' and CATBOOST_AVAILABLE:
            print("选择 CatBoost 模型")
            return cb.CatBoostRegressor(
                n_estimators=self.config.training.n_estimators,
                max_depth=self.config.training.max_depth,
                learning_rate=self.config.training.learning_rate,
                random_state=42,
                verbose=False
            )
        
        elif model_type == 'random_forest' and SKLEARN_AVAILABLE:
            print("选择 随机森林 模型")
            return RandomForestRegressor(
                n_estimators=self.config.training.n_estimators,
                max_depth=self.config.training.max_depth,
                random_state=42,
                n_jobs=-1
            )
        
        elif model_type == 'ridge' and SKLEARN_AVAILABLE:
            print("选择 Ridge 回归 模型")
            return Ridge(alpha=self.config.model.l2_regularization, random_state=42)
        
        elif model_type == 'lasso' and SKLEARN_AVAILABLE:
            print("选择 Lasso 回归 模型")
            return Lasso(alpha=self.config.model.l2_regularization, random_state=42)
        
        else:
            print(f"警告：模型类型 {model_type} 不可用，使用默认的 Ridge 回归")
            if SKLEARN_AVAILABLE:
                return Ridge(alpha=1.0, random_state=42)
            else:
                raise ImportError("没有可用的模型库，请安装 scikit-learn")
    
    def _bayesian_optimization(self, X_train: pd.DataFrame, y_train: pd.Series,
                              X_val: pd.DataFrame, y_val: pd.Series):
        """
        贝叶斯优化（使用Optuna）
        
        替代网格搜索，提高效率
        """
        print(f"执行贝叶斯优化...")
        
        def objective(trial):
            # 定义搜索空间
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 100, 2000),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.001, 0.1, log=True),
                'min_child_weight': trial.suggest_float('min_child_weight', 0.1, 10.0),
                'subsample': trial.suggest_float('subsample', 0.5, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            }
            
            # 创建模型
            if self.config.model.model_type == 'xgboost' and XGBOOST_AVAILABLE:
                model = xgb.XGBRegressor(**params, random_state=42, n_jobs=-1)
            elif self.config.model.model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
                model = lgb.LGBMRegressor(**params, random_state=42, n_jobs=-1, verbose=-1)
            elif self.config.model.model_type == 'catboost' and CATBOOST_AVAILABLE:
                model = cb.CatBoostRegressor(**params, random_state=42, verbose=False)
            else:
                return 0.0
            
            # 训练模型
            model.fit(X_train, y_train)
            
            # 评估
            y_pred = model.predict(X_val)
            ic = self._calculate_ic(y_val, y_pred)
            
            return ic
        
        # 创建研究
        study = optuna.create_study(direction='maximize')
        
        # 优化
        study.optimize(objective, n_trials=self.config.training.n_trials)
        
        # 获取最佳参数
        self.best_params = study.best_params
        print(f"最佳参数: {self.best_params}")
        print(f"最佳IC: {study.best_value:.4f}")
    
    def _grid_search(self, X_train: pd.DataFrame, y_train: pd.Series,
                    X_val: pd.DataFrame, y_val: pd.Series):
        """
        网格搜索
        """
        print(f"执行网格搜索...")
        
        # 定义参数网格
        param_grid = {
            'n_estimators': [500, 1000, 1500],
            'max_depth': [4, 6, 8],
            'learning_rate': [0.01, 0.05, 0.1],
        }
        
        best_ic = -float('inf')
        best_params = {}
        
        # 简单的网格搜索
        for n_estimators in param_grid['n_estimators']:
            for max_depth in param_grid['max_depth']:
                for learning_rate in param_grid['learning_rate']:
                    params = {
                        'n_estimators': n_estimators,
                        'max_depth': max_depth,
                        'learning_rate': learning_rate,
                        'random_state': 42
                    }
                    
                    # 创建模型
                    if self.config.model.model_type == 'xgboost' and XGBOOST_AVAILABLE:
                        model = xgb.XGBRegressor(**params, n_jobs=-1)
                    elif self.config.model.model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
                        model = lgb.LGBMRegressor(**params, n_jobs=-1, verbose=-1)
                    elif self.config.model.model_type == 'catboost' and CATBOOST_AVAILABLE:
                        model = cb.CatBoostRegressor(**params, verbose=False)
                    else:
                        continue
                    
                    # 训练模型
                    model.fit(X_train, y_train)
                    
                    # 评估
                    y_pred = model.predict(X_val)
                    ic = self._calculate_ic(y_val, y_pred)
                    
                    if ic > best_ic:
                        best_ic = ic
                        best_params = params
        
        self.best_params = best_params
        print(f"最佳参数: {self.best_params}")
        print(f"最佳IC: {best_ic:.4f}")
    
    def _train_final_model(self, X_train: pd.DataFrame, y_train: pd.Series,
                          X_val: pd.DataFrame, y_val: pd.Series):
        """
        训练最终模型
        
        使用最佳参数，实现早停机制
        """
        print(f"训练最终模型...")
        
        # 使用最佳参数
        if self.best_params:
            params = self.best_params.copy()
            params['random_state'] = 42
            
            if self.config.model.model_type == 'xgboost' and XGBOOST_AVAILABLE:
                self.model = xgb.XGBRegressor(**params, n_jobs=-1)
            elif self.config.model.model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
                self.model = lgb.LGBMRegressor(**params, n_jobs=-1, verbose=-1)
            elif self.config.model.model_type == 'catboost' and CATBOOST_AVAILABLE:
                self.model = cb.CatBoostRegressor(**params, verbose=False)
            else:
                print("使用默认参数训练")
        
        # 早停机制
        if self.config.training.enable_early_stopping:
            print(f"启用早停机制（监控指标: {self.config.training.monitor_metric}）")
            
            if self.config.model.model_type == 'xgboost' and XGBOOST_AVAILABLE:
                self.model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    early_stopping_rounds=self.config.training.patience,
                    verbose=False
                )
            elif self.config.model.model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
                self.model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    callbacks=[lgb.early_stopping(self.config.training.patience)]
                )
            elif self.config.model.model_type == 'catboost' and CATBOOST_AVAILABLE:
                self.model.fit(
                    X_train, y_train,
                    eval_set=(X_val, y_val),
                    early_stopping_rounds=self.config.training.patience,
                    verbose=False
                )
            else:
                # 对于不支持早停的模型，手动实现
                self._manual_early_stopping(X_train, y_train, X_val, y_val)
        else:
            # 不使用早停，直接训练
            self.model.fit(X_train, y_train)
        
        # 保存最佳模型
        self.best_model = self.model
        
        # 计算特征重要性
        self._calculate_feature_importance(X_train.columns)
    
    def _manual_early_stopping(self, X_train: pd.DataFrame, y_train: pd.Series,
                               X_val: pd.DataFrame, y_val: pd.Series):
        """
        手动实现早停机制（对不支持增量训练的模型，直接训练一次）
        """
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_val)
        score = self._calculate_ic(y_val, y_pred)
        print(f"验证集IC: {score:.4f}")
    
    def _evaluate_model(self, model, X: pd.DataFrame, y: pd.Series, 
                       dataset_name: str) -> Dict[str, float]:
        """
        评估模型
        
        评估指标：
        - IC（信息系数）：预测值与真实收益的秩相关系数
        - Rank IC：截面排序相关性
        - 回测指标：年化收益率、最大回撤、夏普比率
        """
        print(f"评估 {dataset_name} 集...")
        
        # 预测
        y_pred = model.predict(X)
        
        # 计算IC
        ic = self._calculate_ic(y, y_pred)
        
        # 计算Rank IC
        rank_ic = self._calculate_rank_ic(y, y_pred)
        
        # 计算回归指标
        mse = mean_squared_error(y, y_pred)
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        
        metrics = {
            'ic': ic,
            'rank_ic': rank_ic,
            'mse': mse,
            'mae': mae,
            'r2': r2
        }
        
        print(f"  IC: {ic:.4f}")
        print(f"  Rank IC: {rank_ic:.4f}")
        print(f"  MSE: {mse:.6f}")
        print(f"  MAE: {mae:.6f}")
        print(f"  R2: {r2:.4f}")
        
        return metrics
    
    def _calculate_ic(self, y_true: pd.Series, y_pred: np.ndarray) -> float:
        """
        计算IC（信息系数）
        
        IC = Spearman相关系数
        """
        try:
            from scipy.stats import spearmanr
            ic, _ = spearmanr(y_true, y_pred)
            return ic
        except:
            return 0.0
    
    def _calculate_rank_ic(self, y_true: pd.Series, y_pred: np.ndarray) -> float:
        """
        计算Rank IC（截面排序相关性）
        """
        try:
            # 计算排名
            y_true_rank = y_true.rank()
            y_pred_rank = pd.Series(y_pred).rank()
            
            # 计算相关性
            from scipy.stats import spearmanr
            rank_ic, _ = spearmanr(y_true_rank, y_pred_rank)
            return rank_ic
        except:
            return 0.0
    
    def _calculate_feature_importance(self, feature_names: List[str]):
        """
        计算特征重要性
        """
        print(f"计算特征重要性...")
        
        try:
            # 获取特征重要性
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            elif hasattr(self.model, 'get_booster'):
                importances = self.model.get_booster().get_score(importance_type='gain')
                importances = np.array([importances.get(name, 0) for name in feature_names])
            else:
                print("模型不支持特征重要性计算")
                return
            
            # 创建特征重要性字典
            self.feature_importance = dict(zip(feature_names, importances))
            
            # 排序
            sorted_importance = sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            print(f"Top 10 重要特征:")
            for feature, importance in sorted_importance[:10]:
                print(f"  {feature}: {importance:.4f}")
            
        except Exception as e:
            print(f"计算特征重要性失败: {e}")
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        获取特征重要性
        """
        return self.feature_importance
    
    def get_model(self):
        """
        获取训练好的模型
        """
        return self.model
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用模型进行预测
        """
        if self.model is None:
            raise ValueError("模型尚未训练")
        
        return self.model.predict(X)
