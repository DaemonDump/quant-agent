# 目录&文件说明文档

核心定义

- 统一说明项目目录结构与关键文件用途，提供“标准层级→实际目录”的映射，便于 AI 精确定位与读取。

标准层级（规范化视角）

- /data：运行数据与模型产物（原始/处理后/因子）
- /model：模型训练代码与权重
- /strategy：策略逻辑与回测代码
- /utils：通用工具
- /config：配置与参数
- /docs：本文档集合（本次新增）

实际目录映射（当前仓库）

- 数据（/data）
  - [data/tushare/db/quant\_data.db](file:///d:/web%20development/quant/data/tushare/db/quant_data.db)：SQLite 主库
  - [data/tushare/raw/feature\_list.json](file:///d:/web%20development/quant/data/tushare/raw/feature_list.json)：特征与标签配置
  - [data/tushare/models](file:///d:/web%20development/quant/data/tushare/models)：训练输出/导入模型/注册表/日志
  - [data/tushare/reports](file:///d:/web%20development/quant/data/tushare/reports)：覆盖率报告
  - [data/tushare/state](file:///d:/web%20development/quant/data/tushare/state)：训练状态/下载缓存/批量拉数状态
- 模型（/model）
  - [aiagent/ml\_pipeline.py](file:///d:/web%20development/quant/aiagent/ml_pipeline.py)：训练主流程
  - [aiagent/model\_runtime.py](file:///d:/web%20development/quant/aiagent/model_runtime.py)：运行时加载
  - [aiagent/model\_manager.py](file:///d:/web%20development/quant/aiagent/model_manager.py)：模型版本管理/打包
  - [scripts/train\_ml\_model.py](file:///d:/web%20development/quant/scripts/train_ml_model.py)：命令行训练入口
- 策略与回测（/strategy）
  - [signal\_engine](file:///d:/web%20development/quant/signal_engine)：因子计算、信号生成/过滤、触发检查
  - [backtest\_engine](file:///d:/web%20development/quant/backtest_engine)：回测引擎、参数优化、风险测试、过拟合检查
  - [app/routes/strategy.py](file:///d:/web%20development/quant/app/routes/strategy.py)：策略接口（仓位/建议/阈值/权重）
  - [app/routes/backtest.py](file:///d:/web%20development/quant/app/routes/backtest.py)：回测接口
- 工具与运维（/utils）
  - [app/utils.py](file:///d:/web%20development/quant/app/utils.py)：日志初始化等通用工具
  - [scripts](file:///d:/web%20development/quant/scripts)：批量拉数/覆盖率检查/DB 维护/演示脚本
  - [live\_ops](file:///d:/web%20development/quant/live_ops)：实盘监控、交易日志、紧急处理
- 配置（/config）
  - [config.py](file:///d:/web%20development/quant/config.py)：数据库/日志路径与 SECRET\_KEY
  - [strategy\_config.json](file:///d:/web%20development/quant/strategy_config.json)：策略与模型状态持久化
  - [app/schema.sql](file:///d:/web%20development/quant/app/schema.sql)：数据库表结构
- 文档（/docs）
  - 本次新增的 8 份“最简可用版”核心文档

命名规范（统一规则）

- 代码与文件：小写+下划线，例如 factor\_calculator.py、train\_ml\_model.py
- 数据文件：语义+后缀，例如 coverage\_db\_\*.csv、model\_weights.pkl
- 目录：语义化命名，按模块职责划分（app/、aiagent/、backtest\_engine/…）

编写目的

- 让 AI 能依据“标准层级→实际目录”快速定位文件与功能，避免路径/命名不一致引发的读取与调用问题。

