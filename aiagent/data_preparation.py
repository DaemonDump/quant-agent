"""
数据准备模块

功能：
- 历史数据获取（行情、基础、另类数据）
- 特征计算（时序、统计、微观、宏观特征）
- 标签构建（分类、回归、排名任务）
- 时序划分（训练/验证/测试、OOT、时序交叉验证）

设计原则：
- 严格避免前视偏差（Look-ahead Bias）
- 严禁随机划分，必须按时间顺序划分
- 防止数据泄露，确保时序约束不被破坏
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import os
import json
import sqlite3
from pathlib import Path

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

from .config import Config, DataConfig, FeatureConfig, LabelConfig, SplitConfig


class DataPreparation:
    """数据准备主类"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.raw_data_dir = Path(self.config.data.raw_data_dir)
        self.processed_data_dir = Path(self.config.data.processed_data_dir)
        self.feature_data_dir = Path(self.config.data.feature_data_dir)
        
        # 创建目录
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        self.feature_data_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_data(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
        """
        完整数据准备流程
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            包含训练、验证、测试集的字典
        """
        print(f"开始数据准备流程...")
        print(f"股票池: {symbols}")
        print(f"时间范围: {start_date} 至 {end_date}")
        
        # 1. 获取历史数据
        print("\n1. 获取历史数据...")
        market_data = self._fetch_market_data(symbols, start_date, end_date)
        fundamental_data = self._fetch_fundamental_data(symbols, start_date, end_date)
        alternative_data = self._fetch_alternative_data(symbols, start_date, end_date)
        
        # 2. 数据质量检查
        print("\n2. 数据质量检查...")
        market_data = self._check_data_quality(market_data)
        
        # 3. 数据存储
        print("\n3. 数据存储...")
        self._store_raw_data(market_data, fundamental_data, alternative_data)
        
        # 4. 特征计算
        print("\n4. 特征计算...")
        features = self._calculate_features(market_data, fundamental_data, alternative_data)
        
        # 5. 标签构建
        print("\n5. 标签构建...")
        labels = self._construct_labels(market_data)
        
        # 6. 合并特征和标签
        print("\n6. 合并特征和标签...")
        full_data = self._merge_features_labels(features, labels)
        
        # 7. 时序划分
        print("\n7. 时序划分...")
        splits = self._temporal_split(full_data)
        
        print("\n数据准备完成！")
        return splits
    
    def _fetch_market_data(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取行情数据（OHLCV）
        
        严格避免前视偏差：只获取历史数据，不使用未来信息
        """
        print(f"获取行情数据...")
        
        try:
            from data_ingestion import RealTimeDataCollector
            
            collector = RealTimeDataCollector()
            
            # 从数据库获取历史数据
            market_data = []
            for symbol in symbols:
                data = collector.get_historical_data(symbol, start_date, end_date)
                if not data.empty:
                    market_data.append(data)
            
            if market_data:
                result = pd.concat(market_data, ignore_index=True)
                print(f"成功获取 {len(result)} 条行情数据")
                return result
            else:
                print("警告：未获取到行情数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"获取行情数据失败: {e}")
            return pd.DataFrame()
    
    def _fetch_fundamental_data(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取基础数据（财务报表、宏观指标、行业分类、市值）
        """
        print(f"获取基础数据...")
        
        # 这里实现基础数据获取逻辑
        # 暂时返回空DataFrame，后续可以接入Tushare等数据源
        
        return pd.DataFrame()
    
    def _fetch_alternative_data(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取另类数据（舆情、资金流向、分析师预期、北向资金）
        """
        print(f"获取另类数据...")
        
        # 这里实现另类数据获取逻辑
        # 暂时返回空DataFrame，后续可以接入相关数据源
        
        return pd.DataFrame()
    
    def _check_data_quality(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        数据质量检查
        
        检查项：
        - 缺失值检测
        - 价格异常值检测（涨跌停未成交识别）
        - 时间戳对齐
        """
        print(f"执行数据质量检查...")
        
        if data.empty:
            print("警告：数据为空")
            return data
        
        checked_data = data.copy()
        
        # 1. 缺失值检测
        if self.config.data.check_missing_values:
            missing_count = checked_data.isnull().sum()
            if missing_count.sum() > 0:
                print(f"发现缺失值: {missing_count.to_dict()}")
                # 对缺失值进行处理
                checked_data = checked_data.ffill().bfill()
        
        # 2. 价格异常值检测
        if self.config.data.check_price_anomalies:
            # 检测涨跌停未成交的情况
            # 涨跌停：high == low 且 volume == 0
            prev_close = checked_data['close'].shift(1)
            _frozen = (checked_data['high'] == checked_data['low']) & (checked_data['vol'] == 0)
            limit_up = _frozen & (checked_data['close'] > prev_close)
            limit_down = _frozen & (checked_data['close'] < prev_close)
            
            if limit_up.any() or limit_down.any():
                print(f"发现涨跌停数据: {limit_up.sum()} 条涨停, {limit_down.sum()} 条跌停")
                # 可以选择移除或标记这些数据
        
        # 3. 时间戳对齐
        if self.config.data.check_timestamp_alignment:
            # 确保时间戳格式一致
            if 'trade_date' in checked_data.columns:
                checked_data['trade_date'] = pd.to_datetime(checked_data['trade_date'])
                checked_data = checked_data.sort_values('trade_date')
        
        print(f"数据质量检查完成: {len(checked_data)} 条记录")
        return checked_data
    
    def _store_raw_data(self, market_data: pd.DataFrame, 
                       fundamental_data: pd.DataFrame, 
                       alternative_data: pd.DataFrame):
        """
        数据存储
        
        存储格式：Parquet/Arrow
        按日期分区：时间序列查询优化
        建立数据血缘追踪
        """
        print(f"存储原始数据...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 存储行情数据
        if not market_data.empty:
            market_file = self.raw_data_dir / f'market_data_{timestamp}.parquet'
            market_data.to_parquet(market_file, index=False)
            print(f"行情数据已保存: {market_file}")
        
        # 存储基础数据
        if not fundamental_data.empty:
            fundamental_file = self.raw_data_dir / f'fundamental_data_{timestamp}.parquet'
            fundamental_data.to_parquet(fundamental_file, index=False)
            print(f"基础数据已保存: {fundamental_file}")
        
        # 存储另类数据
        if not alternative_data.empty:
            alternative_file = self.raw_data_dir / f'alternative_data_{timestamp}.parquet'
            alternative_data.to_parquet(alternative_file, index=False)
            print(f"另类数据已保存: {alternative_file}")
        
        # 建立数据血缘追踪
        lineage = {
            'timestamp': timestamp,
            'sources': {
                'market': 'tushare',
                'fundamental': 'tushare',
                'alternative': 'tushare'
            },
            'record_counts': {
                'market': len(market_data),
                'fundamental': len(fundamental_data),
                'alternative': len(alternative_data)
            }
        }
        
        lineage_file = self.raw_data_dir / f'data_lineage_{timestamp}.json'
        with open(lineage_file, 'w', encoding='utf-8') as f:
            json.dump(lineage, f, indent=2, ensure_ascii=False)
        print(f"数据血缘已保存: {lineage_file}")
    
    def _calculate_features(self, market_data: pd.DataFrame, 
                         fundamental_data: pd.DataFrame,
                         alternative_data: pd.DataFrame) -> pd.DataFrame:
        """
        特征计算
        
        包括：
        - 时序特征：技术指标（MA/EMA/RSI/MACD/布林带/ATR）
        - 统计特征：收益率偏度、峰度、波动率聚类、价格动量
        - 微观结构特征：买卖价差、订单簿不平衡、非流动性指标
        - 宏观特征：期限利差、信用利差、VIX指数、汇率变动
        
        严格避免前视偏差：所有特征必须基于当前时刻t及之前的数据计算
        """
        print(f"计算特征...")
        
        if market_data.empty:
            print("警告：市场数据为空，无法计算特征")
            return pd.DataFrame()
        
        features = market_data.copy()
        
        # 1. 时序特征：技术指标
        features = self._calculate_technical_indicators(features)
        
        # 2. 统计特征
        features = self._calculate_statistical_features(features)
        
        # 3. 微观结构特征
        features = self._calculate_microstructure_features(features)
        
        # 4. 宏观特征
        features = self._calculate_macro_features(features)
        
        # 5. 特征稳定性检查
        if self.config.feature.check_feature_stability:
            features = self._check_feature_stability(features)
        
        # 6. 特征中性化
        if self.config.feature.enable_neutralization:
            features = self._neutralize_features(features)
        
        print(f"特征计算完成: {len(features.columns)} 个特征")
        return features
    
    def _calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        包括：移动平均线（SMA/EMA）、RSI、MACD、布林带、ATR
        """
        print(f"计算技术指标...")
        
        features = data.copy()
        
        # 移动平均线
        if 'ma' in self.config.feature.technical_indicators:
            features['ma_5'] = features['close'].rolling(window=5).mean()
            features['ma_10'] = features['close'].rolling(window=10).mean()
            features['ma_20'] = features['close'].rolling(window=20).mean()
            features['ma_60'] = features['close'].rolling(window=60).mean()
        
        if 'ema' in self.config.feature.technical_indicators:
            features['ema_5'] = features['close'].ewm(span=5, adjust=False).mean()
            features['ema_10'] = features['close'].ewm(span=10, adjust=False).mean()
            features['ema_20'] = features['close'].ewm(span=20, adjust=False).mean()
        
        # RSI
        if 'rsi' in self.config.feature.technical_indicators:
            if TALIB_AVAILABLE:
                features['rsi_14'] = talib.RSI(features['close'].values, timeperiod=14)
            else:
                # 手动计算RSI
                delta = features['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                features['rsi_14'] = 100 - (100 / (1 + rs))
        
        # MACD
        if 'macd' in self.config.feature.technical_indicators:
            if TALIB_AVAILABLE:
                macd, signal, hist = talib.MACD(features['close'].values)
                features['macd'] = macd
                features['macd_signal'] = signal
                features['macd_hist'] = hist
            else:
                # 手动计算MACD
                ema_12 = features['close'].ewm(span=12, adjust=False).mean()
                ema_26 = features['close'].ewm(span=26, adjust=False).mean()
                features['macd'] = ema_12 - ema_26
                features['macd_signal'] = features['macd'].ewm(span=9, adjust=False).mean()
                features['macd_hist'] = features['macd'] - features['macd_signal']
        
        # 布林带
        if 'bollinger_bands' in self.config.feature.technical_indicators:
            if TALIB_AVAILABLE:
                upper, middle, lower = talib.BBANDS(features['close'].values)
                features['bb_upper'] = upper
                features['bb_middle'] = middle
                features['bb_lower'] = lower
                features['bb_width'] = (upper - lower) / middle
            else:
                # 手动计算布林带
                ma_20 = features['close'].rolling(window=20).mean()
                std_20 = features['close'].rolling(window=20).std()
                features['bb_upper'] = ma_20 + 2 * std_20
                features['bb_middle'] = ma_20
                features['bb_lower'] = ma_20 - 2 * std_20
                features['bb_width'] = (2 * std_20) / ma_20
        
        # ATR（波动率）
        if 'atr' in self.config.feature.technical_indicators:
            if TALIB_AVAILABLE:
                features['atr_14'] = talib.ATR(
                    features['high'].values,
                    features['low'].values,
                    features['close'].values,
                    timeperiod=14
                )
            else:
                # 手动计算ATR
                high_low = features['high'] - features['low']
                high_close = np.abs(features['high'] - features['close'].shift(1))
                low_close = np.abs(features['low'] - features['close'].shift(1))
                true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                features['atr_14'] = true_range.rolling(window=14).mean()
        
        print(f"技术指标计算完成")
        return features
    
    def _calculate_statistical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算统计特征
        
        包括：收益率偏度、峰度、波动率聚类、价格动量
        """
        print(f"计算统计特征...")
        
        features = data.copy()
        
        # 收益率
        features['return_1d'] = features['close'].pct_change(1)
        features['return_3d'] = features['close'].pct_change(3)
        features['return_5d'] = features['close'].pct_change(5)
        features['return_10d'] = features['close'].pct_change(10)
        features['return_20d'] = features['close'].pct_change(20)
        features['return_60d'] = features['close'].pct_change(60)
        
        # 收益率偏度
        if 'returns_skewness' in self.config.feature.statistical_features:
            features['return_skew_20d'] = features['return_20d'].rolling(window=20).skew()
            features['return_skew_60d'] = features['return_60d'].rolling(window=60).skew()
        
        # 收益率峰度
        if 'returns_kurtosis' in self.config.feature.statistical_features:
            features['return_kurtosis_20d'] = features['return_20d'].rolling(window=20).kurt()
            features['return_kurtosis_60d'] = features['return_60d'].rolling(window=60).kurt()
        
        # 波动率聚类
        if 'volatility_cluster' in self.config.feature.statistical_features:
            features['volatility_20d'] = features['return_20d'].rolling(window=20).std()
            features['volatility_60d'] = features['return_60d'].rolling(window=60).std()
        
        # 价格动量
        if 'price_momentum_1m' in self.config.feature.statistical_features:
            features['momentum_1m'] = features['close'] / features['close'].shift(21) - 1  # 1个月
        if 'price_momentum_3m' in self.config.feature.statistical_features:
            features['momentum_3m'] = features['close'] / features['close'].shift(63) - 1  # 3个月
        if 'price_momentum_6m' in self.config.feature.statistical_features:
            features['momentum_6m'] = features['close'] / features['close'].shift(126) - 1  # 6个月
        if 'price_momentum_12m' in self.config.feature.statistical_features:
            features['momentum_12m'] = features['close'] / features['close'].shift(252) - 1  # 12个月
        
        print(f"统计特征计算完成")
        return features
    
    def _calculate_microstructure_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算微观结构特征
        
        包括：买卖价差、订单簿不平衡、非流动性指标
        """
        print(f"计算微观结构特征...")
        
        features = data.copy()
        
        # 买卖价差（用高低价差近似）
        if 'bid_ask_spread' in self.config.feature.microstructure_features:
            features['spread'] = (features['high'] - features['low']) / features['close']
        
        # 订单簿不平衡（用成交量变化近似）
        if 'order_imbalance' in self.config.feature.microstructure_features:
            features['volume_change'] = features['vol'].pct_change(1)
            features['order_imbalance'] = features['volume_change'].rolling(window=5).mean()
        
        # 非流动性指标（Amihud illiquidity ratio）
        if 'illiquidity_ratio' in self.config.feature.microstructure_features:
            features['illiquidity'] = np.abs(features['return_1d']) / features['vol']
            features['illiquidity_ratio'] = features['illiquidity'].rolling(window=20).mean()
        
        print(f"微观结构特征计算完成")
        return features
    
    def _calculate_macro_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算宏观特征
        
        包括：期限利差、信用利差、VIX指数、汇率变动
        """
        print(f"计算宏观特征...")
        
        # 这里可以接入宏观数据源
        # 暂时返回原始数据，后续可以添加宏观特征
        
        print(f"宏观特征计算完成")
        return data
    
    def _check_feature_stability(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        特征稳定性检查
        
        计算特征的时序自相关系数，剔除过于不稳定的特征
        """
        print(f"检查特征稳定性...")
        
        # 计算特征的自相关系数
        feature_cols = [col for col in data.columns if col not in ['trade_date', 'ts_code', 'close']]
        stable_features = []
        
        for col in feature_cols:
            if data[col].dtype in ['float64', 'int64']:
                # 计算滞后1期的自相关系数
                autocorr = data[col].autocorr(lag=1)
                # 如果自相关系数过高（>0.8），说明特征短期记忆过强，不稳定
                if abs(autocorr) < 0.8:
                    stable_features.append(col)
        
        print(f"稳定特征数量: {len(stable_features)}/{len(feature_cols)}")
        
        # 只保留稳定特征
        result = data[['trade_date', 'ts_code', 'close'] + stable_features].copy()
        return result
    
    def _neutralize_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        特征中性化
        
        对市值、行业进行中性化处理（残差化），避免模型过度暴露于风格因子
        """
        print(f"特征中性化...")
        
        features = data.copy()
        
        # 市值中性化
        if 'market_cap' in self.config.feature.neutralize_by:
            if 'market_cap' in features.columns:
                # 计算市值分位数
                features['market_cap_rank'] = features['market_cap'].rank(pct=True)
                # 对特征进行市值中性化
                feature_cols = [col for col in features.columns 
                              if col not in ['trade_date', 'ts_code', 'close', 'market_cap', 'market_cap_rank']]
                for col in feature_cols:
                    if features[col].dtype in ['float64', 'int64']:
                        # 按市值分位数分组，计算残差
                        features[f'{col}_neutral'] = features[col] - features.groupby('market_cap_rank')[col].transform('mean')
        
        # 行业中性化
        if 'industry' in self.config.feature.neutralize_by:
            if 'industry' in features.columns:
                # 对特征进行行业中性化
                feature_cols = [col for col in features.columns 
                              if col not in ['trade_date', 'ts_code', 'close', 'industry']]
                for col in feature_cols:
                    if features[col].dtype in ['float64', 'int64']:
                        # 按行业分组，计算残差
                        features[f'{col}_industry_neutral'] = features[col] - features.groupby('industry')[col].transform('mean')
        
        print(f"特征中性化完成")
        return features
    
    def _construct_labels(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        标签构建
        
        包括：
        - 分类任务（方向预测）：二元分类、三元分类
        - 回归任务（收益预测）：收益率预测、Sharpe比率预测
        - 排名预测：预测个股在截面上的收益排名
        
        标签时效性：使用收盘价到收盘价计算标签
        """
        print(f"构建标签...")
        
        if market_data.empty:
            print("警告：市场数据为空，无法构建标签")
            return pd.DataFrame()
        
        labels = market_data.copy()
        
        # 计算未来收益率
        horizon = self.config.label.prediction_horizon
        labels['future_return'] = labels['close'].shift(-horizon) / labels['close'] - 1
        
        # 根据任务类型构建标签
        task_type = self.config.label.task_type
        
        if task_type == 'classification':
            labels = self._construct_classification_labels(labels)
        elif task_type == 'regression':
            labels = self._construct_regression_labels(labels)
        elif task_type == 'ranking':
            labels = self._construct_ranking_labels(labels)
        
        # 考虑交易成本后的净收益
        if self.config.label.consider_transaction_cost:
            cost_rate = self.config.label.transaction_cost_rate
            labels['net_return'] = labels['future_return'] - cost_rate
        
        print(f"标签构建完成: {task_type}")
        return labels
    
    def _construct_classification_labels(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        构建分类标签
        
        二元分类：未来N日收益率 > 阈值（如0）为正类，反之为负类
        三元分类：上涨（>+2%）、震荡（±2%）、下跌（<-2%）
        """
        classification_type = self.config.label.classification_type
        
        if classification_type == 'binary':
            # 二元分类
            threshold = self.config.label.binary_threshold
            data['label'] = (data['future_return'] > threshold).astype(int)
            data['label_name'] = data['label'].map({0: 'DOWN', 1: 'UP'})
        
        elif classification_type == 'ternary':
            # 三元分类
            up_threshold = self.config.label.ternary_thresholds['up']
            down_threshold = self.config.label.ternary_thresholds['down']
            
            conditions = [
                data['future_return'] > up_threshold,
                (data['future_return'] >= down_threshold) & (data['future_return'] <= up_threshold),
                data['future_return'] < down_threshold
            ]
            choices = ['UP', 'NEUTRAL', 'DOWN']
            data['label'] = np.select(conditions, choices)
            data['label_name'] = data['label']
        
        return data
    
    def _construct_regression_labels(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        构建回归标签
        
        收益率预测：未来N日对数收益率
        Sharpe比率预测：预测未来N日的风险调整后收益
        """
        regression_target = self.config.label.regression_target
        
        if regression_target == 'log_return':
            # 对数收益率
            data['label'] = np.log1p(data['future_return'])
        
        elif regression_target == 'sharpe_ratio':
            # Sharpe比率（简化版）
            data['label'] = data['future_return'] / data['future_return'].rolling(window=20).std()
        
        return data
    
    def _construct_ranking_labels(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        构建排名标签
        
        预测个股在截面上的收益排名（更稳健，降低异常值影响）
        """
        ranking_method = self.config.label.ranking_method
        
        if ranking_method == 'cross_section':
            # 截面排名
            data['label'] = data.groupby('trade_date')['future_return'].rank(pct=True)
        
        elif ranking_method == 'time_series':
            # 时序排名
            data['label'] = data['future_return'].rolling(window=252).rank(pct=True)
        
        return data
    
    def _merge_features_labels(self, features: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
        """
        合并特征和标签
        """
        print(f"合并特征和标签...")
        
        # 按日期和股票代码合并
        if 'trade_date' in features.columns and 'trade_date' in labels.columns:
            full_data = pd.merge(
                features,
                labels[['trade_date', 'ts_code', 'label', 'label_name', 'future_return']],
                on=['trade_date', 'ts_code'],
                how='inner'
            )
        else:
            print("警告：无法合并特征和标签，缺少关键字段")
            return pd.DataFrame()
        
        print(f"合并完成: {len(full_data)} 条记录")
        return full_data
    
    def _temporal_split(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        时序划分
        
        严禁随机划分，必须按时间顺序划分
        训练集：验证集：测试集 = 70% : 15% : 15%
        """
        print(f"执行时序划分...")
        
        if data.empty:
            print("警告：数据为空，无法划分")
            return {}
        
        # 按时间排序
        data = data.sort_values('trade_date')
        
        # 计算划分点
        total_length = len(data)
        train_end = int(total_length * self.config.split.train_ratio)
        val_end = train_end + int(total_length * self.config.split.val_ratio)
        
        # 划分数据集
        train_data = data.iloc[:train_end]
        val_data = data.iloc[train_end:val_end]
        test_data = data.iloc[val_end:]
        
        # 获取时间范围
        train_start = train_data['trade_date'].min()
        train_end_date = train_data['trade_date'].max()
        val_start = val_data['trade_date'].min()
        val_end_date = val_data['trade_date'].max()
        test_start = test_data['trade_date'].min()
        test_end_date = test_data['trade_date'].max()
        
        splits = {
            'train': {
                'data': train_data,
                'start_date': train_start,
                'end_date': train_end_date,
                'size': len(train_data)
            },
            'val': {
                'data': val_data,
                'start_date': val_start,
                'end_date': val_end_date,
                'size': len(val_data)
            },
            'test': {
                'data': test_data,
                'start_date': test_start,
                'end_date': test_end_date,
                'size': len(test_data)
            }
        }
        
        # OOT数据（预留最近3-6个月）
        if self.config.split.enable_oot:
            oot_months = self.config.split.oot_months
            oot_start = test_end_date - timedelta(days=oot_months*30)
            oot_data = data[data['trade_date'] >= oot_start]
            
            splits['oot'] = {
                'data': oot_data,
                'start_date': oot_start,
                'end_date': test_end_date,
                'size': len(oot_data)
            }
        
        print(f"时序划分完成:")
        print(f"  训练集: {train_start} 至 {train_end_date} ({len(train_data)} 条)")
        print(f"  验证集: {val_start} 至 {val_end_date} ({len(val_data)} 条)")
        print(f"  测试集: {test_start} 至 {test_end_date} ({len(test_data)} 条)")
        if 'oot' in splits:
            print(f"  OOT集: {oot_start} 至 {test_end_date} ({len(oot_data)} 条)")
        
        return splits
