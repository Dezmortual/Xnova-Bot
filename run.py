"""
X-NOVA Paper-Trading Bot — flat-layout entry point.
All modules live in the same directory (mobile-GitHub-upload friendly).
"""
import os
import sys
import time
import threading
import logging

# Ensure our own directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from market_data import tick_market
from strategy import evaluate as run_strategy
from config import WEB_PORT
from webapp import create_app
from telegram_bot import start_polling

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

TICK_INTERVAL_SEC = 5


def tick_loop():
    while True:
        try:
            tick_market()
            run_strategy()
        except Exception as e:
            logging.exception("tick error: %s", e)
        time.sleep(TICK_INTERVAL_SEC)


def main():
    threading.Thread(target=tick_loop, daemon=True).start()
    logging.info("Market ticker started (every %ss)", TICK_INTERVAL_SEC)

    app = create_app()
    web_port = int(os.environ.get("PORT", WEB_PORT))
    threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": web_port, "debug": False, "use_reloader": False},
        daemon=True,
    ).start()
    logging.info("Web dashboard on port %s", web_port)

    tg_ok = start_polling()

    print(f"\n🚀 X-NOVA paper-trading bot running!")
    print(f"   Dashboard port: {web_port}")
    if tg_ok:
        print("   Telegram:  poller started — message @dezmorbot")
    print(f"   ⚠️  PAPER TRADING ONLY — no real money\n")

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
