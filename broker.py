import os
from dataclasses import dataclass


@dataclass
class Position:
    side: str
    lots: float
    entry: float
    sl: float
    tp: float
    open_time: object


class PaperBroker:
    def __init__(self, cfg):
        self.cfg = cfg
        self.equity = cfg.initial_equity
        self.positions: list[Position] = []
        self.closed: list[dict] = []

    def open_positions_count(self) -> int:
        return len(self.positions)

    def open(self, order, ts=None):
        half = self.cfg.spread / 2
        entry = order.entry + half if order.side == "BUY" else order.entry - half
        self.positions.append(Position(order.side, order.lots, entry, order.sl, order.tp, ts))
        return True

    def update(self, bar, ts):
        """Cek SL/TP memakai high/low bar. Jika keduanya kena di bar yang sama, anggap SL (konservatif)."""
        for p in list(self.positions):
            if p.side == "BUY":
                hit_sl, hit_tp = bar.low <= p.sl, bar.high >= p.tp
            else:
                hit_sl, hit_tp = bar.high >= p.sl, bar.low <= p.tp
            if hit_sl or hit_tp:
                self._close(p, p.sl if hit_sl else p.tp, ts, "SL" if hit_sl else "TP")

    def _close(self, p, exit_price, ts, why):
        direction = 1 if p.side == "BUY" else -1
        pnl = (exit_price - p.entry) * direction * p.lots * self.cfg.contract_size
        self.equity += pnl
        self.positions.remove(p)
        self.closed.append({"side": p.side, "lots": p.lots, "entry": p.entry, "exit": exit_price,
                            "open_time": p.open_time, "close_time": ts, "pnl": pnl, "reason": why})


class MT5Broker:
    def __init__(self, cfg):
        import MetaTrader5 as mt5
        self.mt5, self.cfg, self.symbol = mt5, cfg, cfg.symbol_mt5
        ok = mt5.initialize(login=int(os.environ["MT5_LOGIN"]),
                            password=os.environ["MT5_PASSWORD"],
                            server=os.environ["MT5_SERVER"])
        if not ok:
            raise RuntimeError(f"MT5 init gagal: {mt5.last_error()}")
        if not mt5.symbol_select(self.symbol, True):
            raise RuntimeError(f"Simbol {self.symbol} tidak tersedia")

    @property
    def equity(self) -> float:
        return self.mt5.account_info().equity

    def open_positions_count(self) -> int:
        return len(self.mt5.positions_get(symbol=self.symbol) or [])

    def current_price(self, side: str) -> float:
        tick = self.mt5.symbol_info_tick(self.symbol)
        return tick.ask if side == "BUY" else tick.bid

    def open(self, order, ts=None):
        mt5 = self.mt5
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(order.lots),
            "type": mt5.ORDER_TYPE_BUY if order.side == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": self.current_price(order.side),
            "sl": order.sl,
            "tp": order.tp,
            "deviation": 20,
            "magic": 777001,
            "comment": "gold-ai-agent",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,  # Ganti ke FOK jika broker menolak
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Order gagal: {result}")
        return True
