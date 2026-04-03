# 量化交易系统 - 技术文档

## 📋 项目概述

**项目名称**：量化交易系统（手动买卖 + 实时数据接入）  
**开发模式**：模块化设计，独立封装，便于调试和迭代  
**技术栈**：Flask + Vue3 + SQLite + Tushare  
**开发周期**：分模块开发，每完成一个模块更新文档

---

## 🤖 Trae AI 使用指南

### ⚠️ 每次打开Trae必读

**重要提示**：每次打开Trae进行开发时，请务必让AI模型首先阅读以下内容：

1. **必须阅读的文档**：
   - 📖 **技术文档**：`TECHNICAL_DOCUMENTATION.md`（当前文件）
     - 包含系统架构、模块设计、开发进度
     - 了解已完成模块和待开发模块
     - 理解模块间的依赖关系
   - 📋 **模块文件开发记录**：位于技术文档的"开发进度记录"部分
     - 查看每个模块已开发的文件清单
     - 了解文件路径、类型、功能描述和状态
     - 方便代码回溯和维护

2. **阅读顺序**：
   - 第一步：阅读"项目概述"和"系统架构"
   - 第二步：阅读"开发进度记录"中的"模块文件开发记录"
   - 第三步：阅读"已完成模块"和"下一步计划"
   - 第四步：根据当前任务，阅读相关模块的详细设计

3. **开发前检查清单**：
   - [ ] 已阅读技术文档的"项目概述"和"系统架构"
   - [ ] 已查看"模块文件开发记录"，了解已完成模块
   - [ ] 已确认当前开发阶段和下一步计划
   - [ ] 已了解模块间的依赖关系
   - [ ] 已查看相关模块的详细设计文档

4. **为什么必须阅读**：
   - **避免重复开发**：了解已完成模块，避免重复实现相同功能
   - **理解架构设计**：理解模块间的依赖关系，确保开发顺序正确
   - **保持代码一致性**：遵循已建立的代码规范和目录结构
   - **快速定位问题**：了解文件位置和功能，快速定位代码问题
   - **提高开发效率**：基于已有设计，减少沟通和确认时间

5. **常见问题**：
   - ❌ **不阅读文档直接开发**：可能导致重复开发、架构冲突、代码不一致
   - ❌ **忽略依赖关系**：可能导致模块无法正常工作
   - ❌ **不遵循文件记录标准**：可能导致代码难以维护和回溯
   - ✅ **正确做法**：每次开发前先阅读技术文档，了解整体情况

### 📌 快速参考

**当前开发状态**：
- 已完成模块：模块1（策略配置中心）、模块2（数据接入与入库）、模块3（因子/信号链路）、模块5（回测与风险验证）、模块6（实盘监控与运维）、aiagent（机器学习训练与推理）
- 待开发模块：无
- 当前阶段：所有模块开发完成，准备进行系统测试和优化

**项目目录结构**：
- `app/` - Flask 后端 + 单页前端（index.html）
- `strategy_config/` - 策略配置中心（StrategyConfig）
- `data_ingestion/` - 数据采集入库（TuShare → SQLite）
- `signal_engine/` - 因子与信号引擎（评分/阈值/过滤/触发）
- `backtest_engine/` - 回测与优化引擎（撮合/指标/优化/评估）
- `live_ops/` - 实盘监控与运维（监控循环/异常/日志/紧急处理）
- `aiagent/` - 机器学习量化模型系统
- `data/` - SQLite/模型/状态文件
- `logs/` - 运行日志
- `scripts/` - 批处理脚本
- `TECHNICAL_DOCUMENTATION.md` - 技术文档（当前文件）

说明：历史上曾存在 `module4/` 作为“主应用目录”，当前已迁移为 `app/`（保留文档中部分 module4 记录用于追溯迁移过程）。

**重要提醒**：每次开发新模块时，请在"模块文件开发记录"中更新文件清单！

### 📝 开发规范

**开发前必读**：
1. **完整阅读技术文档**
   - 每次AI编程前，必须完整阅读技术文档
   - 了解项目的完整逻辑和架构设计
   - 理解当前编写进度和已完成模块
   - 确认下一步开发计划

**开发中必做**：
2. **模块完成后及时记录**
   - 每次完成某一模块的编程时，必须及时记录到技术文档
   - 更新"模块文件开发记录"部分，添加新模块的文件清单
   - 记录文件路径、类型、功能描述和状态
   - 确保文档与代码同步更新

3. **文件修改必须记录**
   - 每次对某文件进行了修改（新增、删除、重命名），必须记入技术文档
   - 在"开发日志"中记录修改原因和影响
   - 更新"模块文件开发记录"中的文件状态
   - 保持文档的准确性和时效性

**开发流程**：
```
开始开发 → 阅读技术文档 → 理解需求和架构 → 编写代码
    ↓
完成模块 → 更新技术文档 → 记录文件清单 → 记录开发日志
    ↓
文件修改 → 记录修改内容 → 更新文档 → 同步状态
```

**文档更新时机**：
- ✅ **模块开发完成**：立即更新"模块文件开发记录"
- ✅ **文件新增/删除**：立即更新文件清单和状态
- ✅ **文件修改**：立即记录修改内容和原因
- ✅ **架构调整**：立即更新"系统架构"和"项目目录结构"
- ✅ **遇到问题**：立即记录到"遇到的问题"部分

**文档维护原则**：
- 📌 **实时性**：代码变更后立即更新文档，不要拖延
- 📌 **准确性**：确保文档内容与实际代码一致
- 📌 **完整性**：记录所有重要变更，包括文件、功能、问题
- 📌 **可追溯**：保持历史记录，方便回溯和问题定位

---

## 🏗️ 系统架构

### 整体架构图
```
┌─────────────────────────────────────────────────────────┐
│                   前端层 (Vue3)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │信号展示  │  │策略配置  │  │回测结果  │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────┘
                      ↕ API调用
┌─────────────────────────────────────────────────────────┐
│                   后端层 (Flask)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │配置中心 │  │数据接入 │  │信号引擎 │  │
│  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │API/前端  │  │回测优化 │  │实盘运维 │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────┘
                      ↕ 数据存取
┌─────────────────────────────────────────────────────────┐
│                 数据层 (SQLite)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │实时数据  │  │历史数据  │  │交易记录  │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 模块间数据流
```
data_ingestion(数据) → signal_engine(信号) → app(输出)
    ↓              ↓              ↓
backtest_engine(回测)    strategy_config(配置)    live_ops(运维)
    ↓              ↓              ↓
  数据库 ←──── 数据库 ←──── 数据库
```

### 2.2. 后端架构：模块化与应用工厂

为了提高代码的可维护性和可扩展性，后端采用了基于 **Flask Blueprints** 的模块化架构和**应用工厂（Application Factory）**模式。

- **应用工厂 (`create_app`)**: 在 `app/__init__.py` 中定义，负责创建和配置Flask应用实例。这种模式有助于集中管理应用的配置、扩展和蓝图注册。
- **蓝图 (Blueprints)**: 每个核心功能模块（如数据、回测、策略）都有自己独立的蓝图文件，存放在 `app/routes/` 目录下。这使得路由和业务逻辑更加清晰，易于管理。

### 2.3. 项目目录结构

```
quant/
├── app/                  # Flask应用核心目录
│   ├── __init__.py       # 应用工厂 (create_app)
│   ├── routes/           # 存放所有蓝图
│   │   ├── __init__.py
│   │   ├── data.py       # 数据相关API
│   │   ├── backtest.py   # 回测相关API
│   │   └── ...
│   ├── db.py             # 数据库管理
│   ├── utils.py          # 通用工具
│   ├── static/           # 静态文件
│   └── templates/        # HTML模板
├── strategy_config/      # 策略配置中心
├── data_ingestion/       # 数据采集入库
├── signal_engine/        # 因子与信号引擎
├── backtest_engine/      # 回测与优化引擎
├── live_ops/             # 实盘监控与运维
├── aiagent/              # 机器学习量化模型系统
├── data/                 # 数据/模型/状态文件（默认 data/tushare/*）
├── logs/                 # 运行日志
├── scripts/              # 拉数/训练/维护脚本
├── tests/                # 测试目录
├── config.py             # 应用配置
├── run.py                # 应用启动脚本
├── TECHNICAL_DOCUMENTATION.md
└── OPTIMIZATION_DOCUMENTATION.md
```

### 目录结构说明
- **TECHNICAL_DOCUMENTATION.md**：项目技术文档，记录系统架构、模块设计、开发进度
- **strategy_config/**：策略配置中心（StrategyConfig，读写 strategy_config.json）
- **data_ingestion/**：数据采集入库（TuShare → 清洗 → SQLite）
- **signal_engine/**：因子与信号引擎（评分、阈值、过滤、触发检查）
- **前端页面**：位于 `app/templates/index.html`（Vue3 + Bootstrap 单页）
- **backtest_engine/**：回测与优化引擎（撮合、绩效指标、参数优化、风险/过拟合评估）
- **live_ops/**：实盘监控与运维（监控循环、异常检测、日志、紧急处理）
- **aiagent/**：机器学习量化模型系统，提供数据准备、模型训练、模型管理和预测服务
- **data/**：SQLite 数据库、模型产物、运行状态文件等
- **logs/**：运行日志输出目录
- **scripts/**：批处理与运维脚本

### 模块间依赖关系（当前实现）
- Flask 层（`app/routes/*`）作为 API 外观层：读取配置（strategy_config）+ 读写 DB（app/db.py & data_ingestion）+ 调用策略/回测/监控模块（signal_engine/backtest_engine/live_ops）。
- signal_engine（因子/信号）被 strategy 路由与 backtest 路由复用。
- aiagent（ML）被训练路由（ml.py）与信号/回测路由（strategy.py/backtest.py）复用（加载模型 bundle、计算特征、predict_proba）。

---

## 🔗 量化过程链路图（端到端）

下面是当前项目“从数据到实盘”的完整链路（同时标注主要目录/文件落点）。

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ 0. 前端入口（单页）                                                            │
│    app/templates/index.html  (Vue3 + Bootstrap)                                │
└───────────────┬───────────────────────────────────────────────────────────────┘
                │ HTTP API
┌───────────────▼───────────────────────────────────────────────────────────────┐
│ 1. 后端 API（Flask Blueprints）                                                │
│    app/__init__.py 注册蓝图；app/routes/* 对外提供接口                          │
│                                                                               │
│   - 数据/Token/指数/标的搜索：app/routes/data.py                                │
│   - 策略配置/信号分析/建议下单：app/routes/strategy.py                          │
│   - 回测/优化/风控/过拟合：app/routes/backtest.py                               │
│   - 模型训练/状态/导入导出：app/routes/ml.py                                    │
│   - 实盘监控/日志/异常：app/routes/monitor.py                                   │
│   - 持仓/交易记录/资金：app/routes/trading.py                                   │
└───────────────┬───────────────────────────────────────────────────────────────┘
                │ 读写配置 / 读写 DB / 调用模块
┌───────────────▼───────────────────────────────────────────────────────────────┐
│ 2. 配置层（策略参数的“单一事实来源”）                                           │
│    strategy_config.json  ←→  strategy_config/strategy_config.py (StrategyConfig)│
└───────────────┬───────────────────────────────────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────────────────────────────────┐
│ 3. 数据层（SQLite + TuShare）                                                   │
│    SQLite: data/tushare/db/quant_data.db                                       │
│    数据采集：data_ingestion/data_collector.py + data_ingestion/db_init.py       │
└───────────────┬───────────────────────────────────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────────────────────────────────┐
│ 4. ML 训练链路（XGBoost 三分类）                                                │
│    aiagent/ml_pipeline.py(train_ml_model)                                      │
│    特征：aiagent/ml_features.py + data/tushare/raw/feature_list.json           │
│    产物：data/tushare/models/<model>/<version>/model_weights.pkl                │
│    状态：data/tushare/state/ml_train_status.json                                │
└───────────────┬───────────────────────────────────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────────────────────────────────┐
│ 5. 信号分析链路（当前时点）                                                     │
│    app/routes/strategy.py + signal_engine/* + aiagent/model_runtime.py          │
└───────────────┬───────────────────────────────────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────────────────────────────────┐
│ 6. 回测验证链路（历史区间）                                                     │
│    app/routes/backtest.py → backtest_engine/backtest_engine.py                  │
└───────────────┬───────────────────────────────────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────────────────────────────────┐
│ 7. 实盘监控链路（运行/运维）                                                    │
│    app/routes/monitor.py → live_ops/realtime_monitor.py                          │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ 文件与目录说明（索引版）

### A. 入口与配置
- `run.py`：Flask 服务启动入口。
- `config.py`：全局配置（DB 路径、日志路径等）。
- `strategy_config.json`：策略配置持久化（策略类型、阈值、仓位限制、模型路径等）。
- `requirements.txt`：依赖安装列表。

### B. Web 层（Flask + 单页前端）
- `app/__init__.py`：应用工厂，注册所有蓝图。
- `app/templates/index.html`：单页前端（数据监控/策略配置/回测/信号/监控/日志/紧急处理）。
- `app/db.py`：SQLite 连接管理 + settings 读写。
- `app/routes/`：
  - `data.py`：TuShare 指数/标的搜索/数据接口（含缓存）。
  - `strategy.py`：信号分析链与策略配置接口。
  - `backtest.py`：回测、优化、风险测试、过拟合检查接口。
  - `ml.py`：训练/状态/导入导出模型接口。
  - `monitor.py`：监控状态/绩效/异常/日志/紧急处理接口。
  - `trading.py`：持仓、交易记录、资金台账接口。

### C. 业务模块
- `strategy_config/`：StrategyConfig（读写 strategy_config.json、默认值、校验）。
- `data_ingestion/`：TuShare 拉数/清洗/入库（SQLite）。
- `signal_engine/`：因子计算、信号生成、过滤与触发逻辑（策略与回测共用）。
- `backtest_engine/`：回测引擎与评估（撮合、绩效指标、参数优化）。
- `live_ops/`：实盘监控与运维（监控循环、异常聚合、日志支撑）。

### D. 机器学习子系统（aiagent）
- `aiagent/ml_pipeline.py`：训练入口（批量取数→特征→标签→滚动训练→保存）。
- `aiagent/ml_features.py`：特征工程（从行情/估值/资金流派生特征列）。
- `aiagent/model_runtime.py`：加载模型 bundle 并推理（predict_proba）。
- `aiagent/feature_spec.py`：读取 feature_list.json（决定特征列集合）。

### E. 数据/模型/状态与日志
- `data/tushare/db/quant_data.db`：SQLite 主库（行情、台账、settings 等）。
- `data/tushare/models/`：训练/导入模型产物（按版本目录）。
- `data/tushare/state/`：训练状态/批处理状态等。
- `logs/`：运行日志输出。

### F. 脚本与测试
- `scripts/`：拉数/训练/维护等脚本入口。
- `tests/`：单元测试目录。

---

## 📦 模块：strategy_config（策略配置中心）

### 模块职责
- 明确策略核心逻辑、适用范围和约束条件
- 为后续模块提供设计依据
- 可独立修改策略类型、目标和约束
- 无需依赖其他模块

### 核心功能
1. **策略类型定义**
   - **类型A：传统策略（Trend Following / Mean Reversion）**
     - 趋势跟踪策略：基于均线/突破规则生成交易信号
     - 均值回归策略：基于偏离均值的回归规则生成交易信号
   - **类型B：机器学习策略（ML Model）**
     - `strategy_type="ml_model"`
     - 数据驱动的预测模型，必须按时序拆分训练/验证/测试集
     - 输出：模型预测得分 → 排序 → 生成信号

2. **机器学习策略的本地训练与部署规范（流程预留）**
   - 数据准备：历史数据按日期排序 → 特征计算 → 构建标签 → 时序划分（训练70%/验证15%/测试15%）
   - 训练：训练集训练 + 验证集早停与调参（禁止测试集参与训练/调参）
   - 部署：本地持久化模型文件（版本化）+ 统一预测接口（输入行情→特征→缺失值填充→预测得分）
   - 页面调用：模型未训练时禁止进入回测/信号流程；模型过期提示但允许继续

2. **适用范围划定**
   - 标的界定：A股市场、沪深300成分股、ETF
   - 周期界定：分钟级+日线级
   - 市场环境适配：牛市、震荡市、熊市

3. **核心目标设定**
   - 收益目标：年化15%-25%
   - 风险目标：最大回撤≤10%、单次亏损≤5%
   - 操作目标：每日≤10次、每周≤50次

4. **交易约束明确**
   - 仓位约束：单票≤10%、总仓位≤80%
   - 交易频率约束：同一标的每日≤2次
   - 流动性约束：近5日平均成交量≥5000万
   - 其他约束：禁止ST股、涨跌停限制

### 技术实现（配置结构）
```python
# 文件位置：strategy_config/strategy_config.py

default_config = {
    "strategy_type": "ml_model",
    "factor_weights": {"valuation": 0.3, "trend": 0.4, "fund": 0.3},
    "ml_model": {"status": "untrained", "last_trained_at": "", "model_path": ""},
    "signal_thresholds": {"buy_score": 8.0, "sell_score": 3.0, "buy_prob": 0.7, "sell_prob": 0.7},
    "trend_following_params": {"short_ma": 10, "long_ma": 30, "breakout_window": 20, "confirm_days": 1},
    "mean_reversion_params": {"lookback": 20, "entry_z": 2.0, "exit_z": 0.5, "max_holding_days": 20},
    "position_limits": {"single_max": 0.1, "total_max": 0.8, "daily_trades": 10, "weekly_trades": 50, "symbol_daily_trades": 2},
    "targets": {"annual_return": 0.20, "max_drawdown": 0.10, "single_loss": 0.05, "daily_loss": 0.02},
    "scope": {"market": "A股", "symbols": ["沪深300成分股", "ETF"], "timeframe": ["分钟级", "日线级"], "market_environment": ["牛市", "震荡市", "熊市"]}
}
```

### 策略开发流程控制（2026-03-27）
- 策略开发被固化为三步：策略配置 → 信号验证 → 回测验证
- “保存并应用”后锁定策略配置，后续步骤不允许再更改策略；需要改策略必须“返回修改策略”，并清空信号与回测结果
- 机器学习策略模型状态未就绪（非 ready/stale）时，回测/优化会提示并终止流程

### API接口
```python
# GET /api/strategy/config - 获取策略配置
# POST /api/strategy/config - 更新策略配置
# GET /api/strategy/params - 获取策略参数
# POST /api/strategy/params - 更新策略参数
```

### 前端页面
- 策略配置页面：调整因子权重、信号阈值
- 参数设置页面：修改交易约束、目标设定
- 策略说明页面：展示策略逻辑和适用范围

---

## 📦 模块：data_ingestion（数据采集入库）

### 模块职责
- 实时股市数据的采集、清洗、存储和更新
- 不参与策略逻辑和信号生成
- 独立运行，后期可单独调试数据源、更新频率、数据清洗规则
- 为 strategy_config、signal_engine、backtest_engine 提供数据支撑

### 核心功能
1. **实时数据采集子模块**
   - 接入分钟级实时行情（1分钟/次更新）
   - 支持同时采集多支标的数据
   - 包含股票代码、最新价、实时成交量、成交额
   - 支持切换数据源、新增/删除标的

2. **数据清洗子模块**
   - 剔除异常值（停牌、涨跌停）
   - 处理复权
   - 按时间戳对齐数据

3. **数据存储与更新子模块**
   - 搭建本地数据库，存储实时数据和历史数据
   - 保障数据可追溯
   - 为 aiagent 训练、signal_engine 因子计算、backtest_engine 回测提供数据支撑

4. **数据校验子模块**
   - 实时校验数据完整性、无延迟
   - 出现异常触发提醒
   - 数据补全机制

### 技术实现
```python
# 文件位置：data_ingestion/data_collector.py

class RealTimeDataCollector:
    def __init__(self, db_path: str = 'quant_data.db'):
        self.db_path = db_path
        self.token = None
        self.pro = None
        self.symbols = []
        
    def set_token(self, token: str):
        self.token = token
        try:
            self.pro = ts.pro_api(token)
            logger.info("Tushare API初始化成功")
        except Exception as e:
            logger.error(f"Tushare API初始化失败: {e}")
            self.pro = None
    
    def set_symbols(self, symbols: List[str]):
        self.symbols = symbols
        logger.info(f"设置监控标的: {symbols}")
    
    def collect_realtime_data(self) -> Dict[str, pd.DataFrame]:
        if not self.pro:
            logger.error("Tushare API未初始化")
            return {}
        
        if not self.symbols:
            logger.warning("未设置监控标的")
            return {}
        
        results = {}
        today = datetime.now().strftime('%Y%m%d')
        
        for symbol in self.symbols:
            try:
                df = self.pro.daily(ts_code=symbol, 
                                   start_date=today,
                                   end_date=today)
                
                if len(df) > 0:
                    cleaned_df = self.clean_data(df, symbol)
                    self.store_data(symbol, cleaned_df)
                    results[symbol] = cleaned_df
                    logger.info(f"成功采集{symbol}数据: {len(df)}条")
                else:
                    logger.warning(f"{symbol}无数据")
                    
            except Exception as e:
                logger.error(f"采集{symbol}数据失败: {e}")
        
        return results
    
    def clean_data(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if df.empty:
            return df
        
        cleaned_df = df.copy()
        
        cleaned_df = cleaned_df.dropna()
        
        cleaned_df = cleaned_df[
            (cleaned_df['high'] >= cleaned_df['low']) &
            (cleaned_df['close'] >= cleaned_df['low']) &
            (cleaned_df['close'] <= cleaned_df['high'])
        ]
        
        cleaned_df = cleaned_df[
            (cleaned_df['vol'] > 0) &
            (cleaned_df['amount'] > 0)
        ]
        
        cleaned_df = cleaned_df.sort_values('trade_date')
        cleaned_df = cleaned_df.reset_index(drop=True)
        
        logger.info(f"{symbol}数据清洗完成: {len(df)} -> {len(cleaned_df)}")
        return cleaned_df
    
    def store_data(self, symbol: str, data: pd.DataFrame):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for _, row in data.iterrows():
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_realtime_data 
                    (symbol, timestamp, price, volume, amount, open_price, high_price, low_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    row['trade_date'],
                    row['close'],
                    row['vol'],
                    row['amount'],
                    row['open'],
                    row['high'],
                    row['low']
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"{symbol}实时数据存储成功: {len(data)}条")
            
        except Exception as e:
            logger.error(f"存储{symbol}实时数据失败: {e}")
    
    def validate_data(self, symbol: str) -> Dict[str, any]:
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = '''
                SELECT COUNT(*) as count,
                       MIN(timestamp) as min_time,
                       MAX(timestamp) as max_time
                FROM stock_realtime_data
                WHERE symbol = ?
            '''
            df = pd.read_sql_query(query, conn, params=(symbol,))
            
            if len(df) > 0:
                result = {
                    'symbol': symbol,
                    'data_count': int(df.iloc[0]['count']),
                    'min_time': df.iloc[0]['min_time'],
                    'max_time': df.iloc[0]['max_time'],
                    'is_valid': True
                }
                
                if result['data_count'] == 0:
                    result['is_valid'] = False
                    result['message'] = '无数据'
                else:
                    max_time = pd.to_datetime(result['max_time'])
                    time_diff = (datetime.now() - max_time).total_seconds()
                    
                    if time_diff > 3600:
                        result['is_valid'] = False
                        result['message'] = f'数据延迟{int(time_diff/60)}分钟'
                    else:
                        result['message'] = '数据正常'
                
                conn.close()
                return result
            else:
                conn.close()
                return {
                    'symbol': symbol,
                    'data_count': 0,
                    'is_valid': False,
                    'message': '无数据'
                }
                
        except Exception as e:
            logger.error(f"验证{symbol}数据失败: {e}")
            return {
                'symbol': symbol,
                'is_valid': False,
                'message': f'验证失败: {str(e)}'
            }
```

### API接口
```python
# GET /api/data/symbols - 获取监控标的列表
# POST /api/data/symbols - 添加/删除监控标的
# GET /api/data/realtime?symbol=xxx&limit=10 - 获取实时数据
# GET /api/data/history?symbol=xxx&start_date=xxx&end_date=xxx - 获取历史数据
# POST /api/data/collect - 手动触发数据采集
# GET /api/data/validate/<symbol> - 验证数据完整性
```

### 数据库表结构
```sql
CREATE TABLE stock_realtime_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    price REAL NOT NULL,
    volume REAL NOT NULL,
    amount REAL NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);

CREATE TABLE stock_history_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume REAL,
    amount REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, trade_date)
);

CREATE TABLE monitored_symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    symbol_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

CREATE INDEX idx_realtime_symbol ON stock_realtime_data(symbol);
CREATE INDEX idx_realtime_timestamp ON stock_realtime_data(timestamp);
CREATE INDEX idx_history_symbol ON stock_history_data(symbol);
CREATE INDEX idx_history_date ON stock_history_data(trade_date);
```

### 前端页面
- 数据监控页面：实时显示多标的数据
- 标的管理页面：添加/删除监控标的
- 数据状态页面：显示数据源状态、数据延迟情况

---

## 📦 模块3：策略逻辑拆解模块

### 模块职责
- 基于实时数据，将"多因子+机器学习"综合策略逻辑拆解为机器可执行的规则
- 不涉及交易接口，仅输出信号逻辑
- 可独立修改策略规则、参数，无需改动数据和信号输出模块

### 核心功能
1. **核心信号子模块**
   - 因子选取与权重设定：估值、趋势、资金三因子
   - 因子标准化处理：归一化至0-1区间
   - 权重分配：估值30%、趋势40%、资金30%
   - 信号生成规则：综合评分+机器学习概率双重判断

2. **信号过滤子模块**
   - 趋势过滤规则：大盘趋势、个股趋势
   - 风险过滤规则：ST股、停牌、涨跌停、流动性
   - 时效性过滤规则：信号有效期10分钟

3. **交易触发逻辑子模块**
   - 买入触发条件：综合评分≥8分、通过所有过滤、仓位未达上限
   - 卖出触发条件：综合评分≤3分、止盈≥10%、止损≥5%
   - 信号优先级：止损>止盈>大盘风险>个股利空>综合评分
   - 手动适配优化：延迟提醒、建议价格区间

### 技术实现
```python
# 文件位置：signal_engine/signal_generator.py

import pandas as pd
import numpy as np
import talib

class SignalGenerator:
    def __init__(self, strategy_config):
        self.config = strategy_config
        
    def calculate_factors(self, data):
        """计算多因子"""
        factors = {}
        
        # 估值因子
        factors['pe'] = data['pe'].iloc[-1]
        factors['pb'] = data['pb'].iloc[-1]
        
        # 趋势因子
        factors['macd'] = talib.MACD(data['close'])[0][-1]
        factors['ma5'] = talib.MA(data['close'], 5)[-1]
        factors['ma10'] = talib.MA(data['close'], 10)[-1]
        
        # 资金因子
        factors['volume_ratio'] = data['volume'].iloc[-1] / data['volume'].mean()
        factors['fund_flow'] = self.calculate_fund_flow(data)
        
        # 因子归一化
        factors = self.normalize_factors(factors)
        
        # 计算综合评分
        score = self.calculate_score(factors)
        
        return factors, score
    
    def generate_signal(self, factors, score, ml_prediction):
        """生成交易信号"""
        # 双重阈值判断
        if score >= self.config.signal_thresholds['buy_score'] and ml_prediction['buy_prob'] >= self.config.signal_thresholds['buy_prob']:
            return 'buy'
        elif score <= self.config.signal_thresholds['sell_score'] and ml_prediction['sell_prob'] >= self.config.signal_thresholds['sell_prob']:
            return 'sell'
        else:
            return 'hold'
```

### API接口
```python
# GET /api/signal/current - 获取当前信号
# POST /api/signal/generate - 手动生成信号
# GET /api/signal/history - 获取历史信号
```

### 前端页面
- 信号监控页面：实时显示买卖信号
- 因子分析页面：展示各因子值和权重
- 信号历史页面：查看历史信号记录

---

## 📦 模块4：信号输出模块

### 模块职责
- 提供Web界面，展示信号、数据和回测结果
- 支持手动买卖操作
- 集成所有模块的API接口
- 提供策略配置和参数调整功能

### 核心功能
1. **前端展示子模块**
   - 实时信号展示：买入/卖出/持有
   - 数据监控：实时行情、历史数据
   - 回测结果展示：绩效指标、资金曲线

2. **手动操作子模块**
   - 手动买入：输入标的、价格、数量
   - 手动卖出：选择持仓、输入价格
   - 交易记录：保存所有手动交易

3. **配置管理子模块**
   - 策略配置：调整因子权重、信号阈值
   - 数据源配置：设置API Token、监控标的
   - 系统设置：日志级别、数据刷新频率

### 技术实现
```python
# 文件位置：module4/app.py

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/signal/current')
def get_current_signal():
    # 获取当前信号
    return jsonify(signal)

@app.route('/api/trade/buy', methods=['POST'])
def manual_buy():
    # 手动买入
    data = request.json
    # 处理买入逻辑
    return jsonify({'success': True})

@app.route('/api/trade/sell', methods=['POST'])
def manual_sell():
    # 手动卖出
    data = request.json
    # 处理卖出逻辑
    return jsonify({'success': True})
```

### API接口
```python
# GET / - 主页面
# GET /api/signal/current - 获取当前信号
# POST /api/trade/buy - 手动买入
# POST /api/trade/sell - 手动卖出
# GET /api/trade/history - 交易历史
# POST /api/strategy/config - 更新策略配置
# POST /api/data/config - 更新数据源配置
```

### 前端页面
- 主页面：实时信号、数据监控、回测结果
- 交易页面：手动买卖操作
- 配置页面：策略配置、数据源配置
- 历史页面：交易记录、信号历史

---

## 📦 模块5：回测与风险验证模块

### 模块职责
- 基于历史数据，验证策略有效性
- 评估策略绩效指标
- 优化策略参数
- 检测过拟合风险

### 核心功能
1. **回测引擎子模块**
   - 数据加载：从数据库加载历史数据
   - 数据划分：训练集70%、验证集20%、测试集10%
   - 回测执行：模拟交易、计算收益
   - 绩效计算：总收益率、年化收益率、最大回撤、夏普比率、胜率、盈亏比

2. **参数优化子模块**
   - 网格搜索：遍历参数组合
   - 遗传算法：智能优化参数
   - 因子权重优化：调整估值、趋势、资金因子权重
   - 信号阈值优化：调整买入/卖出评分和概率阈值

3. **风险测试子模块**
   - VaR计算：风险价值（95%、99%置信度）
   - CVaR计算：条件风险价值
   - 压力测试：极端场景（暴跌、连续下跌、高波动）
   - 市场环境测试：牛市、震荡市、熊市
   - 流动性测试：交易量不足情况

4. **过拟合检查子模块**
   - 训练测试差异：对比训练集和测试集表现
   - 参数敏感性：检查参数微小变化对结果的影响
   - 未来数据泄露：检测是否使用了未来数据
   - 策略复杂度：评估参数数量和规则复杂度

### 技术实现
```python
# 文件位置：backtest_engine/backtest_engine.py

class BacktestEngine:
    def __init__(self, db_path: str = 'quant_data.db'):
        self.db_path = db_path
        self.transaction_cost = 0.003  # 0.3%手续费
        self.initial_capital = 100000  # 初始资金10万
        
    def load_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从数据库加载历史数据"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT * FROM stock_history_data
            WHERE symbol = ? AND trade_date >= ? AND trade_date <= ?
            ORDER BY trade_date ASC
        '''
        df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))
        conn.close()
        return df
    
    def split_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """划分数据集：训练集70%、验证集20%、测试集10%"""
        n = len(df)
        train_end = int(n * 0.7)
        val_end = int(n * 0.9)
        
        train_df = df.iloc[:train_end]
        val_df = df.iloc[train_end:val_end]
        test_df = df.iloc[val_end:]
        
        return train_df, val_df, test_df
    
    def calculate_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """计算绩效指标"""
        total_return = (1 + returns).prod() - 1
        annual_return = (1 + returns.mean()) ** 252 - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        drawdown = (cumulative - cumulative.cummax()) / cumulative.cummax()
        max_drawdown = drawdown.min()
        
        # 胜率和盈亏比
        win_rate = (returns > 0).mean()
        avg_profit = returns[returns > 0].mean() if (returns > 0).any() else 0
        avg_loss = returns[returns < 0].mean() if (returns < 0).any() else 0
        profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio
        }
```

### API接口
```python
# POST /api/backtest/simple - 执行简单回测
# POST /api/backtest/optimize - 参数优化
# POST /api/backtest/risk - 风险测试
# POST /api/backtest/overfitting - 过拟合检查
```

### 前端页面
- 回测页面：选择标的、时间范围、执行回测
- 结果页面：展示绩效指标、资金曲线
- 优化页面：参数优化、结果对比
- 风险页面：风险测试、VaR/CVaR展示

---

## 📦 模块6：实盘监控与运维迭代模块

### 模块职责
- 实时监控交易执行情况
- 记录交易日志和绩效
- 系统异常处理
- 策略迭代优化

### 核心功能
1. **实时监控子模块**
   - 交易监控：实时跟踪交易执行
   - 绩效监控：实时计算收益、回撤
   - 异常监控：检测系统异常、数据异常
   - 告警机制：异常情况自动告警

2. **交易记录子模块**
   - 交易日志：记录所有交易
   - 绩效记录：记录每日收益、回撤
   - 异常记录：记录系统异常、处理结果

3. **迭代优化子模块**
   - 绩效分析：分析策略表现
   - 参数调整：根据市场变化调整参数
   - 模型更新：定期重新训练机器学习模型

4. **紧急处理子模块**
   - 止损处理：触发止损时自动卖出
   - 止盈处理：触发止盈时自动卖出
   - 系统恢复：异常后自动恢复

### 技术实现
```python
# 文件位置：live_ops/realtime_monitor.py

class RealtimeMonitor:
    def __init__(self):
        self.is_running = False
        self.positions = {}
        
    def start_monitoring(self):
        """启动实时监控"""
        self.is_running = True
        while self.is_running:
            # 监控交易执行
            self.monitor_trades()
            
            # 监控绩效
            self.monitor_performance()
            
            # 监控异常
            self.monitor_anomalies()
            
            time.sleep(60)  # 每分钟检查一次
    
    def monitor_trades(self):
        """监控交易执行"""
        # 检查待执行交易
        # 更新持仓
        pass
    
    def monitor_performance(self):
        """监控绩效"""
        # 计算当前收益
        # 计算当前回撤
        pass
    
    def monitor_anomalies(self):
        """监控异常"""
        # 检查数据异常
        # 检查系统异常
        pass
```

### API接口
```python
# GET /api/monitor/status - 获取监控状态
# GET /api/monitor/performance - 获取实时绩效
# GET /api/monitor/trades - 获取交易记录
# POST /api/monitor/emergency - 紧急处理
```

### 前端页面
- 监控页面：实时监控交易和绩效
- 日志页面：查看交易日志、异常记录
- 告警页面：查看告警信息
- 迭代页面：查看优化建议、执行优化

---

## 📝 开发进度记录

### 📋 模块文件开发记录

**记录标准**：
- 每次开发新模块时，记录所有编写的文件及其功能
- 文件路径采用相对于项目根目录的格式（如 `data_ingestion/data_collector.py`）
- 标注文件创建/修改日期和主要功能
- 方便后续代码回溯和维护

#### 模块1：策略顶层设计模块
**开发日期**：2026-03-25

| 文件路径 | 文件类型 | 功能描述 | 状态 |
|---------|---------|---------|------|
| `strategy_config/__init__.py` | 模块导出 | 导出StrategyConfig类 | ✅ 完成 |
| `strategy_config/strategy_config.py` | 核心类 | StrategyConfig类：策略配置管理、参数验证、配置持久化 | ✅ 完成 |

**API接口**（已集成到module4/app.py）：
- `GET /api/strategy/config` - 获取策略配置
- `POST /api/strategy/config` - 更新策略配置
- `GET /api/strategy/params` - 获取策略参数
- `POST /api/strategy/params` - 更新策略参数
- `GET /api/strategy/validate` - 验证策略配置
- `POST /api/strategy/reset` - 重置策略配置为默认值

#### 模块3：策略逻辑拆解模块
**开发日期**：2026-03-25

| 文件路径 | 文件类型 | 功能描述 | 状态 |
|---------|---------|---------|------|
| `signal_engine/__init__.py` | 模块导出 | 导出FactorCalculator、SignalGenerator、SignalFilter、TradeTrigger | ✅ 完成 |
| `signal_engine/factor_calculator.py` | 核心类 | FactorCalculator类：估值因子、趋势因子、资金因子计算、因子归一化、综合评分 | ✅ 完成 |
| `signal_engine/signal_generator.py` | 核心类 | SignalGenerator类：信号生成、置信度计算、批量信号生成 | ✅ 完成 |
| `signal_engine/signal_filter.py` | 核心类 | SignalFilter类：趋势过滤、风险过滤、时效性过滤 | ✅ 完成 |
| `signal_engine/trade_trigger.py` | 核心类 | TradeTrigger类：买入触发检查、卖出触发检查、仓位限制、交易记录 | ✅ 完成 |

**API接口**（已集成到module4/app.py）：
- `POST /api/factor/calculate` - 计算因子
- `POST /api/signal/generate` - 生成交易信号
- `POST /api/signal/filter` - 过滤信号
- `POST /api/trade/check/buy` - 检查买入触发
- `POST /api/trade/check/sell` - 检查卖出触发

#### 模块2：实时数据接入与处理模块
**开发日期**：2026-03-24

| 文件路径 | 文件类型 | 功能描述 | 状态 |
|---------|---------|---------|------|
| `data_ingestion/__init__.py` | 模块导出 | 导出RealTimeDataCollector和数据库相关函数 | ✅ 完成 |
| `data_ingestion/data_collector.py` | 核心类 | RealTimeDataCollector类：数据采集、清洗、存储、验证 | ✅ 完成 |
| `data_ingestion/db_init.py` | 数据库 | 数据库表初始化、监控标的管理 | ✅ 完成 |

**已删除的旧代码**（2026-03-24清理）：
- `data_ingestion/akshare_collector.py` - AkShare数据采集器
- `data_ingestion/baostock_collector.py` - Baostock数据采集器
- `data_ingestion/data_cleaner.py` - 数据清洗
- `data_ingestion/data_collector_simple.py` - 模拟数据采集器
- `data_ingestion/data_storage.py` - 数据存储
- `data_ingestion/data_validator.py` - 数据验证

#### 模块5：回测与风险验证模块
**开发日期**：2026-03-24

| 文件路径 | 文件类型 | 功能描述 | 状态 |
|---------|---------|---------|------|
| `backtest_engine/__init__.py` | 模块导出 | 导出BacktestEngine、ParameterOptimizer、RiskTester、OverfittingChecker | ✅ 完成 |
| `backtest_engine/backtest_engine.py` | 核心类 | BacktestEngine类：数据加载、回测执行、绩效计算、归因分析 | ✅ 完成 |
| `backtest_engine/parameter_optimizer.py` | 核心类 | ParameterOptimizer类：网格搜索、遗传算法、参数优化 | ✅ 完成 |
| `backtest_engine/risk_tester.py` | 核心类 | RiskTester类：VaR/CVaR计算、压力测试、市场环境测试、流动性测试 | ✅ 完成 |
| `backtest_engine/overfitting_checker.py` | 核心类 | OverfittingChecker类：训练测试差异、参数敏感性、未来数据泄露、策略复杂度检查 | ✅ 完成 |

#### 模块6：实盘监控与运维迭代模块
**开发日期**：2026-03-25

| 文件路径 | 文件类型 | 功能描述 | 状态 |
|---------|---------|---------|------|
| `live_ops/__init__.py` | 模块导出 | 导出RealtimeMonitor、TradeLogger、IterationOptimizer、EmergencyHandler | ✅ 完成 |
| `live_ops/realtime_monitor.py` | 核心类 | RealtimeMonitor类：实时监控交易、绩效、异常，告警机制 | ✅ 完成 |
| `live_ops/trade_logger.py` | 核心类 | TradeLogger类：交易日志、绩效记录、异常记录、统计分析 | ✅ 完成 |
| `live_ops/iteration_optimizer.py` | 核心类 | IterationOptimizer类：绩效分析、参数调整、模型更新、优化建议 | ✅ 完成 |
| `live_ops/emergency_handler.py` | 核心类 | EmergencyHandler类：止损、止盈、日亏损限制、总亏损限制、紧急操作 | ✅ 完成 |

**API接口**（已集成到module4/app.py）：
- `GET /api/monitor/status` - 获取监控状态
- `GET /api/monitor/performance` - 获取绩效历史
- `GET /api/monitor/anomalies` - 获取异常历史
- `GET /api/logger/trades` - 获取交易日志
- `GET /api/logger/performance` - 获取绩效日志
- `GET /api/logger/anomalies` - 获取异常日志
- `GET /api/logger/statistics` - 获取交易统计
- `GET /api/logger/summary` - 获取绩效汇总
- `POST /api/optimizer/analyze` - 绩效分析
- `POST /api/optimizer/suggest` - 参数调整建议
- `POST /api/optimizer/optimize` - 参数优化
- `POST /api/optimizer/model/check` - 检查模型更新
- `POST /api/emergency/check/stoploss` - 检查止损
- `POST /api/emergency/check/takeprofit` - 检查止盈
- `POST /api/emergency/check/dailyloss` - 检查日亏损
- `POST /api/emergency/check/totalloss` - 检查总亏损
- `POST /api/emergency/execute` - 执行紧急操作
- `GET /api/emergency/history` - 获取紧急历史
- `GET /api/emergency/summary` - 获取紧急汇总

#### aiagent：机器学习量化模型系统
**开发日期**：2026-03-27

| 文件路径 | 文件类型 | 功能描述 | 状态 |
|---------|---------|---------|------|
| `aiagent/__init__.py` | 模块导出 | 导出Config、DataPreparation、ModelTrainer、ModelManager、PredictionService | ✅ 完成 |
| `aiagent/config.py` | 配置管理 | 配置类：数据配置、特征配置、标签配置、划分配置、模型配置、训练配置、模型管理配置、预测配置、风险控制配置 | ✅ 完成 |
| `aiagent/data_preparation.py` | 数据准备 | DataPreparation类：历史数据获取、特征计算、标签构建、时序划分、数据质量检查、特征稳定性检查、特征中性化 | ✅ 完成 |
| `aiagent/model_trainer.py` | 模型训练 | ModelTrainer类：模型选择、超参数搜索、模型训练、模型评估、特征重要性计算、早停机制 | ✅ 完成 |
| `aiagent/model_manager.py` | 模型管理 | ModelManager类：模型保存、版本管理、模型加载、模型卡片、模型注册表、预测日志记录 | ✅ 完成 |
| `aiagent/prediction_service.py` | 预测服务 | PredictionService类：批量预测、单股预测、数据校验、风险预警、速率限制、分布监控 | ✅ 完成 |
| `aiagent/main.py` | 主入口 | QuantMLSystem类：整合所有模块，提供统一的训练和预测接口 | ✅ 完成 |
| `aiagent/example.py` | 使用示例 | 展示如何使用aiagent模块进行模型训练和预测 | ✅ 完成 |

**核心功能**：
- 数据准备：历史数据获取（行情、基础、另类数据）、特征计算（技术指标、统计特征、微观结构、宏观特征）、标签构建（分类、回归、排名任务）、时序划分（训练/验证/测试、OOT、时序交叉验证）
- 模型训练：模型选择（XGBoost/LightGBM/CatBoost/随机森林/Ridge/Lasso）、训练参数配置（损失函数、评估指标、样本权重）、验证集调参（贝叶斯优化、网格搜索）、早停机制（监控指标、模型检查点）
- 模型管理：模型保存（模型权重、特征配置、模型元数据、环境依赖）、版本管理（语义化版本、模型注册表、影子模式）、模型加载（版本校验、特征对齐、预处理还原）、状态追踪（监控指标、日志记录）
- 预测接口：批量预测、单股预测、数据校验（缺失值处理、数据延迟检查、特征范围检查）、风险预警（分布漂移检测、异常预测值检测）、速率限制与认证

**设计原则**：
- 严格避免前视偏差（Look-ahead Bias）：所有特征必须基于当前时刻t及之前的数据计算
- 严禁随机划分：必须按时间顺序划分（模拟真实交易时序）
- 防止数据泄露：确保时序约束不被破坏
- 优先考虑可解释性：SHAP值分析特征重要性
- 避免过度复杂的模型：金融数据信噪比低，复杂模型易过拟合
- 严格监控验证集表现：防止过拟合

**API接口（已集成的最小可用版本）**：
- `GET /api/ml/status` - 获取训练状态（读取 `data/tushare/state/ml_train_status.json`）
- `POST /api/ml/train` - 启动训练（后台线程执行；支持 `model_name` 指定保存目录名）
- `POST /api/ml/reset_state` - 重置训练状态（发出取消标记，并清理本次未完成输出目录）
- `POST /api/ml/import_model` - 导入并启用本地模型（上传模型文件/目录结构）
- `GET /api/ml/download_model` - 下载当前启用模型（zip）

**API接口（规划/预留，尚未实现或未接入前端）**：
- `POST /api/ml/predict` - 批量预测
- `POST /api/ml/predict/single` - 单股预测
- `GET /api/ml/model/info` - 获取模型信息
- `GET /api/ml/models` - 列出所有模型
- `POST /api/ml/model/save` - 保存模型
- `POST /api/ml/model/load` - 加载模型
- `DELETE /api/ml/model/delete` - 删除模型
- `POST /api/ml/model/production` - 设置生产模型
- `GET /api/ml/signals` - 获取交易信号

**前端功能（已实现的最小可用版本）**：
- 机器学习模型训练与状态面板（策略配置页）
  - 训练保存目录名（`model_name`）
  - 开始训练（轮询 `/api/ml/status`）
  - 训练中进度/消息展示 + 状态更新时间
  - 重置训练状态（取消训练并重置状态）
  - 导入并启用本地模型（选择本地文件夹上传）
  - 下载当前启用模型（zip）

- 模型管理面板
  - 模型列表（模型名称、版本、保存时间、生产状态）
  - 模型详情（模型信息、训练指标、特征列表）
  - 模型操作（加载模型、删除模型、设置生产模型）
  - 模型卡片展示

- 预测服务面板
  - 批量预测（股票列表、特征数据输入）
  - 单股预测（股票代码、特征数据输入）
  - 预测结果展示（预测分数、预期收益、预测方向、置信度、排名）
  - 风险预警展示（分布漂移、异常预测值）

- 模型性能监控
  - 预测分布监控
  - 特征重要性监控
  - 性能衰减预警
  - 预测日志查询

#### 主应用：app（Flask）+ 单页前端
**开发日期**：2026-03-24（持续更新）

| 文件路径 | 文件类型 | 功能描述 | 状态 |
|---------|---------|---------|------|
| `run.py` | 启动入口 | 启动 Flask 服务（create_app + app.run） | ✅ 完成 |
| `app/templates/index.html` | 单页前端 | 前端界面：数据展示、策略配置、回测结果、信号分析 | ✅ 完成 |
| `requirements.txt` | 依赖配置 | Python依赖包列表 | ✅ 完成 |
| `tests/test_module2.py` | 测试脚本 | data_ingestion 功能测试 | ✅ 完成 |
| `tests/test_module5.py` | 测试脚本 | backtest_engine 功能测试 | ✅ 完成 |

**API接口**（完整列表）：
- `GET /api/settings/token` - 获取Tushare Token
- `POST /api/settings/token` - 保存Tushare Token
- `DELETE /api/settings/token` - 清除Tushare Token
- `GET /api/market/indices` - 获取市场指数数据
- `GET /api/positions` - 获取持仓列表
- `POST /api/positions` - 添加持仓
- `PUT /api/positions/<position_id>` - 更新持仓
- `DELETE /api/positions/<position_id>` - 删除持仓
- `GET /api/trades` - 获取交易记录
- `POST /api/trades` - 添加交易记录
- `GET /api/funds` - 获取可用资金
- `POST /api/funds` - 更新可用资金
- `GET /api/strategy/status` - 获取策略状态
- `POST /api/strategy/status` - 更新策略状态
- `GET /api/data/symbols` - 获取监控标的数据
- `POST /api/data/symbols` - 添加监控标的
- `GET /api/data/realtime` - 获取实时数据
- `GET /api/data/history` - 获取历史数据
- `POST /api/data/collect` - 采集数据
- `GET /api/data/validate/<symbol>` - 验证数据
- `POST /api/backtest/simple` - 简单回测
- `POST /api/backtest/optimize` - 参数优化
- `POST /api/backtest/risk` - 风险测试
- `POST /api/backtest/overfitting` - 过拟合检查
- `GET /api/strategy/config` - 获取策略配置
- `POST /api/strategy/config` - 更新策略配置
- `GET /api/strategy/params` - 获取策略参数
- `POST /api/strategy/params` - 更新策略参数
- `GET /api/strategy/validate` - 验证策略配置
- `POST /api/strategy/reset` - 重置策略配置
- `POST /api/factor/calculate` - 计算因子
- `POST /api/signal/generate` - 生成交易信号
- `POST /api/signal/filter` - 过滤信号
- `POST /api/trade/check/buy` - 检查买入触发
- `POST /api/trade/check/sell` - 检查卖出触发

**前端功能**（2026-03-25新增）：
- 策略信号分析面板
  - 股票代码输入
  - 完整分析功能（一键执行所有分析步骤）
  - 分步分析功能（计算因子、生成信号、过滤信号、检查买入、检查卖出）
  - 因子分析展示（估值因子、趋势因子、资金因子、综合评分）
  - 信号信息展示（信号类型、置信度、原因）
  - 过滤结果展示（过滤状态、原因）
  - 买入触发检查展示（触发状态、原因、建议数量、建议价格）
  - 卖出触发检查展示（触发状态、原因、建议价格）

- 实时监控面板
  - 监控状态展示（运行中/已停止）
  - 监控间隔设置
  - 持仓监控（活跃持仓、监控股票数）
  - 绩效监控（今日盈亏、总盈亏）
  - 异常监控（今日异常、异常总数）
  - 监控控制（启动、停止、刷新）
  - 绩效历史展示
  - 异常历史展示

- 交易日志面板
  - 交易日志查询（刷新交易日志、刷新绩效日志、刷新异常日志、刷新统计数据）
  - 交易日志展示
  - 绩效日志展示
  - 异常日志展示
  - 交易统计展示
  - 绩效汇总展示

- 紧急处理面板
  - 止损检查（股票代码、持仓数量、成本价格、当前价格）
  - 止盈检查（股票代码、持仓数量、成本价格、当前价格）
  - 日亏损检查（今日盈亏、初始资金）
  - 总亏损检查（总盈亏、初始资金）
  - 紧急操作（卖出所有持仓、停止所有交易、紧急停止）
  - 紧急历史展示
  - 紧急汇总展示（总事件数、活跃事件、已解决事件、当前规则）

**前端子菜单**（7个模块功能区分）：
1. 📊 数据监控 - 主仪表板，展示资金、持仓、市场指数、交易记录
2. 🎯 策略配置 - 策略类型、因子权重、信号阈值、持仓限制、目标设置、策略范围
3. 📈 信号分析 - 因子计算、信号生成、信号过滤、买入触发、卖出触发
4. 🧪 回测验证 - 简单回测、参数优化、风险测试、过拟合检查
5. 🔔 实时监控 - 监控状态、绩效监控、异常监控、监控控制
6. 📝 交易日志 - 交易日志、绩效日志、异常日志、交易统计
7. 🚨 紧急处理 - 止损检查、止盈检查、日亏损检查、总亏损检查、紧急操作

**模块集成**：
- ✅ 模块1（策略顶层设计模块）
- ✅ 模块2（实时数据接入与处理模块）
- ✅ 模块3（策略逻辑拆解模块）
- ✅ 模块5（回测与风险验证模块）
- ✅ 模块6（实盘监控与运维迭代模块）

### 系统完成状态
- **开发状态**：✅ 所有6个核心模块开发完成
- **前端状态**：✅ 所有模块前端界面实现完成
- **API状态**：✅ 所有模块API接口实现完成
- **文档状态**：✅ 技术文档更新完成
- **测试状态**：✅ 基本功能测试通过

### 系统功能总览
1. **策略顶层设计**（模块1）
   - 策略类型定义（多因子+机器学习）
   - 因子权重配置（估值、趋势、资金）
   - 信号阈值设置（买入/卖出评分和概率）
   - 交易约束设定（仓位、频率、流动性）
   - 目标设定（收益、风险、操作）

2. **实时数据接入与处理**（模块2）
   - 实时数据采集（Tushare API）
   - 数据清洗（异常值处理、复权）
   - 数据存储（SQLite数据库）
   - 数据校验（完整性、延迟检测）

3. **策略逻辑拆解**（模块3）
   - 因子计算（估值、趋势、资金因子）
   - 信号生成（买入/卖出/持有）
   - 信号过滤（趋势、风险、时效性）
   - 交易触发（买入/卖出检查）

4. **信号输出**（模块4）
   - Flask后端API（50+接口）
   - Vue.js前端界面（7个子菜单）
   - 数据展示（资金、持仓、市场指数）
   - 用户交互（策略配置、回测验证）

5. **回测与风险验证**（模块5）
   - 回测引擎（历史数据回测）
   - 参数优化（网格搜索、遗传算法）
   - 风险测试（VaR、压力测试）
   - 过拟合检查（训练测试差异、参数敏感性）

6. **实盘监控与运维迭代**（模块6）
   - 实时监控（交易、绩效、异常）
   - 交易日志（交易记录、绩效记录）
   - 迭代优化（绩效分析、参数调整、模型更新）
   - 紧急处理（止损、止盈、日亏损、总亏损）

7. **机器学习量化模型系统**（aiagent）
   - 数据准备（历史数据获取、特征计算、标签构建、时序划分）
   - 模型训练（模型选择、超参数搜索、模型评估、早停机制）
   - 模型管理（模型保存、版本管理、模型加载、状态追踪）
   - 预测服务（批量预测、单股预测、数据校验、风险预警）

### 下一步计划
- 将aiagent模块集成到Flask应用中，添加机器学习相关的API接口
- 在前端添加机器学习模型相关的界面（模型训练、模型管理、预测服务、性能监控）
- 系统集成测试
- 性能优化
- 用户体验优化
- 生产环境部署

---

### 已完成模块
- [x] 模块1：策略顶层设计模块
- [x] 模块2：实时数据接入与处理模块
- [x] 模块3：策略逻辑拆解模块
- [x] 模块4：信号输出模块
- [x] 模块5：回测与风险验证模块
- [x] 模块6：实盘监控与运维迭代模块
- [x] aiagent：机器学习量化模型系统

### 开发顺序（按依赖关系）

#### 依赖关系图
```
模块2（数据层）────────────────────────────────┐
    ↓                                          │
模块5（回测层）───────────────────────────────┤
    ↓                                          │
模块1（策略设计层）───────────────────────────┤
    ↓                                          │
模块3（策略逻辑层）───────────────────────────┤
    ↓                                          │
模块4（信号输出层）───────────────────────────┤
    ↓                                          │
模块6（运维监控层）───────────────────────────┘
```

#### 模块开发状态总览
| 模块 | 开发状态 | 完成度 | 开始时间 | 完成时间 | 备注 |
|------|---------|-------|---------|---------|------|
| 模块2 | 已完成 | 100% | 2026-03-24 | 2026-03-24 | 基础数据层，优先级最高 |
| 模块5 | 已完成 | 100% | 2026-03-24 | 2026-03-24 | 依赖模块2 |
| 模块1 | 已完成 | 100% | 2026-03-25 | 2026-03-25 | 策略顶层设计，为后续模块提供配置基础 |
| 模块3 | 已完成 | 100% | 2026-03-25 | 2026-03-25 | 依赖模块1、模块2，实现策略逻辑拆解 |
| 模块4 | 已完成 | 100% | 2026-03-24 | 2026-03-25 | 依赖所有模块，集成前端界面和API接口 |
| 模块6 | 已完成 | 100% | 2026-03-25 | 2026-03-25 | 依赖所有模块，实现实盘监控和运维迭代 |

#### 当前开发阶段
- **阶段**：系统开发完成
- **状态**：6个核心模块全部开发完成，前端界面全部实现，系统功能完整
- **下一步**：系统测试和优化
- **预计开始时间**：2026-03-25

#### 开发日志
```
2026-03-24 - 技术文档初始化
  - 创建技术文档框架
  - 定义6个核心模块
  - 绘制系统架构图
  - 明确模块依赖关系
  - 制定开发顺序
  - 添加实时进度跟踪机制

2026-03-25 - 模块4开发完成
  - 完善前端界面，集成模块3功能
  - 添加策略信号分析面板：
    * 股票代码输入框
    * 完整分析按钮（一键执行所有分析步骤）
    * 分步分析按钮（计算因子、生成信号、过滤信号、检查买入、检查卖出）
  - 添加因子分析展示：
    * 估值因子、趋势因子、资金因子、综合评分
  - 添加信号信息展示：
    * 信号类型（买入/卖出/持有）
    * 置信度
    * 信号原因
  - 添加过滤结果展示：
    * 过滤状态（通过/被过滤）
    * 过滤原因
  - 添加买入触发检查展示：
    * 触发状态
    * 触发原因
    * 建议数量
    * 建议价格区间
  - 添加卖出触发检查展示：
    * 触发状态
    * 触发原因
    * 建议价格区间
  - 添加前端方法：
    * calculateFactors() - 计算因子
    * generateSignal() - 生成信号
    * filterSignal() - 过滤信号
    * checkBuyTrigger() - 检查买入触发
    * checkSellTrigger() - 检查卖出触发
    * runFullAnalysis() - 完整分析
  - 添加前端数据结构：
    * strategySignal - 存储策略信号分析结果
    * signalSymbol - 存储当前分析的股票代码
  - 测试所有功能，确保服务器正常运行
  - 更新技术文档，记录模块4开发进度

2026-03-25 - 模块6开发完成
  - 创建模块6目录结构：live_ops/
  - 实现RealtimeMonitor类，包含：
    * start_monitoring() - 启动实时监控
    * stop_monitoring() - 停止实时监控
    * monitor_trades() - 监控交易执行
    * execute_trade() - 执行交易
    * monitor_performance() - 监控绩效
    * monitor_anomalies() - 监控异常
    * _detect_price_anomalies() - 检测价格异常
    * _detect_volume_anomalies() - 检测成交量异常
    * record_anomaly() - 记录异常
    * get_status() - 获取监控状态
    * get_performance_history() - 获取绩效历史
    * get_anomaly_history() - 获取异常历史
    * set_monitor_interval() - 设置监控间隔
  - 实现TradeLogger类，包含：
    * log_trade() - 记录交易
    * log_performance() - 记录绩效
    * log_anomaly() - 记录异常
    * get_trade_log() - 获取交易日志
    * get_performance_log() - 获取绩效日志
    * get_anomaly_log() - 获取异常日志
    * get_daily_performance() - 获取指定日期的绩效
    * get_trade_statistics() - 获取交易统计
    * get_performance_summary() - 获取绩效汇总
    * clear_old_logs() - 清理旧日志
    * export_logs() - 导出日志到文件
  - 实现IterationOptimizer类，包含：
    * analyze_performance() - 分析策略表现
    * suggest_parameter_adjustments() - 建议参数调整
    * optimize_parameters() - 优化参数
    * should_update_model() - 判断是否需要更新模型
    * update_model() - 更新机器学习模型
    * get_optimization_history() - 获取优化历史
    * get_model_update_history() - 获取模型更新历史
    * get_optimization_summary() - 获取优化汇总
    * get_model_summary() - 获取模型汇总
    * clear_old_history() - 清理旧历史记录
  - 实现EmergencyHandler类，包含：
    * check_stop_loss() - 检查止损
    * check_take_profit() - 检查止盈
    * check_daily_loss_limit() - 检查日亏损限制
    * check_total_loss_limit() - 检查总亏损限制
    * execute_emergency_action() - 执行紧急操作
    * _execute_sell() - 执行卖出操作
    * _execute_stop_trading() - 执行停止交易操作
    * _execute_emergency_stop() - 执行紧急停止操作
    * record_emergency() - 记录紧急事件
    * resolve_emergency() - 解决紧急事件
    * get_emergency_history() - 获取紧急事件历史
    * get_active_emergencies() - 获取活跃的紧急事件
    * update_emergency_rules() - 更新紧急规则
    * get_current_rules() - 获取当前紧急规则
    * get_emergency_summary() - 获取紧急事件汇总
  - 创建模块导出文件：live_ops/__init__.py
  - 集成到module4/app.py，添加Flask API接口：
    * GET /api/monitor/status - 获取监控状态
    * GET /api/monitor/performance - 获取绩效历史
    * GET /api/monitor/anomalies - 获取异常历史
    * GET /api/logger/trades - 获取交易日志
    * GET /api/logger/performance - 获取绩效日志
    * GET /api/logger/anomalies - 获取异常日志
    * GET /api/logger/statistics - 获取交易统计
    * GET /api/logger/summary - 获取绩效汇总
    * POST /api/optimizer/analyze - 绩效分析
    * POST /api/optimizer/suggest - 参数调整建议
    * POST /api/optimizer/optimize - 参数优化
    * POST /api/optimizer/model/check - 检查模型更新
    * POST /api/emergency/check/stoploss - 检查止损
    * POST /api/emergency/check/takeprofit - 检查止盈
    * POST /api/emergency/check/dailyloss - 检查日亏损
    * POST /api/emergency/check/totalloss - 检查总亏损
    * POST /api/emergency/execute - 执行紧急操作
    * GET /api/emergency/history - 获取紧急历史
    * GET /api/emergency/summary - 获取紧急汇总
  - 支持实时监控、交易记录、绩效分析
  - 支持参数优化、模型更新、优化建议
  - 支持止损、止盈、日亏损限制、总亏损限制
  - 支持紧急操作执行和记录
  - 更新技术文档，记录模块6开发进度

2026-03-25 - 前端开发完成
  - 完善前端界面，实现所有模块的前端功能
  - 添加7个前端子菜单，区分不同模块功能：
    * 📊 数据监控 - 主仪表板
    * 🎯 策略配置 - 策略参数设置
    * 📈 信号分析 - 策略信号分析
    * 🧪 回测验证 - 回测和风险测试
    * 🔔 实时监控 - 实时监控面板
    * 📝 交易日志 - 日志查询和统计
    * 🚨 紧急处理 - 风险控制和紧急操作
  - 在前端data()函数中添加紧急处理相关数据变量：
    * emergencyCheck - 紧急检查参数
    * emergencyResults - 紧急检查结果
    * emergencyHistory - 紧急事件历史
    * emergencySummary - 紧急事件汇总
  - 在前端methods中添加紧急处理相关方法：
    * checkStopLoss() - 检查止损
    * checkTakeProfit() - 检查止盈
    * checkDailyLoss() - 检查日亏损
    * checkTotalLoss() - 检查总亏损
    * executeEmergency() - 执行紧急操作
    * loadEmergencyHistory() - 加载紧急历史
    * loadEmergencySummary() - 加载紧急汇总
  - 在mounted()钩子中添加紧急历史和汇总的自动加载
  - 修复后端API接口，统一返回格式（result字段）
  - 测试所有前端功能，确保界面正常显示
  - 更新技术文档，记录前端开发完成状态

2026-03-25 - 模块3开发完成
  - 创建模块3目录结构：signal_engine/
  - 实现FactorCalculator类，包含：
    * calculate_all_factors() - 计算所有因子
    * _calculate_valuation_factors() - 计算估值因子（PE、PB）
    * _calculate_trend_factors() - 计算趋势因子（MA5、MA10、MA20、动量）
    * _calculate_fund_factors() - 计算资金因子（成交量比率、成交额比率）
    * _normalize_pe() - 归一化PE因子
    * _normalize_pb() - 归一化PB因子
    * _normalize_trend() - 归一化趋势因子
    * _calculate_momentum() - 计算动量因子
    * _normalize_volume_ratio() - 归一化成交量比率
    * _normalize_amount_ratio() - 归一化成交额比率
    * _calculate_total_score() - 计算综合评分
    * update_weights() - 更新因子权重
  - 实现SignalGenerator类，包含：
    * generate_signal() - 生成交易信号
    * _determine_signal() - 确定信号类型（买入/卖出/持有）
    * _get_signal_reason() - 获取信号原因
    * _calculate_confidence() - 计算信号置信度
    * generate_batch_signals() - 批量生成信号
    * update_thresholds() - 更新信号阈值
    * get_current_thresholds() - 获取当前阈值
  - 实现SignalFilter类，包含：
    * filter_signal() - 过滤信号
    * _apply_trend_filter() - 应用趋势过滤（大盘趋势、个股趋势）
    * _apply_risk_filter() - 应用风险过滤（ST股、停牌、涨跌停、流动性）
    * _apply_time_validity_filter() - 应用时效性过滤（信号有效期）
    * filter_batch_signals() - 批量过滤信号
    * update_filter_rules() - 更新过滤规则
    * get_current_rules() - 获取当前规则
  - 实现TradeTrigger类，包含：
    * check_buy_trigger() - 检查买入触发条件
    * check_sell_trigger() - 检查卖出触发条件
    * _check_position_limits() - 检查仓位限制
    * _check_trade_count() - 检查交易次数
    * _check_risk_limits() - 检查风险限制
    * _check_sell_signal() - 检查卖出信号
    * _check_profit_loss() - 检查盈亏条件
    * _check_position_risk() - 检查持仓风险
    * _calculate_buy_quantity() - 计算买入数量
    * _get_suggested_price_range() - 获取建议价格区间
    * record_trade() - 记录交易
    * get_trade_history() - 获取交易历史
    * update_position_limits() - 更新仓位限制
    * update_targets() - 更新目标设定
    * get_current_limits() - 获取当前限制
  - 创建模块导出文件：signal_engine/__init__.py
  - 集成到module4/app.py，添加Flask API接口：
    * POST /api/factor/calculate - 计算因子
    * POST /api/signal/generate - 生成交易信号
    * POST /api/signal/filter - 过滤信号
    * POST /api/trade/check/buy - 检查买入触发
    * POST /api/trade/check/sell - 检查卖出触发
  - 支持因子权重配置、信号阈值配置
  - 支持趋势过滤、风险过滤、时效性过滤
  - 支持仓位限制、交易次数限制、盈亏触发
  - 更新技术文档，记录模块3开发进度

2026-03-25 - 模块1开发完成
  - 创建模块1目录结构：strategy_config/
  - 实现StrategyConfig类，包含：
    * _load_config() - 加载配置文件
    * _get_default_config() - 获取默认配置
    * save_config() - 保存配置到文件
    * get_config() - 获取完整配置
    * update_config() - 更新配置
    * get_strategy_type() - 获取策略类型
    * get_factor_weights() - 获取因子权重
    * get_signal_thresholds() - 获取信号阈值
    * get_position_limits() - 获取仓位限制
    * get_targets() - 获取目标设定
    * get_scope() - 获取适用范围
    * validate_config() - 验证配置有效性
    * reset_to_default() - 重置为默认配置
  - 创建模块导出文件：strategy_config/__init__.py
  - 集成到module4/app.py，添加Flask API接口：
    * GET /api/strategy/config - 获取策略配置
    * POST /api/strategy/config - 更新策略配置
    * GET /api/strategy/params - 获取策略参数
    * POST /api/strategy/params - 更新策略参数
    * GET /api/strategy/validate - 验证策略配置
    * POST /api/strategy/reset - 重置策略配置为默认值
  - 配置文件支持JSON格式持久化
  - 支持配置验证和错误提示
  - 更新技术文档，记录模块1开发进度

2026-03-24 - 模块2开发完成
  - 创建模块2目录结构：backend/module2_data/
  - 实现RealTimeDataCollector类，包含：
    * collect_realtime_data() - 实时数据采集
    * collect_history_data() - 历史数据采集
    * clean_data() - 数据清洗（剔除异常值、复权处理、时间对齐）
    * store_data() - 实时数据存储
    * store_history_data() - 历史数据存储
    * validate_data() - 数据校验（完整性、延迟检测）
    * get_realtime_data() - 获取实时数据
    * get_history_data() - 获取历史数据
  - 创建数据库表结构：
    * stock_realtime_data - 实时数据表
    * stock_history_data - 历史数据表
    * monitored_symbols - 监控标的表
    * 创建索引优化查询性能
  - 创建Flask API接口：
    * GET /api/data/symbols - 获取监控标的列表
    * POST /api/data/symbols - 添加/删除监控标的
    * GET /api/data/realtime - 获取实时数据
    * GET /api/data/history - 获取历史数据
    * POST /api/data/collect - 手动触发数据采集
    * GET /api/data/validate/<symbol> - 验证数据完整性
  - 创建测试脚本test_module2.py
  - 所有功能测试通过
  - 集成到主应用app.py

2026-03-24 - 模块5开发完成
  - 创建模块5目录结构：backend/module5_backtest/
  - 实现BacktestEngine类，包含：
    * load_data() - 从数据库加载历史数据
    * split_data() - 划分数据集（训练集70%、验证集20%、测试集10%）
    * calculate_returns() - 计算收益率
    * calculate_metrics() - 计算绩效指标（总收益率、年化收益率、最大回撤、夏普比率、胜率、盈亏比）
    * run_simple_backtest() - 执行简单回测（买入持有策略）
    * run_strategy_backtest() - 执行策略回测
    * calculate_attribution() - 归因分析
  - 实现ParameterOptimizer类，包含：
    * grid_search() - 网格搜索优化参数
    * genetic_algorithm() - 遗传算法优化参数
    * optimize_factor_weights() - 优化因子权重
    * optimize_signal_thresholds() - 优化信号阈值
  - 实现RiskTester类，包含：
    * calculate_var() - 计算风险价值（VaR）
    * calculate_cvar() - 计算条件风险价值（CVaR）
    * calculate_max_consecutive_losses() - 计算最大连续亏损次数
    * calculate_volatility() - 计算波动率
    * stress_test() - 极端场景压力测试
    * market_regime_test() - 市场环境测试（牛市、震荡市、熊市）
    * liquidity_test() - 流动性测试
    * comprehensive_risk_test() - 综合风险测试
  - 实现OverfittingChecker类，包含：
    * check_train_test_gap() - 检查训练集和测试集表现差异
    * check_parameter_sensitivity() - 检查参数敏感性
    * check_future_data_leakage() - 检查未来数据泄露
    * check_strategy_complexity() - 检查策略复杂度
    * comprehensive_overfitting_check() - 综合过拟合检查
  - 创建Flask API接口：
    * POST /api/backtest/simple - 执行简单回测
    * POST /api/backtest/optimize - 参数优化
    * POST /api/backtest/risk - 风险测试
    * POST /api/backtest/overfitting - 过拟合检查
  - 创建测试脚本test_module5.py
  - 所有功能测试通过
  - 集成到主应用app.py

2026-03-24 - 目录结构优化
  - 重新组织项目目录结构，按职责划分目录
  - 将模块2代码从 module4/backend/module2_data/ 移动到 data_ingestion/
  - 将模块5代码从 module4/backend/module5_backtest/ 移动到 backtest_engine/
  - 删除 module4/backend/ 目录，清理旧代码
  - 更新导入路径：
    * `from backend.module2_data` → `from data_ingestion`
    * `from backend.module5_backtest` → `from backtest_engine`
  - 更新测试脚本中的导入路径：
    * test_module2.py: `from backend.module2_data` → `from data_ingestion`
    * test_module5.py: `from backend.module5_backtest` → `from backtest_engine`
  - 更新技术文档，添加完整的项目目录结构说明
  - 验证所有导入路径正确，应用启动正常

2026-03-24 - 清理旧代码
  - 检查 strategy_config/ 和 data_ingestion/ 目录，识别旧代码
  - 删除 data_ingestion/ 中的旧代码文件：
    * akshare_collector.py - AkShare数据采集器
    * baostock_collector.py - Baostock数据采集器
    * data_cleaner.py - 数据清洗
    * data_collector_simple.py - 模拟数据采集器
    * data_storage.py - 数据存储
    * data_validator.py - 数据验证
  - 保留 data_ingestion/ 中本次开发的代码：
    * __init__.py
    * data_collector.py
    * db_init.py
  - 在技术文档中添加"模块文件开发记录"部分，记录所有模块的文件清单
  - 建立文件记录标准：记录文件路径、类型、功能描述和状态
  - 方便后续代码回溯和维护
  - 清理 data_ingestion/ 和 backtest_engine/ 中的__pycache__目录
  - 删除 backtest_engine/ 中的旧代码文件：
    * backtest_framework.py - 旧版回测框架
  - 验证 data_ingestion/ 和 backtest_engine/ 目录只包含本次开发的代码

2026-03-24 - 技术文档位置调整
  - 将技术文档从 module4/TECHNICAL_DOCUMENTATION.md 移动到项目根目录 TECHNICAL_DOCUMENTATION.md
  - 更新技术文档中的目录结构说明，移除module4/下的TECHNICAL_DOCUMENTATION.md引用
  - 确保技术文档位于项目根目录，方便所有模块访问和更新

2026-03-28 - 机器学习训练与模型管理优化
  - 前端策略配置页新增模型管理能力：
    * 训练保存目录名（model_name）
    * 训练完成弹窗展示保存路径/目录
    * 选择本地模型并上传导入启用
    * 下载当前启用模型（zip）
    * 训练中展示状态更新时间、支持重置训练状态
  - 后端新增/完善机器学习相关接口：
    * GET /api/ml/status（训练状态）
    * POST /api/ml/train（支持 model_name）
    * POST /api/ml/reset_state（取消训练 + 清理未完成输出目录 + 重置状态）
    * POST /api/ml/import_model（导入本地模型）
    * GET /api/ml/download_model（导出模型 zip）
  - 训练稳定性提升：
    * 训练状态超时自动转 error
    * 取消标记机制：训练线程检测后尽快退出
    * 状态文件并发写入：唯一 tmp 文件名 + 重试 + 原子替换，修复 Windows Errno 13
    * 训练进度更新更频繁（避免“卡在某个百分比”的误判）
```

### 遇到的问题
- 无

### 下一步计划
1. **第1步**：✅ 模块2 - 实时数据接入与处理模块（已完成）
   - ✅ 创建项目目录结构
   - ✅ 实现数据采集功能
   - ✅ 实现数据清洗功能
   - ✅ 实现数据存储功能
   - ✅ 实现数据校验功能
   - ✅ 创建API接口
   - ✅ 更新技术文档

2. **第2步**：✅ 模块5 - 回测与风险验证模块（已完成）
   - ✅ 创建项目目录结构
   - ✅ 实现回测框架
   - ✅ 实现参数优化功能
   - ✅ 实现风险测试功能
   - ✅ 实现过拟合排查功能
   - ✅ 创建API接口
   - ✅ 更新技术文档

3. **第3步**：✅ 模块1 - 策略顶层设计模块（已完成）
   - ✅ 创建项目目录结构
   - ✅ 实现策略配置类
   - ✅ 创建API接口
   - ✅ 更新技术文档

4. **第4步**：✅ 模块3 - 策略逻辑拆解模块（已完成）
   - ✅ 创建项目目录结构
   - ✅ 实现因子计算功能
   - ✅ 实现信号生成功能
   - ✅ 实现信号过滤功能
   - ✅ 实现交易触发功能
   - ✅ 创建API接口
   - ✅ 更新技术文档
5. **第5步**：✅ 模块4 - 信号输出模块（已完成）
   - ✅ 创建Flask主应用
   - ✅ 实现API接口
   - ✅ 实现前端界面
   - ✅ 集成所有模块
   - ✅ 添加策略信号分析功能
   - ✅ 测试所有功能
   - ✅ 更新技术文档
6. **第6步**：✅ 模块6 - 实盘监控与运维迭代模块（已完成）
   - ✅ 创建项目目录结构
   - ✅ 实现实时监控功能
   - ✅ 实现交易记录功能
   - ✅ 实现迭代优化功能
   - ✅ 实现紧急处理功能
   - ✅ 创建API接口
   - ✅ 更新技术文档

---

## 🛠️ 运维脚本：历史数据批量采集（2026-03-27）

### 脚本位置
- `scripts/fetch_history_batch.py`

### 功能说明
- 根据标的集合与时间窗口，从 Tushare 批量拉取日线行情（daily）与每日指标（daily_basic），写入 SQLite（表：`stock_history_data`）。
- 自动读取系统设置中的 Token（`settings.tushare_token`），不需要命令行传 Token。
- 支持节流与分批，降低限速风险；支持 `--dry-run` 验证集合与参数。

### 参数
- `--universe`：`hs300 | all | file | list`（默认 `hs300`）
- `--file`：当 `--universe file` 时，文本文件路径（每行一个 `ts_code`）
- `--symbols`：当 `--universe list` 时，逗号分隔股票列表（如 `000001.SZ,600519.SH`）
- `--start`：开始日期（YYYYMMDD），默认 `20220101`
- `--end`：结束日期（YYYYMMDD），默认当天
- `--db`：数据库路径，默认 `quant_data.db`
- `--sleep`：每支间隔秒数（默认 `0.2`）
- `--batch-size`：每处理 N 支后暂停 2 秒（默认 `500`）
- `--dry-run`：仅打印前 10 支，验证集合与参数

### 用法示例
- 沪深300：`python scripts/fetch_history_batch.py --universe hs300 --start 20220101 --end 20260326`
- 全 A 股（建议夜间）：`python scripts/fetch_history_batch.py --universe all --start 20220101 --end 20260326 --sleep 0.2 --batch-size 500`
- 自定义列表：`python scripts/fetch_history_batch.py --universe list --symbols "000001.SZ,000002.SZ,600519.SH" --start 20220101 --end 20260326`
- 自文件列表：`python scripts/fetch_history_batch.py --universe file --file d:\codes.txt --start 20220101 --end 20260326`

### 备注
- 训练/回测阶段仅读取本地数据，不再调用 Tushare；只有“缺口补齐/增量更新”会消耗 Tushare Token。
- 清洗与合并逻辑与 `data_ingestion/data_collector.py` 一致（包含 PE/PB 合并与关键字段空值过滤）。

---

## 🧠 机器学习特征工程的可扩展性规范（2026-03-27）

### 设计目标
- 后续增加/修改因子低成本（尽量只改配置不改代码）
- 可复现（训练参数与特征版本可追溯）
- 线上离线一致（训练与推理完全同构）

### 推荐实现
- **配置驱动的因子清单**
  - 统一维护 `feature_list`（或 JSON 配置），定义启用的因子与窗口参数。
  - 数据准备、模型训练、在线推理均从同一配置读取，禁止分别写死。
- **特征版本化（强校验）**
  - 对 `feature_list` 计算 `feature_list_hash`，写入 `model_config.json`。
  - 推理加载模型时校验哈希：不一致则将模型状态标记为 `stale` 并提示重新训练，避免“训练一套、推理一套”。
- **统计量随模型走**
  - 训练集生成并保存 `feature_stats.json`（均值/分位/缺失率/填充策略/标准化参数）。
  - 推理阶段严格复用该统计量进行缺失值填充与标准化，保证一致性。
- **与传统策略解耦**
  - 趋势跟踪/均值回归参数模块独立于机器学习特征体系；修改 ML 因子不影响传统策略配置与回测。

### 约束与注意
- 机器学习策略（`strategy_type="ml_model"`）增删因子后必须重新训练模型，否则不允许进入回测/信号流程（或提示后终止）。
- 仅对传统策略做参数调整（均线窗口/阈值等）不涉及训练。

## 📚 参考文档

### 技术文档
- Flask官方文档：https://flask.palletsprojects.com/
- Vue3官方文档：https://vuejs.org/
- Tushare官方文档：https://tushare.pro/
- SQLite文档：https://www.sqlite.org/docs.html

### 算法文档
- 多因子模型：https://www.investopedia.com/terms/m/multifactor-model
- 机器学习在量化中的应用：https://www.quantstart.com/articles/
- 回测方法论：https://www.quantopian.com/posts/an-introduction-to-backtesting/
- 风险管理：https://www.investopedia.com/terms/r/risk-management.asp

### 数据源文档
- Tushare数据接口：https://tushare.pro/document/2
- AKShare数据接口：https://akshare.akfamily.xyz/
- Baostock数据接口：http://baostock.com/baostock/index.html
