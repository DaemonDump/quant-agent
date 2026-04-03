# 批量落数文档

用于记录每次历史数据批量落库与覆盖率报告的执行情况，保证数据生产可追溯、可复现、可核对。

---

## 记录规范

- 执行入口：scripts/fetch_history_batch.py 或 scripts/run_batches.ps1
- 必要参数：universe、start、end、db
- 输出产物：
  - SQLite 表 stock_history_data
  - 覆盖率报告 CSV 与同名 Markdown 概览（在 reports/ 目录）
- 断点续传：scripts/.fetch_state.txt，进程中断后可续传

---

## 执行记录

### 2026-03-27 现状与首次报告

- 操作时间：2026-03-27
- 内容：新增批量落数脚本与覆盖率统计脚本；生成第一份覆盖率报告（基于当前 DB）
- 覆盖率汇总：
  - 完整覆盖：1
  - 部分覆盖：1498
  - 缺失：0
  - 窗口：20220101 ~ 20260326
- 报告文件：reports/coverage_db_20220101_20260326.csv（同名 .md 概览）

---

### 追加记录模板

- 操作时间：YYYY-MM-DD HH:MM
- 执行方式：fetch_history_batch.py 或 run_batches.ps1
- 参数：universe=..., start=YYYYMMDD, end=YYYYMMDD, db=..., sleep=..., batch_size=...
- 结果：fetched_ok=.../total=...
- 报告：reports/coverage_...csv（同名 .md）


### 2026-03-27 18:34
- 执行方式：fetch_history_batch.py
- 参数：universe=all, start=20220101, end=20260326, db=quant_data.db, sleep=0.2, batch_size=500
- 结果：fetched_ok=5397/total=5398, 用时=2225s

### 2026-03-27 18:35
- 执行方式：run_batches.ps1
- 参数：universe=all, start=20220101, end=20260326, db=quant_data.db, sleep=0.2, batch_size=500
- 报告：reports\coverage_db_20220101_20260326_20260327_1834.csv
