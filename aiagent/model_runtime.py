import json
import os
import pickle
from typing import Any, Dict, List, Optional, Tuple


def read_json_if_exists(path: str) -> Dict[str, Any]:
    try:
        if path and os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        return {}
    return {}


def resolve_model_path(model_path: str) -> str:
    path = (model_path or '').strip()
    if not path:
        return ''
    if os.path.exists(path):
        return path
    model_dir = path if os.path.isdir(path) else os.path.dirname(path)
    if not model_dir:
        return ''
    candidates = [
        path,
        os.path.join(model_dir, 'model_weights.json'),
        os.path.join(model_dir, 'model_weights.pkl'),
        os.path.join(model_dir, 'model.json'),
        os.path.join(model_dir, 'model.pkl'),
    ]
    for fp in candidates:
        if fp and os.path.exists(fp):
            return fp
    return ''


def read_model_bundle_metadata(model_path: str) -> Dict[str, Any]:
    abs_model_path = resolve_model_path(model_path)
    if not abs_model_path:
        return {}
    model_dir = os.path.dirname(abs_model_path)
    metadata = read_json_if_exists(os.path.join(model_dir, 'metadata.json'))
    model_file = metadata.get('model_file') or os.path.basename(abs_model_path)
    explicit_type = metadata.get('actual_model_type') or ''
    if explicit_type:
        actual_model_type = explicit_type
    elif str(model_file).lower().endswith('.json') or abs_model_path.lower().endswith('.json'):
        actual_model_type = 'xgboost'
    elif str(model_file).lower().endswith('.pkl') or abs_model_path.lower().endswith('.pkl'):
        actual_model_type = 'pickle'
    else:
        actual_model_type = metadata.get('model_type') or 'pickle'
    info = dict(metadata)
    info['actual_model_type'] = actual_model_type
    info['resolved_model_path'] = abs_model_path
    info['model_file'] = model_file
    return info


def load_model_bundle(model_path: str) -> Tuple[Optional[Any], Optional[Dict[str, Any]], List[str], Dict[str, Any]]:
    info = read_model_bundle_metadata(model_path)
    abs_model_path = info.get('resolved_model_path') or ''
    if not abs_model_path:
        return None, None, [], {}

    model = None
    try:
        if abs_model_path.lower().endswith('.json'):
            import xgboost as xgb
            model = xgb.XGBClassifier()
            model.load_model(abs_model_path)
        else:
            with open(abs_model_path, 'rb') as f:
                model = pickle.load(f)
    except Exception:
        return None, None, [], info

    model_dir = os.path.dirname(abs_model_path)
    feature_stats = read_json_if_exists(os.path.join(model_dir, 'feature_stats.json')) or None
    feature_cfg = read_json_if_exists(os.path.join(model_dir, 'feature_config.json'))
    feature_names = list(feature_cfg.get('feature_names') or info.get('feature_names') or [])

    cal_path = os.path.join(model_dir, 'calibrator.pkl')
    if os.path.exists(cal_path):
        try:
            with open(cal_path, 'rb') as f:
                calibrator = pickle.load(f)
            info['calibrator'] = calibrator
        except Exception:
            pass

    return model, feature_stats, feature_names, info
