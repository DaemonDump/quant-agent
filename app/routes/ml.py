import os
import json
import threading
from datetime import datetime
import time
import uuid
import zipfile

from flask import Blueprint, jsonify, request, current_app, send_file

from strategy_config import StrategyConfig
from aiagent.ml_pipeline import train_ml_model
from aiagent.feature_spec import get_default_feature_list_path
from aiagent.model_runtime import read_model_bundle_metadata


ml_bp = Blueprint('ml_bp', __name__)

_TRAINING_STALE_SECONDS = 1800

def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _state_path() -> str:
    root = _project_root()
    return os.path.join(root, "data", "tushare", "state", "ml_train_status.json")

def _cancel_path() -> str:
    return _state_path() + ".cancel"

def _write_cancel(task_id: str):
    p = _cancel_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    payload = {"task_id": task_id, "requested_at": datetime.now().isoformat()}
    _atomic_write_json(p, payload)

def _try_remove_cancel():
    try:
        p = _cancel_path()
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass


def _safe_abs_under_root(rel_or_abs: str) -> str:
    root = os.path.normpath(_project_root())
    p = (rel_or_abs or "").strip()
    if not p:
        return ""
    abs_p = os.path.normpath(p if os.path.isabs(p) else os.path.join(root, p))
    if os.path.commonpath([root, abs_p]) != root:
        return ""
    return abs_p


def _read_state() -> dict:
    p = _state_path()
    if not os.path.exists(p):
        return {"status": "untrained"}
    try:
        with open(p, "r", encoding="utf-8") as f:
            state = json.load(f)
        if state.get("status") == "training":
            updated_at = state.get("updated_at")
            if updated_at:
                try:
                    dt = datetime.fromisoformat(updated_at)
                    age_seconds = (datetime.now() - dt).total_seconds()
                    if age_seconds > _TRAINING_STALE_SECONDS:
                        payload = dict(state)
                        payload["status"] = "error"
                        payload["message"] = f"训练状态超过{int(_TRAINING_STALE_SECONDS/60)}分钟未更新，训练进程可能已停止，请重试训练或重置训练状态"
                        payload["progress"] = int(payload.get("progress") or 0)
                        _write_state(payload)

                        try:
                            cfg = StrategyConfig()
                            cfg_dict = cfg.get_config() or {}
                            ml = (cfg_dict.get("ml_model") or {})
                            if cfg_dict.get("strategy_type") == "ml_model" and ml.get("status") == "training" and not (ml.get("model_path") or ""):
                                cfg.update_config({
                                    "ml_model": {
                                        "status": "error",
                                        "last_trained_at": ml.get("last_trained_at") or "",
                                        "model_path": ml.get("model_path") or ""
                                    }
                                })
                        except Exception:
                            pass

                        return payload
                except Exception:
                    pass
        return state
    except Exception:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read().strip()
            if not raw:
                return {"status": "training", "message": "训练状态写入中，请稍后刷新", "progress": 0}
        except Exception:
            pass
        return {"status": "training", "message": "训练状态读取中，请稍后刷新", "progress": 0}


def _write_state(payload: dict):
    p = _state_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    payload = dict(payload)
    payload["updated_at"] = datetime.now().isoformat()
    _atomic_write_json(p, payload)


def _atomic_write_json(path: str, payload: dict):
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    last_err = None
    for i in range(8):
        tmp = f"{path}.{uuid.uuid4().hex}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
            return
        except Exception as e:
            last_err = e
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            time.sleep(0.05 * (i + 1))
    if last_err:
        raise last_err


def _train_thread(db_path: str, feature_spec_path: str, start_date: str, end_date: str, limit_symbols: int, model_name: str):
    cfg = StrategyConfig()
    cfg_dict = cfg.get_config() or {}
    prev_ml = (cfg_dict.get("ml_model") or {})
    cfg.update_config({
        "ml_model": {
            "status": "training",
            "last_trained_at": prev_ml.get("last_trained_at") or "",
            "model_path": prev_ml.get("model_path") or ""
        }
    })
    _write_state({"status": "training", "message": "训练任务已启动", "progress": 0})

    try:
        split = {
            "mode": "walk_forward",
            "train_months": 12,
            "val_months": 3,
            "test_months": 1,
            "step_months": 3
        }
        result = train_ml_model(
            db_path=db_path,
            feature_spec_path=feature_spec_path,
            start_date=start_date,
            end_date=end_date,
            split=split,
            state_path=_state_path(),
            model_name=model_name,
            limit_symbols=limit_symbols
        )
        if not result.get("success"):
            if result.get("canceled"):
                prev_path = (prev_ml.get("model_path") or "")
                cfg.update_config({
                    "ml_model": {
                        "status": "ready" if prev_path else "untrained",
                        "last_trained_at": prev_ml.get("last_trained_at") or "",
                        "model_path": prev_path,
                        "actual_model_type": prev_ml.get("actual_model_type") or "",
                        "trainer_name": prev_ml.get("trainer_name") or "",
                        "model_file": prev_ml.get("model_file") or ""
                    }
                })
                return
            cfg.update_config({"ml_model": {"status": "error"}})
            return

        cfg.update_config({
            "ml_model": {
                "status": "ready",
                "last_trained_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "model_path": result.get("model_path", "") or (prev_ml.get("model_path") or ""),
                "actual_model_type": result.get("actual_model_type", "") or "xgboost",
                "trainer_name": "xgboost_classifier",
                "model_file": os.path.basename(result.get("model_path", "") or "model_weights.pkl")
            }
        })
    except Exception as e:
        _write_state({"status": "error", "message": str(e), "progress": 0})
        cfg.update_config({"ml_model": {"status": "error"}})


@ml_bp.route('/api/ml/status', methods=['GET'])
def ml_status():
    state = _read_state()
    try:
        cfg = StrategyConfig()
        cfg_dict = cfg.get_config() or {}
        ml = (cfg_dict.get('ml_model') or {})
        model_path = (state.get('model_path') or ml.get('model_path') or '').strip()
        if model_path:
            info = read_model_bundle_metadata(_safe_abs_under_root(model_path))
            if info:
                state['actual_model_type'] = info.get('actual_model_type') or state.get('actual_model_type') or ''
                state['model_file'] = info.get('model_file') or state.get('model_file') or ''
    except Exception:
        pass
    return jsonify({"success": True, "state": state})


@ml_bp.route('/api/ml/train', methods=['POST'])
def ml_train():
    data = request.json or {}
    cfg = StrategyConfig()
    if cfg.get_strategy_type() != "ml_model":
        return jsonify({"error": "策略类型错误", "message": "当前不是机器学习策略"}), 400

    current_state = _read_state()
    if current_state.get("status") == "training":
        return jsonify({"error": "训练中", "message": "当前已有训练任务在执行"}), 409

    db_path = current_app.config.get("DATABASE")
    feature_spec_path = data.get("feature_spec_path") or get_default_feature_list_path()
    start_date = data.get("start_date") or "20220101"
    end_date = data.get("end_date") or "20260326"
    limit_symbols = int(data.get("limit_symbols") or 0)
    model_name = (data.get("model_name") or "ml_model").strip()
    if not model_name or len(model_name) > 64:
        return jsonify({"error": "参数错误", "message": "model_name 不合法"}), 400
    for ch in model_name:
        if not (ch.isalnum() or ch in ("_", "-")):
            return jsonify({"error": "参数错误", "message": "model_name 仅允许字母数字、_、-"}), 400

    _try_remove_cancel()

    t = threading.Thread(
        target=_train_thread,
        args=(db_path, feature_spec_path, start_date, end_date, limit_symbols, model_name),
        daemon=True
    )
    t.start()

    return jsonify({"success": True, "message": "训练已启动"})

@ml_bp.route('/api/ml/reset_state', methods=['POST'])
def ml_reset_state():
    try:
        current = _read_state()
        task_id = (current.get("task_id") or "").strip()
        if task_id:
            _write_cancel(task_id)
        out_dir = (current.get("output_dir") or "").strip()
        if out_dir:
            root = _project_root()
            abs_out = os.path.normpath(os.path.join(root, out_dir))
            models_root = os.path.normpath(os.path.join(root, "data", "tushare", "models"))
            if os.path.commonpath([models_root, abs_out]) == models_root and os.path.exists(abs_out):
                import shutil
                shutil.rmtree(abs_out, ignore_errors=True)

        cfg = StrategyConfig()
        cfg_dict = cfg.get_config() or {}
        ml = (cfg_dict.get("ml_model") or {})
        keep_path = ml.get("model_path") or ""
        cfg.update_config({
            "ml_model": {
                "status": "ready" if keep_path else "untrained",
                "last_trained_at": ml.get("last_trained_at") or "",
                "model_path": keep_path,
                "actual_model_type": ml.get("actual_model_type") or "",
                "trainer_name": ml.get("trainer_name") or "",
                "model_file": ml.get("model_file") or ""
            }
        })
        _write_state({"status": "untrained", "message": "训练状态已重置", "progress": 0})
        return jsonify({"success": True, "message": "训练状态已重置"})
    except Exception as e:
        return jsonify({"error": "重置失败", "message": str(e)}), 500


@ml_bp.route('/api/ml/download_model', methods=['GET'])
def ml_download_model():
    cfg = StrategyConfig()
    cfg_dict = cfg.get_config() or {}
    ml = (cfg_dict.get("ml_model") or {})
    model_path = (ml.get("model_path") or "").strip()
    if not model_path:
        state = _read_state()
        model_path = (state.get("model_path") or "").strip()
    abs_model_path = _safe_abs_under_root(model_path)
    if not abs_model_path or not os.path.exists(abs_model_path):
        return jsonify({"error": "参数错误", "message": "未找到可下载的模型文件"}), 400

    model_dir = os.path.dirname(abs_model_path)
    if not model_dir or not os.path.isdir(model_dir):
        return jsonify({"error": "参数错误", "message": "模型目录不存在"}), 400

    root = _project_root()
    downloads_dir = os.path.join(root, "data", "tushare", "state", "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    zip_name = f"model_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    zip_path = os.path.join(downloads_dir, zip_name)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _, filenames in os.walk(model_dir):
            for fn in filenames:
                abs_fp = os.path.join(dirpath, fn)
                rel_fp = os.path.relpath(abs_fp, model_dir)
                zf.write(abs_fp, arcname=rel_fp)

    return send_file(zip_path, as_attachment=True, download_name=zip_name)


@ml_bp.route('/api/ml/import_model', methods=['POST'])
def ml_import_model():
    cfg = StrategyConfig()
    if cfg.get_strategy_type() != "ml_model":
        return jsonify({"error": "策略类型错误", "message": "当前不是机器学习策略"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "参数错误", "message": "缺少模型文件"}), 400

    root = _project_root()
    batch = datetime.now().strftime("%Y%m%d%H%M%S")
    import_dir = os.path.join(root, "data", "tushare", "models", "imported", batch)
    os.makedirs(import_dir, exist_ok=True)

    for f in files:
        rel = (f.filename or "").replace("\\", "/").lstrip("/")
        rel = os.path.normpath(rel)
        if not rel or rel.startswith("..") or os.path.isabs(rel):
            return jsonify({"error": "参数错误", "message": "模型文件路径不合法"}), 400
        dest = os.path.normpath(os.path.join(import_dir, rel))
        if os.path.commonpath([import_dir, dest]) != import_dir:
            return jsonify({"error": "参数错误", "message": "模型文件路径不合法"}), 400
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        f.save(dest)

    abs_candidates = []
    for dirpath, _, filenames in os.walk(import_dir):
        for fn in filenames:
            low = fn.lower()
            if low in ("model_weights.pkl", "model.pkl", "model_weights.json", "model.json"):
                abs_candidates.append(os.path.join(dirpath, fn))

    def _score(p: str) -> int:
        name = os.path.basename(p).lower()
        if name == "model_weights.json":
            return 0
        if name == "model_weights.pkl":
            return 1
        if name == "model.json":
            return 2
        return 3

    abs_model_path = sorted(abs_candidates, key=_score)[0] if abs_candidates else ""
    if not abs_model_path or not os.path.exists(abs_model_path):
        return jsonify({"error": "导入失败", "message": "未找到 model_weights.json、model_weights.pkl、model.json 或 model.pkl"}), 400

    rel_model_path = os.path.relpath(abs_model_path, root)
    imported_info = read_model_bundle_metadata(abs_model_path)
    cfg.update_config({
        "ml_model": {
            "status": "ready",
            "last_trained_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "model_path": rel_model_path,
            "actual_model_type": imported_info.get("actual_model_type") or "",
            "trainer_name": ((imported_info.get("metadata") or {}).get("trainer_name") or ""),
            "model_file": imported_info.get("model_file") or ""
        }
    })
    _write_state({"status": "ready", "message": "已导入模型", "progress": 100, "model_path": rel_model_path})

    return jsonify({"success": True, "message": "模型已导入并启用", "model_path": rel_model_path})
