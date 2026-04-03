"""
预测接口模块

功能：
- 输入格式（实时数据接口、数据校验）
- 输出格式（预测响应、风险预警）
- API端点（RESTful API、WebSocket实时推送）
- 限流与认证（API Key认证、速率限制）
- 错误处理

设计原则：
- 支持批量预测优先
- 实现数据校验和异常检测
- 提供风险预警机制
- 确保高可用性和性能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
import uuid
import time
from pathlib import Path
import logging
from functools import wraps
from collections import defaultdict

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from .config import Config, PredictionConfig
from .model_manager import ModelManager


class PredictionService:
    """预测服务主类"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.model_manager = ModelManager(self.config)
        
        # 当前加载的模型
        self.current_model = None
        self.current_model_version = None
        self.current_model_metadata = None
        
        # 特征配置
        self.feature_names = []
        self.feature_stats = {}
        
        # 速率限制
        self.rate_limiter = RateLimiter(self.config.prediction.rate_limit_per_minute)
        
        # 分布监控
        self.distribution_monitor = DistributionMonitor(self.config.prediction.drift_threshold)
        
        # 设置日志
        self.logger = self._setup_logger()
        
        # 加载最新模型
        self._load_latest_model()
    
    def _setup_logger(self) -> logging.Logger:
        """
        设置日志记录器
        """
        logger = logging.getLogger('PredictionService')
        logger.setLevel(logging.INFO)
        
        # 创建日志目录
        log_dir = Path(self.config.model_management.models_dir) / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_dir / 'prediction_service.log')
        file_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        return logger
    
    def _load_latest_model(self):
        """
        加载最新模型
        """
        try:
            self.current_model, self.current_model_metadata = self.model_manager.load_model(
                'ml_model', version=None
            )
            self.current_model_version = self.current_model_metadata['version']
            self.feature_names = self.current_model_metadata['feature_names']
            
            self._load_feature_stats()
            
            self.logger.info(f"成功加载模型: v{self.current_model_version}")
        except Exception as e:
            self.logger.warning(f"加载模型失败: {e}")
            self.current_model = None
    
    def _load_feature_stats(self):
        """
        加载特征统计信息（用于标准化）
        """
        try:
            model_dir = Path(self.config.model_management.models_dir) / 'ml_model' / str(self.current_model_version)
            stats_file = model_dir / 'feature_stats.json'
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.feature_stats = data
                    return
            for feature in self.feature_names:
                self.feature_stats[feature] = {'mean': 0.0, 'std': 1.0}
        except Exception as e:
            self.logger.warning(f"加载特征统计信息失败: {e}")
    
    def predict(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        批量预测接口
        
        接收股票列表和特征数据，返回预测结果
        
        Args:
            request: 预测请求
                {
                    "request_id": "uuid_v4",
                    "timestamp": "2026-03-27T09:30:00+08:00",
                    "universe": ["000001.SZ", "600000.SH", ...],
                    "feature_data": {
                        "000001.SZ": {
                            "close": 10.5,
                            "volume": 1000000,
                            ...
                        }
                    },
                    "model_version": "v1.2.0"  // 可选
                }
                
        Returns:
            预测响应
                {
                    "request_id": "uuid_v4",
                    "timestamp": "2026-03-27T09:30:05+08:00",
                    "model_version": "v1.2.0",
                    "predictions": {
                        "000001.SZ": {
                            "score": 0.85,
                            "expected_return": 0.025,
                            "direction": "UP",
                            "confidence": 0.92,
                            "rank": 15
                        }
                    },
                    "model_latency_ms": 150,
                    "status": "success",
                    "warnings": []
                }
        """
        start_time = time.time()
        
        # 1. 生成请求ID
        request_id = request.get('request_id', str(uuid.uuid4()))
        
        # 2. 检查模型是否可用
        if self.current_model is None:
            return {
                'request_id': request_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': 'Model not available',
                'error_code': 'MODEL_NOT_LOADED'
            }
        
        # 3. 数据校验
        validation_result = self._validate_request(request)
        if not validation_result['valid']:
            return {
                'request_id': request_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': validation_result['error'],
                'error_code': 'INVALID_REQUEST'
            }
        
        # 4. 数据延迟检查
        if self.config.prediction.enable_data_delay_check:
            delay_check = self._check_data_delay(request)
            if not delay_check['valid']:
                return {
                    'request_id': request_id,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'error',
                    'error': delay_check['error'],
                    'error_code': 'DATA_DELAY'
                }
        
        # 5. 特征处理
        features_df = self._process_features(request['feature_data'])
        
        # 6. 执行预测
        predictions = self._execute_prediction(features_df)
        
        # 7. 风险预警
        warnings = self._check_risks(predictions)
        
        # 8. 计算耗时
        latency_ms = (time.time() - start_time) * 1000
        
        # 9. 构建响应
        response = {
            'request_id': request_id,
            'timestamp': datetime.now().isoformat(),
            'model_version': self.current_model_version,
            'predictions': predictions,
            'model_latency_ms': latency_ms,
            'status': 'success',
            'warnings': warnings
        }
        
        # 10. 记录日志
        self.model_manager.log_prediction(
            request_id,
            features_df.iloc[0].to_dict(),
            list(predictions.values())[0]['score'],
            self.current_model_version,
            latency_ms
        )
        
        return response
    
    def _validate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        数据校验
        
        检查项：
        - 缺失值处理
        - 特征范围检查
        """
        # 检查必需字段
        required_fields = ['universe', 'feature_data']
        for field in required_fields:
            if field not in request:
                return {'valid': False, 'error': f'Missing required field: {field}'}
        
        # 检查特征数据
        feature_data = request['feature_data']
        if not feature_data:
            return {'valid': False, 'error': 'No feature data provided'}
        
        # 检查每个股票的特征
        for symbol, features in feature_data.items():
            # 缺失值检查
            if self.config.prediction.enable_missing_value_handling:
                missing_features = [f for f in self.feature_names if f not in features]
                if missing_features:
                    if self.config.prediction.missing_value_strategy == 'return_error':
                        return {
                            'valid': False,
                            'error': f'Missing features for {symbol}: {missing_features}'
                        }
                    else:
                        # 使用训练集均值填充
                        for f in missing_features:
                            features[f] = self.feature_stats[f]['mean']
            
            # 特征范围检查
            if self.config.prediction.enable_outlier_detection:
                for feature, value in features.items():
                    if feature in self.feature_stats:
                        mean = self.feature_stats[feature]['mean']
                        std = self.feature_stats[feature]['std']
                        # 检查是否超过10倍标准差
                        if abs(value - mean) > 10 * std:
                            self.logger.warning(f'异常特征值: {symbol}.{feature} = {value}')
        
        return {'valid': True}
    
    def _check_data_delay(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        数据延迟检查
        
        检查最新数据时间戳，若延迟超过阈值拒绝预测
        """
        if 'timestamp' not in request:
            return {'valid': True}  # 没有时间戳，跳过检查
        
        try:
            request_time = datetime.fromisoformat(request['timestamp'].replace('Z', '+00:00'))
            current_time = datetime.now()
            
            delay_seconds = (current_time - request_time).total_seconds()
            max_delay = self.config.prediction.max_delay_seconds
            
            if delay_seconds > max_delay:
                return {
                    'valid': False,
                    'error': f'Data delay too large: {delay_seconds:.1f}s > {max_delay}s'
                }
            
            return {'valid': True}
        except Exception as e:
            self.logger.warning(f"数据延迟检查失败: {e}")
            return {'valid': True}
    
    def _process_features(self, feature_data: Dict[str, Dict[str, float]]) -> pd.DataFrame:
        """
        特征处理
        
        将输入特征转换为模型输入格式
        """
        # 提取特征
        features_list = []
        symbols = []
        
        for symbol, features in feature_data.items():
            # 确保特征顺序与训练时一致
            feature_vector = []
            for feature_name in self.feature_names:
                if feature_name in features:
                    value = features[feature_name]
                    # 标准化
                    if feature_name in self.feature_stats:
                        mean = self.feature_stats[feature_name]['mean']
                        std = self.feature_stats[feature_name]['std']
                        value = (value - mean) / std if std != 0 else 0.0
                    feature_vector.append(value)
                else:
                    # 缺失特征使用均值填充
                    feature_vector.append(0.0)
            
            features_list.append(feature_vector)
            symbols.append(symbol)
        
        # 创建DataFrame
        features_df = pd.DataFrame(features_list, columns=self.feature_names, index=symbols)
        
        return features_df
    
    def _execute_prediction(self, features_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        执行预测
        
        返回预测结果，包括：
        - score: 预测分数
        - expected_return: 预期收益率
        - direction: 预测方向
        - confidence: 置信度
        - rank: 排名
        """
        symbols = list(features_df.index.astype(str))
        results = {}

        if hasattr(self.current_model, 'predict_proba'):
            probas = np.asarray(self.current_model.predict_proba(features_df), dtype=float)
            classes = list(getattr(self.current_model, 'classes_', []))
            class_to_idx = {int(cls): idx for idx, cls in enumerate(classes)} if classes else {}
            buy_idx = class_to_idx.get(1, 1 if probas.shape[1] > 1 else 0)
            sell_idx = class_to_idx.get(0, 0)
            neutral_idx = class_to_idx.get(2, 2 if probas.shape[1] > 2 else None)

            buy_probs = probas[:, buy_idx]
            sell_probs = probas[:, sell_idx]
            neutral_probs = probas[:, neutral_idx] if neutral_idx is not None and neutral_idx < probas.shape[1] else np.zeros(len(symbols), dtype=float)
            net_scores = buy_probs - sell_probs
            ranks = pd.Series(net_scores, index=symbols).rank(ascending=False, method='min')

            for i, symbol in enumerate(symbols):
                if buy_probs[i] >= sell_probs[i] and buy_probs[i] >= neutral_probs[i]:
                    direction = 'UP'
                elif sell_probs[i] >= buy_probs[i] and sell_probs[i] >= neutral_probs[i]:
                    direction = 'DOWN'
                else:
                    direction = 'NEUTRAL'

                confidence = float(max(buy_probs[i], sell_probs[i], neutral_probs[i]))
                expected_return = float(net_scores[i] * 0.1)
                results[symbol] = {
                    'score': float(net_scores[i]),
                    'buy_prob': float(buy_probs[i]),
                    'sell_prob': float(sell_probs[i]),
                    'neutral_prob': float(neutral_probs[i]),
                    'expected_return': expected_return,
                    'direction': direction,
                    'confidence': confidence,
                    'rank': int(ranks.loc[symbol])
                }
            return results

        predictions = np.asarray(self.current_model.predict(features_df), dtype=float)
        ranks = pd.Series(predictions, index=symbols).rank(ascending=False, method='min')
        for i, symbol in enumerate(symbols):
            score = float(predictions[i])
            if score > 0.5:
                direction = 'UP'
            elif score < 0.5:
                direction = 'DOWN'
            else:
                direction = 'NEUTRAL'
            confidence = float(min(1.0, abs(score - 0.5) * 2))
            expected_return = float((score - 0.5) * 0.1)
            results[symbol] = {
                'score': score,
                'expected_return': expected_return,
                'direction': direction,
                'confidence': confidence,
                'rank': int(ranks.loc[symbol])
            }
        return results
    
    def _check_risks(self, predictions: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        风险预警
        
        检查项：
        - 输入分布漂移
        - 预测值异常
        """
        warnings = []
        
        # 1. 分布漂移检测
        if self.config.prediction.enable_drift_detection:
            drift_detected = self.distribution_monitor.check_drift(predictions)
            if drift_detected:
                warnings.append('Input distribution drift detected')
        
        # 2. 异常预测值检测
        if self.config.prediction.enable_outlier_detection:
            outlier_threshold = self.config.prediction.outlier_threshold
            for symbol, pred in predictions.items():
                if abs(pred['expected_return']) > outlier_threshold:
                    warnings.append(f'Outlier prediction for {symbol}: {pred["expected_return"]:.2%}')
        
        return warnings
    
    def predict_single(self, symbol: str, features: Dict[str, float]) -> Dict[str, Any]:
        """
        单只股票实时预测
        
        Args:
            symbol: 股票代码
            features: 特征数据
            
        Returns:
            预测结果
        """
        request = {
            'request_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'universe': [symbol],
            'feature_data': {
                symbol: features
            }
        }
        
        return self.predict(request)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取当前服务模型信息
        
        包括：模型版本、训练日期、性能指标
        """
        if self.current_model_metadata is None:
            return {
                'status': 'error',
                'error': 'No model loaded'
            }
        
        return {
            'model_name': self.current_model_metadata['model_name'],
            'version': self.current_model_version,
            'saved_at': self.current_model_metadata['saved_at'],
            'model_type': self.current_model_metadata['model_type'],
            'feature_count': self.current_model_metadata['feature_count'],
            'training_metrics': self.current_model_metadata['training_metrics'],
            'production_ready': self.current_model_metadata['production_ready']
        }
    
    def get_signals(self, top_n: int = 20) -> Dict[str, Any]:
        """
        获取今日全部买入/卖出信号列表
        
        按分数排序
        """
        # 这里需要从数据库或其他数据源获取当前市场的特征数据
        # 暂时返回空结果
        
        return {
            'buy_signals': [],
            'sell_signals': [],
            'timestamp': datetime.now().isoformat()
        }


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, rate_limit_per_minute: int):
        self.rate_limit = rate_limit_per_minute
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        """
        检查是否允许请求
        
        Args:
            client_id: 客户端标识
            
        Returns:
            是否允许
        """
        now = time.time()
        minute_ago = now - 60
        
        # 清理过期请求
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]
        
        # 检查是否超过限制
        if len(self.requests[client_id]) >= self.rate_limit:
            return False
        
        # 记录请求
        self.requests[client_id].append(now)
        return True


class DistributionMonitor:
    """分布监控器"""
    
    def __init__(self, drift_threshold: float):
        self.drift_threshold = drift_threshold
        self.baseline_distribution = None
    
    def set_baseline(self, predictions: Dict[str, Dict[str, Any]]):
        """
        设置基线分布
        """
        scores = [pred['score'] for pred in predictions.values()]
        self.baseline_distribution = {
            'mean': np.mean(scores),
            'std': np.std(scores)
        }
    
    def check_drift(self, predictions: Dict[str, Dict[str, Any]]) -> bool:
        """
        检查分布漂移
        
        使用KS检验或简单的均值/标准差比较
        """
        if self.baseline_distribution is None:
            return False
        
        scores = [pred['score'] for pred in predictions.values()]
        current_mean = np.mean(scores)
        current_std = np.std(scores)
        
        # 计算分布差异
        mean_diff = abs(current_mean - self.baseline_distribution['mean'])
        std_diff = abs(current_std - self.baseline_distribution['std'])
        
        # 如果差异超过阈值，认为发生了漂移
        if mean_diff > self.drift_threshold or std_diff > self.drift_threshold:
            return True
        
        return False


def require_api_key(f):
    """
    API Key认证装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 这里实现API Key验证逻辑
        # 暂时跳过验证
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(f):
    """
    速率限制装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 这里实现速率限制逻辑
        # 暂时跳过限制
        return f(*args, **kwargs)
    return decorated_function
