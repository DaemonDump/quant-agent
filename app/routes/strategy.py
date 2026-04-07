from flask import Blueprint, jsonify, request, current_app
from strategy_config import StrategyConfig
from signal_engine import FactorCalculator, SignalGenerator, SignalFilter, TradeTrigger
from data_ingestion import RealTimeDataCollector
from app.db import get_db, get_setting
from aiagent.model_runtime import load_model_bundle
import pandas as pd
from datetime import datetime, timedelta
import os
import json as _json

strategy_bp = Blueprint('strategy_bp', __name__)

def _load_ml_runtime(cfg_dict):
    ml_cfg = cfg_dict.get('ml_model') or {}
    model_path = (ml_cfg.get('model_path') or '').strip()
    if not model_path:
        return None, None, None, None, {}
    if os.path.isabs(model_path):
        abs_model_path = model_path
    else:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        abs_model_path = os.path.join(root, model_path)
    model, feature_stats, feature_names, runtime_info = load_model_bundle(abs_model_path)
    calibrator = runtime_info.pop('calibrator', None)
    return model, feature_stats, feature_names, calibrator, runtime_info

_FEAT_LOOKBACK = 120
_TRANSACTION_COST = 0.000085
_STAMP_DUTY = 0.001
_SLIPPAGE = 0.001
_LOT_SIZE = 100

def _calc_suggested_trade(symbol: str, final_target_position: float, hist_df) -> dict:
    """
    根据最终目标仓位比例，结合当前持仓与可用资金，
    计算建议买卖数量（与回测引擎规则完全一致：整手100股、含滑点/佣金/印花税）。
    """
    try:
        if 'close_price' in hist_df.columns:
            current_price = float(hist_df['close_price'].iloc[-1])
        else:
            current_price = float(hist_df['close'].iloc[-1])
    except Exception:
        return {'action': 'hold', 'reason': '无法获取当前价格'}

    try:
        db = get_db()
        available_capital = float(get_setting('available_funds', '100000.0') or 100000.0)
        row = db.execute(
            'SELECT quantity, avg_price FROM positions WHERE symbol = ? ORDER BY created_at DESC LIMIT 1',
            (symbol.upper(),)
        ).fetchone()
        current_shares = int(row['quantity']) if row else 0
        avg_cost = float(row['avg_price']) if row else 0.0
    except Exception:
        available_capital = 100000.0
        current_shares = 0
        avg_cost = 0.0

    total_assets = available_capital + current_shares * current_price
    desired_value = total_assets * final_target_position
    desired_shares = int((desired_value / current_price) // _LOT_SIZE) * _LOT_SIZE

    result = {
        'current_price': round(current_price, 4),
        'current_shares': current_shares,
        'available_capital': round(available_capital, 2),
        'total_assets': round(total_assets, 2),
        'final_target_position': round(final_target_position, 4),
        'desired_shares': desired_shares,
    }

    if desired_shares > current_shares:
        buy_shares = desired_shares - current_shares
        actual_buy_price = current_price * (1 + _SLIPPAGE)
        max_affordable = int((available_capital / actual_buy_price) // _LOT_SIZE) * _LOT_SIZE
        buy_shares = min(buy_shares, max_affordable)
        if buy_shares <= 0:
            result.update({'action': 'hold', 'reason': '资金不足或目标仓位变化不足一手'})
        else:
            buy_amount = buy_shares * actual_buy_price
            commission = buy_amount * _TRANSACTION_COST
            total_cost = buy_amount + commission
            result.update({
                'action': 'buy',
                'shares': buy_shares,
                'hands': buy_shares // _LOT_SIZE,
                'exec_price': round(actual_buy_price, 4),
                'amount': round(buy_amount, 2),
                'commission': round(commission, 2),
                'total_cost': round(total_cost, 2),
                'reason': f'目标仓位 {final_target_position:.1%}，建议买入 {buy_shares} 股（{buy_shares // _LOT_SIZE} 手）',
            })
    elif desired_shares < current_shares and current_shares > 0:
        sell_shares = current_shares - desired_shares
        sell_shares = int(sell_shares // _LOT_SIZE) * _LOT_SIZE
        if sell_shares <= 0:
            result.update({'action': 'hold', 'reason': '目标仓位变化不足一手'})
        else:
            actual_sell_price = current_price * (1 - _SLIPPAGE)
            sell_amount = sell_shares * actual_sell_price
            commission = sell_amount * _TRANSACTION_COST
            stamp_duty = sell_amount * _STAMP_DUTY
            total_fee = commission + stamp_duty
            net_proceeds = sell_amount - total_fee
            cost_basis = avg_cost * sell_shares if avg_cost > 0 else 0.0
            profit = net_proceeds - cost_basis
            result.update({
                'action': 'sell',
                'shares': sell_shares,
                'hands': sell_shares // _LOT_SIZE,
                'exec_price': round(actual_sell_price, 4),
                'amount': round(sell_amount, 2),
                'commission': round(commission, 2),
                'stamp_duty': round(stamp_duty, 2),
                'total_cost': round(total_fee, 2),
                'total_fee': round(total_fee, 2),
                'net_proceeds': round(net_proceeds, 2),
                'estimated_profit': round(profit, 2),
                'reason': f'目标仓位 {final_target_position:.1%}，建议卖出 {sell_shares} 股（{sell_shares // _LOT_SIZE} 手）',
            })
    else:
        result.update({'action': 'hold', 'reason': f'当前持仓已符合目标仓位 {final_target_position:.1%}'})

    return result

def _make_ml_prediction(hist_df, model, feature_stats, feature_names, calibrator=None):
    if model is None or not feature_names:
        return None
    try:
        from aiagent.ml_features import compute_features
        from aiagent.ml_pipeline import _apply_stats
        tail_df = hist_df.iloc[-_FEAT_LOOKBACK:] if len(hist_df) > _FEAT_LOOKBACK else hist_df
        df_feat = compute_features(tail_df, feature_names)
        if df_feat is None or df_feat.empty:
            return None
        missing = [c for c in feature_names if c not in df_feat.columns]
        if missing:
            return None
        X = df_feat[feature_names].iloc[[-1]]
        X_arr = _apply_stats(X, feature_stats) if feature_stats else X.values
        if calibrator is not None:
            try:
                proba = calibrator.predict_proba(X_arr)[0]
            except Exception:
                proba = model.predict_proba(X_arr)[0]
        else:
            proba = model.predict_proba(X_arr)[0]
        sell_prob = float(proba[0])
        buy_prob = float(proba[1])
        neutral_prob = float(proba[2]) if len(proba) > 2 else max(0.0, 1.0 - buy_prob - sell_prob)
        return {'buy_prob': buy_prob, 'sell_prob': sell_prob, 'neutral_prob': neutral_prob}
    except Exception:
        return None

def _derive_ml_target_position(sig, ml_pred, signal_thresholds, risk_preference,
                               hist_df=None, cfg_dict=None):
    total_score = float(sig.get('total_score', 0.5) or 0.5)
    buy_score_th = float(signal_thresholds.get('buy_score', 8.0) or 8.0)
    sell_score_th = float(signal_thresholds.get('sell_score', 3.0) or 3.0)
    if buy_score_th <= sell_score_th:
        score_norm = 1.0 if total_score >= buy_score_th else 0.0
    else:
        score_norm = (total_score - sell_score_th) / (buy_score_th - sell_score_th)
        score_norm = max(0.0, min(1.0, score_norm))
    signal_name = sig.get('signal') or 'hold'
    if ml_pred is not None:
        buy_prob = float(ml_pred.get('buy_prob', 0.5) or 0.5)
        sell_prob = float(ml_pred.get('sell_prob', 0.5) or 0.5)
        neutral_prob = float(ml_pred.get('neutral_prob', 0.0) or 0.0)
        raw_strength = buy_prob - sell_prob
        neutral_suppression = max(0.0, 1.0 - neutral_prob * 1.5)
        prob_strength = max(0.0, min(1.0, raw_strength * neutral_suppression))
    else:
        conf = float(sig.get('confidence', 0.5) or 0.5)
        conf = max(0.0, min(1.0, conf))
        if signal_name == 'sell':
            prob_strength = 0.0
        elif signal_name == 'buy':
            prob_strength = conf
        else:
            prob_strength = conf * 0.3
    base_strength = max(0.0, min(1.0, score_norm * prob_strength))
    gamma = 2.2 - (1.7 * risk_preference)
    target_position = float(base_strength ** gamma)

    _cfg = cfg_dict or {}
    mf_cfg = _cfg.get('market_filter') or {}
    vp_cfg = _cfg.get('volatility_penalty') or {}

    _mf_enabled = bool(mf_cfg.get('enabled', True))
    _mf_ma_period = int(mf_cfg.get('ma_period', 20))
    _mf_below_cap = float(mf_cfg.get('below_ma_cap', 0.5))
    _mf_far_cap = float(mf_cfg.get('far_below_ma_cap', 0.2))
    _mf_far_pct = float(mf_cfg.get('far_below_pct', -0.05))
    _vp_enabled = bool(vp_cfg.get('enabled', True))
    _vp_mid = float(vp_cfg.get('atr_threshold_mid', 0.025))
    _vp_high = float(vp_cfg.get('atr_threshold_high', 0.035))
    _vp_pen_mid = float(vp_cfg.get('penalty_mid', 0.7))
    _vp_pen_high = float(vp_cfg.get('penalty_high', 0.4))

    if _mf_enabled and hist_df is not None and len(hist_df) >= _mf_ma_period:
        try:
            from app.db import get_db, get_setting
            import tushare as ts
            token = get_setting('tushare_token')
            if token:
                _mf_index = str(mf_cfg.get('index_code', '000300.SH'))
                cur_date = str(hist_df['trade_date'].iloc[-1])
                _pro = ts.pro_api(token)
                _extra_start = str(int(cur_date) - 300)
                _idx_df = _pro.index_daily(ts_code=_mf_index, start_date=_extra_start, end_date=cur_date)
                if _idx_df is not None and not _idx_df.empty:
                    _idx_df = _idx_df.sort_values('trade_date')
                    _index_close_map = dict(zip(
                        _idx_df['trade_date'].astype(str).tolist(),
                        _idx_df['close'].astype(float).tolist()
                    ))
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
        except Exception:
            pass

    if _vp_enabled and hist_df is not None and len(hist_df) >= 15:
        try:
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
        except Exception:
            pass

    return float(target_position)

@strategy_bp.route('/api/strategy/config', methods=['GET', 'POST'])
def handle_strategy_config():
    try:
        config = StrategyConfig()
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'config': config.get_config()
            })
        elif request.method == 'POST':
            data = request.json
            updates = data.get('updates', {})
            if not updates:
                return jsonify({'error': '参数错误', 'message': '缺少更新参数'}), 400
            
            success = config.update_config(updates)
            if success:
                return jsonify({
                    'success': True,
                    'message': '策略配置更新成功',
                    'config': config.get_config()
                })
            else:
                return jsonify({'error': '更新失败', 'message': '策略配置更新失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e), 'message': '处理策略配置请求失败'}), 500

@strategy_bp.route('/api/strategy/params', methods=['GET', 'POST'])
def handle_strategy_params():
    try:
        config = StrategyConfig()
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'params': {
                    'strategy_type': config.get_strategy_type(),
                    'risk_preference': config.get_risk_preference(),
                    'factor_weights': config.get_factor_weights(),
                    'signal_thresholds': config.get_signal_thresholds(),
                    'position_limits': config.get_position_limits(),
                    'targets': config.get_targets(),
                    'scope': config.get_scope()
                }
            })
        elif request.method == 'POST':
            data = request.json
            param_type = data.get('param_type')
            param_value = data.get('param_value')
            
            if not param_type or param_value is None:
                return jsonify({'error': '参数错误', 'message': '缺少参数类型或值'}), 400
            
            valid_types = ['strategy_type', 'risk_preference', 'factor_weights', 'signal_thresholds', 'position_limits', 'targets', 'scope']
            if param_type not in valid_types:
                return jsonify({'error': '参数错误', 'message': f'无效的参数类型，必须是: {", ".join(valid_types)}'}), 400
            
            success = config.update_config({param_type: param_value})
            if success:
                return jsonify({
                    'success': True,
                    'message': f'{param_type}更新成功',
                    'params': {
                        'strategy_type': config.get_strategy_type(),
                        'risk_preference': config.get_risk_preference(),
                        'factor_weights': config.get_factor_weights(),
                        'signal_thresholds': config.get_signal_thresholds(),
                        'position_limits': config.get_position_limits(),
                        'targets': config.get_targets(),
                        'scope': config.get_scope()
                    }
                })
            else:
                return jsonify({'error': '更新失败', 'message': '策略参数更新失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e), 'message': '更新策略参数失败'}), 500

@strategy_bp.route('/api/strategy/validate', methods=['GET'])
def validate_strategy_config():
    try:
        config = StrategyConfig()
        validation_result = config.validate_config()
        return jsonify({
            'success': True,
            'validation': validation_result
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '验证策略配置失败'}), 500

@strategy_bp.route('/api/strategy/reset', methods=['POST'])
def reset_strategy_config():
    try:
        config = StrategyConfig()
        config.reset_to_default()
        return jsonify({
            'success': True,
            'message': '策略配置已重置为默认值',
            'config': config.get_config()
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '重置策略配置失败'}), 500

def get_stock_data(symbol, limit=1000):
    """获取股票数据，如果数据库没有则从 Tushare 抓取"""
    symbol = symbol.upper()
    db = get_db()
    query = '''
        SELECT trade_date,
               open_price, high_price, low_price, close_price,
               open_price as open, high_price as high, low_price as low, close_price as close,
               volume, amount, pe, pb, turnover_rate, total_mv, buy_lg_amount, net_mf_amount, net_amount_rate
        FROM stock_history_data
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT ?
    '''
    df = pd.read_sql_query(query, db, params=(symbol, limit))
    
    if len(df) < 20:
        token = get_setting('tushare_token')
        if not token:
            return pd.DataFrame()
            
        collector = RealTimeDataCollector(current_app.config['DATABASE'])
        collector.set_token(token)
        
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y%m%d')
        
        df_new = collector.collect_history_data(symbol, start_date, end_date)
        if df_new is not None and not df_new.empty:
            df = pd.read_sql_query(query, db, params=(symbol, limit))
            
    return df


def get_stock_data_range(symbol, start_date=None, end_date=None, lookback_extra=120):
    """按日期范围获取股票数据，并在 start_date 前额外补充 lookback_extra 条用于因子计算"""
    symbol = symbol.upper()
    db = get_db()

    def _norm(d):
        if not d:
            return None
        return d.replace('-', '')

    start_str = _norm(start_date)
    end_str = _norm(end_date) or datetime.now().strftime('%Y%m%d')

    if start_str:
        query_main = '''
            SELECT trade_date,
                   open_price, high_price, low_price, close_price,
                   open_price as open, high_price as high, low_price as low, close_price as close,
                   volume, amount, pe, pb, turnover_rate, total_mv, buy_lg_amount, net_mf_amount, net_amount_rate
            FROM stock_history_data
            WHERE symbol = ? AND trade_date >= ? AND trade_date <= ?
            ORDER BY trade_date ASC
        '''
        query_pre = '''
            SELECT trade_date,
                   open_price, high_price, low_price, close_price,
                   open_price as open, high_price as high, low_price as low, close_price as close,
                   volume, amount, pe, pb, turnover_rate, total_mv, buy_lg_amount, net_mf_amount, net_amount_rate
            FROM stock_history_data
            WHERE symbol = ? AND trade_date < ?
            ORDER BY trade_date DESC
            LIMIT ?
        '''
        df_main = pd.read_sql_query(query_main, db, params=(symbol, start_str, end_str))
        df_pre = pd.read_sql_query(query_pre, db, params=(symbol, start_str, int(lookback_extra)))
        if not df_pre.empty:
            df_pre = df_pre.sort_values('trade_date', ascending=True)
        df = pd.concat([df_pre, df_main], ignore_index=True) if not df_pre.empty else df_main
        eval_dates = df_main['trade_date'].astype(str).tolist() if not df_main.empty else []
    else:
        query_all = '''
            SELECT trade_date,
                   open_price, high_price, low_price, close_price,
                   open_price as open, high_price as high, low_price as low, close_price as close,
                   volume, amount, pe, pb, turnover_rate, total_mv, buy_lg_amount, net_mf_amount, net_amount_rate
            FROM stock_history_data
            WHERE symbol = ? AND trade_date <= ?
            ORDER BY trade_date ASC
        '''
        df = pd.read_sql_query(query_all, db, params=(symbol, end_str))
        eval_dates = df['trade_date'].astype(str).tolist() if not df.empty else []

    if df.empty or len(df) < 20:
        token = get_setting('tushare_token')
        if token:
            collector = RealTimeDataCollector(current_app.config['DATABASE'])
            collector.set_token(token)
            fetch_end = end_str
            fetch_start = (datetime.now() - timedelta(days=365 * 5)).strftime('%Y%m%d')
            df_new = collector.collect_history_data(symbol, fetch_start, fetch_end)
            if df_new is not None and not df_new.empty:
                if start_str:
                    df_main = pd.read_sql_query(query_main, db, params=(symbol, start_str, end_str))
                    df_pre = pd.read_sql_query(query_pre, db, params=(symbol, start_str, int(lookback_extra)))
                    if not df_pre.empty:
                        df_pre = df_pre.sort_values('trade_date', ascending=True)
                    df = pd.concat([df_pre, df_main], ignore_index=True) if not df_pre.empty else df_main
                    eval_dates = df_main['trade_date'].astype(str).tolist() if not df_main.empty else []
                else:
                    df = pd.read_sql_query(query_all, db, params=(symbol, end_str))
                    eval_dates = df['trade_date'].astype(str).tolist() if not df.empty else []

    if df.empty:
        return df, []

    df['trade_date'] = df['trade_date'].astype(str)
    df = df.sort_values('trade_date').reset_index(drop=True)

    return df, eval_dates

@strategy_bp.route('/api/factor/calculate', methods=['POST'])
def calculate_factors():
    try:
        data = request.json
        symbol = data.get('symbol')
        if not symbol:
            return jsonify({'error': '参数错误', 'message': '缺少股票代码'}), 400
        
        df = get_stock_data(symbol)

        if df.empty:
            return jsonify({'error': '数据不足', 'message': '该股票无历史数据，请检查Token或代码是否正确'}), 400
        
        # 计算因子需要按日期升序
        df = df.sort_values('trade_date', ascending=True)
        
        config = StrategyConfig()
        factor_weights = config.get_factor_weights()
        
        calculator = FactorCalculator(factor_weights)
        factors = calculator.calculate_all_factors(df)
        
        if factors is None:
            return jsonify({'error': '计算失败', 'message': '因子计算逻辑返回空值，请检查数据完整性'}), 500
            
        return jsonify({
            'success': True,
            'symbol': symbol,
            'factors': factors
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '因子计算失败'}), 500

@strategy_bp.route('/api/signal/generate', methods=['POST'])
def generate_signal():
    try:
        data = request.json
        symbol = data.get('symbol')
        if not symbol:
            return jsonify({'error': '参数错误', 'message': '缺少股票代码'}), 400

        df = get_stock_data(symbol)

        if df.empty:
            return jsonify({'error': '数据不足', 'message': '该股票无历史数据'}), 400
        
        df = df.sort_values('trade_date', ascending=True)
        
        config = StrategyConfig()
        cfg_dict = config.get_config() or {}
        factor_weights = config.get_factor_weights()
        signal_thresholds = config.get_signal_thresholds()
        risk_preference = data.get('risk_preference', config.get_risk_preference())
        try:
            risk_preference = max(0.0, min(1.0, float(risk_preference)))
        except Exception:
            risk_preference = 0.5
        
        calculator = FactorCalculator(factor_weights)
        factors = calculator.calculate_all_factors(df)
        
        if factors is None:
            return jsonify({'error': '因子计算失败', 'message': '无法计算因子'}), 500
        
        generator = SignalGenerator(signal_thresholds)
        ml_pred = None
        runtime_info = {}
        if cfg_dict.get('strategy_type') == 'ml_model':
            model, feature_stats, feature_names, calibrator, runtime_info = _load_ml_runtime(cfg_dict)
            ml_pred = _make_ml_prediction(df, model, feature_stats, feature_names, calibrator)
        signal = generator.generate_signal(factors, ml_pred)
        if ml_pred is not None:
            signal['ml_buy_prob'] = float(ml_pred.get('buy_prob', 0.5) or 0.5)
            signal['ml_sell_prob'] = float(ml_pred.get('sell_prob', 0.5) or 0.5)
            signal['ml_neutral_prob'] = float(ml_pred.get('neutral_prob', 0.0) or 0.0)
        if cfg_dict.get('strategy_type') == 'ml_model':
            signal['target_position'] = _derive_ml_target_position(
                signal, ml_pred, signal_thresholds, risk_preference,
                hist_df=df, cfg_dict=cfg_dict
            )
            signal['actual_model_type'] = (runtime_info or {}).get('actual_model_type') or ((cfg_dict.get('ml_model') or {}).get('actual_model_type') or '')
        signal['risk_preference'] = risk_preference
        signal['data_count'] = len(df)

        position_limits = cfg_dict.get('position_limits') or {}
        single_position_limit = float(position_limits.get('single_max') or 0.2)
        target_pos = float(signal.get('target_position') or 0.0)
        final_target_position = min(target_pos, single_position_limit)
        signal['final_target_position'] = final_target_position

        suggested_trade = _calc_suggested_trade(symbol, final_target_position, df)
        signal['suggested_trade'] = suggested_trade

        return jsonify({
            'success': True,
            'symbol': symbol,
            'signal': signal
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '信号生成失败'}), 500

@strategy_bp.route('/api/signal/filter', methods=['POST'])
def filter_signal():
    try:
        data = request.json
        signal = data.get('signal')
        if not signal:
            return jsonify({'error': '参数错误', 'message': '缺少信号数据'}), 400
            
        signal_filter = SignalFilter()
        result = signal_filter.filter_signal(signal)
        
        # 为了前端兼容
        result['passed'] = not result['filtered']
        
        return jsonify({
            'success': True,
            'filtered': result
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '信号过滤失败'}), 500

@strategy_bp.route('/api/trade/check/buy', methods=['POST'])
def check_buy_trigger():
    try:
        data = request.json
        signal = data.get('signal')
        current_price = data.get('current_price', 0)
        available_capital = data.get('available_capital', None)
        
        if not signal:
            return jsonify({'error': '参数错误', 'message': '缺少信号数据'}), 400
            
        config = StrategyConfig()
        position_limits = config.get_position_limits()
        targets = config.get_targets()
        cfg_dict = config.get_config() or {}
        risk_preference = data.get('risk_preference', cfg_dict.get('risk_preference', 0.5))
        try:
            risk_preference = max(0.0, min(1.0, float(risk_preference)))
        except Exception:
            risk_preference = 0.5
        trigger = TradeTrigger(position_limits=position_limits, targets=targets, risk_preference=risk_preference)

        db = get_db()
        rows = db.execute('SELECT * FROM positions ORDER BY created_at DESC').fetchall()
        current_positions = [dict(r) for r in rows] if rows else []

        if available_capital is None:
            available_capital = float(get_setting('available_funds', '100000.0') or 100000.0)
        else:
            available_capital = float(available_capital or 0)

        result = trigger.check_buy_trigger(signal, current_positions, current_price, available_capital)
        
        # 为了前端兼容
        result['can_trigger'] = result['triggered']
        result['quantity'] = result.get('suggested_quantity', 0)
        result['risk_preference'] = risk_preference
        
        return jsonify({
            'success': True,
            'trigger': result
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '买入触发检查失败'}), 500

@strategy_bp.route('/api/trade/check/sell', methods=['POST'])
def check_sell_trigger():
    try:
        data = request.json
        signal = data.get('signal')
        symbol = data.get('symbol')
        current_price = data.get('current_price', 0)
        
        if not signal or not symbol:
            return jsonify({'error': '参数错误', 'message': '缺少信号或股票代码'}), 400
            
        config = StrategyConfig()
        position_limits = config.get_position_limits()
        targets = config.get_targets()
        cfg_dict = config.get_config() or {}
        risk_preference = data.get('risk_preference', cfg_dict.get('risk_preference', 0.5))
        try:
            risk_preference = max(0.0, min(1.0, float(risk_preference)))
        except Exception:
            risk_preference = 0.5
        trigger = TradeTrigger(position_limits=position_limits, targets=targets, risk_preference=risk_preference)

        db = get_db()
        row = db.execute('SELECT * FROM positions WHERE symbol = ? ORDER BY created_at DESC LIMIT 1', (symbol,)).fetchone()
        position = dict(row) if row else {'symbol': symbol, 'quantity': 0, 'avg_price': 0}
        result = trigger.check_sell_trigger(signal, position, current_price)
        
        # 为了前端兼容
        result['can_trigger'] = result['triggered']
        result['quantity'] = result.get('suggested_quantity', 0)
        result['risk_preference'] = risk_preference
        
        return jsonify({
            'success': True,
            'trigger': result
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '卖出触发检查失败'}), 500


@strategy_bp.route('/api/signal/history', methods=['POST'])
def signal_history():
    try:
        data = request.json
        symbol = data.get('symbol')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if not symbol:
            return jsonify({'error': '参数错误', 'message': '缺少股票代码'}), 400
        if not start_date:
            return jsonify({'error': '参数错误', 'message': '缺少起始日期'}), 400

        config = StrategyConfig()
        cfg_dict = config.get_config() or {}
        factor_weights = config.get_factor_weights()
        signal_thresholds = config.get_signal_thresholds()
        position_limits = cfg_dict.get('position_limits') or {}
        single_position_limit = float(position_limits.get('single_max') or 0.2)

        risk_preference = data.get('risk_preference', config.get_risk_preference())
        try:
            risk_preference = max(0.0, min(1.0, float(risk_preference)))
        except Exception:
            risk_preference = 0.5

        df, eval_dates = get_stock_data_range(symbol, start_date=start_date, end_date=end_date)
        if df.empty or not eval_dates:
            return jsonify({'error': '数据不足', 'message': '该股票在指定日期范围内无数据'}), 400

        model, feature_stats, feature_names, calibrator, runtime_info = None, None, None, None, {}
        if cfg_dict.get('strategy_type') == 'ml_model':
            model, feature_stats, feature_names, calibrator, runtime_info = _load_ml_runtime(cfg_dict)

        calculator = FactorCalculator(factor_weights)
        generator = SignalGenerator(signal_thresholds)

        results = []
        df_sorted = df.sort_values('trade_date').reset_index(drop=True)
        date_to_idx = {d: i for i, d in enumerate(df_sorted['trade_date'].astype(str).tolist())}
        lookback_window = 200

        for trade_date in eval_dates:
            row_idx = date_to_idx.get(str(trade_date))
            if row_idx is None:
                continue
            if row_idx < 1:
                continue

            slice_start = max(0, row_idx - lookback_window)
            df_slice = df_sorted.iloc[slice_start:row_idx + 1]

            factors = calculator.calculate_all_factors(df_slice)
            if factors is None:
                continue

            ml_pred = None
            if model is not None:
                ml_pred = _make_ml_prediction(df_slice, model, feature_stats, feature_names, calibrator)

            signal = generator.generate_signal(factors, ml_pred)

            if ml_pred is not None:
                signal['ml_buy_prob'] = round(float(ml_pred.get('buy_prob', 0.5) or 0.5), 4)
                signal['ml_sell_prob'] = round(float(ml_pred.get('sell_prob', 0.5) or 0.5), 4)
                signal['ml_neutral_prob'] = round(float(ml_pred.get('neutral_prob', 0.0) or 0.0), 4)

            if cfg_dict.get('strategy_type') == 'ml_model':
                signal['target_position'] = _derive_ml_target_position(
                    signal, ml_pred, signal_thresholds, risk_preference,
                    hist_df=df_slice, cfg_dict=cfg_dict
                )

            target_pos = float(signal.get('target_position') or 0.0)
            final_target_position = min(target_pos, single_position_limit)
            signal['final_target_position'] = round(final_target_position, 4)

            row = df_sorted.iloc[row_idx]
            if row_idx + 1 < len(df_sorted):
                next_row = df_sorted.iloc[row_idx + 1]
                next_open = round(float(next_row['open']), 4)
                next_close = round(float(next_row['close']), 4)
            else:
                next_open = None
                next_close = None

            results.append({
                'date': trade_date,
                'close': round(float(row['close']), 4),
                'signal': signal.get('signal'),
                'total_score': round(float(signal.get('total_score') or 0), 4),
                'confidence': round(float(signal.get('confidence') or 0), 4),
                'ml_buy_prob': signal.get('ml_buy_prob'),
                'ml_sell_prob': signal.get('ml_sell_prob'),
                'final_target_position': signal.get('final_target_position'),
                'reason': signal.get('reason', ''),
                'next_open': next_open,
                'next_close': next_close,
            })

        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'start_date': start_date,
            'end_date': end_date or datetime.now().strftime('%Y-%m-%d'),
            'risk_preference': risk_preference,
            'count': len(results),
            'rows': results,
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '历史信号分析失败'}), 500
