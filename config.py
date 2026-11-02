import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Simbol
    symbol_yf: str = "GC=F"          # Gold futures di Yahoo Finance (data backtest/paper)
    symbol_mt5: str = "XAUUSD"       # Sesuaikan dengan nama simbol di broker Anda
    timeframe: str = "1h"
    history_period: str = "730d"     # Batas maksimal yfinance untuk data 1h

    # Indikator
    ema_fast: int = 20
    ema_slow: int = 50
    ema_trend: int = 200
    rsi_period: int = 14
    atr_period: int = 14

    # Stop loss / take profit (kelipatan ATR)
    sl_atr_mult: float = 1.5
    tp_atr_mult: float = 3.0         # Risk:Reward = 1:2

    # Manajemen risiko
    initial_equity: float = 10_000
    risk_per_trade: float = 0.01     # 1% equity per trade
    max_daily_loss: float = 0.03     # Berhenti trading jika rugi 3% dalam sehari
    max_open_positions: int = 1

    # Spesifikasi kontrak XAUUSD (1 lot = 100 oz)
    contract_size: float = 100
    min_lot: float = 0.01
    lot_step: float = 0.01
    max_lot: float = 5.0
    spread: float = 0.30             # Asumsi spread dalam USD

    # LLM
    use_llm: bool = os.getenv("USE_LLM", "false").lower() == "true"
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-4-5")
    llm_min_confidence: float = 0.6

    # Loop
    loop_seconds: int = 60
