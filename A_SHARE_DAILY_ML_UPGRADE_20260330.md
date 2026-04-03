# A股日线机器学习量化系统改进实施文档

## 1. 文档目的

本文档基于当前代码库的真实实现状态，整理出一份可直接落地的 A 股日线级别机器学习量化系统升级方案，用于指导后续 2~4 周的分阶段改造工作。

目标不是推翻现有系统，而是在保留现有 Flask + SQLite + Tushare + 自建训练链路的基础上，逐步实现：

- 全市场日线前复权数据标准化
- 从 20 个基础因子升级到 36 个高质量因子
- 由固定切分训练升级为 Walk-Forward 滚动训练
- 每日自动更新数据、计算因子、训练模型、输出选股信号
- 后续过渡到多股票组合回测与组合风控

---

## 2. 当前系统基线

### 2.1 训练与数据现状

- 当前训练主链路：
  - [app/routes/ml.py](file:///d:/web%20development/quant/app/routes/ml.py)
  - [aiagent/ml_pipeline.py](file:///d:/web%20development/quant/aiagent/ml_pipeline.py)
- 当前训练模型：
  - XGBoost 分类器
- 当前股票池规模：
  - 全市场约 5492 只股票
- 当前默认训练时间范围：
  - 2022-01-01 ~ 2026-03-26
- 当前样本规模：
  - 训练集约 365 万行
  - 验证集约 62 万行
  - 测试集约 94 万行
- 当前因子数量：
  - 20 个
  - 配置文件：[data/tushare/raw/feature_list.json](file:///d:/web%20development/quant/data/tushare/raw/feature_list.json)
- 当前训练耗时：
  - 最近一次训练约 224 秒

### 2.2 当前已存在的问题

- 数据口径尚未明确统一为“前复权训练标准”
- 特征维度偏少，难以充分表达 A 股日线风格轮动
- 训练集切分仍以固定时间段为主，不能有效应对政策与风格切换
- 数据读取仍以 SQLite 串行读取为主，I/O 与循环开销较大
- 当前回测系统仍以单标的回测为主，不支持“全市场 Top-N 组合选股回测”
- 风险测试和过拟合检查尚未完全围绕策略资金曲线工作

---

## 3. 升级目标

### 3.1 核心目标

- 数据层：统一前复权日线数据，建立稳定的增量更新与缓存链路
- 因子层：将 20 个基础因子扩展到 36 个核心因子
- 模型层：将固定切分训练升级为滚动窗口 Walk-Forward
- 平台层：保留现有主框架，优先增强训练、特征和自动化，不做大规模重构
- 回测层：先补齐组合级回测能力，再考虑更复杂的组合风控与行业约束

### 3.2 设计原则

- 以日线级交易为主，不引入高频架构
- 保留现有前后端主链路，避免推翻式开发
- 优先保证训练与实盘信号一致性
- 优先提升可复现性，再追求复杂度
- 单次迭代只处理一个核心问题，避免一次性改造过大

---

## 4. 模块化实施方案

## 4.1 数据层改造

### 4.1.1 统一复权方式

统一原则：

- 训练、因子计算、回测、信号生成全部使用前复权数据
- 后复权仅用于展示长期走势图或人工复盘，不参与模型训练

建议落地点：

- 训练读取入口统一在 [aiagent/ml_pipeline.py](file:///d:/web%20development/quant/aiagent/ml_pipeline.py)
- 数据抓取脚本统一在 `scripts/` 层增加前复权拉取逻辑
- 数据写库时显式记录 `adj_type=qfq`

### 4.1.2 数据源与字段标准化

建议统一使用以下 Tushare 接口：

- `pro_bar`：日线前复权 OHLCV + amount
- `daily_basic`：换手率、市值、PE、PB
- `moneyflow`：资金流向字段
- `stock_basic`：股票基础信息、上市日期、行业
- `trade_cal`：交易日历

建议新增标准字段层：

- `trade_date`
- `ts_code`
- `open`
- `high`
- `low`
- `close`
- `vol`
- `amount`
- `turnover_rate`
- `pe_ttm`
- `pb`
- `total_mv`
- `net_mf_amount`
- `buy_lg_amount`

### 4.1.3 数据清洗建议

- 剔除 ST 股票
- 剔除上市未满 60 日新股
- 对长期停牌标的进行过滤
- 价格/成交量异常值做 3σ 或分位数截断
- 慢变量允许前向填充
- 快变量按字段性质处理，避免无脑前填

### 4.1.4 数据读取优化建议

当前建议优先级：

1. 先做批量读取
2. 再做 feather/parquet 因子缓存
3. 最后再考虑多进程并行

原因：

- SQLite 读性能瓶颈当前明显存在，但直接多进程访问 SQLite 风险较高
- 对现有项目来说，“批量读取 + 文件缓存”是收益最高、风险最低的第一步

---

## 4.2 因子层改造

### 4.2.1 保留的 20 个基础因子

- `close`
- `volume`
- `amount`
- `return_1d`
- `return_5d`
- `ma_5`
- `ma_10`
- `ma_20`
- `ma_60`
- `ma_bias_5`
- `ma_bias_10`
- `ma_bias_20`
- `rsi_14`
- `macd`
- `macd_signal`
- `macd_hist`
- `atr_14`
- `obv`
- `pe`
- `pb`

### 4.2.2 新增的 16 个目标因子

#### 动量类

- `return_20d`
- `return_60d`
- `momentum_rank`

#### 波动率与风险类

- `volatility_20d`
- `volatility_60d`
- `beta_1y`

#### 资金流向类

- `net_amount`
- `net_amount_rate`
- `buy_lg_amount`

#### 成交量与资金效率类

- `volume_ma5_ratio`
- `volume_ma20_ratio`
- `turnover_rate`
- `amount_ma_ratio`

#### 趋势强度类

- `trend_strength`
- `close_above_ma20`

#### 基本面增强类

- `market_cap`

### 4.2.3 工程实现约束

新增因子分两类实现：

#### 单股票时序型因子

适合继续放在 [aiagent/ml_features.py](file:///d:/web%20development/quant/aiagent/ml_features.py) 中：

- `return_20d`
- `return_60d`
- `volatility_20d`
- `volatility_60d`
- `volume_ma5_ratio`
- `volume_ma20_ratio`
- `amount_ma_ratio`
- `trend_strength`
- `close_above_ma20`

#### 横截面型因子

不适合直接在单股票 rolling 函数里实现，需要新增“同日全市场横截面计算层”：

- `momentum_rank`
- `beta_1y`
- `market_cap` 中性化
- 行业中性化扩展

建议新增一个横截面处理模块，例如：

- `aiagent/cross_section_features.py`

### 4.2.4 因子处理规范

- 去极值：优先采用分位数截断或 3σ
- 标准化：统一采用 Z-score
- 中性化：先做市值中性化，行业中性化作为第二阶段增强
- 缓存：因子矩阵按日期分块缓存到 feather/parquet

---

## 4.3 模型与训练方式改造

## 4.3.1 模型参数建议

当前不建议一上来直接使用最激进参数，建议分两版迭代。

### 第一版建议参数

```python
n_estimators = 1200
max_depth = 7
learning_rate = 0.02
min_child_weight = 1.0
subsample = 0.8
colsample_bytree = 0.8
early_stopping_rounds = 30
tree_method = "hist"
eval_metric = "mlogloss"
```

### 第二版目标参数

```python
n_estimators = 1500
max_depth = 8
learning_rate = 0.01
min_child_weight = 1.0
subsample = 0.8
colsample_bytree = 0.8
early_stopping_rounds = 20
tree_method = "hist"
eval_metric = "mlogloss"
```

说明：

- 当前模型是三分类，不建议直接把 `auc` 作为主评估指标
- 主评估指标建议：
  - `mlogloss`
  - `merror`
- 若后续改成二分类“上涨/非上涨”，再考虑 `auc`

## 4.3.2 Walk-Forward 滚动训练

建议配置：

- 训练窗口：12 个月
- 验证窗口：3 个月
- 预测窗口：1 个月
- 滑动步长：1 个月

建议逻辑：

- 保证严格时间顺序：`train < val < test`
- 每一轮训练输出独立模型
- 每一轮测试结果拼接形成完整滚动回测序列
- 训练样本增加时间权重：
  - 近 3 个月权重 = 1.0
  - 更早 3~12 个月权重 = 0.8

建议改造文件：

- [aiagent/ml_pipeline.py](file:///d:/web%20development/quant/aiagent/ml_pipeline.py)
- [app/routes/ml.py](file:///d:/web%20development/quant/app/routes/ml.py)

## 4.3.3 训练效率优化

建议优先顺序：

1. `hist` 树方法
2. 早停
3. 因子缓存
4. 批量读取
5. 多进程特征计算

不建议第一阶段就上复杂多进程训练器，原因是：

- 当前最先需要保证的是训练逻辑正确性与可复现性
- 多进程会显著提高排障难度

---

## 4.4 回测与组合选股改造

### 4.4.1 当前限制

当前回测系统仍以单标的回测为主：

- [app/routes/backtest.py](file:///d:/web%20development/quant/app/routes/backtest.py)
- [backtest_engine/backtest_engine.py](file:///d:/web%20development/quant/backtest_engine/backtest_engine.py)

因此，本阶段不能直接把“全市场前 30 只/50 只选股组合回测”完全视为已具备能力。

### 4.4.2 回测升级目标

第二阶段建议新增：

- 全市场候选池打分
- 每日选择 Top-N 股票
- 组合级持仓状态
- 组合级资金曲线
- 行业约束
- 总仓位约束

### 4.4.3 推荐回测评估指标

- IC
- RankIC
- 胜率
- 盈亏比
- 最大回撤
- Top-N 组合收益
- 月度换手率
- 行业暴露

---

## 4.5 自动化与运行层改造

目标链路：

- 每日收盘后自动拉取数据
- 更新数据库与缓存
- 计算因子
- 月度滚动训练
- 每日输出选股信号
- 异常告警

建议后续新增脚本：

- `scripts/update_daily_data.py`
- `scripts/build_factor_cache.py`
- `scripts/train_walkforward.py`
- `scripts/generate_daily_signals.py`
- `scripts/check_model_health.py`

---

## 5. 分阶段实施清单

## 阶段 1：数据与因子基础升级

目标：

- 数据口径统一
- 补齐新增因子中最有价值的一批
- 保持训练主链路可运行

必须完成：

- 前复权口径统一
- Tushare 字段标准化
- 增量更新机制
- 批量读取
- 新增 8~12 个高收益因子
- 标准化与去极值

建议本阶段新增的优先因子：

- `return_20d`
- `return_60d`
- `volatility_20d`
- `volatility_60d`
- `volume_ma5_ratio`
- `volume_ma20_ratio`
- `turnover_rate`
- `amount_ma_ratio`
- `trend_strength`
- `close_above_ma20`
- `market_cap`
- `net_amount`

## 阶段 2：训练链路升级

目标：

- 用 Walk-Forward 替换固定切分
- 将训练结果变成可拼接的滚动评估

必须完成：

- 动态窗口切分
- 时间权重
- 每轮模型输出
- 滚动结果汇总
- XGBoost 参数升级

## 阶段 3：组合回测与选股输出

目标：

- 从单标的回测升级到组合级 Top-N 回测

必须完成：

- 股票池候选打分
- Top-N 组合生成
- 组合级持仓结构
- 行业与总仓位约束
- 组合净值曲线

## 阶段 4：自动化与监控

目标：

- 降低日常人工干预
- 建立模型健康监控

必须完成：

- 定时任务
- 自动更新
- 自动信号输出
- 训练失败告警
- 信号质量监控

---

## 6. 推荐修改文件清单

### 第一优先级

- [aiagent/ml_pipeline.py](file:///d:/web%20development/quant/aiagent/ml_pipeline.py)
- [aiagent/ml_features.py](file:///d:/web%20development/quant/aiagent/ml_features.py)
- [data/tushare/raw/feature_list.json](file:///d:/web%20development/quant/data/tushare/raw/feature_list.json)
- [app/routes/ml.py](file:///d:/web%20development/quant/app/routes/ml.py)

### 第二优先级

- 新增 `aiagent/cross_section_features.py`
- 新增因子缓存模块
- 新增数据增量更新脚本

### 第三优先级

- [app/routes/backtest.py](file:///d:/web%20development/quant/app/routes/backtest.py)
- [backtest_engine/backtest_engine.py](file:///d:/web%20development/quant/backtest_engine/backtest_engine.py)

---

## 7. 风险与注意事项

### 7.1 技术风险

- 横截面因子不能继续套用单股票 rolling 写法
- 多进程 + SQLite 可能带来锁与并发问题
- 特征数增加后，训练时长可能明显上升

### 7.2 评估风险

- 不建议把“准确率”作为唯一主目标
- 三分类任务不建议直接使用 `auc` 作为主指标
- 若没有组合回测，单票回测不能代表全市场选股策略表现

### 7.3 工程风险

- 一次性改造过多模块会导致链路不稳定
- 建议每完成一个阶段就做一次端到端验证

---

## 8. 预期结果

完成阶段 1~2 后，预期系统能够实现：

- 全市场前复权日线数据标准化
- 约 30~36 个核心因子稳定计算
- 基于 Walk-Forward 的滚动训练
- 更贴近当前市场风格的模型更新方式
- 每日输出可解释的选股信号

完成阶段 3~4 后，预期系统能够进一步实现：

- Top-N 组合选股回测
- 基础行业与仓位风控
- 自动化日常运行
- 模型质量监控与异常告警

---

## 9. 最终建议

本项目最优路线不是“推翻重写”，而是：

- 保留现有主系统
- 先升级数据与训练逻辑
- 再扩展组合回测
- 最后补齐自动化与监控

建议立即启动的实际工作包只有三个：

- 数据口径统一为前复权
- 增加第一批 8~12 个关键因子
- 将固定切分训练改造为 Walk-Forward

这三项完成后，系统会从“能训练的量化原型”升级为“可以持续迭代的日线机器学习选股平台”。

---

## 10. 2026-03-31 回测参数序贯优化与性能改造（已落地）

本节记录今天已完成的“回测参数序贯优化（前端引导）+ 后端性能改造（GPU批量推理）”，用于解决优化卡在 95%/96% 且 CPU 占满的问题，并保证优化结果可持久化、跨页面一致展示。

### 10.1 背景问题

- 旧的参数优化流程在网格搜索中对每个组合重复执行 ML 推理（逐行 `predict_proba`），组合数一大就会出现长时间占用 CPU、前端进度卡住的问题。
- 信号阈值优化网格为 5×5×5×5=625 组合；若每组合都跑 300 行推理，推理次数可达 18 万级别，严重拖慢优化。
- Flask debug 模式下默认 reloader 可能导致训练/优化线程被重启中断（需避免文件改动触发重载）。

### 10.2 前端：序贯优化引导 + 状态持久化

落地内容：

- 回测界面用三步序贯面板替代“优化类型下拉 + 一键优化”：
  1) 因子权重 → 2) 信号阈值 → 3) 仓位规则
- 未完成上一步时，下一步按钮禁用；优化运行中禁用其它按钮；成功后标记“已完成”。
- 优化状态写入 localStorage，刷新/切换页面不丢失；信号分析界面只读展示优化状态，并提示“请在回测验证区配置/执行优化”。

相关文件：

- [index.html](file:///d:/web%20development/quant/app/templates/index.html)

### 10.3 后端：GPU批量推理 + 预计算复用（核心性能改造）

总体思路：把“重活”集中到一次性预计算，网格搜索阶段只做轻量数值计算，避免每个组合重复 ML 推理。

关键改造点：

- 模型加载与缓存：
  - `_ensure_model_loaded()` 仅加载一次 ML 模型并缓存到类成员，避免在网格搜索中反复从磁盘读取模型。
  - 对 XGBoost 模型尝试设置 `device='cuda'` + `tree_method='hist'`，将推理切换到 GPU（若环境不支持则自动回退）。
- 一次性批量推理（GPU/CPU均可复用）：
  - `_precompute_ml_proba()`：对测试集最多 300 行，构造特征矩阵，一次性调用 `predict_proba(X_all)` 计算全量概率，输出：
    - `proba_map = {row_idx: (buy_prob, sell_prob)}`
    - `full_df / warmup_len / test_df` 供后续因子与回测使用
- 因子分量预计算：
  - `_precompute_factor_scores()`：对测试集逐行预计算三类因子分量 `valuation/trend/fund`（不做权重加权），输出：
    - `factor_rows = [{'v':..., 't':..., 'f':...}, ...]`
- 轻量级回测：
  - `_run_fast_backtest()`：输入 `test_df + factor_rows + proba_map + 参数`，直接计算目标仓位并进行回测资金曲线计算，不再调用 ML 推理函数。
  - 网格搜索阶段仅重复调用 `_run_fast_backtest()`，其复杂度与“组合数 × 测试行数”线性相关，但每步都是纯数值计算，速度远高于 ML 推理。

相关文件：

- [parameter_optimizer.py](file:///d:/web%20development/quant/backtest_engine/parameter_optimizer.py)

### 10.4 网格规模控制

- 因子权重：3×3×3=27（`valuation/trend/fund`）
- 信号阈值：由 5⁴=625 缩减为 3⁴=81（`buy_score/sell_score/buy_prob/sell_prob`）
- 仓位规则：风险偏好 5 组（`risk_preference`）

### 10.5 结果与预期效果

- 优化不再出现“卡在 95%/96% 且 CPU 占满”的长时间状态：推理阶段集中在一次性批量计算，且优先走 GPU。
- 网格搜索阶段由“每组合重复 ML 推理”转为“复用预计算结果的轻量级回测”，整体耗时显著下降。
- 序贯优化的交互与持久化能力完善：回测页配置后返回信号分析页可直接看到只读状态，避免用户误操作。

### 10.6 2026-04-01 回测驱动信号分析（锁定标的 + 下单建议）

目标：让“信号分析”的输出成为回测层最终口径的延伸，而不是一套可随意换股/换逻辑的独立模块，确保用户在回测里调优的因子权重、阈值与仓位规则能无缝映射为实盘执行建议。

落地内容：

- 流程顺序调整（前端菜单与进入门禁）：
  - 菜单顺序改为：策略配置 → 回测验证 → 信号分析
  - 进入信号分析前必须先完成至少一次回测（避免“没回测就看信号”的断链）
- 标的锁定与持久化：
  - 回测成功后自动将回测标的同步到 `signalSymbol`，并在信号分析页锁定输入框（不可更换个股）
  - 锁定状态与标的写入 localStorage，刷新页面也能恢复（`quant_backtest_completed_v1` / `quant_backtest_symbol_v1`）
  - 当用户“返回修改策略”解锁流程时，自动清理锁定状态与回测完成标记
- 信号输出升级为“回测最终执行口径”（B方案）：
  - 信号分析接口除返回 `target_position`（裁剪前）外，新增 `final_target_position`（按单票上限裁剪后）
  - 新增 `suggested_trade`：给出与回测引擎一致的下单建议（买/卖/持有、建议股数/手数、滑点执行价、佣金/印花税、合计费用、卖出时预估盈亏）

涉及文件：

- 前端流程与锁定逻辑：[index.html](file:///d:/web%20development/quant/app/templates/index.html)
- 信号生成与下单建议计算：[strategy.py](file:///d:/web%20development/quant/app/routes/strategy.py)

注意事项：

- 下单建议会按“整手 100 股”向下取整；若目标变化不足一手，会返回 `hold` 并给出原因。
- 若未能读取到持仓/可用资金设置，会按默认资金进行估算（用于信号分析展示，不等同于真实券商账户的最终可成交结果）。

### 10.7 2026-04-01 参数主控中心迁移到回测层

目标：让“会直接影响回测结果与信号输出口径”的参数，集中在回测验证页面统一调整，避免用户在策略配置和回测页面之间来回切换造成认知割裂。

本次迁移原则：

- 已明确进入回测执行或信号最终口径的参数，迁移到回测层
- 尚未完整接入回测引擎、更多属于全局限制或筛选指标的参数，暂留策略配置层

已迁移到回测层的参数：

- 因子权重（`factor_weights`）
- 信号阈值（`signal_thresholds`）
- 风险偏好（`risk_preference`）
- 单票仓位上限（`position_limits.single_max`）
- 单笔止损（`targets.single_loss`）

前端落地方式：

- 策略配置页不再展示 ML 策略的因子权重与信号阈值主控项
- 回测页新增：
  - “因子权重（回测调优）”
  - “信号阈值（回测调优）”
  - “风险与止损（回测调优）”
- 每个区块都提供“应用到策略配置”按钮，点击后将当前参数写回 `strategy_config.json`
- 一旦这些参数发生修改，就会立即使“已完成回测”状态失效，用户必须重新执行回测后才能进入信号分析，保证信号分析永远对应最新回测方案

暂未迁移、仍保留在策略配置层的参数：

- `position_limits.total_max`
- `position_limits.daily_trades`
- `position_limits.symbol_daily_trades`
- `targets.daily_loss`
- `targets.annual_return`
- `targets.max_drawdown`

原因：

- 这些参数目前要么尚未完整进入回测执行引擎，要么更适合作为全局风控限制/验收指标，而不是单标的回测时直接调节的执行参数。

### 10.8 2026-04-01 回测执行层接入交易频率与日亏损约束

目标：让原本只在交易触发/配置层存在的约束，真正进入回测执行过程，使回测曲线与“带约束的实际执行”一致，并确保信号分析继承同一套最终规则。

本次接入的约束（单标的日线回测）：

- `position_limits.daily_trades`：日内买入次数上限（达到上限后，当天不再允许新增买入；卖出允许用于降风险）
- `position_limits.symbol_daily_trades`：单标的日内买入次数上限（单标的回测下会与 daily_trades 取更严格者）
- `targets.daily_loss`：日内最大亏损阈值（按日收益率口径，达到阈值后当日不再允许新增买入；卖出允许用于降风险）

涉及文件：

- 回测执行约束落地：[backtest_engine.py](file:///d:/web%20development/quant/backtest_engine/backtest_engine.py)
- 回测接口参数下发与展示：[backtest.py](file:///d:/web%20development/quant/app/routes/backtest.py)
- 回测页参数入口与“应用到策略配置”：[index.html](file:///d:/web%20development/quant/app/templates/index.html)

### 10.9 2026-04-01 全链路审查与关键缺口修复（已落地）

目标：对“策略配置 → 回测验证 → 信号分析”链路做端到端审查，修复会直接影响回测口径与信号展示一致性的关键缺口。

修复项：

- 回测高级配置的止损/止盈生效：
  - 现状：前端回测高级配置已提供 `stop_loss/take_profit` 输入，但后端未读取，导致参数实际无效。
  - 落地：在回测接口中读取并下发到引擎；引擎在每个 bar 基于持仓均价计算 `pnl_pct`，触发止损/止盈时强制将目标仓位置为 0（清仓优先于策略信号）。
  - 涉及文件：
    - [backtest.py](file:///d:/web%20development/quant/app/routes/backtest.py)
    - [backtest_engine.py](file:///d:/web%20development/quant/backtest_engine/backtest_engine.py)
- 信号分析“下单建议”费用字段对齐：
  - 现状：前端展示使用 `suggested_trade.total_cost`，但后端卖出分支返回 `total_fee`，导致“合计费用”可能为空。
  - 落地：卖出分支同时补齐 `total_cost` 字段（与 `total_fee` 同值），保持前后端字段一致。
  - 涉及文件：
    - [strategy.py](file:///d:/web%20development/quant/app/routes/strategy.py)
- 回测手续费率默认值修正：
  - 现状：前端默认 `commission_rate=0.003`（千三）显著偏高，容易导致回测收益被错误压低。
  - 落地：前端默认值改为 `0.0003`（万三），并在输入框标注“手续费率（小数）”。
  - 涉及文件：
    - [index.html](file:///d:/web%20development/quant/app/templates/index.html)
- 回测高级配置输入单位提示完善：
  - `stop_loss/take_profit` 输入框明确为“小数”口径，并给出示例 placeholder（`-0.10 / 0.20`），降低误填概率。
  - 涉及文件：
    - [index.html](file:///d:/web%20development/quant/app/templates/index.html)
