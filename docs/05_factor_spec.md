# 因子说明文档

核心定义

- 说明系统中用于“信号/模型”的全部因子（含规则因子与 ML 特征），并给出每个因子的名称、计算口径（公式/窗口）、数据来源与必要处理流程。

一、规则因子（signal\_engine，用于评分与阈值信号）

1. 估值因子（valuation）

- 因子名称：PE 估值评分
  - 公式：pe\_score = piecewise(pe)（区间映射：<=10→1.0，<=20→0.8，<=30→0.6，<=50→0.4，否则 0.2）
  - 数据来源：SQLite.stock\_history\_data.pe（来自 Tushare daily\_basic）
- 因子名称：PB 估值评分
  - 公式：pb\_score = piecewise(pb)（<=1.0→1.0，<=1.5→0.8，<=2.0→0.6，<=3.0→0.4，否则 0.2）
  - 数据来源：SQLite.stock\_history\_data.pb（来自 Tushare daily\_basic）
- 估值总分
  - 公式：valuation\_score = (pe\_score + pb\_score) / 2
  - 输出：valuation.score（0\~1）

1. 趋势因子（trend，依赖 TA-Lib）

- 因子名称：均线强弱（MA5/MA10/MA20）
  - 公式：ma\_score = piecewise((price - MA) / MA)
  - 数据来源：输入行情 close（近 N 日）
- 因子名称：动量（5日动量）
  - 公式：momentum = (close\[-1] - close\[-5]) / close\[-5]，再按区间映射为分数
  - 数据来源：输入行情 close
- 趋势总分
  - 公式：trend\_score = (ma5\_score + ma10\_score + ma20\_score + momentum\_score) / 4
  - 输出：trend.score（0\~1）

1. 资金因子（fund）

- 因子名称：成交量放大比率
  - 公式：volume\_ratio = volume\_t / mean(volume\_{t-20:t-1})
  - 数据来源：输入行情 volume
- 因子名称：成交额放大比率
  - 公式：amount\_ratio = amount\_t / mean(amount\_{t-20:t-1})
  - 数据来源：输入行情 amount
- 资金总分
  - 公式：fund\_score = (score(volume\_ratio) + score(amount\_ratio)) / 2
  - 输出：fund.score（0\~1）

1. 综合总分（0\~10）

- 公式：total\_score = 10 \* clip01(valuation\_score*w\_v + trend\_score*w\_t + fund\_score\*w\_f)
- 权重来源：strategy\_config.json.factor\_weights（默认 0.2/0.6/0.2）

实现参考

- [factor\_calculator.py](file:///d:/web%20development/quant/signal_engine/factor_calculator.py#L14-L236)

二、机器学习特征（aiagent，用于训练与推理）

特征配置来源

- [feature\_list.json](file:///d:/web%20development/quant/data/tushare/raw/feature_list.json)

特征计算入口

- [ml\_features.py](file:///d:/web%20development/quant/aiagent/ml_features.py#L70-L186)

逐项因子说明（与 feature\_list.json 保持一致）

- close：收盘价（原始值）；来源：stock\_history\_data.close\_price
- volume：成交量（原始值）；来源：stock\_history\_data.volume
- amount：成交额（原始值）；来源：stock\_history\_data.amount
- return\_1d：1日收益率；公式：pct\_change(close, 1)
- return\_5d：5日收益率；公式：pct\_change(close, 5)
- return\_20d：20日收益率；公式：pct\_change(close, 20)
- return\_60d：60日收益率；公式：pct\_change(close, 60)
- ma\_5：5日均线；公式：SMA(close, 5)
- ma\_10：10日均线；公式：SMA(close, 10)
- ma\_20：20日均线；公式：SMA(close, 20)
- ma\_60：60日均线；公式：SMA(close, 60)
- ma\_bias\_5：5日乖离；公式：close/(ma\_5+1e-12) - 1
- ma\_bias\_10：10日乖离；公式：close/(ma\_10+1e-12) - 1
- ma\_bias\_20：20日乖离；公式：close/(ma\_20+1e-12) - 1
- volatility\_20d：20日波动率；公式：std(pct\_change(close,1), window=20)
- volatility\_60d：60日波动率；公式：std(pct\_change(close,1), window=60)
- volume\_ma5\_ratio：量比(5)；公式：volume / (SMA(volume,5)+1e-12)
- volume\_ma20\_ratio：量比(20)；公式：volume / (SMA(volume,20)+1e-12)
- amount\_ma\_ratio：额比(20)；公式：amount / (SMA(amount,20)+1e-12)
- trend\_strength：趋势强度；公式：(close - ma\_20) / (ma\_20+1e-12)
- close\_above\_ma20：收盘高于MA20；公式：1.0 if close>ma\_20 else 0.0
- rsi\_14：RSI(14)；公式：TA-Lib RSI 或 rolling mean 近似
- macd：MACD；公式：EMA12-EMA26
- macd\_signal：MACD 信号线；公式：EMA9(macd)
- macd\_hist：MACD 柱；公式：macd - macd\_signal
- atr\_14：ATR(14)；公式：TA-Lib ATR 或 TR rolling mean
- obv：OBV；公式：cumsum(sign(diff(close))\*volume)
- pe：市盈率；来源：stock\_history\_data.pe
- pb：市净率；来源：stock\_history\_data.pb
- turnover\_rate：换手率；来源：stock\_history\_data.turnover\_rate
- buy\_lg\_amount：大单买入额；来源：stock\_history\_data.buy\_lg\_amount
- net\_amount：净流入额；来源：stock\_history\_data.net\_mf\_amount（在特征中命名为 net\_amount）
- net\_amount\_rate：净流入占比；来源：stock\_history\_data.net\_amount\_rate（缺失时用 net\_mf\_amount/amount 兜底）
- market\_cap：总市值；来源：stock\_history\_data.total\_mv（在特征中命名为 market\_cap）

因子处理逻辑（最小必需）

- 缺失值：由训练管线统一处理；推理严格复用训练时的统计量（feature\_stats）
- 归一化/标准化：以模型 bundle 中的 feature\_stats.json 为准（训练生成，推理复用）
- 去极值：当前以“稳定可用”为主，优先保证口径一致；如需去极值，应落在训练/推理共用的特征处理层并随模型版本化

编写目的

- 让 AI 能基于清晰的“特征名→公式→来源→处理”映射，快速复用因子计算、排查特征口径差异，并支持后续新增/替换因子时的最小改动。

