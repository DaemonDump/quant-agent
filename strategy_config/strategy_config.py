import json
import os
import uuid
from typing import Dict, List, Any
from app.utils import logger
from datetime import datetime
from aiagent.model_runtime import read_model_bundle_metadata, resolve_model_path


_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'strategy_config.json'
)


class StrategyConfig:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or _DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        logger.info("策略配置初始化完成")

    def _atomic_write_json(self, path: str, payload: Dict[str, Any]) -> bool:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = f"{path}.{uuid.uuid4().hex}.tmp"
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
            return True
        except Exception:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            return False

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if config.get('strategy_type') == 'multi_factor_ml':
                    config['strategy_type'] = 'ml_model'
                pl = config.get('position_limits')
                corrected = False
                if 'risk_preference' not in config:
                    config['risk_preference'] = 0.5
                    corrected = True
                ml = config.get('ml_model')
                if isinstance(ml, dict):
                    for k in ('actual_model_type', 'trainer_name', 'model_file'):
                        if k not in ml:
                            ml[k] = ''
                            corrected = True
                    config['ml_model'] = ml
                if isinstance(pl, dict):
                    for k in ('single_max', 'total_max'):
                        v = pl.get(k, None)
                        if v is None:
                            continue
                        try:
                            fv = float(v)
                        except Exception:
                            continue
                        if 1.0 < fv <= 100.0:
                            pl[k] = fv / 100.0
                            corrected = True
                    config['position_limits'] = pl
                if corrected:
                    self._atomic_write_json(self.config_path, config)
                logger.info(f"从{self.config_path}加载配置成功")
                return config
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                return self._get_default_config()
        else:
            logger.info(f"配置文件不存在，使用默认配置")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'strategy_type': 'ml_model',
            'risk_preference': 0.5,
            'factor_weights': {
                'valuation': 0.3,
                'trend': 0.4,
                'fund': 0.3
            },
            'ml_model': {
                'status': 'untrained',
                'last_trained_at': '',
                'model_path': '',
                'actual_model_type': '',
                'trainer_name': '',
                'model_file': ''
            },
            'signal_thresholds': {
                'buy_score': 6.5,
                'sell_score': 5.5,
                'buy_prob': 0.6,
                'sell_prob': 0.6
            },
            'trend_following_params': {
                'short_ma': 10,
                'long_ma': 30,
                'breakout_window': 20,
                'confirm_days': 1
            },
            'mean_reversion_params': {
                'lookback': 20,
                'entry_z': 2.0,
                'exit_z': 0.5,
                'max_holding_days': 20
            },
            'position_limits': {
                'single_max': 0.1,
                'total_max': 0.8,
                'daily_trades': 10,
                'weekly_trades': 50,
                'symbol_daily_trades': 2
            },
            'targets': {
                'annual_return': 0.20,
                'max_drawdown': 0.10,
                'single_loss': 0.05,
                'daily_loss': 0.02
            },
            'scope': {
                'market': 'A股',
                'symbols': ['沪深300成分股', 'ETF'],
                'timeframe': ['分钟级', '日线级'],
                'market_environment': ['牛市', '震荡市', '熊市']
            }
        }

    def save_config(self):
        try:
            ok = self._atomic_write_json(self.config_path, self.config)
            if ok:
                logger.info(f"配置保存到{self.config_path}成功")
                return True
            logger.error("保存配置文件失败: 原子写入失败")
            return False
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False

    def get_config(self) -> Dict[str, Any]:
        self._refresh_ml_model_status()
        return self.config

    def _refresh_ml_model_status(self):
        try:
            if self.config.get('strategy_type') != 'ml_model':
                return
            ml = self.config.get('ml_model') or {}
            status = ml.get('status', 'untrained')
            model_path = ml.get('model_path') or ''
            corrected = False
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if not model_path:
                try:
                    state_path = os.path.join(root, 'data', 'tushare', 'state', 'ml_train_status.json')
                    if os.path.exists(state_path):
                        with open(state_path, 'r', encoding='utf-8') as f:
                            state = json.load(f) or {}
                        p = (state.get('model_path') or '').strip()
                        if p:
                            abs_p = p if os.path.isabs(p) else os.path.join(root, p)
                            if os.path.exists(abs_p):
                                ml['model_path'] = p
                                if ml.get('status') not in ('training',):
                                    ml['status'] = 'ready'
                                corrected = True
                                model_path = ml.get('model_path') or ''
                except Exception:
                    pass
                if model_path:
                    self.config['ml_model'] = ml
                    if corrected:
                        self.save_config()
                else:
                    if status not in ('untrained', 'training'):
                        ml['status'] = 'untrained'
                    self.config['ml_model'] = ml
                    return
            abs_model_path = model_path
            if not os.path.isabs(abs_model_path):
                abs_model_path = os.path.join(root, model_path)

            if not os.path.exists(abs_model_path):
                alt_path = resolve_model_path(abs_model_path)
                if os.path.exists(alt_path):
                    if os.path.isabs(model_path):
                        ml['model_path'] = alt_path
                    else:
                        ml['model_path'] = os.path.relpath(alt_path, root)
                    abs_model_path = alt_path
                    corrected = True
                else:
                    ml['status'] = 'error'
                    self.config['ml_model'] = ml
                    return

            model_info = read_model_bundle_metadata(abs_model_path)
            if model_info:
                ml['actual_model_type'] = model_info.get('actual_model_type') or ml.get('actual_model_type') or ''
                ml['model_file'] = model_info.get('model_file') or ml.get('model_file') or ''
                meta = model_info.get('metadata') or {}
                trainer_name = meta.get('trainer_name') or model_info.get('trainer_name') or ''
                if trainer_name:
                    ml['trainer_name'] = trainer_name

            try:
                from aiagent.feature_spec import current_feature_list_hash
                current_hash = current_feature_list_hash()
            except Exception:
                current_hash = ''

            model_dir = os.path.dirname(abs_model_path)
            feature_cfg = os.path.join(model_dir, 'feature_config.json')
            if os.path.exists(feature_cfg):
                with open(feature_cfg, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                expected_hash = cfg.get('feature_list_hash') or ''
                if current_hash and expected_hash and current_hash != expected_hash:
                    ml['status'] = 'stale'
                else:
                    if ml.get('status') not in ('training',):
                        ml['status'] = 'ready'
            else:
                if ml.get('status') not in ('training',):
                    ml['status'] = 'ready'

            self.config['ml_model'] = ml
            if corrected:
                self.save_config()
        except Exception as e:
            logger.error(f"刷新模型状态失败: {e}")

    def update_config(self, updates: Dict[str, Any]):
        try:
            if isinstance(updates, dict) and isinstance(updates.get('ml_model'), dict):
                incoming = dict(updates.get('ml_model') or {})
                cur = self.config.get('ml_model') or {}
                if 'model_path' in incoming:
                    inc_path = (incoming.get('model_path') or '').strip()
                    cur_path = (cur.get('model_path') or '').strip()
                    if not inc_path and cur_path:
                        incoming.pop('model_path', None)
                if 'last_trained_at' in incoming:
                    inc_ts = (incoming.get('last_trained_at') or '').strip()
                    cur_ts = (cur.get('last_trained_at') or '').strip()
                    if not inc_ts and cur_ts:
                        incoming.pop('last_trained_at', None)
                updates = dict(updates)
                updates['ml_model'] = incoming

            if isinstance(updates, dict) and 'risk_preference' in updates:
                try:
                    rp = float(updates.get('risk_preference', 0.5))
                except Exception:
                    rp = 0.5
                updates = dict(updates)
                updates['risk_preference'] = max(0.0, min(1.0, rp))

            if isinstance(updates, dict) and isinstance(updates.get('position_limits'), dict):
                pl = dict(updates.get('position_limits') or {})
                for k in ('single_max', 'total_max'):
                    v = pl.get(k, None)
                    if v is None:
                        continue
                    try:
                        fv = float(v)
                    except Exception:
                        continue
                    if 1.0 < fv <= 100.0:
                        pl[k] = fv / 100.0
                updates = dict(updates)
                updates['position_limits'] = pl

            for key, value in updates.items():
                if key in self.config and isinstance(self.config[key], dict) and isinstance(value, dict):
                    self.config[key].update(value)
                else:
                    self.config[key] = value
            
            self.save_config()
            logger.info(f"配置更新成功: {list(updates.keys())}")
            return True
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False

    def get_strategy_type(self) -> str:
        return self.config.get('strategy_type', 'ml_model')

    def get_factor_weights(self) -> Dict[str, float]:
        return self.config.get('factor_weights', {})

    def get_risk_preference(self) -> float:
        try:
            value = float(self.config.get('risk_preference', 0.5))
        except Exception:
            value = 0.5
        return max(0.0, min(1.0, value))

    def get_signal_thresholds(self) -> Dict[str, float]:
        return self.config.get('signal_thresholds', {})

    def get_position_limits(self) -> Dict[str, Any]:
        return self.config.get('position_limits', {})

    def get_targets(self) -> Dict[str, float]:
        return self.config.get('targets', {})

    def get_scope(self) -> Dict[str, Any]:
        return self.config.get('scope', {})

    def validate_config(self) -> Dict[str, Any]:
        errors = []
        warnings = []

        strategy_type = self.get_strategy_type()

        if strategy_type == 'ml_model':
            factor_weights = self.get_factor_weights()
            total_weight = sum(factor_weights.values())
            
            if abs(total_weight - 1.0) > 0.01:
                errors.append(f"因子权重总和应为1.0，当前为{total_weight}")

            signal_thresholds = self.get_signal_thresholds()
            if signal_thresholds.get('buy_score', 0) <= signal_thresholds.get('sell_score', 0):
                errors.append("买入评分阈值应大于卖出评分阈值")

        risk_preference = self.get_risk_preference()
        if not 0.0 <= risk_preference <= 1.0:
            errors.append("风险偏好必须在0到1之间")

        if strategy_type == 'trend_following':
            tf = self.config.get('trend_following_params') or {}
            short_ma = tf.get('short_ma', 10)
            long_ma = tf.get('long_ma', 30)
            if short_ma >= long_ma:
                errors.append(f"短均线周期({short_ma})必须小于长均线周期({long_ma})")
            if short_ma < 1:
                errors.append("短均线周期必须大于0")
            if tf.get('confirm_days', 1) < 1:
                errors.append("确认天数必须大于0")

        if strategy_type == 'mean_reversion':
            mr = self.config.get('mean_reversion_params') or {}
            entry_z = mr.get('entry_z', 2.0)
            exit_z = mr.get('exit_z', 0.5)
            if entry_z <= exit_z:
                errors.append(f"入场Z分数({entry_z})必须大于出场Z分数({exit_z})")
            if mr.get('lookback', 20) < 5:
                errors.append("回望窗口期至少为5天")

        position_limits = self.get_position_limits()
        if position_limits.get('single_max', 0) > 1.0:
            errors.append("单票最大仓位不能超过100%")
        
        if position_limits.get('total_max', 0) > 1.0:
            errors.append("总仓位不能超过100%")

        targets = self.get_targets()
        if targets.get('annual_return', 0) < 0:
            warnings.append("年化收益目标为负值")

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def reset_to_default(self):
        self.config = self._get_default_config()
        self.save_config()
        logger.info("配置已重置为默认值")
