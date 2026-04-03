# 系统架构与代码优化记录

**日期：** 2026-03-29
**执行阶段：** 全面架构审查与重构落地 (高、中、低优先级)

---

## 1. 高优先级优化 (🔴 High Priority)
这些修复解决了系统中的致命错误和导致核心功能失效的逻辑漏洞。

- **修复 `module4` 导入崩溃**
  - **问题**：`module4/__init__.py` 中存在引用不存在模块 `app_simple.py` 的死代码，导致导入时报 `ImportError` 崩溃。
  - **修复**：清空了导致崩溃的导入语句。
- **修复 `EmergencyHandler` 止损功能失效**
  - **问题**：止损和止盈功能内部引用了不存在的 `utils.database` 模块，导致触发紧急操作时系统报错，完全无法卖出。
  - **修复**：将其替换为通过 `sqlite3` 直接连接正确的 `data/tushare/db/quant_data.db` 路径，并修正了写入的表名为 `trade_records`。
- **修复数据库旧路径硬编码问题**
  - **问题**：`strategy.py` 和 `data.py` 中硬编码了废弃的 `DATABASE = 'quant_data.db'`。
  - **修复**：移除了硬编码的常量，统一替换为使用 Flask `current_app.config['DATABASE']` 来获取正确的数据库路径。
- **修复 `TradeLogger` 无状态导致日志为空**
  - **问题**：`monitor.py` 在处理交易日志 API 时，每次都会实例化一个新的 `TradeLogger`，导致返回的日志列表永远为空。
  - **修复**：在 `monitor.py` 中将 `TradeLogger` 改为模块级单例 `_trade_logger`。
- **修复 `genetic_algorithm` 参数忽略问题**
  - **问题**：`parameter_optimizer.py` 的遗传算法在评估适应度时，完全没有将生成的参数传入回测引擎，导致每代个体的回测结果都一样。
  - **修复**：将硬编码的回测调用改为接收 `evaluate_fn` 回调，与 `grid_search` 保持接口一致，确保参数正确参与运算。

---

## 2. 中优先级优化 (🟡 Medium Priority)
这些修复解决了冗余代码、命名不一致以及数据库结构缺失的问题。

- **数据库 `schema.sql` 补列与迁移**
  - **问题**：`stock_history_data` 表缺失因子计算所依赖的 `pre_close`、`change_pct`、`pe`、`pb`、`total_mv`、`circ_mv` 列。
  - **修复**：在 `schema.sql` 中补充了这些列的定义，并在 `db_init.py` 中编写并执行了热迁移函数 `_migrate_history_columns`，补齐了现有数据库表字段。
- **消除重复定义的 `close()` 方法**
  - **问题**：`BacktestEngine` 和 `RealTimeDataCollector` 类中均存在连续两遍完全相同的 `close()` 方法定义。
  - **修复**：删除了各文件中多余的方法定义。
- **统一日志系统**
  - **问题**：`data_ingestion`, `backtest_engine` 的多个文件中调用了 `logging.basicConfig`，与全局的 `app/utils.py` 提供的 `setup_logger()` 冲突，导致日志双轨制和重复输出。
  - **修复**：删除了各业务模块中所有的 `logging.basicConfig` 调用，统一改为只通过 `logging.getLogger(__name__)` 获取。
- **消除 `StrategyConfig` 的 CWD 依赖**
  - **问题**：`strategy_config.json` 的默认路径依赖当前工作目录（CWD），从不同位置启动时会找不到文件。
  - **修复**：利用 `__file__` 构造了绝对路径 `_DEFAULT_CONFIG_PATH` 作为配置文件的默认路径。

---

## 3. 低优先级优化 (🟢 Low Priority)
这些优化主要针对性能瓶颈、缓存、遗留废弃文件清理等长期架构改善项。

- **`TradeLogger` 数据持久化到数据库**
  - **优化**：之前交易记录仅存在内存列表，重启即丢失。现将 `log_trade` 的记录直接存入 SQLite 的 `trade_records` 表，并将 `get_trade_log` 改为从数据库读取。
- **为 Tushare 频繁调用接口添加缓存**
  - **优化**：在 `app/routes/data.py` 中为 `search_stocks` (缓存 24 小时) 和 `market_indices` (缓存 5 分钟) 添加了内存缓存，极大缓解了 UI 刷新时对 Tushare API 的请求压力。
- **优化回测引擎 O(n²) 性能瓶颈**
  - **优化**：`run_strategy_backtest` 原先通过 `apply` 加 `loc` 对历史数据逐行拷贝切片，导致 O(n²) 的严重性能损耗。优化为预先通过 `iloc` 获取视图并在循环中追加，大幅降低 Pandas 拷贝开销。
- **清理无用文件与目录结构**
  - **清理**：删除了空壳目录 `module4/`。
  - **清理**：删除了根目录下与 `data/tushare/reports` 重复的冗余 `reports/` 目录。
  - **清理**：删除了无用的 `utils/` 目录和带有死代码的 `aiagent/main.py`。
  - **清理**：删除了残留在根目录下的空旧数据库文件 `quant_data.db`。
  - **重构**：将根目录散落的独立脚本 `check_divs.py`、`trace_divs.py`、`update_db.py` 统一移动至 `scripts/` 目录中。
