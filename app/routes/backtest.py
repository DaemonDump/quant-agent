import os
from flask import Blueprint, jsonify, request, current_app
from backtest_engine import BacktestEngine, ParameterOptimizer, RiskTester, OverfittingChecker
from app.db import get_setting
from data_ingestion.data_collector import RealTimeDataCollector
from strategy_config import StrategyConfig
from signal_engine import FactorCalculator, SignalGenerator
from aiagent.model_runtime import load_model_bundle

backtest_bp = Blueprint('backtest_bp', __name__)

DATABASE = 'data/tushare/db/quant_data.db'

def _normalize_date(date_str: str) -> str:
    if not date_str:
        return date_str
    return date_str.replace('-', '')

def _get_db_path() -> str:
    try:
        return current_app.config.get('DATABASE') or DATABASE
    except Exception:
        return DATABASE

def _get_symbol_range(conn, symbol: str):
    try:
        cur = conn.cursor()
        cur.execute('SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM stock_history_data WHERE symbol=?', (symbol,))
        row = cur.fetchone()
        if not row:
            return None
        return {'min_date': row[0], 'max_date': row[1], 'count': row[2]}
    except Exception:
        return None

def _ensure_history_data(symbol: str, start_date: str, end_date: str) -> bool:
    token = get_setting('tushare_token')
    if not token:
        return False

    collector = RealTimeDataCollector(_get_db_path())
    collector.set_token(token)
    df_new = collector.collect_history_data(symbol, start_date, end_date)
    return df_new is not None and not df_new.empty

@backtest_bp.route('/api/backtest/simple', methods=['POST'])
def run_simple_backtest():
    try:
        data = request.json
        symbol = data.get('symbol')
        start_date = _normalize_date(data.get('start_date'))
        end_date = _normalize_date(data.get('end_date'))
        
        if not symbol or not start_date or not end_date:
            return jsonify({'error': '参数错误', 'message': '缺少必要参数'}), 400
        
        symbol = symbol.upper()

        commission_rate = float(data.get('commission_rate') or data.get('commission') or 0.0003)
        slippage_rate = float(data.get('slippage') or 0.001)
        initial_capital = float(data.get('initial_capital') or 100000)

        cfg = StrategyConfig()
        cfg_dict = cfg.get_config() or {}
        strategy_type = cfg_dict.get('strategy_type') or 'ml_model'
        risk_preference = data.get('risk_preference', cfg_dict.get('risk_preference', 0.5))
        try:
            risk_preference = max(0.0, min(1.0, float(risk_preference)))
        except Exception:
            risk_preference = 0.5
        position_limits = cfg_dict.get('position_limits') or {}
        targets = cfg_dict.get('targets') or {}

        _hard_max_pos_raw = data.get('hard_max_position')
        _hard_single_loss_raw = data.get('hard_single_loss')
        try:
            _hard_max_pos = float(_hard_max_pos_raw) / 100.0 if _hard_max_pos_raw not in (None, '', 0) else None
        except Exception:
            _hard_max_pos = None
        try:
            _hard_single_loss = float(_hard_single_loss_raw) / 100.0 if _hard_single_loss_raw not in (None, '', 0) else None
        except Exception:
            _hard_single_loss = None

        strategy_single_max = float(position_limits.get('single_max') or 0.2)
        if _hard_max_pos is not None:
            single_position_limit = min(strategy_single_max, _hard_max_pos)
        else:
            single_position_limit = strategy_single_max

        tf_params = (cfg_dict.get('trend_following_params') or {})
        mr_params = (cfg_dict.get('mean_reversion_params') or {})
        ml_weights = (cfg_dict.get('factor_weights') or {})
        ml_thresholds = (cfg_dict.get('signal_thresholds') or {})
        ml_calc = FactorCalculator(ml_weights)
        ml_gen = SignalGenerator(ml_thresholds)

        mf_cfg = cfg_dict.get('market_filter') or {}
        vp_cfg = cfg_dict.get('volatility_penalty') or {}
        _mf_enabled = bool(mf_cfg.get('enabled', True))
        _mf_index = str(mf_cfg.get('index_code', '000300.SH'))
        _mf_ma_period = int(mf_cfg.get('ma_period', 20))
        _mf_below_cap = float(mf_cfg.get('below_ma_cap', 0.5))
        _mf_far_cap = float(mf_cfg.get('far_below_ma_cap', 0.2))
        _mf_far_pct = float(mf_cfg.get('far_below_pct', -0.05))
        _vp_enabled = bool(vp_cfg.get('enabled', True))
        _vp_mid = float(vp_cfg.get('atr_threshold_mid', 0.025))
        _vp_high = float(vp_cfg.get('atr_threshold_high', 0.035))
        _vp_pen_mid = float(vp_cfg.get('penalty_mid', 0.7))
        _vp_pen_high = float(vp_cfg.get('penalty_high', 0.4))

        _index_close_map = {}
        if _mf_enabled and strategy_type == 'ml_model':
            try:
                token = get_setting('tushare_token')
                if token:
                    import tushare as ts
                    ts.set_token = lambda x: None
                    _pro = ts.pro_api(token)
                    _extra_start = str(int(start_date) - 300)
                    _idx_df = _pro.index_daily(
                        ts_code=_mf_index,
                        start_date=_extra_start,
                        end_date=end_date
                    )
                    if _idx_df is not None and not _idx_df.empty:
                        _idx_df = _idx_df.sort_values('trade_date')
                        _index_close_map = dict(zip(
                            _idx_df['trade_date'].astype(str).tolist(),
                            _idx_df['close'].astype(float).tolist()
                        ))
            except Exception:
                _index_close_map = {}

        _ml_model = None
        _feature_stats = None
        _feature_names = None
        _runtime_info = {}
        if strategy_type == 'ml_model':
            _ml_cfg = cfg_dict.get('ml_model') or {}
            _model_path = _ml_cfg.get('model_path') or ''
            if _model_path:
                _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                _abs_model_path = os.path.join(_root, _model_path) if not os.path.isabs(_model_path) else _model_path
                _ml_model, _feature_stats, _feature_names, _runtime_info = load_model_bundle(_abs_model_path)

        _FEAT_LOOKBACK = 120

        def _make_ml_prediction(hist_df):
            if _ml_model is None or not _feature_names:
                return None
            try:
                from aiagent.ml_features import compute_features
                from aiagent.ml_pipeline import _apply_stats
                tail_df = hist_df.iloc[-_FEAT_LOOKBACK:] if len(hist_df) > _FEAT_LOOKBACK else hist_df
                df_feat = compute_features(tail_df, _feature_names)
                if df_feat is None or df_feat.empty:
                    return None
                missing = [c for c in _feature_names if c not in df_feat.columns]
                if missing:
                    return None
                X = df_feat[_feature_names].iloc[[-1]]
                if _feature_stats:
                    X_arr = _apply_stats(X, _feature_stats)
                else:
                    X_arr = X.values
                proba = _ml_model.predict_proba(X_arr)[0]
                return {'buy_prob': float(proba[1]), 'sell_prob': float(proba[0])}
            except Exception:
                return None

        def strategy_func(hist_df):
            if hist_df is None or len(hist_df) < 30:
                return 'hold'

            if strategy_type == 'trend_following':
                short_n = int(tf_params.get('short_ma', 10))
                long_n = int(tf_params.get('long_ma', 30))
                breakout_window = int(tf_params.get('breakout_window', 20))
                confirm_days = int(tf_params.get('confirm_days', 1))
                if len(hist_df) < max(short_n, long_n, breakout_window) + confirm_days + 1:
                    return 'hold'
                close = hist_df['close_price'].astype(float)
                short_ma = close.rolling(short_n, min_periods=short_n).mean()
                long_ma = close.rolling(long_n, min_periods=long_n).mean()
                if len(short_ma) < confirm_days + 1 or len(long_ma) < confirm_days + 1:
                    return 'hold'
                golden_cross = all(
                    short_ma.iloc[-(confirm_days + 1 - i)] > long_ma.iloc[-(confirm_days + 1 - i)]
                    for i in range(confirm_days)
                ) and short_ma.iloc[-(confirm_days + 1)] <= long_ma.iloc[-(confirm_days + 1)]
                death_cross = all(
                    short_ma.iloc[-(confirm_days + 1 - i)] < long_ma.iloc[-(confirm_days + 1 - i)]
                    for i in range(confirm_days)
                ) and short_ma.iloc[-(confirm_days + 1)] >= long_ma.iloc[-(confirm_days + 1)]
                recent_high = close.iloc[-breakout_window:].max() if len(close) >= breakout_window else close.max()
                recent_low = close.iloc[-breakout_window:].min() if len(close) >= breakout_window else close.min()
                current_price = float(close.iloc[-1])
                breakout_up = current_price >= float(recent_high) * 0.99
                breakout_down = current_price <= float(recent_low) * 1.01
                if golden_cross or breakout_up:
                    return 'buy'
                if death_cross or breakout_down:
                    return 'sell'
                return 'hold'

            if strategy_type == 'mean_reversion':
                lookback = int(mr_params.get('lookback', 20))
                entry_z = float(mr_params.get('entry_z', 2.0))
                exit_z = float(mr_params.get('exit_z', 0.5))
                if len(hist_df) < lookback + 2:
                    return 'hold'
                close = hist_df['close_price'].astype(float)
                mean = close.rolling(lookback, min_periods=lookback).mean().iloc[-1]
                std = close.rolling(lookback, min_periods=lookback).std().iloc[-1]
                if std is None or std == 0 or mean is None:
                    return 'hold'
                z = (float(close.iloc[-1]) - float(mean)) / float(std)
                if z <= -entry_z:
                    return 'buy'
                if z >= exit_z:
                    return 'sell'
                return 'hold'

            mapped = hist_df.rename(columns={'close_price': 'close'})
            factors = ml_calc.calculate_all_factors(mapped)
            ml_pred = _make_ml_prediction(hist_df)
            sig = ml_gen.generate_signal(factors, ml_pred)
            # 对 ml_model：返回“目标持仓占比”（0~1），使回测引擎可以做部分调仓。
            # 约定：返回值表示期望市值/总资产比例；引擎内部再按 single_position_limit 二次裁剪。
            total_score = float(sig.get('total_score', 0.5) or 0.5)
            buy_score_th = float(ml_thresholds.get('buy_score', 8.0) or 8.0)
            sell_score_th = float(ml_thresholds.get('sell_score', 3.0) or 3.0)

            if buy_score_th <= sell_score_th:
                score_norm = 1.0 if total_score >= buy_score_th else 0.0
            else:
                score_norm = (total_score - sell_score_th) / (buy_score_th - sell_score_th)
                score_norm = max(0.0, min(1.0, score_norm))

            signal_name = (sig.get('signal') or 'hold')
            if ml_pred is not None:
                buy_prob = float(ml_pred.get('buy_prob', 0.5) or 0.5)
                sell_prob = float(ml_pred.get('sell_prob', 0.5) or 0.5)
                # 用联合概率抑制“频繁打满仓位”：仅当买入概率高且卖出概率低时才提升仓位
                prob_strength = max(0.0, min(1.0, buy_prob * (1.0 - sell_prob)))
            else:
                # 模型概率缺失时仍返回连续仓位，避免回退成 buy/sell 的满仓/清仓二元行为
                conf = float(sig.get('confidence', 0.5) or 0.5)
                conf = max(0.0, min(1.0, conf))
                if signal_name == 'sell':
                    prob_strength = 0.0
                elif signal_name == 'buy':
                    prob_strength = conf
                else:  # hold
                    prob_strength = conf * 0.3

            base_strength = max(0.0, min(1.0, score_norm * prob_strength))
            gamma = 2.2 - (1.7 * risk_preference)  # [2.2, 0.5]
            target_position = base_strength ** gamma

            if _mf_enabled and _index_close_map:
                cur_date = str(hist_df['trade_date'].iloc[-1])
                sorted_dates = sorted(d for d in _index_close_map if d <= cur_date)
                if len(sorted_dates) >= _mf_ma_period:
                    recent_closes = [_index_close_map[d] for d in sorted_dates[-_mf_ma_period:]]
                    idx_ma20 = sum(recent_closes) / _mf_ma_period
                    idx_close = _index_close_map[sorted_dates[-1]]
                    deviation = (idx_close - idx_ma20) / idx_ma20
                    if deviation < _mf_far_pct:
                        target_position *= _mf_far_cap
                    elif deviation < 0:
                        ratio = deviation / _mf_far_pct
                        cap = 1.0 - ratio * (1.0 - _mf_below_cap)
                        target_position *= cap

            if _vp_enabled and len(hist_df) >= 15:
                close_arr = hist_df['close_price'].astype(float).values
                high_arr = hist_df['high_price'].astype(float).values
                low_arr = hist_df['low_price'].astype(float).values
                tr_arr = []
                for k in range(1, min(15, len(close_arr))):
                    tr = max(
                        high_arr[-k] - low_arr[-k],
                        abs(high_arr[-k] - close_arr[-k - 1]),
                        abs(low_arr[-k] - close_arr[-k - 1])
                    )
                    tr_arr.append(tr)
                if tr_arr:
                    atr14 = sum(tr_arr) / len(tr_arr)
                    atr_pct = atr14 / close_arr[-1] if close_arr[-1] > 0 else 0.0
                    if atr_pct >= _vp_high:
                        target_position *= _vp_pen_high
                    elif atr_pct >= _vp_mid:
                        ratio = (atr_pct - _vp_mid) / (_vp_high - _vp_mid)
                        penalty = _vp_pen_mid + ratio * (_vp_pen_high - _vp_pen_mid)
                        target_position *= penalty

            return float(target_position)

        _strategy_single_loss = targets.get('single_loss')
        _strategy_take_profit = targets.get('take_profit')

        try:
            _stop_loss_val = abs(float(_strategy_single_loss)) if _strategy_single_loss not in (None, 0, '') else None
        except Exception:
            _stop_loss_val = None
        try:
            _take_profit_val = abs(float(_strategy_take_profit)) if _strategy_take_profit not in (None, 0, '') else None
        except Exception:
            _take_profit_val = None

        if _hard_single_loss is not None:
            if _stop_loss_val is None:
                _stop_loss_val = _hard_single_loss
            else:
                _stop_loss_val = min(_stop_loss_val, _hard_single_loss)

        _bt_kwargs = dict(
            single_position_limit=single_position_limit,
            commission=commission_rate,
            slippage=slippage_rate,
            stop_loss=_stop_loss_val,
            take_profit=_take_profit_val
        )
        engine = BacktestEngine(_get_db_path())
        engine.initial_capital = initial_capital
        try:
            result = engine.run_strategy_backtest(symbol, start_date, end_date, strategy_func, **_bt_kwargs)
        finally:
            engine.close()

        if not result.get('success'):
            if result.get('message') == '无数据':
                fetched = _ensure_history_data(symbol, start_date, end_date)
                if fetched:
                    engine = BacktestEngine(_get_db_path())
                    engine.initial_capital = initial_capital
                    try:
                        result = engine.run_strategy_backtest(symbol, start_date, end_date, strategy_func, **_bt_kwargs)
                    finally:
                        engine.close()

            if not result.get('success'):
                engine = BacktestEngine(_get_db_path())
                try:
                    rng = _get_symbol_range(engine.conn, symbol)
                finally:
                    engine.close()

                if rng and rng.get('count', 0) > 0:
                    return jsonify({
                        'error': '回测失败',
                        'message': f'该日期区间无数据。本地已有历史范围: {rng.get("min_date")} ~ {rng.get("max_date")}（共{rng.get("count")}条），请调整回测起止日期'
                    }), 400

                return jsonify({'error': '回测失败', 'message': result.get('message', '回测失败')}), 400

        metrics = result.get('metrics', {}) or {}
        payload = {
            'success': True,
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'train_size': result.get('train_size'),
            'val_size': result.get('val_size'),
            'test_size': result.get('test_size'),
            'applied_params': {
                'initial_capital': initial_capital,
                'commission_rate': commission_rate,
                'slippage': slippage_rate,
                'single_position_limit': single_position_limit,
                'risk_preference': risk_preference,
                'actual_model_type': (_runtime_info or {}).get('actual_model_type') or ((cfg_dict.get('ml_model') or {}).get('actual_model_type') or '')
            },
            'trades': result.get('trades', []),
            'price_series': result.get('price_series', []),
            'equity_curve': result.get('equity_curve', [])
        }
        payload.update(metrics)

        return jsonify(payload)
    except Exception as e:
        return jsonify({'error': str(e), 'message': '执行回测失败'}), 500

@backtest_bp.route('/api/backtest/optimize', methods=['POST'])
def optimize_parameters():
    try:
        data = request.json
        symbol = data.get('symbol')
        start_date = _normalize_date(data.get('start_date'))
        end_date = _normalize_date(data.get('end_date'))
        optimization_type = data.get('optimization_type') or data.get('type', 'factor_weights')
        
        if not symbol or not start_date or not end_date:
            return jsonify({'error': '参数错误', 'message': '缺少必要参数'}), 400
        
        symbol = symbol.upper()

        cfg = StrategyConfig()
        cfg_dict = cfg.get_config() or {}
        strategy_type = cfg_dict.get('strategy_type') or 'ml_model'

        engine = BacktestEngine(_get_db_path())
        try:
            optimizer = ParameterOptimizer(engine)
            if strategy_type == 'ml_model':
                if optimization_type == 'factor_weights':
                    result = optimizer.optimize_factor_weights(symbol, start_date, end_date)
                    bp = result.get('best_params') or {}
                    best_cfg = {}
                    if bp:
                        best_cfg = {
                            'factor_weights': {
                                'valuation': float(bp.get('valuation_weight', 0.3)),
                                'trend': float(bp.get('trend_weight', 0.4)),
                                'fund': float(bp.get('fund_weight', 0.3))
                            }
                        }
                elif optimization_type == 'signal_thresholds':
                    result = optimizer.optimize_signal_thresholds(symbol, start_date, end_date)
                    bp = result.get('best_params') or {}
                    best_cfg = {}
                    if bp:
                        best_cfg = {
                            'signal_thresholds': {
                                'buy_score': float(bp.get('buy_score', 8.0)),
                                'sell_score': float(bp.get('sell_score', 3.0)),
                                'buy_prob': float(bp.get('buy_prob', 0.7)),
                                'sell_prob': float(bp.get('sell_prob', 0.7))
                            }
                        }
                elif optimization_type == 'position_rules':
                    result = optimizer.optimize_position_rules(symbol, start_date, end_date)
                    bp = result.get('best_params') or {}
                    best_cfg = {}
                    if bp:
                        best_cfg = {
                            'risk_preference': float(bp.get('risk_preference', 0.8))
                        }
                else:
                    return jsonify({'error': '参数错误', 'message': '不支持的优化类型'}), 400
            elif strategy_type == 'trend_following':
                result = optimizer.optimize_trend_following_params(symbol, start_date, end_date)
                bp = result.get('best_params') or {}
                best_cfg = {'trend_following_params': bp} if bp else {}
            elif strategy_type == 'mean_reversion':
                result = optimizer.optimize_mean_reversion_params(symbol, start_date, end_date)
                bp = result.get('best_params') or {}
                best_cfg = {'mean_reversion_params': bp} if bp else {}
            else:
                return jsonify({'error': '参数错误', 'message': '不支持的策略类型'}), 400

            if best_cfg:
                cfg.update_config(best_cfg)

            return jsonify({
                'success': True,
                'strategy_type': strategy_type,
                'optimization_type': optimization_type,
                'result': result,
                'best_config_patch': best_cfg,
                'applied': bool(best_cfg)
            })
        finally:
            engine.close()
    except Exception as e:
        return jsonify({'error': str(e), 'message': '参数优化失败'}), 500

@backtest_bp.route('/api/backtest/risk', methods=['POST'])
def run_risk_test():
    try:
        data = request.json
        symbol = data.get('symbol')
        start_date = _normalize_date(data.get('start_date'))
        end_date = _normalize_date(data.get('end_date'))
        test_type = data.get('risk_test_type') or data.get('type', 'comprehensive')
        
        if not symbol or not start_date or not end_date:
            return jsonify({'error': '参数错误', 'message': '缺少必要参数'}), 400
        
        symbol = symbol.upper()

        engine = BacktestEngine(_get_db_path())
        try:
            tester = RiskTester(engine)
        
            if test_type == 'stress':
                result = tester.stress_test(symbol, start_date, end_date)
            elif test_type == 'regime':
                result = tester.market_regime_test(symbol, start_date, end_date)
            elif test_type == 'liquidity':
                result = tester.liquidity_test(symbol, start_date, end_date)
            elif test_type == 'comprehensive':
                result = tester.comprehensive_risk_test(symbol, start_date, end_date)
            else:
                return jsonify({'error': '参数错误', 'message': '不支持的测试类型'}), 400
            
            return jsonify(result)
        finally:
            engine.close()
    except Exception as e:
        return jsonify({'error': str(e), 'message': '风险测试失败'}), 500

@backtest_bp.route('/api/backtest/overfitting', methods=['POST'])
def check_overfitting():
    try:
        data = request.json
        symbol = data.get('symbol')
        start_date = _normalize_date(data.get('start_date'))
        end_date = _normalize_date(data.get('end_date'))
        params = data.get('params', {})
        
        if not symbol or not start_date or not end_date:
            return jsonify({'error': '参数错误', 'message': '缺少必要参数'}), 400
        
        symbol = symbol.upper()

        engine = BacktestEngine(_get_db_path())
        try:
            checker = OverfittingChecker(engine)
            result = checker.comprehensive_overfitting_check(symbol, start_date, end_date, params)
            return jsonify(result)
        finally:
            engine.close()
    except Exception as e:
        return jsonify({'error': str(e), 'message': '过拟合检查失败'}), 500
