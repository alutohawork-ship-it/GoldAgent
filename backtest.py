import pandas as pd
from broker import PaperBroker
from risk import RiskManager
from strategy import generate_signal


def run_backtest(df: pd.DataFrame, cfg, reviewer=None):
    broker, risk = PaperBroker(cfg), RiskManager(cfg)
    pending = None
    equity_curve = []

    for i in range(1, len(df)):
        ts, bar = df.index[i], df.iloc[i]

        # 1) Eksekusi sinyal dari bar sebelumnya di harga OPEN bar ini (hindari look-ahead)
        if pending is not None:
            order = risk.build_order(pending.action, bar.open, pending.atr, broker.equity)
            if order:
                approved, _ = reviewer.review(df.iloc[:i], pending, order) if reviewer else (True, "")
                if approved:
                    broker.open(order, ts)
            pending = None

        # 2) Cek SL/TP
        broker.update(bar, ts)

        # 3) Hitung sinyal di close bar ini
        risk.update_day(ts, broker.equity)
        sig = generate_signal(df.iloc[i - 1:i + 1])
        if sig.action != "HOLD":
            ok, _ = risk.can_trade(broker.equity, broker.open_positions_count())
            if ok:
                pending = sig

        equity_curve.append(broker.equity)

    return broker, pd.Series(equity_curve, index=df.index[1:])


def print_report(broker, equity, cfg):
    trades = pd.DataFrame(broker.closed)
    print("\n===== HASIL BACKTEST =====")
    print(f"Periode       : {equity.index[0]} -> {equity.index[-1]}")
    print(f"Equity awal   : ${cfg.initial_equity:,.2f}")
    print(f"Equity akhir  : ${broker.equity:,.2f}")
    print(f"Return        : {(broker.equity / cfg.initial_equity - 1) * 100:.2f}%")
    if trades.empty:
        print("Tidak ada trade.")
        return
    wins, losses = trades[trades.pnl > 0], trades[trades.pnl <= 0]
    pf = wins.pnl.sum() / abs(losses.pnl.sum()) if not losses.empty else float("inf")
    dd = (equity / equity.cummax() - 1).min() * 100
    print(f"Jumlah trade  : {len(trades)}")
    print(f"Win rate      : {len(wins) / len(trades) * 100:.1f}%")
    print(f"Profit factor : {pf:.2f}")
    print(f"Max drawdown  : {dd:.2f}%")
    trades.to_csv("backtest_trades.csv", index=False)
    print("Detail trade disimpan ke backtest_trades.csv")
