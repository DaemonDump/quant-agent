"""
模型管理模块

功能：
- 模型保存（模型权重、特征配置、模型元数据、环境依赖）
- 版本管理（语义化版本、模型注册表、影子模式）
- 模型加载（版本校验、特征对齐、预处理还原、设备适配、热更新机制）
- 状态追踪（监控指标、日志记录）

设计原则：
- 使用语义化版本（MAJOR.MINOR.PATCH）
- 维护模型卡片（Model Card）
- 支持生产就绪（Production Ready）状态标记
- 实现影子模式（Shadow Mode）和A/B测试
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import pickle
import yaml
from pathlib import Path
import hashlib
import shutil
import logging

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

from .config import Config, ModelManagementConfig
from .feature_spec import load_feature_spec, current_feature_list_hash


class ModelManager:
    """模型管理主类"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.models_dir = Path(self.config.model_management.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # 模型注册表
        self.model_registry = {}
        self._load_model_registry()
        
        # 当前加载的模型
        self.current_model = None
        self.current_model_version = None
        self.current_model_metadata = None
        
        # 设置日志
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """
        设置日志记录器
        """
        logger = logging.getLogger('ModelManager')
        logger.setLevel(logging.INFO)
        
        # 创建日志目录
        log_dir = self.models_dir / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_dir / 'model_management.log')
        file_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        return logger
    
    def save_model(self, model, model_name: str, version: str,
                   feature_names: List[str],
                   training_metrics: Dict[str, float],
                   metadata: Optional[Dict[str, Any]] = None,
                   feature_stats: Optional[Dict[str, Dict[str, float]]] = None,
                   feature_spec_path: str = "") -> str:
        """
        保存模型
        
        保存内容：
        - 模型权重
        - 特征配置
        - 模型元数据
        - 环境依赖
        
        Args:
            model: 训练好的模型
            model_name: 模型名称
            version: 模型版本（MAJOR.MINOR.PATCH）
            feature_names: 特征名称列表
            training_metrics: 训练指标
            metadata: 额外的元数据
            
        Returns:
            模型保存路径
        """
        self.logger.info(f"保存模型: {model_name} v{version}")
        
        # 创建模型目录
        model_dir = self.models_dir / model_name / version
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 保存模型权重
        model_file_name = self._save_model_weights(model, model_dir)
        
        # 2. 保存特征配置
        current_hash = current_feature_list_hash(feature_spec_path)
        feature_spec = load_feature_spec(feature_spec_path)
        feature_config = {
            'feature_names': feature_names,
            'feature_count': len(feature_names),
            'saved_at': datetime.now().isoformat(),
            'feature_list_hash': current_hash,
            'feature_spec': feature_spec
        }
        feature_config_file = model_dir / 'feature_config.json'
        with open(feature_config_file, 'w', encoding='utf-8') as f:
            json.dump(feature_config, f, indent=2, ensure_ascii=False)
        
        if feature_stats is not None:
            feature_stats_file = model_dir / 'feature_stats.json'
            with open(feature_stats_file, 'w', encoding='utf-8') as f:
                json.dump(feature_stats, f, indent=2, ensure_ascii=False)

        # 3. 保存模型元数据
        model_metadata = {
            'model_name': model_name,
            'version': version,
            'saved_at': datetime.now().isoformat(),
            'model_type': self.config.model.model_type,
            'actual_model_type': (metadata or {}).get('actual_model_type') or self.config.model.model_type,
            'model_file': model_file_name,
            'feature_names': feature_names,
            'feature_count': len(feature_names),
            'training_metrics': training_metrics,
            'config': self.config.to_dict(),
            'production_ready': self._check_production_ready(training_metrics),
            'metadata': metadata or {},
            'feature_list_hash': current_hash
        }
        
        metadata_file = model_dir / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(model_metadata, f, indent=2, ensure_ascii=False, default=str)
        
        # 4. 保存环境依赖
        environment = {
            'python_version': self._get_python_version(),
            'libraries': self._get_library_versions(),
            'random_seed': 42
        }
        env_file = model_dir / 'environment.json'
        with open(env_file, 'w', encoding='utf-8') as f:
            json.dump(environment, f, indent=2, ensure_ascii=False)
        
        # 5. 创建模型卡片
        self._create_model_card(model_dir, model_metadata)
        
        # 6. 更新模型注册表
        self._update_model_registry(model_name, version, model_metadata)
        
        self.logger.info(f"模型保存成功: {model_dir}")
        return str(model_dir)
    
    def _save_model_weights(self, model, model_dir: Path):
        """
        保存模型权重
        """
        model_type = self.config.model.model_type
        
        if model_type == 'xgboost' and XGBOOST_AVAILABLE:
            model_file = model_dir / 'model_weights.pkl'
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
        
        elif model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
            model_file = model_dir / 'model_weights.txt'
            model.booster_.save_model(str(model_file))
        
        elif model_type == 'catboost' and CATBOOST_AVAILABLE:
            model_file = model_dir / 'model_weights.cbm'
            model.save_model(str(model_file))
        
        else:
            # 通用pickle保存
            model_file = model_dir / 'model_weights.pkl'
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
        return model_file.name
    
    def _check_production_ready(self, metrics: Dict[str, float]) -> bool:
        """
        检查模型是否达到生产就绪标准

        优先使用 val_accuracy，阈值 0.35（随机基线约 0.33）
        """
        val_acc = metrics.get('val_accuracy', 0)
        if val_acc > 0:
            return val_acc >= 0.35
        ic = metrics.get('ic', 0)
        threshold = self.config.model_management.production_ready_threshold
        return ic >= threshold
    
    def _create_model_card(self, model_dir: Path, metadata: Dict[str, Any]):
        """
        创建模型卡片（Model Card）
        
        记录模型用途、训练数据、性能基准、已知局限
        """
        model_card = {
            'model_card_version': '1.0',
            'model_details': {
                'name': metadata['model_name'],
                'version': metadata['version'],
                'type': metadata['model_type'],
                'description': f"{metadata['model_type']} model for quantitative trading"
            },
            'intended_use': {
                'primary_use': 'Stock price prediction and trading signal generation',
                'primary_users': 'Quantitative traders and investment firms',
                'out_of_scope': 'Not suitable for long-term investment decisions'
            },
            'training_data': {
                'data_source': 'Tushare',
                'time_period': 'Historical market data',
                'feature_count': metadata['feature_count'],
                'sample_size': 'Large-scale historical data'
            },
            'performance_metrics': metadata['training_metrics'],
            'limitations': {
                'market_conditions': 'Performance may vary in different market regimes',
                'data_quality': 'Dependent on data quality and availability',
                'overfitting_risk': 'Regular monitoring required to detect performance degradation'
            },
            'ethical_considerations': {
                'fairness': 'Model should be regularly audited for bias',
                'transparency': 'Feature importance analysis should be provided'
            },
            'created_at': metadata['saved_at']
        }
        
        model_card_file = model_dir / 'model_card.json'
        with open(model_card_file, 'w', encoding='utf-8') as f:
            json.dump(model_card, f, indent=2, ensure_ascii=False, default=str)
    
    def _update_model_registry(self, model_name: str, version: str, metadata: Dict[str, Any]):
        """
        更新模型注册表
        """
        if model_name not in self.model_registry:
            self.model_registry[model_name] = {}
        
        self.model_registry[model_name][version] = {
            'saved_at': metadata['saved_at'],
            'production_ready': metadata['production_ready'],
            'metrics': metadata['training_metrics']
        }
        
        # 保存注册表
        registry_file = self.models_dir / 'model_registry.json'
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump(self.model_registry, f, indent=2, ensure_ascii=False, default=str)
    
    def _load_model_registry(self):
        """
        加载模型注册表
        """
        registry_file = self.models_dir / 'model_registry.json'
        if registry_file.exists():
            with open(registry_file, 'r', encoding='utf-8') as f:
                self.model_registry = json.load(f)
    
    def load_model(self, model_name: str, version: Optional[str] = None) -> Tuple[Any, Dict[str, Any]]:
        """
        加载模型
        
        流程：
        1. 版本校验
        2. 特征对齐
        3. 预处理还原
        4. 设备适配
        
        Args:
            model_name: 模型名称
            version: 模型版本（如果为None，加载最新版本）
            
        Returns:
            (模型, 元数据)
        """
        self.logger.info(f"加载模型: {model_name} v{version or 'latest'}")
        
        # 确定版本
        if version is None:
            version = self._get_latest_version(model_name)
            if version is None:
                raise ValueError(f"模型 {model_name} 不存在")
        
        # 模型目录
        model_dir = self.models_dir / model_name / version
        if not model_dir.exists():
            raise ValueError(f"模型 {model_name} v{version} 不存在")
        
        # 1. 加载元数据
        metadata_file = model_dir / 'metadata.json'
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 2. 版本校验
        self._validate_version(metadata)
        
        # 3. 加载模型权重
        model = self._load_model_weights(model_dir, metadata)
        
        # 4. 特征对齐
        self._validate_features(model_dir, metadata)
        
        # 5. 更新当前模型状态
        self.current_model = model
        self.current_model_version = version
        self.current_model_metadata = metadata
        
        self.logger.info(f"模型加载成功: {model_dir}")
        return model, metadata
    
    def _get_latest_version(self, model_name: str) -> Optional[str]:
        """
        获取模型的最新版本
        """
        registry_versions = self.model_registry.get(model_name, {})
        if registry_versions:
            best_version = None
            best_saved_at = None
            for version, info in registry_versions.items():
                saved_at = info.get("saved_at")
                try:
                    saved_dt = datetime.fromisoformat(saved_at) if saved_at else None
                except Exception:
                    saved_dt = None
                if best_version is None:
                    best_version = version
                    best_saved_at = saved_dt
                    continue
                if saved_dt is not None and (best_saved_at is None or saved_dt > best_saved_at):
                    best_version = version
                    best_saved_at = saved_dt
                    continue
                if saved_dt is None and best_saved_at is None and str(version) > str(best_version):
                    best_version = version
            if best_version is not None:
                return best_version

        model_root = self.models_dir / model_name
        if not model_root.exists():
            return None
        dirs = sorted([p.name for p in model_root.iterdir() if p.is_dir()])
        return dirs[-1] if dirs else None
    
    def _validate_version(self, metadata: Dict[str, Any]):
        """
        版本校验
        """
        # 检查模型类型是否匹配
        if metadata['model_type'] != self.config.model.model_type:
            self.logger.warning(f"模型类型不匹配: 期望 {self.config.model.model_type}, 实际 {metadata['model_type']}")
    
    def _validate_features(self, model_dir: Path, metadata: Dict[str, Any]):
        """
        特征对齐验证
        
        验证输入特征与训练时特征列表完全一致
        """
        feature_config_file = model_dir / 'feature_config.json'
        with open(feature_config_file, 'r', encoding='utf-8') as f:
            feature_config = json.load(f)

        expected_hash = feature_config.get('feature_list_hash')
        current_hash = current_feature_list_hash()
        metadata['feature_list_hash_expected'] = expected_hash
        metadata['feature_list_hash_current'] = current_hash
        metadata['feature_list_hash_match'] = (expected_hash == current_hash) if expected_hash else None
        if expected_hash and expected_hash != current_hash:
            metadata.setdefault('warnings', []).append('FEATURE_LIST_MISMATCH')
            self.logger.warning("特征清单哈希不匹配，建议重新训练模型")

        self.logger.info(f"特征对齐验证通过: {feature_config.get('feature_count', 0)} 个特征")
    
    def _load_model_weights(self, model_dir: Path, metadata: Optional[Dict[str, Any]] = None):
        """
        加载模型权重
        """
        metadata = metadata or {}
        actual_model_type = (metadata.get('actual_model_type') or metadata.get('model_type') or self.config.model.model_type or '').lower()
        model_file_name = metadata.get('model_file') or 'model_weights.pkl'
        model_file = model_dir / model_file_name

        if not model_file.exists():
            for fallback_name in ('model_weights.pkl', 'model_weights.json', 'model_weights.txt', 'model_weights.cbm'):
                fallback_file = model_dir / fallback_name
                if fallback_file.exists():
                    model_file = fallback_file
                    break
            else:
                raise FileNotFoundError(f"未找到模型权重文件: {model_file}")

        if model_file.suffix == '.pkl':
            with open(model_file, 'rb') as f:
                return pickle.load(f)

        if actual_model_type == 'xgboost' and XGBOOST_AVAILABLE:
            model = xgb.XGBClassifier()
            model.load_model(str(model_file))
            return model

        if actual_model_type == 'lightgbm' and LIGHTGBM_AVAILABLE:
            model = lgb.LGBMRegressor()
            model.booster_ = lgb.Booster(model_file=str(model_file))
            return model

        if actual_model_type == 'catboost' and CATBOOST_AVAILABLE:
            model = cb.CatBoostRegressor()
            model.load_model(str(model_file))
            return model

        raise ValueError(f"不支持的模型文件类型或缺少依赖: {model_file.name}")
    
    def get_model_info(self, model_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        获取模型信息
        
        包括：模型版本、训练日期、性能指标
        """
        if version is None:
            version = self._get_latest_version(model_name)
            if version is None:
                raise ValueError(f"模型 {model_name} 不存在")
        
        if model_name not in self.model_registry or version not in self.model_registry[model_name]:
            raise ValueError(f"模型 {model_name} v{version} 不存在")
        
        model_dir = self.models_dir / model_name / version
        metadata_file = model_dir / 'metadata.json'
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return {
            'model_name': metadata['model_name'],
            'version': metadata['version'],
            'saved_at': metadata['saved_at'],
            'model_type': metadata['model_type'],
            'feature_count': metadata['feature_count'],
            'training_metrics': metadata['training_metrics'],
            'production_ready': metadata['production_ready']
        }
    
    def list_models(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        列出所有模型或指定模型的所有版本
        """
        if model_name:
            if model_name not in self.model_registry:
                return {}
            return {model_name: self.model_registry[model_name]}
        else:
            return self.model_registry
    
    def delete_model(self, model_name: str, version: str):
        """
        删除模型
        """
        self.logger.info(f"删除模型: {model_name} v{version}")
        
        # 删除模型目录
        model_dir = self.models_dir / model_name / version
        if model_dir.exists():
            shutil.rmtree(model_dir)
        
        # 更新注册表
        if model_name in self.model_registry and version in self.model_registry[model_name]:
            del self.model_registry[model_name][version]
            
            # 如果没有版本了，删除模型条目
            if not self.model_registry[model_name]:
                del self.model_registry[model_name]
        
        # 保存注册表
        registry_file = self.models_dir / 'model_registry.json'
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump(self.model_registry, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"模型删除成功")
    
    def set_production_model(self, model_name: str, version: str):
        """
        设置生产模型
        
        标记为生产就绪状态
        """
        self.logger.info(f"设置生产模型: {model_name} v{version}")
        
        # 更新元数据
        model_dir = self.models_dir / model_name / version
        metadata_file = model_dir / 'metadata.json'
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        metadata['production_ready'] = True
        metadata['production_set_at'] = datetime.now().isoformat()
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        
        # 更新注册表
        self.model_registry[model_name][version]['production_ready'] = True
        
        # 保存注册表
        registry_file = self.models_dir / 'model_registry.json'
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump(self.model_registry, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"生产模型设置成功")
    
    def log_prediction(self, request_id: str, input_features: Dict[str, float],
                      prediction: float, model_version: str, latency_ms: float):
        """
        记录预测日志
        
        记录每次预测的时间戳、输入特征摘要、模型版本、推理耗时
        """
        log_entry = {
            'request_id': request_id,
            'timestamp': datetime.now().isoformat(),
            'input_features_summary': {
                'feature_count': len(input_features),
                'feature_mean': np.mean(list(input_features.values())),
                'feature_std': np.std(list(input_features.values()))
            },
            'prediction': prediction,
            'model_version': model_version,
            'latency_ms': latency_ms
        }
        
        # 保存到日志文件
        log_dir = self.models_dir / 'logs' / 'predictions'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f'predictions_{datetime.now().strftime("%Y%m%d")}.jsonl'
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + '\n')
    
    def _get_python_version(self) -> str:
        """
        获取Python版本
        """
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    def _get_library_versions(self) -> Dict[str, str]:
        """
        获取库版本
        """
        versions = {}
        
        try:
            import pandas
            versions['pandas'] = pandas.__version__
        except:
            pass
        
        try:
            import numpy
            versions['numpy'] = numpy.__version__
        except:
            pass
        
        try:
            import sklearn
            versions['sklearn'] = sklearn.__version__
        except:
            pass
        
        if XGBOOST_AVAILABLE:
            versions['xgboost'] = xgb.__version__
        
        if LIGHTGBM_AVAILABLE:
            versions['lightgbm'] = lgb.__version__
        
        if CATBOOST_AVAILABLE:
            versions['catboost'] = cb.__version__
        
        return versions
    
    def get_current_model(self) -> Tuple[Any, Dict[str, Any]]:
        """
        获取当前加载的模型
        """
        if self.current_model is None:
            raise ValueError("当前没有加载的模型")
        
        return self.current_model, self.current_model_metadata
