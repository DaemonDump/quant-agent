# 代码规范&优化历程文档（

核心定义

- 给出可执行的代码规范（便于 AI 阅读/生成/复用），并记录对“最简可用版”有决定性影响的少量关键优化节点（3–5条），用于理解代码演进方向。

代码规范（可执行约束）

- 命名规范
  - 变量/函数：小写+下划线，例如 factor\_value、calculate\_factor()
  - 类：大驼峰，例如 FactorCalculator、BacktestEngine
  - 常量：全大写+下划线，例如 LOG\_LEVEL
- 模块边界
  - Web/API：仅处理参数校验、编排调用与响应格式，目录 [app/routes](file:///d:/web%20development/quant/app/routes)
  - 业务引擎：信号/回测/训练逻辑分别落在 [signal\_engine](file:///d:/web%20development/quant/signal_engine)、[backtest\_engine](file:///d:/web%20development/quant/backtest_engine)、[aiagent](file:///d:/web%20development/quant/aiagent)
  - 数据读写：集中在 SQLite 与 data 目录产物，避免散落硬编码路径
- 错误处理
  - 输入不合法：返回 4xx（API 层）
  - 内部异常：记录日志（logger）并返回 5xx（API 层避免暴露内部细节）
- 类型与序列化
  - 对外 JSON：必须确保数值为 Python 原生类型（float/int/list），避免 numpy 标量导致序列化失败（已在因子模块做了处理）
- 测试规范
  - tests/ 必须可离线运行，不依赖外部网络与真实 Token（已将测试改为本地 DB 逻辑）

关键优化历程（仅保留影响“可用性/正确性/维护性”的核心节点）

- 2026-03-27：信号链路稳定性修复（前端渲染与后端序列化）
  - 原因：因子结果包含 numpy 标量导致 `jsonify` 失败，前端对 undefined 调用 toFixed 导致页面崩溃
  - 方案：因子结果统一转换为 Python 原生类型；前端增加空值防护并统一字段名
  - 效果：信号分析链路从“偶发 500/页面失效”恢复为稳定可用
  - 参考：[OPTIMIZATION\_DOCUMENTATION.md](file:///d:/web%20development/quant/OPTIMIZATION_DOCUMENTATION.md#L38-L55)、[factor\_calculator.py](file:///d:/web%20development/quant/signal_engine/factor_calculator.py#L58-L77)
- 2026-03-29：数据库字段标准化与热迁移
  - 原因：历史行情表缺少因子/训练所需字段（pe/pb/市值/资金流等）
  - 方案：补齐 schema，并提供迁移函数在已有库上热补列
  - 效果：训练/回测/信号计算对字段依赖一致，减少“无字段/空数据”故障
  - 参考：[ARCHITECTURE\_OPTIMIZATION\_20260329.md](file:///d:/web%20development/quant/ARCHITECTURE_OPTIMIZATION_20260329.md#L32-L35)、[db\_init.py](file:///d:/web%20development/quant/data_ingestion/db_init.py#L7-L28)、[schema.sql](file:///d:/web%20development/quant/app/schema.sql#L41-L86)
- 2026-03-29：消除路径硬编码，统一 DB 路径来源
  - 原因：部分模块硬编码旧 DB 路径，导致从不同入口启动时读写错库
  - 方案：统一从 Flask `current_app.config['DATABASE']` 或 Config.DATABASE 获取
  - 效果：不同启动方式下数据一致，降低运维排障成本
  - 参考：[ARCHITECTURE\_OPTIMIZATION\_20260329.md](file:///d:/web%20development/quant/ARCHITECTURE_OPTIMIZATION_20260329.md#L17-L20)、[config.py](file:///d:/web%20development/quant/config.py#L15-L27)
- 2026-03-29：参数优化器评估接口统一（避免“参数未参与评估”）
  - 原因：遗传算法评估时未正确传入参数，导致搜索无效
  - 方案：改为以 evaluate\_fn 回调为统一入口，与 grid\_search 对齐
  - 效果：参数优化结果可解释且可复现
  - 参考：[ARCHITECTURE\_OPTIMIZATION\_20260329.md](file:///d:/web%20development/quant/ARCHITECTURE_OPTIMIZATION_20260329.md#L23-L26)、[parameter\_optimizer.py](file:///d:/web%20development/quant/backtest_engine/parameter_optimizer.py#L257-L311)
- 2026-03-27：批量落库与覆盖率报告（数据生产可追溯）
  - 原因：训练/回测前需要可复现的数据准备与缺口核对
  - 方案：新增批量脚本 + 覆盖率报告（CSV + MD 概览）
  - 效果：数据准备过程可复现、可核对、可审计
  - 参考：[BATCH\_INGEST\_DOCUMENTATION.md](file:///d:/web%20development/quant/BATCH_INGEST_DOCUMENTATION.md#L7-L15)、[coverage\_db\_20220101\_20260326.md](file:///d:/web%20development/quant/data/tushare/reports/coverage_db_20220101_20260326.md#L1-L16)

编写目的

- 让 AI 能在一致的规范下阅读与生成代码，并通过少量关键优化节点理解“为什么现在这样实现”，避免引入回归与分叉实现。

