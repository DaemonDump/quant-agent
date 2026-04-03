# 系统架构文档

核心定义

- 明确量化模型整体技术框架、模块划分及模块间关联；仅保留核心模块与数据流，便于 AI 快速理解与检索。

核心模块（固定6层）

- 数据层：采集与存储行情/基础数据。实现位置：[data\_ingestion](file:///d:/web%20development/quant/data_ingestion) + SQLite 数据库 [quant\_data.db](file:///d:/web%20development/quant/data/tushare/db/quant_data.db)
- 因子层：从原始数据计算因子并做处理（去极值/归一化/滑窗），为模型与策略提供输入。[ml\_features.py](file:///d:/web%20development/quant/aiagent/ml_features.py) + [signal\_engine](file:///d:/web%20development/quant/signal_engine)
- 模型层：训练与推理机器学习模型，输出信号/概率。[ml\_pipeline.py](file:///d:/web%20development/quant/aiagent/ml_pipeline.py) + 运行时加载 [model\_runtime.py](file:///d:/web%20development/quant/aiagent/model_runtime.py)
- 回测层：对策略/信号进行历史验证，输出指标与交易记录。[backtest\_engine.py](file:///d:/web%20development/quant/backtest_engine/backtest_engine.py) + 参数优化 [parameter\_optimizer.py](file:///d:/web%20development/quant/backtest_engine/parameter_optimizer.py)
- 执行层：将信号/建议对接到前端与台账，辅助手动下单与记录。[app/routes](file:///d:/web%20development/quant/app/routes) + 单页前端 [index.html](file:///d:/web%20development/quant/app/templates/index.html)
- 基础支撑层：配置、依赖、日志、脚本与运维工具。[config.py](file:///d:/web%20development/quant/config.py) + [requirements.txt](file:///d:/web%20development/quant/requirements.txt) + [scripts](file:///d:/web%20development/quant/scripts)

技术栈与版本（从代码与依赖文件抽取）

- 运行环境：Python 3.13（见 __pycache__ 标识）
- 后端框架：Flask 3.0.0（REST API + Blueprints）
- 前端：Vue3（嵌入 [index.html](file:///d:/web%20development/quant/app/templates/index.html)）
- 数据库：SQLite（本地文件 [quant\_data.db](file:///d:/web%20development/quant/data/tushare/db/quant_data.db)）
- 科学计算：Pandas 2.1.4、NumPy 1.26.2
- 金融因子：TA-Lib 0.4.28（talib-binary）
- 机器学习：XGBoost 2.1.4、scikit-learn 1.3.2
- 数据源：Tushare 1.4.5（pro\_api）

数据流说明（自证可复现路径）

- 数据层→因子层：data\_ingestion 将 Tushare 数据落库到 SQLite；因子层读取 [stock\_history\_data](file:///d:/web%20development/quant/app/schema.sql#L41-L86) 填充特征，输出因子矩阵。
- 因子层→模型层：模型训练/推理读取特征配置 [feature\_list.json](file:///d:/web%20development/quant/data/tushare/raw/feature_list.json)，计算特征并训练/加载模型（XGBoost）。
- 模型层→回测层：将模型信号或策略规则输入回测引擎，生成绩效指标与交易记录。
- 模型层/回测层→执行层：API 将分析结果返回前端，页面展示并写入台账（positions/trade\_records/settings 等）。

编写目的

- 帮助 AI 快速掌握模型的整体结构与数据流，定位具体代码文件与运行产物，从而支持后续文档与代码的精确读取与生成。

