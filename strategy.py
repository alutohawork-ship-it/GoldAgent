from dataclasses import dataclass
import pandas as pd


@dataclass
class Signal:
    action: str   # "BUY" | "SELL" | "HOLD"
    reason: str
    price: float
    atr: float


def generate_signal(df: pd.DataFrame) -> Signal:
    """Sinyal dihitung dari bar TERAKHIR yang sudah close."""
    last, prev = df.iloc[-1], df.iloc[-2]

    cross_up = prev.ema_fast <= prev.ema_slow and last.ema_fast > last.ema_slow
    cross_dn = prev.ema_fast >= prev.ema_slow and last.ema_fast < last.ema_slow
    uptrend = last.close > last.ema_trend
    downtrend = last.close < last.ema_trend

    if cross_up and uptrend and last.rsi < 70:
        return Signal("BUY", f"EMA cross up, di atas EMA200, RSI={last.rsi:.1f}",
                      last.close, last.atr)
    if cross_dn and downtrend and last.rsi > 30:
        return Signal("SELL", f"EMA cross down, di bawah EMA200, RSI={last.rsi:.1f}",
                      last.close, last.atr)
    return Signal("HOLD", "Tidak ada setup", last.close, last.atr)
