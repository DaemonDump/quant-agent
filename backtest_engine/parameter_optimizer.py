import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Callable, Any
import logging
from itertools import product
import random

logger = logging.getLogger(__name__)


class ParameterOptimizer:
    def __init__(self, backtest_engine):
        self.backtest_engine = backtest_engine
        self._cached_ml_model = None
        self._cached_feature_stats = None
        self._cached_feature_names = []
        self._model_loaded = False

    def _ensure_model_loaded(self):
        if self._model_loaded:
            return
        self._model_loaded = True
        import os
        from strategy_config import StrategyConfig
        from aiagent.model_runtime import load_model_bundle
        _cfg = StrategyConfig().get_config() or {}
        _ml_cfg = _cfg.get('ml_model') or {}
        _model_path = _ml_cfg.get('model_path') or ''
        if _model_path:
            try:
                _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                _abs = os.path.join(_root, _model_path) if not os.path.isabs(_model_path) else _model_path
                self._cached_ml_model, self._cached_feature_stats, self._cached_feature_names, _ = load_model_bundle(_abs)
                try:
                    self._cached_ml_model.set_params(device='cuda', tree_method='hist')
                    logger.info("XGBoost 已切换到 GPU (cuda)")
                except Exception:
                    pass
                logger.info(f"ML模型已加载: {_abs}")
            except Exception as e:
                logger.warning(f"ML模型加载失败: {e}")
                self._cached_ml_model = None

    def _precompute_ml_proba(self, symbol: str, start_date: str, end_date: str,
                              max_test_rows: int = 300) -> Dict:
        """
        预先批量计算所有测试行的 ML 概率（一次 GPU 推理），
        返回 {row_idx: (buy_prob, sell_prob)} 的字典，供网格搜索复用。
        同时返回 full_df / warmup_len / test_df 供因子计算使用。
        """
        import os
        from aiagent.ml_features import compute_features
        from aiagent.ml_pipeline import _apply_stats

        self._ensure_model_loaded()

        df = self.backtest_engine.load_data(symbol, start_date, end_date)
        if df.empty:
            return {'success': False, 'message': '无数据'}

        train_df, val_df, test_df = self.backtest_engine.split_data(df)
        if len(test_df) == 0:
            return {'success': False, 'message': '测试集为空'}

        if max_test_rows and len(test_df) > max_test_rows:
            test_df = test_df.iloc[-max_test_rows:].copy()

        warmup_df = train_df.copy()
        warmup_len = len(warmup_df)
        full_df = pd.concat([warmup_df, test_df], ignore_index=True)

        proba_map = {}
        _FEAT_LOOKBACK = 120

        if self._cached_ml_model is not None and self._cached_feature_names:
            feat_rows = []
            valid_indices = []
            for i in range(len(test_df)):
                hist_slice = full_df.iloc[: warmup_len + i + 1]
                tail_df = hist_slice.iloc[-_FEAT_LOOKBACK:]
                try:
                    feat_df = compute_features(tail_df, self._cached_feature_names)
                    if feat_df is not None and not feat_df.empty:
                        row_feat = feat_df[self._cached_feature_names].iloc[-1].values
                        feat_rows.append(row_feat)
                        valid_indices.append(i)
                except Exception:
                    pass

            if feat_rows:
                X_all = np.array(feat_rows, dtype=np.float32)
                if self._cached_feature_stats:
                    import pandas as _pd
                    X_df = _pd.DataFrame(X_all, columns=self._cached_feature_names)
                    X_all = _apply_stats(X_df, self._cached_feature_stats)
                try:
                    all_proba = self._cached_ml_model.predict_proba(X_all)
                    for idx, proba in zip(valid_indices, all_proba):
                        proba_map[idx] = (float(proba[1]), float(proba[0]))
                except Exception as e:
                    logger.warning(f"批量GPU推理失败: {e}")

        return {
            'success': True,
            'full_df': full_df,
            'warmup_len': warmup_len,
            'test_df': test_df,
            'proba_map': proba_map,
        }

    def _precompute_factor_scores(self, full_df: pd.DataFrame, warmup_len: int,
                                   test_df: pd.DataFrame) -> List[Dict]:
        """
        预计算所有测试行的原始因子分量（valuation/trend/fund score），
        不含权重加权，供网格搜索时快速重算 total_score。
        返回列表，每个元素对应一个测试行：
        {'v': valuation_score, 't': trend_score, 'f': fund_score}
        """
        from signal_engine import FactorCalculator
        _dummy_calc = FactorCalculator({'valuation': 1.0, 'trend': 0.0, 'fund': 0.0})
        factor_rows = []
        for i in range(len(test_df)):
            hist_slice = full_df.iloc[: warmup_len + i + 1]
            mapped = hist_slice.rename(columns={'close_price': 'close'})
            try:
                factors = _dummy_calc.calculate_all_factors(mapped)
                if factors:
                    factor_rows.append({
                        'v': float(factors.get('valuation_score', 0.5)),
                        't': float(factors.get('trend_score', 0.5)),
                        'f': float(factors.get('fund_score', 0.5)),
                    })
                else:
                    factor_rows.append({'v': 0.5, 't': 0.5, 'f': 0.5})
            except Exception:
                factor_rows.append({'v': 0.5, 't': 0.5, 'f': 0.5})
        return factor_rows

    def _run_fast_backtest(self, test_df: pd.DataFrame,
                           factor_rows: List[Dict],
                           proba_map: Dict[int, tuple],
                           factor_weights: Dict,
                           signal_thresholds: Dict,
                           risk_preference: float = 0.8) -> Dict:
        """
        轻量级回测：直接使用预计算的因子分量和ML概率，
        不再调用 FactorCalculator / ML推理，速度极快。
        """
        vw = float(factor_weights.get('valuation', 0.33))
        tw = float(factor_weights.get('trend', 0.33))
        fw = float(factor_weights.get('fund', 0.34))
        total_w = vw + tw + fw
        if total_w <= 0:
            total_w = 1.0
        vw /= total_w
        tw /= total_w
        fw /= total_w

        buy_score_th = float(signal_thresholds.get('buy_score', 6.5))
        sell_score_th = float(signal_thresholds.get('sell_score', 5.5))
        buy_prob_th = float(signal_thresholds.get('buy_prob', 0.65))
        sell_prob_th = float(signal_thresholds.get('sell_prob', 0.65))
        gamma = 2.2 - (1.7 * risk_preference)

        score_range = buy_score_th - sell_score_th

        transaction_cost = self.backtest_engine.transaction_cost
        stamp_duty = self.backtest_engine.stamp_duty
        initial_capital = self.backtest_engine.initial_capital
        single_position_limit = 0.2
        slippage = 0.001
        lot_size = 100

        capital = float(initial_capital)
        position = 0
        cost_basis_total = 0.0
        equity_curve = []
        trades = []

        prices = test_df['close_price'].values.astype(float)
        dates = test_df['trade_date'].values

        for i in range(len(test_df)):
            price = prices[i]
            fr = factor_rows[i] if i < len(factor_rows) else {'v': 0.5, 't': 0.5, 'f': 0.5}
            raw_score = (fr['v'] * vw + fr['t'] * tw + fr['f'] * fw) * 10.0
            raw_score = max(0.0, min(10.0, raw_score))

            buy_prob, sell_prob = 0.5, 0.5
            if i in proba_map:
                buy_prob, sell_prob = proba_map[i]

            if score_range <= 0:
                score_norm = 1.0 if raw_score >= buy_score_th else 0.0
            else:
                score_norm = (raw_score - sell_score_th) / score_range
                score_norm = max(0.0, min(1.0, score_norm))

            prob_strength = buy_prob * (1.0 - sell_prob)
            base_strength = max(0.0, min(1.0, score_norm * prob_strength))
            signal_val = float(base_strength ** gamma)

            total_assets = capital + position * price
            current_fraction = (position * price) / total_assets if total_assets > 0 else 0.0
            desired_fraction = max(0.0, min(single_position_limit, signal_val))

            desired_value = total_assets * desired_fraction
            desired_shares = int((desired_value / price) // lot_size) * lot_size
            desired_shares = max(0, desired_shares)

            if desired_shares > position:
                actual_buy_price = price * (1 + slippage)
                buy_shares = desired_shares - position
                max_affordable = int((capital / actual_buy_price) // lot_size) * lot_size
                buy_shares = int(min(buy_shares, max_affordable))
                if buy_shares > 0:
                    buy_amount = float(buy_shares) * actual_buy_price
                    buy_cost = buy_amount * transaction_cost
                    buy_total = buy_amount + buy_cost
                    if buy_total <= capital:
                        capital -= buy_total
                        position += buy_shares
                        cost_basis_total += buy_total
                        trades.append({'date': dates[i], 'action': 'buy', 'price': price,
                                       'shares': buy_shares, 'amount': buy_amount, 'cost': buy_cost})
            elif desired_shares < position and position > 0:
                sell_shares = position - desired_shares
                if sell_shares > 0:
                    actual_sell_price = price * (1 - slippage)
                    sell_amount = float(sell_shares) * actual_sell_price
                    sell_cost = sell_amount * (transaction_cost + stamp_duty)
                    sell_total = sell_amount - sell_cost
                    proportion = sell_shares / position
                    cost_basis_reduce = cost_basis_total * proportion
                    profit = sell_total - cost_basis_reduce
                    capital += sell_total
                    position -= sell_shares
                    cost_basis_total -= cost_basis_reduce
                    if position <= 0:
                        position = 0
                        cost_basis_total = 0.0
                    trades.append({'date': dates[i], 'action': 'sell', 'price': price,
                                   'shares': sell_shares, 'amount': sell_amount,
                                   'cost': sell_cost, 'profit': profit})

            equity_curve.append(capital + position * price)

        if len(equity_curve) < 2:
            return {'success': False, 'message': '数据不足'}

        equity_arr = np.array(equity_curve, dtype=np.float64)
        returns = np.diff(equity_arr) / equity_arr[:-1]
        returns = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)
        metrics = self.backtest_engine.calculate_metrics(pd.Series(returns))
        return {'success': True, 'metrics': metrics, 'trades': trades}

    def grid_search(self, evaluate_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
                   param_grid: Dict[str, List[Any]],
                   metric: str = 'sharpe_ratio',
                   top_k: int = 20) -> Dict[str, any]:
        """网格搜索优化参数"""
        logger.info("开始网格搜索参数优化")
        
        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        all_combinations = list(product(*param_values))
        
        logger.info(f"总共需要测试 {len(all_combinations)} 种参数组合")
        
        best_result = None
        best_score = -np.inf
        all_results = []
        
        for i, combination in enumerate(all_combinations):
            # 构建参数字典
            params = dict(zip(param_names, combination))
            
            result = evaluate_fn(params)
            if result.get('success') and 'metrics' in result and result['metrics']:
                score = float(result['metrics'].get(metric, -np.inf))
                
                # 记录结果
                all_results.append({
                    'params': params,
                    'score': score,
                    'metrics': result['metrics']
                })
                
                # 更新最佳结果
                if score > best_score:
                    best_score = score
                    best_result = {
                        'params': params,
                        'score': score,
                        'metrics': result['metrics']
                    }
            
            # 进度提示
            if (i + 1) % 10 == 0:
                logger.info(f"已完成 {i + 1}/{len(all_combinations)} 个参数组合")
        
        logger.info(f"网格搜索完成，最佳{metric}: {best_score:.4f}")
        all_results_sorted = sorted(all_results, key=lambda x: x.get('score', -np.inf), reverse=True)
        
        return {
            'best_params': best_result['params'] if best_result else {},
            'best_score': best_score,
            'best_metrics': best_result['metrics'] if best_result else {},
            'top_results': all_results_sorted[:max(1, int(top_k))]
        }
    
    def genetic_algorithm(self, evaluate_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
                       param_ranges: Dict[str, Tuple[float, float]],
                       population_size: int = 20,
                       generations: int = 50,
                       mutation_rate: float = 0.1,
                       metric: str = 'sharpe_ratio') -> Dict[str, any]:
        """遗传算法优化参数"""
        logger.info("开始遗传算法参数优化")
        
        population = self._init_population(param_ranges, population_size)
        
        best_result = None
        best_score = -np.inf
        best_history = []
        
        for generation in range(generations):
            fitness_scores = []
            for individual in population:
                params = self._decode_individual(individual, param_ranges)
                
                result = evaluate_fn(params)
                
                if result.get('success') and 'metrics' in result:
                    score = result['metrics'].get(metric, -np.inf)
                    fitness_scores.append(score)
                    
                    if score > best_score:
                        best_score = score
                        best_result = {
                            'params': params,
                            'score': score,
                            'metrics': result['metrics']
                        }
                else:
                    fitness_scores.append(-np.inf)
            
            # 记录历史
            best_history.append({
                'generation': generation,
                'best_score': best_score,
                'avg_score': np.mean(fitness_scores)
            })
            
            # 选择
            selected = self._selection(population, fitness_scores, population_size // 2)
            
            # 交叉
            offspring = self._crossover(selected, population_size)
            
            # 变异
            population = self._mutation(offspring, param_ranges, mutation_rate)
            
            # 进度提示
            if (generation + 1) % 10 == 0:
                logger.info(f"第 {generation + 1} 代，最佳{metric}: {best_score:.4f}")
        
        logger.info(f"遗传算法完成，最佳{metric}: {best_score:.4f}")
        
        return {
            'best_params': best_result['params'] if best_result else {},
            'best_score': best_score,
            'best_metrics': best_result['metrics'] if best_result else {},
            'history': best_history
        }
    
    def _init_population(self, param_ranges: Dict[str, Tuple[float, float]], 
                       size: int) -> List[List[float]]:
        """初始化种群"""
        population = []
        for _ in range(size):
            individual = []
            for param_name, (min_val, max_val) in param_ranges.items():
                value = random.uniform(min_val, max_val)
                individual.append(value)
            population.append(individual)
        return population
    
    def _decode_individual(self, individual: List[float], 
                        param_ranges: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
        """解码个体为参数字典"""
        param_names = list(param_ranges.keys())
        return dict(zip(param_names, individual))
    
    def _selection(self, population: List[List[float]], 
                 fitness_scores: List[float], 
                 num_select: int) -> List[List[float]]:
        """选择操作（轮盘赌选择）"""
        # 转换为正数
        min_score = min(fitness_scores)
        adjusted_scores = [s - min_score + 1e-6 for s in fitness_scores]
        
        # 计算概率
        total = sum(adjusted_scores)
        probabilities = [s / total for s in adjusted_scores]
        
        # 选择
        selected = []
        for _ in range(num_select):
            idx = np.random.choice(len(population), p=probabilities)
            selected.append(population[idx].copy())
        
        return selected
    
    def _crossover(self, parents: List[List[float]], 
                  num_offspring: int) -> List[List[float]]:
        """交叉操作"""
        offspring = []
        while len(offspring) < num_offspring:
            # 随机选择两个父代
            parent1 = random.choice(parents)
            parent2 = random.choice(parents)
            
            # 单点交叉
            crossover_point = random.randint(1, len(parent1) - 1)
            child1 = parent1[:crossover_point] + parent2[crossover_point:]
            child2 = parent2[:crossover_point] + parent1[crossover_point:]
            
            offspring.extend([child1, child2])
        
        return offspring[:num_offspring]
    
    def _mutation(self, population: List[List[float]], 
                 param_ranges: Dict[str, Tuple[float, float]], 
                 rate: float) -> List[List[float]]:
        """变异操作"""
        for individual in population:
            for i in range(len(individual)):
                if random.random() < rate:
                    param_name = list(param_ranges.keys())[i]
                    min_val, max_val = param_ranges[param_name]
                    individual[i] = random.uniform(min_val, max_val)
        return population
    
    def _make_ml_strategy_func(self, factor_weights: Dict, signal_thresholds: Dict,
                                risk_preference: float = 0.8):
        from signal_engine import FactorCalculator, SignalGenerator
        from aiagent.ml_features import compute_features

        self._ensure_model_loaded()
        _ml_model = self._cached_ml_model
        _feature_stats = self._cached_feature_stats
        _feature_names = self._cached_feature_names

        calc = FactorCalculator(factor_weights)
        gen = SignalGenerator(signal_thresholds)
        buy_score_th = float(signal_thresholds.get('buy_score', 6.5))
        sell_score_th = float(signal_thresholds.get('sell_score', 5.5))

        def strategy_func(hist_df):
            if hist_df is None or len(hist_df) < 30:
                return 0.0
            mapped = hist_df.rename(columns={'close_price': 'close'})
            factors = calc.calculate_all_factors(mapped)
            sig_result = gen.generate_signal(factors)
            total_score = float(sig_result.get('total_score') or 0.0)

            buy_prob, sell_prob = 0.5, 0.5
            if _ml_model is not None and _feature_names:
                try:
                    from aiagent.ml_pipeline import _apply_stats
                    _FEAT_LOOKBACK = 120
                    tail_df = hist_df.iloc[-_FEAT_LOOKBACK:]
                    feat_df = compute_features(tail_df, _feature_names)
                    if feat_df is not None and not feat_df.empty:
                        X = feat_df[_feature_names].iloc[[-1]]
                        if _feature_stats:
                            X_arr = _apply_stats(X, _feature_stats)
                        else:
                            X_arr = X.values
                        proba = _ml_model.predict_proba(X_arr)[0]
                        if proba is not None and len(proba) >= 2:
                            buy_prob = float(proba[1])
                            sell_prob = float(proba[0])
                except Exception:
                    pass

            score_range = buy_score_th - sell_score_th
            if score_range <= 0:
                score_norm = 0.5
            else:
                score_norm = (total_score - sell_score_th) / score_range
            score_norm = max(0.0, min(1.0, score_norm))
            prob_strength = buy_prob * (1.0 - sell_prob)
            base_strength = max(0.0, min(1.0, score_norm * prob_strength))
            gamma = 2.2 - (1.7 * risk_preference)
            return float(base_strength ** gamma)

        return strategy_func

    def optimize_factor_weights(self, symbol: str, start_date: str, end_date: str) -> Dict[str, any]:
        """优化因子权重（GPU批量推理 + 预计算因子分量）"""
        from strategy_config import StrategyConfig
        _cfg = StrategyConfig().get_config() or {}
        _signal_thresholds = _cfg.get('signal_thresholds') or {}
        _risk_preference = float(_cfg.get('risk_preference') or 0.8)

        precomp = self._precompute_ml_proba(symbol, start_date, end_date, max_test_rows=300)
        if not precomp.get('success'):
            return {'best_params': {}, 'best_score': -np.inf, 'best_metrics': {},
                    'top_results': [], 'error': precomp.get('message', '预计算失败')}

        full_df = precomp['full_df']
        warmup_len = precomp['warmup_len']
        test_df = precomp['test_df']
        proba_map = precomp['proba_map']

        logger.info("开始预计算因子分量...")
        factor_rows = self._precompute_factor_scores(full_df, warmup_len, test_df)
        logger.info(f"因子分量预计算完成，共 {len(factor_rows)} 行")

        param_grid = {
            'valuation_weight': [0.2, 0.4, 0.6],
            'trend_weight': [0.2, 0.4, 0.6],
            'fund_weight': [0.2, 0.4, 0.6]
        }

        param_names = list(param_grid.keys())
        all_combinations = list(product(*param_grid.values()))
        logger.info(f"因子权重网格搜索：共 {len(all_combinations)} 种组合")

        best_result = None
        best_score = -np.inf
        all_results = []

        for i, combination in enumerate(all_combinations):
            params = dict(zip(param_names, combination))
            total = params['valuation_weight'] + params['trend_weight'] + params['fund_weight']
            if total <= 0:
                continue
            weights = {
                'valuation': params['valuation_weight'] / total,
                'trend': params['trend_weight'] / total,
                'fund': params['fund_weight'] / total,
            }
            result = self._run_fast_backtest(test_df, factor_rows, proba_map,
                                             weights, _signal_thresholds, _risk_preference)
            if result.get('success') and result.get('metrics'):
                score = float(result['metrics'].get('sharpe_ratio', -np.inf))
                all_results.append({'params': params, 'score': score, 'metrics': result['metrics']})
                if score > best_score:
                    best_score = score
                    best_result = {'params': params, 'score': score, 'metrics': result['metrics']}
            if (i + 1) % 10 == 0:
                logger.info(f"因子权重优化进度: {i + 1}/{len(all_combinations)}")

        all_results_sorted = sorted(all_results, key=lambda x: x.get('score', -np.inf), reverse=True)

        final_params = {}
        if best_result:
            p = best_result['params']
            total = p['valuation_weight'] + p['trend_weight'] + p['fund_weight']
            final_params = {
                'valuation_weight': p['valuation_weight'] / total,
                'trend_weight': p['trend_weight'] / total,
                'fund_weight': p['fund_weight'] / total,
            }

        return {
            'best_params': final_params,
            'best_score': best_score,
            'best_metrics': best_result['metrics'] if best_result else {},
            'top_results': all_results_sorted[:20],
        }

    def optimize_signal_thresholds(self, symbol: str, start_date: str, end_date: str) -> Dict[str, any]:
        """优化信号阈值（GPU批量推理 + 预计算因子分量）"""
        from strategy_config import StrategyConfig
        _cfg = StrategyConfig().get_config() or {}
        _factor_weights = _cfg.get('factor_weights') or {}
        _risk_preference = float(_cfg.get('risk_preference') or 0.8)

        precomp = self._precompute_ml_proba(symbol, start_date, end_date, max_test_rows=300)
        if not precomp.get('success'):
            return {'best_params': {}, 'best_score': -np.inf, 'best_metrics': {},
                    'top_results': [], 'error': precomp.get('message', '预计算失败')}

        full_df = precomp['full_df']
        warmup_len = precomp['warmup_len']
        test_df = precomp['test_df']
        proba_map = precomp['proba_map']

        logger.info("开始预计算因子分量（信号阈值优化）...")
        factor_rows = self._precompute_factor_scores(full_df, warmup_len, test_df)
        logger.info(f"因子分量预计算完成，共 {len(factor_rows)} 行")

        param_grid = {
            'buy_score': [6.0, 7.5, 9.0],
            'sell_score': [1.0, 2.5, 4.0],
            'buy_prob': [0.6, 0.7, 0.8],
            'sell_prob': [0.6, 0.7, 0.8],
        }

        param_names = list(param_grid.keys())
        all_combinations = list(product(*param_grid.values()))
        logger.info(f"信号阈值网格搜索：共 {len(all_combinations)} 种组合")

        best_result = None
        best_score = -np.inf
        all_results = []

        for i, combination in enumerate(all_combinations):
            params = dict(zip(param_names, combination))
            thresholds = {
                'buy_score': float(params['buy_score']),
                'sell_score': float(params['sell_score']),
                'buy_prob': float(params['buy_prob']),
                'sell_prob': float(params['sell_prob']),
            }
            result = self._run_fast_backtest(test_df, factor_rows, proba_map,
                                             _factor_weights, thresholds, _risk_preference)
            if result.get('success') and result.get('metrics'):
                score = float(result['metrics'].get('sharpe_ratio', -np.inf))
                all_results.append({'params': params, 'score': score, 'metrics': result['metrics']})
                if score > best_score:
                    best_score = score
                    best_result = {'params': params, 'score': score, 'metrics': result['metrics']}
            if (i + 1) % 20 == 0:
                logger.info(f"信号阈值优化进度: {i + 1}/{len(all_combinations)}")

        all_results_sorted = sorted(all_results, key=lambda x: x.get('score', -np.inf), reverse=True)

        return {
            'best_params': best_result['params'] if best_result else {},
            'best_score': best_score,
            'best_metrics': best_result['metrics'] if best_result else {},
            'top_results': all_results_sorted[:20],
        }

    def optimize_position_rules(self, symbol: str, start_date: str, end_date: str) -> Dict[str, any]:
        """优化仓位规则参数（GPU批量推理 + 预计算因子分量）"""
        from strategy_config import StrategyConfig
        _cfg = StrategyConfig().get_config() or {}
        _factor_weights = _cfg.get('factor_weights') or {}
        _signal_thresholds = _cfg.get('signal_thresholds') or {}

        precomp = self._precompute_ml_proba(symbol, start_date, end_date, max_test_rows=300)
        if not precomp.get('success'):
            return {'best_params': {}, 'best_score': -np.inf, 'best_metrics': {},
                    'top_results': [], 'error': precomp.get('message', '预计算失败')}

        full_df = precomp['full_df']
        warmup_len = precomp['warmup_len']
        test_df = precomp['test_df']
        proba_map = precomp['proba_map']

        logger.info("开始预计算因子分量（仓位规则优化）...")
        factor_rows = self._precompute_factor_scores(full_df, warmup_len, test_df)
        logger.info(f"因子分量预计算完成，共 {len(factor_rows)} 行")

        param_grid = {
            'risk_preference': [0.2, 0.4, 0.6, 0.8, 1.0],
        }

        param_names = list(param_grid.keys())
        all_combinations = list(product(*param_grid.values()))
        logger.info(f"仓位规则网格搜索：共 {len(all_combinations)} 种组合")

        best_result = None
        best_score = -np.inf
        all_results = []

        for i, combination in enumerate(all_combinations):
            params = dict(zip(param_names, combination))
            rp = float(params['risk_preference'])
            result = self._run_fast_backtest(test_df, factor_rows, proba_map,
                                             _factor_weights, _signal_thresholds, rp)
            if result.get('success') and result.get('metrics'):
                score = float(result['metrics'].get('sharpe_ratio', -np.inf))
                all_results.append({'params': params, 'score': score, 'metrics': result['metrics']})
                if score > best_score:
                    best_score = score
                    best_result = {'params': params, 'score': score, 'metrics': result['metrics']}

        all_results_sorted = sorted(all_results, key=lambda x: x.get('score', -np.inf), reverse=True)

        return {
            'best_params': best_result['params'] if best_result else {},
            'best_score': best_score,
            'best_metrics': best_result['metrics'] if best_result else {},
            'top_results': all_results_sorted[:5],
        }

    def optimize_trend_following_params(self, symbol: str, start_date: str, end_date: str) -> Dict[str, any]:
        param_grid = {
            'short_ma': [5, 10, 15],
            'long_ma': [20, 30, 60],
            'breakout_window': [10, 20, 30],
            'confirm_days': [1, 2]
        }

        def evaluate_fn(params: Dict[str, Any]) -> Dict[str, Any]:
            short_n = int(params['short_ma'])
            long_n = int(params['long_ma'])
            breakout_window = int(params['breakout_window'])
            confirm_days = int(params['confirm_days'])

            def strategy_func(hist_df):
                if hist_df is None or len(hist_df) < max(short_n, long_n, breakout_window) + confirm_days + 1:
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
                if golden_cross or current_price >= float(recent_high) * 0.99:
                    return 'buy'
                if death_cross or current_price <= float(recent_low) * 1.01:
                    return 'sell'
                return 'hold'

            return self.backtest_engine.run_strategy_backtest(symbol, start_date, end_date, strategy_func, max_test_rows=300)

        return self.grid_search(evaluate_fn, param_grid, 'sharpe_ratio', top_k=20)

    def optimize_mean_reversion_params(self, symbol: str, start_date: str, end_date: str) -> Dict[str, any]:
        param_grid = {
            'lookback': [10, 20, 30],
            'entry_z': [1.5, 2.0, 2.5],
            'exit_z': [0.3, 0.5, 0.8],
            'max_holding_days': [10, 20]
        }

        def evaluate_fn(params: Dict[str, Any]) -> Dict[str, Any]:
            lookback = int(params['lookback'])
            entry_z = float(params['entry_z'])
            exit_z = float(params['exit_z'])

            def strategy_func(hist_df):
                if hist_df is None or len(hist_df) < lookback + 2:
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

            return self.backtest_engine.run_strategy_backtest(symbol, start_date, end_date, strategy_func, max_test_rows=300)

        return self.grid_search(evaluate_fn, param_grid, 'sharpe_ratio', top_k=20)
