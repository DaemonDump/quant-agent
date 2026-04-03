import os
import sys
import argparse
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from aiagent.ml_pipeline import train_ml_model
from aiagent.feature_spec import get_default_feature_list_path
from strategy_config.strategy_config import StrategyConfig


def parse_args():
    p = argparse.ArgumentParser(prog="train_ml_model", description="Train ML model from local SQLite data")
    p.add_argument("--db", type=str, default="data/tushare/db/quant_data.db")
    p.add_argument("--feature-spec", type=str, default=get_default_feature_list_path())
    p.add_argument("--start", type=str, default="20220101")
    p.add_argument("--end", type=str, default="20260326")
    p.add_argument("--limit-symbols", type=int, default=0)
    p.add_argument("--state", type=str, default="data/tushare/state/ml_train_status.json")
    return p.parse_args()


def main():
    args = parse_args()
    split = {
        "mode": "walk_forward",
        "train_months": 12,
        "val_months": 3,
        "test_months": 1,
        "step_months": 1
    }
    result = train_ml_model(
        db_path=args.db,
        feature_spec_path=args.feature_spec,
        start_date=args.start,
        end_date=args.end,
        split=split,
        state_path=args.state,
        model_name="ml_model",
        limit_symbols=args.limit_symbols
    )

    cfg = StrategyConfig()
    if result.get("success"):
        cfg.update_config({
            "strategy_type": "ml_model",
            "ml_model": {
                "status": "ready",
                "last_trained_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "model_path": result.get("model_path", "")
            }
        })
        print("训练完成:", result.get("model_path"))
    else:
        cfg.update_config({"ml_model": {"status": "error"}})
        print("训练失败:", result.get("message"))


if __name__ == "__main__":
    main()
