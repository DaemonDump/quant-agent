# 实盘风控&运行记录文档

核心定义

- 定义实盘（手动下单场景）的风控阈值与运行记录规范，使 AI 可协助监控、排查与复盘；仅保留最小可执行内容。

一、实盘风控规则（阈值来源：strategy\_config.json）

1. 仓位风控

- 单票仓位上限：position\_limits.single\_max = 0.1（10%）
- 总仓位上限：position\_limits.total\_max = 0.8（80%）
- 单票日交易次数：position\_limits.symbol\_daily\_trades = 2
- 全部日交易次数：position\_limits.daily\_trades = 10
- 全部周交易次数：position\_limits.weekly\_trades = 50

1. 回撤/亏损风控

- 最大回撤目标：targets.max\_drawdown = 0.1（10%）
- 单笔止损阈值：targets.single\_loss = 0.05（5%）
- 单日亏损阈值：targets.daily\_loss = 0.02（2%）
- 触发动作（最简版）
  - 达到单日亏损阈值：当日停止新增仓位，仅允许减仓/平仓
  - 达到最大回撤阈值：将总仓位上限临时降为 50%（可通过配置更新）

1. 异常风控（触发即暂停）

- 数据异常：行情延迟/缺失（当日无最新交易日数据）
- 预测异常：模型状态非 ready（ml\_model.status != "ready"）
- 系统异常：接口连续 5xx、数据库锁冲突、训练状态异常占用

二、实盘运行记录（每日 1 次，固定格式）

记录频率

- 每个交易日收盘后记录 1 次；若当日出现异常，额外记录一次“异常补充记录”

记录内容（固定三段）

- 运行状态：正常 / 异常
- 核心数据：持仓、成交、当日盈亏、累计盈亏、模型状态
- 异常情况：现象、开始时间、处理动作、处理结果

记录格式（固定文本模板）

- 日期：YYYY-MM-DD
- 运行状态：正常|异常
- 持仓：N 只（可从 positions 表汇总）
- 成交：buy=N 次，sell=N 次（可从 trade\_records 表汇总）
- 当日盈亏：+/-X
- 累计盈亏：+/-X
- 模型状态：ready|training|stale|error（来自 strategy\_config.json.ml\_model.status）
- 异常：无 | <简述>
- 处理：无 | <动作与结果>

三、数据落点（用于复盘与追溯）

- 持仓台账：SQLite.positions（接口：[trading.py](file:///d:/web%20development/quant/app/routes/trading.py#L40-L87)）
- 交易台账：SQLite.trade\_records（接口：[trading.py](file:///d:/web%20development/quant/app/routes/trading.py#L88-L120)）
- 策略状态：SQLite.strategy\_status（接口：[trading.py](file:///d:/web%20development/quant/app/routes/trading.py#L136-L169)）
- 模型状态：strategy\_config.json.ml\_model（路径：[strategy\_config.json](file:///d:/web%20development/quant/strategy_config.json#L43-L50)）

编写目的

- 让 AI 能依据明确阈值进行实盘监控与告警，并通过统一的运行记录格式支撑复盘与迭代优化。

