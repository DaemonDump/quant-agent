import json
import os
import hashlib
from typing import Any, Dict


def get_default_feature_list_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data", "tushare", "raw", "feature_list.json")


def load_feature_spec(path: str = "") -> Dict[str, Any]:
    resolved = path or get_default_feature_list_path()
    if not os.path.exists(resolved):
        return {
            "version": "default",
            "features": [],
            "label": {}
        }
    with open(resolved, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"version": "invalid", "features": [], "label": {}}
    data.setdefault("version", "unknown")
    data.setdefault("features", [])
    data.setdefault("label", {})
    return data


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def feature_list_hash(feature_spec: Dict[str, Any]) -> str:
    canonical = _canonical_json(feature_spec)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def current_feature_list_hash(path: str = "") -> str:
    spec = load_feature_spec(path)
    return feature_list_hash(spec)

