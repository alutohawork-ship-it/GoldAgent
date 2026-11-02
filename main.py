import argparse
import logging
import time

from backtest import print_report, run_backtest
from broker import MT5Broker, PaperBroker
from config import Config
from data import fetch_mt5, fetch_yf
from indicators import add_indicators
from llm_agent import LLMReviewer
from risk import RiskManager
from strategy import generate_signal

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s",
                    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()])
log = logging.getLogger("gold-agent")


def run_realtime(cfg: Config, live: bool):
    broker = MT5Broker(cfg) if live else PaperBroker(cfg)
    risk = RiskManager(cfg)
    reviewer = LLMReviewer(cfg.llm_model, cfg.llm_min_confidence) if cfg.use_llm else None
    last_bar_time = None
    log.info(f"Agent mulai | mode={'LIVE' if live else 'PAPER'} | LLM={'ON' if reviewer else 'OFF'}")

    while True:
        try:
            raw = fetch_mt5(cfg.symbol_mt5, cfg.timeframe) if live \
                else fetch_yf(cfg.symbol_yf, cfg.timeframe, "60d")
            df = add_indicators(raw, cfg)
            closed = df.iloc[:-1]  # Bar terakhir masih berjalan, jangan dipakai untuk sinyal

            if not live:
                broker.update(df.iloc[-1], df.index[-1])

            bar_time = closed.index[-1]
            if bar_time != last_bar_time:
                last_bar_time = bar_time
                equity = broker.equity
                risk.update_day(bar_time, equity)
                sig = generate_signal(closed)
                log.info(f"Bar {bar_time} | close={sig.price:.2f} | {sig.action} | {sig.reason} | equity=${equity:,.2f}")

                if sig.action != "HOLD":
                    ok, why = risk.can_trade(equity, broker.open_positions_count())
                    if not ok:
                        log.warning(f"Dilewati: {why}")
                    else:
                        entry = broker.current_price(sig.action) if live else float(df.iloc[-1].close)
                        order = risk.build_order(sig.action, entry, sig.atr, equity)
                        if order is None:
                            log.warning("Lot terlalu kecil, order dibatalkan")
                        else:
                            approved, reason = reviewer.review(closed, sig, order) if reviewer else (True, "LLM off")
                            log.info(f"Review LLM: {'APPROVE' if approved else 'REJECT'} - {reason}")
                            if approved:
                                broker.open(order, bar_time)
                                log.info(f"ORDER: {order}")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            log.exception(f"Error di loop: {e}")

        time.sleep(cfg.loop_seconds)


def main():
    p = argparse.ArgumentParser(description="AI Agent Trading Gold (XAUUSD)")
    p.add_argument("mode", choices=["backtest", "paper", "live"])
    p.add_argument("--llm-backtest", action="store_true",
                   help="Pakai LLM saat backtest (memakan biaya API)")
    args = p.parse_args()
    cfg = Config()

    if args.mode == "backtest":
        df = add_indicators(fetch_yf(cfg.symbol_yf, cfg.timeframe, cfg.history_period), cfg)
        reviewer = LLMReviewer(cfg.llm_model, cfg.llm_min_confidence) if args.llm_backtest else None
        broker, equity = run_backtest(df, cfg, reviewer)
        print_report(broker, equity, cfg)
    else:
        if args.mode == "live":
            confirm = input("⚠️  Mode LIVE akan memakai uang sungguhan. Ketik 'YA' untuk lanjut: ")
            if confirm != "YA":
                return
        run_realtime(cfg, live=(args.mode == "live"))


if __name__ == "__main__":
    main()
