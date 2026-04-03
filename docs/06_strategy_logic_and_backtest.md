# 策略逻辑与回测文档

核心定义

- 说明策略执行的核心逻辑、回测方案与指标，保留复现所需的最小集合。

策略逻辑（执行流程）

- 策略思想：结合规则因子总分（0\~10）与 ML 信号（概率/评分），生成买卖建议
- 调仓规则：按日级驱动；建议持仓上限与单票约束从策略配置读取
- 仓位管理：单票≤10%，总仓≤80%，日/周交易次数限制（见 [strategy\_config.json](file:///d:/web%20development/quant/strategy_config.json#L14-L20)）
- 止盈止损：参考 targets（单笔亏损 5%、日亏损 2% 提示），策略引擎可按约束过滤信号
- 接入位置：[app/routes/strategy.py](file:///d:/web%20development/quant/app/routes/strategy.py)

回测方案（单票最简版）

- 回测引擎：买入持有 / 自定义策略两类
  - 简单回测：在测试集首尾做一次买入/卖出，计算费用与盈亏
  - 自定义策略：逐 bar 仓位/撮合/费用/止损止盈约束
- 时间划分：预热集70%、验证集0%、测试集30%（见 [backtest\_engine.py](file:///d:/web%20development/quant/backtest_engine/backtest_engine.py#L47-L60)）
- 费用模型：
  - 佣金：0.000085（万零点八五）
  - 印花税：0.001（千一，仅卖出）
  - 滑点：默认 0.001（策略回测接口）
- 口径约束：仅使用当日及历史数据计算因子与信号，不引入未来函数

回测参数（接口）

- [run\_strategy\_backtest(..., commission=None, slippage=0.001, ...)](file:///d:/web%20development/quant/backtest_engine/backtest_engine.py#L197-L206)
- [calculate\_metrics(returns)](file:///d:/web%20development/quant/backtest_engine/backtest_engine.py#L68-L117)

回测指标（核心4项）

- 年化收益率 annual\_return
- 最大回撤 max\_drawdown
- 夏普比率 sharpe\_ratio（年化 3% 无风险利率换算）
- 胜率 win\_rate

输出与展示

- API 返回：指标字典 + 交易记录（买入/卖出两条，含费用与盈亏）
- 前端展示：指标卡与交易表格（见 [index.html](file:///d:/web%20development/quant/app/templates/index.html)）

编写目的

- 让 AI 在不引入复杂组合与行业约束的前提下，复现最小策略与回测链路，并能在此基础上逐步完善组合级回测与风控。

