import math
from dataclasses import dataclass


@dataclass
class Order:
    side: str
    lots: float
    entry: float
    sl: float
    tp: float


class RiskManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.day = None
        self.day_start_equity = None

    def update_day(self, ts, equity: float):
        d = ts.date()
        if d != self.day:
            self.day = d
            self.day_start_equity = equity

    def can_trade(self, equity: float, open_positions: int):
        if open_positions >= self.cfg.max_open_positions:
            return False, "Maks posisi terbuka tercapai"
        if self.day_start_equity and equity <= self.day_start_equity * (1 - self.cfg.max_daily_loss):
            return False, "Batas rugi harian tercapai, trading dihentikan hari ini"
        return True, ""

    def build_order(self, side: str, entry: float, atr: float, equity: float):
        c = self.cfg
        sl_dist = atr * c.sl_atr_mult
        tp_dist = atr * c.tp_atr_mult
        if sl_dist <= 0:
            return None

        risk_amount = equity * c.risk_per_trade
        lots = risk_amount / (sl_dist * c.contract_size)
        lots = math.floor(lots / c.lot_step) * c.lot_step
        lots = round(min(lots, c.max_lot), 2)
        if lots < c.min_lot:
            return None  # Equity terlalu kecil untuk SL sejauh ini

        if side == "BUY":
            sl, tp = entry - sl_dist, entry + tp_dist
        else:
            sl, tp = entry + sl_dist, entry - tp_dist
        return Order(side, lots, round(entry, 2), round(sl, 2), round(tp, 2))
