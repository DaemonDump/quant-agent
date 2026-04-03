# 模型设计与训练文档

核心定义

- 说明模型目标、特征体系、标签构建与训练流程；仅保留可复现训练所需的核心信息。

模型目标（当前实现）

- 预测未来若干交易日的收益方向与幅度，用于生成买卖信号或评分参考（分类与回归并存，以 5 日为主）
- 训练/推理：XGBoost 分类器（bundle 持久化于 data/tushare/models/ml\_model/\*）

特征体系（输入）

- 配置来源：[feature\_list.json](file:///d:/web%20development/quant/data/tushare/raw/feature_list.json)
- 典型特征（部分）：日收益率 return\_1d/5d/20d/60d、均线及乖离 ma\_5/10/20/60 + bias、波动率 volatility\_20d/60d、量价比 volume\_ma5/20\_ratio、趋势强度 trend\_strength、RSI/MACD/ATR/OBV、估值/资金/市值（pe/pb/turnover\_rate/buy\_lg\_amount/net\_amount\_rate/market\_cap）
- 计算入口：[ml\_features.py](file:///d:/web%20development/quant/aiagent/ml_features.py#L70-L186)

标签构建（输出）

- 分类标签：label\_5d\_class（未来5日累计收益高于 up\_threshold=3% 为 1；低于 -3% 为 0；其它可视为不确定/忽略）
- 回归标签：label\_5d\_return（未来5日累计收益）
- 配置字段：feature\_list.json 中的 label 配置（horizon\_days/up\_threshold/down\_threshold）

训练流程（可复现步骤）

- 入口：命令行 [train\_ml\_model.py](file:///d:/web%20development/quant/scripts/train_ml_model.py#L13-L21)
- 数据范围：默认 20220101 \~ 20260326（可通过参数覆盖）
- 切分方式：Walk-Forward（train\_months=12, val\_months=3, test\_months=1, step\_months=1）
- 过程：
  - 读取 SQLite 历史数据（OHLCV + 估值/资金）
  - 依据 feature\_list 计算特征，按 label 生成训练标签
  - 按时间滚动做训练/验证/测试，记录指标与元信息（metadata）
  - 保存模型 bundle（weights.pkl + feature\_config/feature\_stats/metadata/model\_card）
- 状态写入：训练成功后更新 [strategy\_config.json](file:///d:/web%20development/quant/strategy_config.json) 的 ml\_model 状态与路径（ready/last\_trained\_at/model\_path）

超参数搜索（策略）

- 当前版本以稳定训练与数据一致性为主；若需调参，可围绕 XGBoost 常见参数（学习率/树深度/叶子数/L1/L2）做网格或贝叶斯
- 原则：先固定数据口径与特征版本，再做少量超参搜索，避免“数据与超参同时漂移”导致不可复现

过拟合与一致性约束

- 使用时间序列滚动切分，验证集与测试集不与训练区间重叠
- 特征统计（均值/方差/缺失处理）随模型保存并在推理时一致复用
- 训练/推理统一前复权日线口径；若数据不足，优先补齐数据再训练

编写目的

- 为 AI 提供可复现训练流程的最小必要信息，确保“读取配置→准备特征与标签→滚动训练→保存 bundle→更新状态”的链路稳定。

