# 部署与运维文档

核心定义

- 给出最小可运行的环境搭建、启动与日常运维流程；仅保留能让系统“跑起来并可排障”的关键信息。

环境搭建（最小依赖）

- Python：建议与当前一致（本仓库运行痕迹为 Python 3.13）
- 依赖安装：见 [requirements.txt](file:///d:/web%20development/quant/requirements.txt)（核心：Flask/Pandas/NumPy/XGBoost/Tushare/TA-Lib）
- 数据库：SQLite 文件，无需独立服务

配置项（运行必需）

- Tushare Token（建议仅在本机环境变量或 SQLite settings 中保存）
  - Web 设置接口：POST /api/settings/token（保存到 settings 表）
- SECRET\_KEY（生产必须配置）
  - 读取位置：[config.py](file:///d:/web%20development/quant/config.py#L6-L14)
  - 建议：通过环境变量 SECRET\_KEY 明确设置，避免重启后会话失效
- 数据库路径
  - 默认：[data/tushare/db/quant\_data.db](file:///d:/web%20development/quant/data/tushare/db/quant_data.db)

启动流程（本地部署）

- <br />
  1. 安装依赖：pip install -r requirements.txt
- <br />
  1. 启动服务：python run.py（入口：[run.py](file:///d:/web%20development/quant/run.py)）
- <br />
  1. 访问页面：GET /（模板：[index.html](file:///d:/web%20development/quant/app/templates/index.html)）

数据准备（训练/回测前）

- 初始化/迁移表结构：通过数据接入模块初始化（见 [db\_init.py](file:///d:/web%20development/quant/data_ingestion/db_init.py#L30-L78)）
- 批量落库（可选但推荐）
  - 执行入口：[fetch\_history\_batch.py](file:///d:/web%20development/quant/scripts/fetch_history_batch.py) 或 [run\_batches.ps1](file:///d:/web%20development/quant/scripts/run_batches.ps1)
  - 记录规范与报告：见 [BATCH\_INGEST\_DOCUMENTATION.md](file:///d:/web%20development/quant/BATCH_INGEST_DOCUMENTATION.md)

模型训练（可选）

- 命令行入口：[train\_ml\_model.py](file:///d:/web%20development/quant/scripts/train_ml_model.py)
- 训练产物：data/tushare/models/ml\_model/<version>/（weights + metadata + stats）
- 训练状态：data/tushare/state/ml\_train\_status.json

日志与定位

- Web/应用日志：[logs/app.log](file:///d:/web%20development/quant/logs/app.log)
- 系统日志：[logs/quant\_system.log](file:///d:/web%20development/quant/logs/quant_system.log)
- 模型日志：data/tushare/models/logs/\*

常见问题（最小排障清单）

- 数据获取失败
  - 检查：Token 是否已保存；Tushare 限流；网络可用性
  - 处理：降低批量脚本 sleep；重试；查看 logs
- 因子/趋势计算失败
  - 检查：TA-Lib 是否安装（talib-binary）
  - 处理：安装依赖；或在无 TA-Lib 情况下接受趋势因子降级
- 回测无数据
  - 检查：DB 是否存在目标标的与区间数据；trade\_date 格式是否为 YYYYMMDD
  - 处理：先用批量落库脚本补齐数据
- 训练失败/中断
  - 检查：state 文件是否被并发写入；磁盘空间；模型目录权限
  - 处理：清理 state.cancel；重启训练；保留 logs 以便复盘

重启流程（最小）

- <br />
  1. 停止当前进程
- <br />
  1. 检查 config/env 与数据库路径
- <br />
  1. 启动 python run.py
- <br />
  1. 验证首页可访问，检查 logs/app.log 是否报错

编写目的

- 让 AI 能在最少步骤下完成环境搭建、启动与排障，保障系统可运行、可维护、可迭代。

