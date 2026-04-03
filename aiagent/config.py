"""
配置管理模块

定义机器学习模型训练和预测的配置参数
"""

import os
from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class DataConfig:
    """数据准备配置"""
    
    # 数据源配置
    data_sources: Dict[str, str] = field(default_factory=lambda: {
        'market': 'tushare',
        'fundamental': 'tushare',
        'alternative': 'tushare'
    })
    
    # 数据存储配置
    storage_format: str = 'parquet'
    partition_by_date: bool = True
    enable_data_lineage: bool = True
    enable_version_control: bool = True
    
    # 数据质量检查
    check_missing_values: bool = True
    check_price_anomalies: bool = True
    check_timestamp_alignment: bool = True
    
    # 数据路径
    raw_data_dir: str = 'data/tushare/raw'
    processed_data_dir: str = 'data/tushare/processed'
    feature_data_dir: str = 'data/tushare/features'


@dataclass
class FeatureConfig:
    """特征工程配置"""
    
    # 时序特征
    technical_indicators: List[str] = field(default_factory=lambda: [
        'sma', 'ema', 'rsi', 'macd', 'bollinger_bands', 'atr'
    ])
    
    # 统计特征
    statistical_features: List[str] = field(default_factory=lambda: [
        'returns_skewness', 'returns_kurtosis', 'volatility_cluster', 
        'price_momentum_1m', 'price_momentum_3m', 
        'price_momentum_6m', 'price_momentum_12m'
    ])
    
    # 微观结构特征
    microstructure_features: List[str] = field(default_factory=lambda: [
        'bid_ask_spread', 'order_imbalance', 'illiquidity_ratio'
    ])
    
    # 宏观特征
    macro_features: List[str] = field(default_factory=lambda: [
        'term_spread', 'credit_spread', 'vix_index', 'exchange_rate'
    ])
    
    # 特征计算约束
    avoid_lookahead_bias: bool = True
    check_feature_stability: bool = True
    enable_neutralization: bool = True
    
    # 中性化配置
    neutralize_by: List[str] = field(default_factory=lambda: ['market_cap', 'industry'])


@dataclass
class LabelConfig:
    """标签构建配置"""
    
    # 任务类型
    task_type: str = 'classification'  # classification, regression, ranking
    
    # 分类任务配置
    classification_type: str = 'binary'  # binary, ternary
    binary_threshold: float = 0.0
    ternary_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'up': 0.02,
        'down': -0.02
    })
    
    # 回归任务配置
    regression_target: str = 'log_return'  # log_return, sharpe_ratio
    prediction_horizon: int = 5  # 预测未来N日
    
    # 排名任务配置
    ranking_method: str = 'cross_section'  # cross_section, time_series
    
    # 标签时效性
    use_close_to_close: bool = True
    consider_transaction_cost: bool = True
    transaction_cost_rate: float = 0.001


@dataclass
class SplitConfig:
    """时序划分配置"""
    
    # 划分比例
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    
    # 划分策略
    split_strategy: str = 'temporal'  # temporal, rolling_window, expanding_window
    use_time_series_cv: bool = True
    cv_window_size: int = 252  # 一年交易日
    cv_step_size: int = 21  # 一月交易日
    
    # OOT配置
    enable_oot: bool = True
    oot_months: int = 6  # 预留最近6个月


@dataclass
class ModelConfig:
    """模型训练配置"""
    
    # 模型类型
    model_type: str = 'xgboost'  # xgboost, lightgbm, catboost, lstm, transformer
    
    # 损失函数
    loss_function: str = 'weighted_cross_entropy'  # weighted_cross_entropy, focal_loss, huber_loss, quantile_loss, listnet
    
    # 评估指标
    metrics: List[str] = field(default_factory=lambda: [
        'ic', 'rank_ic', 'annual_return', 'max_drawdown', 'sharpe_ratio'
    ])
    
    # 样本权重
    enable_time_decay: bool = True
    decay_factor: float = 0.995
    enable_market_cap_weighting: bool = True
    
    # 正则化策略
    dropout_rate: float = 0.3
    l2_regularization: float = 1e-4
    enable_feature_selection: bool = True
    feature_selection_method: str = 'l1'  # l1, importance_based


@dataclass
class TrainingConfig:
    """训练参数配置"""
    
    # 超参数搜索
    optimization_method: str = 'bayesian'  # bayesian, grid_search, random_search
    n_trials: int = 100
    early_stopping_patience: int = 15
    
    # 训练参数
    n_estimators: int = 1000
    max_depth: int = 6
    learning_rate: float = 0.01
    min_child_weight: float = 1.0
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    
    # 早停配置
    enable_early_stopping: bool = True
    monitor_metric: str = 'val_ic'
    patience: int = 20
    min_delta: float = 0.001
    
    # 模型检查点
    save_best_model: bool = True
    enable_model_ema: bool = True
    ema_decay: float = 0.999


@dataclass
class ModelManagementConfig:
    """模型管理配置"""
    
    # 版本控制
    use_semantic_versioning: bool = True
    version_format: str = 'MAJOR.MINOR.PATCH'
    
    # 模型注册表
    enable_model_registry: bool = True
    enable_model_card: bool = True
    production_ready_threshold: float = 0.03  # IC > 0.03 才能标记为生产版本
    
    # 影子模式
    enable_shadow_mode: bool = False
    shadow_traffic_ratio: float = 0.1  # 10% 流量分配给新版本
    
    # 模型存储
    models_dir: str = 'data/tushare/models'
    enable_hot_swap: bool = True
    enable_ab_testing: bool = True


@dataclass
class PredictionConfig:
    """预测接口配置"""
    
    # 输入输出格式
    input_format: str = 'json'
    output_format: str = 'json'
    
    # 数据校验
    enable_missing_value_handling: bool = True
    missing_value_strategy: str = 'fill_with_mean'  # fill_with_mean, return_error
    enable_data_delay_check: bool = True
    max_delay_seconds: int = 300  # 5分钟
    
    # 风险预警
    enable_drift_detection: bool = True
    drift_threshold: float = 0.1  # 分布差异超过10%触发警告
    enable_outlier_detection: bool = True
    outlier_threshold: float = 0.2  # 预测收益超过20%标记异常
    
    # API配置
    enable_api_key_auth: bool = True
    rate_limit_per_minute: int = 1000
    enable_batch_prediction: bool = True
    enable_websocket: bool = False


@dataclass
class RiskControlConfig:
    """风险控制配置"""
    
    # 关键风险控制点
    ensure_no_data_leakage: bool = True
    ensure_temporal_ordering: bool = True
    ensure_no_future_info: bool = True
    
    # 非平稳性处理
    retrain_frequency: str = 'monthly'  # monthly, quarterly
    detect_non_stationarity: bool = True
    
    # 过拟合防范
    max_train_val_ic_gap: float = 0.02  # 训练集IC - 验证集IC < 0.02 必须弃用
    enable_cross_validation: bool = True
    
    # 实盘一致性
    consider_slippage: bool = True
    slippage_rate: float = 0.001
    consider_transaction_cost: bool = True
    handle_limit_up_down: bool = True
    handle_suspension: bool = True


class Config:
    """主配置类"""
    
    def __init__(self):
        self.data = DataConfig()
        self.feature = FeatureConfig()
        self.label = LabelConfig()
        self.split = SplitConfig()
        self.model = ModelConfig()
        self.training = TrainingConfig()
        self.model_management = ModelManagementConfig()
        self.prediction = PredictionConfig()
        self.risk_control = RiskControlConfig()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'data': self.data.__dict__,
            'feature': self.feature.__dict__,
            'label': self.label.__dict__,
            'split': self.split.__dict__,
            'model': self.model.__dict__,
            'training': self.training.__dict__,
            'model_management': self.model_management.__dict__,
            'prediction': self.prediction.__dict__,
            'risk_control': self.risk_control.__dict__
        }
