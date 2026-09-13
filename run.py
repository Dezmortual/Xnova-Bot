"""
X-NOVA Paper-Trading Bot — entry point.
Simple & reliable: Flask in one thread, market ticker in another,
Telegram long-polling in a third. No fancy asyncio/job queue to go wrong.
"""
import os
import sys
import time
import threading
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading.market_data import tick_market
from trading.strategy import evaluate as run_strategy
from trading.config import WEB_PORT
from web.app import create_app
from bot.telegram_bot import start_polling

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

TICK_INTERVAL_SEC = 5


def tick_loop():
    """Market + strategy loop. Runs in a daemon thread, forever."""
    while True:
        try:
            tick_market()
            run_strategy()
        except Exception as e:
            logging.exception("tick error: %s", e)
        time.sleep(TICK_INTERVAL_SEC)


def main():
    # 1. Market tick thread
    threading.Thread(target=tick_loop, daemon=True).start()
    logging.info("Market ticker started (every %ss)", TICK_INTERVAL_SEC)

    # 2. Web dashboard thread (use PORT env var if set by cloud host)
    app = create_app()
    web_port = int(os.environ.get("PORT", WEB_PORT))
    threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": web_port, "debug": False, "use_reloader": False},
        daemon=True,
    ).start()
    logging.info("Web dashboard on port %s", web_port)

    # 3. Telegram long-polling thread
    tg_ok = start_polling()

    print(f"\n🚀 X-NOVA paper-trading bot running!")
    print(f"   Dashboard port: {web_port}")
    if tg_ok:
        print("   Telegram:  poller started — message @dezmorbot")
    else:
        print("   Telegram:  disabled (no token)")
    print(f"   ⚠️  PAPER TRADING ONLY — no real money\n")

    # Main thread just sleeps
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
