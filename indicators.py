import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame, cfg) -> pd.DataFrame:
    df = df.copy()
    df["ema_fast"] = df["close"].ewm(span=cfg.ema_fast, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=cfg.ema_slow, adjust=False).mean()
    df["ema_trend"] = df["close"].ewm(span=cfg.ema_trend, adjust=False).mean()

    # RSI (Wilder)
    delta = df["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / cfg.rsi_period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / cfg.rsi_period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - 100 / (1 + rs)

    # ATR (Wilder)
    prev_close = df["close"].shift()
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1 / cfg.atr_period, adjust=False).mean()

    # Buang periode warm-up agar EMA200 valid
    return df.iloc[cfg.ema_trend:].dropna()
