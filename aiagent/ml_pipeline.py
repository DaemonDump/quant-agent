import json
import os
import pickle
import sqlite3
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple
import uuid

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, log_loss
try:
    from sklearn.calibration import CalibratedClassifierCV
    SKLEARN_CALIBRATION_AVAILABLE = True
except Exception:
    SKLEARN_CALIBRATION_AVAILABLE = False
try:
    from xgboost import XGBClassifier
except Exception:
    XGBClassifier = None

from .config import Config
from .feature_spec import load_feature_spec
from .ml_features import compute_features
from .model_manager import ModelManager


def _parse_ymd(s: str) -> str:
    return s.replace("-", "")


def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _get_table_select_cols(conn: sqlite3.Connection) -> List[str]:
    available_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(stock_history_data)").fetchall()
    }
    required_cols = [
        "symbol", "trade_date", "open_price", "high_price", "low_price",
        "close_price", "volume", "amount", "pe", "pb"
    ]
    optional_cols = [
        "turnover_rate", "total_mv", "circ_mv",
        "buy_lg_amount", "net_mf_amount", "net_amount_rate", "adj_type"
    ]
    missing_required = [c for c in required_cols if c not in available_cols]
    if missing_required:
        raise RuntimeError(f"stock_history_data 缺少必要字段: {', '.join(missing_required)}")
    return required_cols + [
        c if c in available_cols else f"NULL AS {c}"
        for c in optional_cols
    ]


def _load_all_symbols_data(conn: sqlite3.Connection, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    select_cols = _get_table_select_cols(conn)
    placeholders = ",".join("?" * len(symbols))
    q = f"""
        SELECT {", ".join(select_cols)}
        FROM stock_history_data
        WHERE symbol IN ({placeholders}) AND trade_date >= ? AND trade_date <= ?
        ORDER BY symbol ASC, trade_date ASC
    """
    return pd.read_sql_query(q, conn, params=(*symbols, start_date, end_date))


def _build_labels(df_feat: pd.DataFrame, horizon_days: int, up: float, down: float) -> pd.DataFrame:
    df = df_feat.copy()
    if "volume" in df.columns:
        vol = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        df = df[vol > 0].copy()
    if "amount" in df.columns:
        amt = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        df = df[amt > 0].copy()
    if "close" in df.columns and "open" in df.columns:
        close_s = pd.to_numeric(df["close"], errors="coerce")
        open_s = pd.to_numeric(df["open"], errors="coerce")
        pct_chg = (close_s - open_s).abs() / open_s.replace(0, np.nan)
        df = df[pct_chg < 0.205].copy()
    future_close = df.groupby("symbol")["close"].shift(-horizon_days)
    next_open = df.groupby("symbol")["open"].shift(-1)
    df["label_5d_return"] = future_close / next_open - 1.0
    r = df["label_5d_return"]
    df["label_5d_class"] = np.where(r > up, 1, np.where(r < down, 0, 2))
    df = df.dropna(subset=["label_5d_return"])
    return df


def _split_mask(dates: pd.Series, start: str, end: str) -> pd.Series:
    return (dates >= start) & (dates <= end)


def _generate_walk_forward_windows(
    start_date: str,
    end_date: str,
    train_months: int = 12,
    val_months: int = 3,
    test_months: int = 1,
    step_months: int = 1
) -> List[Dict[str, Tuple[str, str]]]:
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    cursor = start_ts.replace(day=1)
    windows: List[Dict[str, Tuple[str, str]]] = []

    while True:
        train_start = cursor
        val_start = train_start + pd.DateOffset(months=train_months)
        test_start = val_start + pd.DateOffset(months=val_months)
        if test_start > end_ts:
            break

        train_end = val_start - pd.Timedelta(days=1)
        val_end = test_start - pd.Timedelta(days=1)
        raw_test_end = test_start + pd.DateOffset(months=test_months) - pd.Timedelta(days=1)
        test_end = min(raw_test_end, end_ts)

        windows.append({
            "train": (train_start.strftime("%Y%m%d"), train_end.strftime("%Y%m%d")),
            "val": (val_start.strftime("%Y%m%d"), val_end.strftime("%Y%m%d")),
            "test": (test_start.strftime("%Y%m%d"), test_end.strftime("%Y%m%d"))
        })
        cursor = cursor + pd.DateOffset(months=step_months)

    return windows


def _resolve_training_windows(start_date: str, end_date: str, split: Dict[str, Any]) -> Tuple[str, List[Dict[str, Tuple[str, str]]], Dict[str, Any]]:
    mode = str(split.get("mode") or "").strip().lower()
    if mode == "walk_forward":
        wf_cfg = {
            "mode": "walk_forward",
            "train_months": int(split.get("train_months", 12)),
            "val_months": int(split.get("val_months", 3)),
            "test_months": int(split.get("test_months", 1)),
            "step_months": int(split.get("step_months", 1)),
        }
        windows = _generate_walk_forward_windows(
            start_date=start_date,
            end_date=end_date,
            train_months=wf_cfg["train_months"],
            val_months=wf_cfg["val_months"],
            test_months=wf_cfg["test_months"],
            step_months=wf_cfg["step_months"]
        )
        return "walk_forward", windows, wf_cfg

    normalized = {
        "train": (_parse_ymd(split["train"][0]), _parse_ymd(split["train"][1])),
        "val": (_parse_ymd(split["val"][0]), _parse_ymd(split["val"][1])),
        "test": (_parse_ymd(split["test"][0]), _parse_ymd(split["test"][1]))
    }
    return "fixed", [normalized], {"mode": "fixed"}


def _compute_feature_stats(X: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    stats = {}
    for col in X.columns:
        s = pd.to_numeric(X[col], errors="coerce")
        missing_rate = float(s.isna().mean())
        mean = float(s.mean(skipna=True)) if missing_rate < 1.0 else 0.0
        std = float(s.std(skipna=True)) if missing_rate < 1.0 else 1.0
        if not np.isfinite(std) or std <= 1e-12:
            std = 1.0
        if not np.isfinite(mean):
            mean = 0.0
        stats[col] = {"mean": mean, "std": std, "missing_rate": missing_rate}
    return stats


def _apply_stats(X: pd.DataFrame, stats: Dict[str, Dict[str, float]]) -> np.ndarray:
    arrs = []
    for col in X.columns:
        s = pd.to_numeric(X[col], errors="coerce")
        mean = stats[col]["mean"]
        std = stats[col]["std"]
        x = s.fillna(mean).to_numpy(dtype=float)
        x = (x - mean) / std
        arrs.append(x)
    return np.column_stack(arrs)


def _build_time_weights(trade_dates: pd.Series) -> np.ndarray:
    dates = pd.to_datetime(trade_dates.astype(str), format="%Y%m%d", errors="coerce")
    if dates.isna().all():
        return np.ones(len(trade_dates), dtype=float)
    latest = dates.max()
    recent_cutoff = latest - pd.DateOffset(months=3)
    return np.where(dates >= recent_cutoff, 1.0, 0.8).astype(float)


def train_ml_model(
    db_path: str,
    feature_spec_path: str,
    start_date: str,
    end_date: str,
    split: Dict[str, Any],
    state_path: str,
    model_name: str = "ml_model",
    limit_symbols: int = 0
) -> Dict[str, Any]:
    cfg = Config()
    start_date = _parse_ymd(start_date)
    end_date = _parse_ymd(end_date)
    split_mode, training_windows, split_meta = _resolve_training_windows(start_date, end_date, split)

    _ensure_dir(state_path)

    cancel_path = state_path + ".cancel"

    class CancelledError(Exception):
        pass

    def cancel_requested(task_id: str) -> bool:
        try:
            if not os.path.exists(cancel_path):
                return False
            with open(cancel_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            target = (payload.get("task_id") or "").strip()
            return (not target) or target == "*" or target == task_id
        except Exception:
            return True

    def clear_cancel_flag():
        try:
            if os.path.exists(cancel_path):
                os.remove(cancel_path)
        except Exception:
            pass

    def write_state(payload: Dict[str, Any]):
        if cancel_requested(task_id):
            payload = {"task_id": task_id, "status": "untrained", "message": "训练已取消", "progress": 0}
        payload = dict(payload)
        payload["updated_at"] = datetime.now().isoformat()
        last_err = None
        for i in range(8):
            tmp = f"{state_path}.{uuid.uuid4().hex}.tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                os.replace(tmp, state_path)
                if cancel_requested(task_id):
                    raise CancelledError()
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

    task_id = datetime.now().strftime("%Y%m%d%H%M%S")
    clear_cancel_flag()
    write_state({"task_id": task_id, "status": "training", "message": "开始训练", "progress": 0})

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    last_output_dir = ""
    conn = None
    try:
        feature_spec = load_feature_spec(feature_spec_path)
        features: List[str] = list(feature_spec.get("features") or [])
        label_cfg = feature_spec.get("label") or {}
        horizon = int(label_cfg.get("horizon_days", 5))
        up = float(label_cfg.get("up_threshold", 0.02))
        down = float(label_cfg.get("down_threshold", -0.02))

        t0 = time.time()
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM stock_history_data")
        symbols = [row[0] for row in cur.fetchall()]
        symbols = sorted([s for s in symbols if s])
        if limit_symbols and limit_symbols > 0:
            symbols = symbols[:limit_symbols]

        total = len(symbols)
        if total == 0:
            write_state({"task_id": task_id, "status": "error", "message": "数据库无股票数据"})
            return {"success": False, "message": "数据库无股票数据"}

        write_state({
            "task_id": task_id,
            "status": "training",
            "message": f"批量读取 {total} 只股票数据...",
            "progress": 2
        })

        BATCH_SIZE = 500
        raw_frames: List[pd.DataFrame] = []
        for batch_start in range(0, total, BATCH_SIZE):
            batch = symbols[batch_start: batch_start + BATCH_SIZE]
            raw_frames.append(_load_all_symbols_data(conn, batch, start_date, end_date))
            pct = round(2 + (batch_start + len(batch)) / total * 8, 1)
            write_state({
                "task_id": task_id,
                "status": "training",
                "message": f"读取数据 {min(batch_start + BATCH_SIZE, total)}/{total}",
                "progress": pct
            })

        if conn is not None:
            conn.close()
            conn = None

        raw_df = pd.concat(raw_frames, ignore_index=True) if raw_frames else pd.DataFrame()
        del raw_frames

        if raw_df.empty:
            write_state({"task_id": task_id, "status": "error", "message": "数据库无股票数据"})
            return {"success": False, "message": "数据库无股票数据"}

        sym_counts = raw_df.groupby("symbol").size()
        valid_symbols = sym_counts[sym_counts >= 120].index.tolist()

        all_rows = []
        last_state_t = 0.0
        for idx, s in enumerate(valid_symbols, 1):
            if cancel_requested(task_id):
                write_state({"task_id": task_id, "status": "untrained", "message": "训练已取消", "progress": 0})
                return {"success": False, "canceled": True, "message": "训练已取消"}
            df = raw_df[raw_df["symbol"] == s].reset_index(drop=True)
            df_feat = compute_features(df, features)
            if cancel_requested(task_id):
                write_state({"task_id": task_id, "status": "untrained", "message": "训练已取消", "progress": 0})
                return {"success": False, "canceled": True, "message": "训练已取消"}
            if df_feat.empty:
                continue
            df_feat["close"] = pd.to_numeric(df_feat.get("close"), errors="coerce")
            df_feat["open"] = pd.to_numeric(df.get("open_price"), errors="coerce").values
            df_lab = _build_labels(df_feat, horizon, up, down)
            if cancel_requested(task_id):
                write_state({"task_id": task_id, "status": "untrained", "message": "训练已取消", "progress": 0})
                return {"success": False, "canceled": True, "message": "训练已取消"}
            if df_lab.empty:
                continue

            cols = ["trade_date", "symbol"] + features + ["label_5d_class", "label_5d_return"]
            all_rows.append(df_lab[cols])
            now_t = time.time()
            if idx == 1 or idx % 50 == 0 or (now_t - last_state_t) > 3.0:
                last_state_t = now_t
                write_state({
                    "task_id": task_id,
                    "status": "training",
                    "message": f"特征构建 {idx}/{len(valid_symbols)}（当前：{s}）",
                    "progress": round(10 + idx / len(valid_symbols) * 50, 1)
                })

        del raw_df

        if XGBClassifier is None:
            raise RuntimeError("未安装 xgboost，请先执行 pip install -r requirements.txt")
        if not all_rows:
            write_state({"task_id": task_id, "status": "error", "message": "无可训练样本"})
            return {"success": False, "message": "无可训练样本"}

        all_df = pd.concat(all_rows, ignore_index=True)
        del all_rows
        all_df["trade_date"] = all_df["trade_date"].astype(str)
        all_df = all_df.sort_values(["trade_date", "symbol"]).reset_index(drop=True)

        feat_raw = np.empty((len(all_df), len(features)), dtype=np.float64)
        for fi, col in enumerate(features):
            col_s = pd.to_numeric(all_df[col], errors="coerce")
            col_mean = float(col_s.mean(skipna=True)) if col_s.notna().any() else 0.0
            if not np.isfinite(col_mean):
                col_mean = 0.0
            feat_raw[:, fi] = col_s.fillna(col_mean).to_numpy(dtype=np.float64)
        label_arr = all_df["label_5d_class"].to_numpy(dtype=np.int32)
        date_arr = all_df["trade_date"].to_numpy()

        wf_records: List[Dict[str, Any]] = []
        clf = None
        feature_stats = {}
        train_row_count = 0
        val_row_count = 0
        test_row_count = 0
        metrics: Dict[str, Any] = {}
        selected_window: Dict[str, Tuple[str, str]] = {}
        best_candidate = None
        best_clf = None
        best_feature_stats: Dict[str, Dict[str, float]] = {}
        best_metrics: Dict[str, Any] = {}
        best_selected_window: Dict[str, Tuple[str, str]] = {}
        best_train_row_count = 0
        best_val_row_count = 0
        best_test_row_count = 0

        for win_idx, win in enumerate(training_windows, 1):
            m_train = (date_arr >= win["train"][0]) & (date_arr <= win["train"][1])
            m_val   = (date_arr >= win["val"][0])   & (date_arr <= win["val"][1])
            m_test  = (date_arr >= win["test"][0])  & (date_arr <= win["test"][1])
            if not m_train.any() or not m_val.any() or not m_test.any():
                continue

            X_train_raw = feat_raw[m_train]
            X_val_raw   = feat_raw[m_val]
            X_test_raw  = feat_raw[m_test]
            y_train = label_arr[m_train]
            y_val   = label_arr[m_val]
            y_test  = label_arr[m_test]
            train_dates = date_arr[m_train]

            progress = 60 + round(win_idx / max(len(training_windows), 1) * 25, 1)
            write_state({
                "task_id": task_id,
                "status": "training",
                "message": f"滚动训练窗口 {win_idx}/{len(training_windows)}",
                "progress": progress,
                "actual_model_type": "xgboost",
                "split_mode": split_mode
            })

            col_means = X_train_raw.mean(axis=0)
            col_stds  = X_train_raw.std(axis=0)
            col_stds[col_stds <= 1e-12] = 1.0
            col_stds[~np.isfinite(col_stds)] = 1.0
            col_means[~np.isfinite(col_means)] = 0.0

            X_train_arr = (X_train_raw - col_means) / col_stds
            X_val_arr   = (X_val_raw   - col_means) / col_stds
            X_test_arr  = (X_test_raw  - col_means) / col_stds

            feature_stats = {
                col: {"mean": float(col_means[fi]), "std": float(col_stds[fi]), "missing_rate": 0.0}
                for fi, col in enumerate(features)
            }

            dates_pd = pd.to_datetime(pd.Series(train_dates).astype(str), format="%Y%m%d", errors="coerce")
            latest = dates_pd.max()
            recent_cutoff = latest - pd.DateOffset(months=3)
            sample_weight = np.where(dates_pd >= recent_cutoff, 1.0, 0.8).astype(float)

            train_row_count = int(m_train.sum())
            val_row_count   = int(m_val.sum())
            test_row_count  = int(m_test.sum())

            clf = XGBClassifier(
                objective='multi:softprob',
                num_class=3,
                eval_metric='mlogloss',
                n_estimators=int(cfg.training.n_estimators),
                max_depth=int(cfg.training.max_depth),
                learning_rate=float(cfg.training.learning_rate),
                min_child_weight=float(cfg.training.min_child_weight),
                subsample=float(cfg.training.subsample),
                colsample_bytree=float(cfg.training.colsample_bytree),
                reg_lambda=float(cfg.model.l2_regularization or 1.0),
                random_state=42,
                tree_method='hist',
                n_jobs=max(1, (os.cpu_count() or 2) - 1),
                early_stopping_rounds=int(cfg.training.patience)
            )
            clf.fit(
                X_train_arr,
                y_train,
                sample_weight=sample_weight,
                eval_set=[(X_val_arr, y_val)],
                verbose=False
            )

            val_pred = clf.predict(X_val_arr)
            val_proba = clf.predict_proba(X_val_arr)
            test_pred = clf.predict(X_test_arr)
            test_proba = clf.predict_proba(X_test_arr)
            metrics = {
                "val_accuracy": float(accuracy_score(y_val, val_pred)),
                "val_f1_weighted": float(f1_score(y_val, val_pred, average="weighted")),
                "val_logloss": float(log_loss(y_val, val_proba, labels=[0, 1, 2])),
                "test_accuracy": float(accuracy_score(y_test, test_pred)),
                "test_f1_weighted": float(f1_score(y_test, test_pred, average="weighted")),
                "test_logloss": float(log_loss(y_test, test_proba, labels=[0, 1, 2]))
            }
            selected_window = win
            wf_records.append({
                "index": win_idx,
                "train": {"start": win["train"][0], "end": win["train"][1], "rows": train_row_count},
                "val": {"start": win["val"][0], "end": win["val"][1], "rows": val_row_count},
                "test": {"start": win["test"][0], "end": win["test"][1], "rows": test_row_count},
                "best_iteration": int(getattr(clf, 'best_iteration', -1)),
                "val_accuracy": metrics["val_accuracy"],
                "val_f1_weighted": metrics["val_f1_weighted"],
                "val_logloss": metrics["val_logloss"],
                "test_accuracy": metrics["test_accuracy"],
                "test_f1_weighted": metrics["test_f1_weighted"],
                "test_logloss": metrics["test_logloss"]
            })
            candidate = (
                float(metrics["val_logloss"]),
                -float(metrics["val_f1_weighted"]),
                -float(metrics["val_accuracy"])
            )
            if best_candidate is None or candidate < best_candidate:
                best_candidate = candidate
                best_clf = clf
                best_feature_stats = dict(feature_stats)
                best_metrics = dict(metrics)
                best_selected_window = dict(win)
                best_train_row_count = train_row_count
                best_val_row_count = val_row_count
                best_test_row_count = test_row_count

        if clf is None or not wf_records:
            write_state({"task_id": task_id, "status": "error", "message": "滚动训练窗口样本不足"})
            return {"success": False, "message": "滚动训练窗口样本不足"}

        if best_clf is not None:
            clf = best_clf
            feature_stats = best_feature_stats
            metrics = best_metrics
            selected_window = best_selected_window
            train_row_count = best_train_row_count
            val_row_count = best_val_row_count
            test_row_count = best_test_row_count

        calibrator = None
        if SKLEARN_CALIBRATION_AVAILABLE:
            try:
                write_state({"task_id": task_id, "status": "training", "message": "拟合概率校准器", "progress": 88})
                m_cal = (date_arr >= selected_window["val"][0]) & (date_arr <= selected_window["val"][1])
                if m_cal.sum() >= 30:
                    X_cal_raw = feat_raw[m_cal]
                    y_cal = label_arr[m_cal]
                    col_means_arr = np.array([feature_stats[c]["mean"] for c in features], dtype=np.float64)
                    col_stds_arr = np.array([feature_stats[c]["std"] for c in features], dtype=np.float64)
                    col_stds_arr[col_stds_arr <= 1e-12] = 1.0
                    X_cal_arr = (X_cal_raw - col_means_arr) / col_stds_arr
                    cal_cv = CalibratedClassifierCV(clf, method='isotonic', cv='prefit')
                    cal_cv.fit(X_cal_arr, y_cal)
                    calibrator = cal_cv
            except Exception:
                calibrator = None

        if split_mode == "walk_forward":
            metrics = dict(metrics)
            metrics["wf_window_count"] = int(len(wf_records))
            metrics["wf_test_accuracy_mean"] = float(np.mean([r["test_accuracy"] for r in wf_records]))
            metrics["wf_test_f1_weighted_mean"] = float(np.mean([r["test_f1_weighted"] for r in wf_records]))
            metrics["wf_test_logloss_mean"] = float(np.mean([r["test_logloss"] for r in wf_records]))

        write_state({"task_id": task_id, "status": "training", "message": "保存模型", "progress": 90, "metrics": metrics})

        manager = ModelManager()
        version = datetime.now().strftime("%Y%m%d%H%M")
        last_output_dir = os.path.join("data", "tushare", "models", model_name, version)
        model_path = os.path.join(last_output_dir, "model_weights.pkl")
        write_state({
            "task_id": task_id,
            "status": "training",
            "message": "准备保存模型",
            "progress": 89,
            "output_dir": last_output_dir,
            "model_path": model_path,
            "metrics": metrics,
            "actual_model_type": "xgboost"
        })
        manager.save_model(
            clf,
            model_name=model_name,
            version=version,
            feature_names=features,
            training_metrics=metrics,
            metadata={
                "task_type": "classification",
                "actual_model_type": "xgboost",
                "trainer_name": "xgboost_classifier",
                "n_classes": 3,
                "classes": [0, 1, 2],
                "best_iteration": int(getattr(clf, 'best_iteration', -1)),
                "best_score": float(getattr(clf, 'best_score', 0.0) or 0.0),
                "has_calibrator": calibrator is not None,
                "model_params": {
                    "n_estimators": int(cfg.training.n_estimators),
                    "max_depth": int(cfg.training.max_depth),
                    "learning_rate": float(cfg.training.learning_rate),
                    "min_child_weight": float(cfg.training.min_child_weight),
                    "subsample": float(cfg.training.subsample),
                    "colsample_bytree": float(cfg.training.colsample_bytree),
                    "early_stopping_rounds": int(cfg.training.patience)
                },
                "train_rows": train_row_count,
                "val_rows": val_row_count,
                "test_rows": test_row_count,
                "split_mode": split_mode,
                "split": selected_window,
                "window": {"start": start_date, "end": end_date},
                "walk_forward": {
                    **split_meta,
                    "window_count": int(len(wf_records)),
                    "windows": wf_records
                }
            },
            feature_stats=feature_stats,
            feature_spec_path=feature_spec_path
        )

        if calibrator is not None:
            try:
                cal_path = os.path.join(root, last_output_dir, "calibrator.pkl")
                with open(cal_path, "wb") as f:
                    pickle.dump(calibrator, f)
            except Exception:
                pass

        elapsed = int(time.time() - t0)
        write_state({
            "task_id": task_id,
            "status": "ready",
            "message": "训练完成",
            "progress": 100,
            "model_path": model_path,
            "metrics": metrics,
            "elapsed_seconds": elapsed,
            "actual_model_type": "xgboost",
            "split_mode": split_mode
        })

        return {
            "success": True,
            "model_path": model_path,
            "metrics": metrics,
            "elapsed_seconds": elapsed,
            "actual_model_type": "xgboost",
            "split_mode": split_mode
        }
    except CancelledError:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
        if last_output_dir:
            try:
                abs_out = os.path.join(root, last_output_dir)
                abs_out = os.path.normpath(abs_out)
                if os.path.exists(abs_out):
                    import shutil
                    shutil.rmtree(abs_out, ignore_errors=True)
            except Exception:
                pass
        return {"success": False, "canceled": True, "message": "训练已取消"}
