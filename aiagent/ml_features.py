import numpy as np
import pandas as pd

try:
    import talib
    _TALIB = True
except Exception:
    _TALIB = False


def _rsi(close: np.ndarray, period: int) -> np.ndarray:
    if _TALIB:
        return talib.RSI(close.astype(np.float64, copy=False), timeperiod=period)
    delta = np.diff(close, prepend=np.nan)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(gain).rolling(period, min_periods=period).mean().to_numpy()
    roll_down = pd.Series(loss).rolling(period, min_periods=period).mean().to_numpy()
    rs = roll_up / (roll_down + 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def _macd(close: np.ndarray):
    if _TALIB:
        macd, signal, hist = talib.MACD(
            close.astype(np.float64, copy=False),
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )
        return macd, signal, hist
    s = pd.Series(close)
    ema_fast = s.ewm(span=12, adjust=False).mean()
    ema_slow = s.ewm(span=26, adjust=False).mean()
    macd = (ema_fast - ema_slow).to_numpy()
    signal = pd.Series(macd).ewm(span=9, adjust=False).mean().to_numpy()
    hist = macd - signal
    return macd, signal, hist


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    if _TALIB:
        return talib.ATR(
            high.astype(np.float64, copy=False),
            low.astype(np.float64, copy=False),
            close.astype(np.float64, copy=False),
            timeperiod=period
        )
    h = pd.Series(high)
    l = pd.Series(low)
    c = pd.Series(close)
    prev_close = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean().to_numpy()


def _obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    if _TALIB:
        return talib.OBV(
            close.astype(np.float64, copy=False),
            volume.astype(np.float64, copy=False)
        )
    s_close = pd.Series(close)
    s_vol = pd.Series(volume)
    direction = np.sign(s_close.diff()).fillna(0.0).to_numpy()
    obv = (direction * s_vol.to_numpy()).cumsum()
    return obv


def compute_features(df: pd.DataFrame, feature_names):
    if df.empty:
        return pd.DataFrame()

    base = df.copy()
    base = base.sort_values("trade_date").reset_index(drop=True)

    def _series(name: str, default=np.nan):
        if name in base.columns:
            return pd.to_numeric(base[name], errors="coerce")
        return pd.Series(default, index=base.index, dtype=float)

    close_s = _series("close_price")
    open_s = _series("open_price")
    high_s = _series("high_price")
    low_s = _series("low_price")
    volume_s = _series("volume")
    amount_s = _series("amount")
    total_mv_s = _series("total_mv")
    turnover_rate_s = _series("turnover_rate")
    buy_lg_amount_s = _series("buy_lg_amount")
    net_mf_amount_s = _series("net_mf_amount")
    net_amount_rate_s = _series("net_amount_rate")

    close = close_s.to_numpy(dtype=float)
    high = high_s.to_numpy(dtype=float)
    low = low_s.to_numpy(dtype=float)
    volume = volume_s.to_numpy(dtype=float)
    amount = amount_s.to_numpy(dtype=float)

    out = pd.DataFrame(index=base.index)
    if "close" in feature_names:
        out["close"] = close
    if "open" in feature_names:
        out["open"] = open_s.to_numpy(dtype=float)
    if "volume" in feature_names:
        out["volume"] = volume
    if "amount" in feature_names:
        out["amount"] = amount

    if "return_1d" in feature_names:
        out["return_1d"] = pd.Series(close).pct_change().to_numpy()
    if "return_5d" in feature_names:
        out["return_5d"] = pd.Series(close).pct_change(5).to_numpy()
    if "return_20d" in feature_names:
        out["return_20d"] = close_s.pct_change(20).to_numpy()
    if "return_60d" in feature_names:
        out["return_60d"] = close_s.pct_change(60).to_numpy()
    if "volatility_20d" in feature_names:
        out["volatility_20d"] = close_s.pct_change().rolling(20, min_periods=20).std().to_numpy()
    if "volatility_60d" in feature_names:
        out["volatility_60d"] = close_s.pct_change().rolling(60, min_periods=60).std().to_numpy()

    for n in (5, 10, 20, 60):
        ma_key = f"ma_{n}"
        bias_key = f"ma_bias_{n}"
        if ma_key in feature_names or bias_key in feature_names:
            ma_s = close_s.rolling(n, min_periods=n).mean()
            ma = ma_s.to_numpy()
            if ma_key in feature_names:
                out[ma_key] = ma
            if bias_key in feature_names:
                out[bias_key] = (close / (ma + 1e-12)) - 1.0
            if n == 5 and "volume_ma5_ratio" in feature_names:
                volume_ma5 = volume_s.rolling(5, min_periods=5).mean()
                out["volume_ma5_ratio"] = (volume_s / (volume_ma5 + 1e-12)).to_numpy()
            if n == 20:
                if "volume_ma20_ratio" in feature_names:
                    volume_ma20 = volume_s.rolling(20, min_periods=20).mean()
                    out["volume_ma20_ratio"] = (volume_s / (volume_ma20 + 1e-12)).to_numpy()
                if "amount_ma_ratio" in feature_names:
                    amount_ma20 = amount_s.rolling(20, min_periods=20).mean()
                    out["amount_ma_ratio"] = (amount_s / (amount_ma20 + 1e-12)).to_numpy()
                if "trend_strength" in feature_names:
                    out["trend_strength"] = ((close_s - ma_s) / (ma_s + 1e-12)).to_numpy()
                if "close_above_ma20" in feature_names:
                    out["close_above_ma20"] = (close_s > ma_s).astype(float).to_numpy()

    if "rsi_14" in feature_names:
        out["rsi_14"] = _rsi(close, 14)

    if "macd" in feature_names or "macd_signal" in feature_names or "macd_hist" in feature_names:
        macd, signal, hist = _macd(close)
        if "macd" in feature_names:
            out["macd"] = macd
        if "macd_signal" in feature_names:
            out["macd_signal"] = signal
        if "macd_hist" in feature_names:
            out["macd_hist"] = hist

    if "atr_14" in feature_names:
        out["atr_14"] = _atr(high, low, close, 14)

    if "obv" in feature_names:
        out["obv"] = _obv(close, volume)

    if "pe" in feature_names:
        out["pe"] = _series("pe").to_numpy(dtype=float)
    if "pb" in feature_names:
        out["pb"] = _series("pb").to_numpy(dtype=float)
    if "turnover_rate" in feature_names:
        out["turnover_rate"] = turnover_rate_s.to_numpy(dtype=float)
    if "buy_lg_amount" in feature_names:
        out["buy_lg_amount"] = buy_lg_amount_s.to_numpy(dtype=float)
    if "net_amount" in feature_names:
        out["net_amount"] = net_mf_amount_s.to_numpy(dtype=float)
    if "net_amount_rate" in feature_names:
        if "net_amount_rate" in base.columns:
            out["net_amount_rate"] = net_amount_rate_s.to_numpy(dtype=float)
        else:
            out["net_amount_rate"] = (net_mf_amount_s / (amount_s.replace(0, np.nan))).to_numpy(dtype=float)
    if "market_cap" in feature_names:
        out["market_cap"] = total_mv_s.to_numpy(dtype=float)

    out["trade_date"] = base["trade_date"].astype(str)
    out["symbol"] = base["symbol"].astype(str)
    return out
