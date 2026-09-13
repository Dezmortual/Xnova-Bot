"""
Telegram bot — straight HTTP long-polling implementation.
No framework magic, totally predictable and easy to debug.
"""
import time
import html
import threading
import requests
import logging
from datetime import datetime, timezone

from trading.config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS, RISK, SYMBOL
from trading.market_data import get_current_price
from trading.portfolio import PORTFOLIO
from trading.strategy import latest_indicator_readout

logger = logging.getLogger("telegram")

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

BANNER = (
    "🚀 <b>X-NOVA Paper-Trading Bot</b>\n"
    "✅ Safe simulation mode (no real money)\n"
    "⚡ Indicator-based strategy\n"
    "💰 Let's test this responsibly.\n\n"
    "Use /help to see commands."
)


def _allowed(uid: int) -> bool:
    return (not ALLOWED_USER_IDS) or (uid in ALLOWED_USER_IDS)


def _ts(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def send(chat_id, text, parse_mode="HTML", reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(f"{API}/sendMessage", json=payload, timeout=15)
        logger.info("sendMessage to %s -> %s", chat_id, r.status_code)
        if not r.ok:
            logger.error("sendMessage failed: %s %s", r.status_code, r.text[:500])
    except Exception as e:
        logger.exception("send error: %s", e)


def _status_text() -> str:
    price = get_current_price()
    eq = PORTFOLIO.equity(price)
    pnl_pct = PORTFOLIO.total_pnl_pct(price)
    ind = latest_indicator_readout()
    status = "🟢 RUNNING" if PORTFOLIO.running else "🔴 PAUSED"

    lines = [
        f"<b>Status:</b> {status}",
        f"<b>Symbol:</b> {html.escape(SYMBOL)}",
        f"<b>Price:</b> ${price:,.2f}",
        f"<b>Cash:</b> ${PORTFOLIO.cash:,.2f}",
        f"<b>Equity:</b> ${eq:,.2f}  ({pnl_pct:+.2f}%)",
        f"<b>Open positions:</b> {len(PORTFOLIO.positions)}/{RISK.max_open_positions}",
        "",
        "<b>Indicators:</b>",
        f"  RSI({RISK.rsi_period}): {ind.get('rsi', 0):.2f}",
        f"  MACD: {ind.get('macd', 0):.4f} / Signal: {ind.get('macd_signal', 0):.4f}",
        f"  EMA({RISK.ema_trend}): {ind.get('ema_trend', 0):,.2f}",
        "",
        f"<b>Last signal:</b> {html.escape(PORTFOLIO.last_signal)}",
    ]
    if PORTFOLIO.positions:
        lines += ["", "<b>Open positions:</b>"]
        for p in PORTFOLIO.positions:
            cur_pnl = (price - p.entry_price) * p.quantity
            cur_pnl_pct = (price - p.entry_price) / p.entry_price * 100
            lines.append(
                f"  #{p.id} entry ${p.entry_price:,.2f} size ${p.size_usdt:,.2f} "
                f"PnL {cur_pnl:+,.2f} ({cur_pnl_pct:+.2f}%) "
                f"SL ${p.stop_loss:,.2f} / TP ${p.take_profit:,.2f}"
            )
    return "\n".join(lines)


def handle_message(msg):
    """Dispatch one incoming message."""
    chat_id = msg["chat"]["id"]
    uid = msg["from"]["id"]
    text = (msg.get("text") or "").strip()
    uname = msg["from"].get("username", "")

    logger.info("MSG from %s (id=%s): %r", uname, uid, text)

    # Access control
    if not _allowed(uid):
        send(chat_id,
             f"⛔ Access denied.\nYour Telegram ID is <code>{uid}</code>\n"
             f"Add it to ALLOWED_USER_IDS in .env to enable access.",
             parse_mode="HTML")
        return

    cmd = text.split()[0].lower() if text else ""
    args = text.split()[1:]

    if cmd in ("/start", "/help"):
        if cmd == "/start":
            send(chat_id, BANNER, parse_mode="HTML")
        send(chat_id,
             "<b>Commands:</b>\n"
             "/status   — balance, P&amp;L, positions, indicators\n"
             "/trades   — last 10 trades\n"
             "/startbot — start auto-trading\n"
             "/stopbot  — pause auto-trading\n"
             "/settings — show risk settings\n"
             "/setrisk &lt;sl%&gt; &lt;tp%&gt; &lt;pos%&gt; &lt;max_pos&gt;  (e.g. /setrisk 2 4 5 3)\n"
             "/reset    — reset paper account\n"
             "/myid     — show your Telegram ID\n"
             "/help     — this message",
             parse_mode="HTML")

    elif cmd == "/status":
        send(chat_id, _status_text(), parse_mode="HTML")

    elif cmd == "/startbot":
        PORTFOLIO.running = True
        PORTFOLIO.save()
        send(chat_id, "🟢 Auto-trading <b>STARTED</b>.\n" + _status_text(), parse_mode="HTML")

    elif cmd == "/stopbot":
        PORTFOLIO.running = False
        PORTFOLIO.save()
        send(chat_id, "🔴 Auto-trading <b>PAUSED</b>.", parse_mode="HTML")

    elif cmd == "/trades":
        recent = PORTFOLIO.trades[-10:]
        if not recent:
            send(chat_id, "No trades yet.")
            return
        lines = ["<b>Recent trades:</b>"]
        for t in recent:
            pnl_str = f" PnL {t.pnl:+,.2f}" if t.side == "sell" else ""
            lines.append(
                f"[{_ts(t.timestamp)}] {t.side.upper()} "
                f"{t.quantity:.6f} @ ${t.price:,.2f}{pnl_str} — {html.escape(t.reason)}"
            )
        send(chat_id, "\n".join(lines), parse_mode="HTML")

    elif cmd == "/settings":
        send(chat_id,
             f"<b>Risk settings:</b>\n"
             f"  Stop-loss: {RISK.stop_loss_pct}%\n"
             f"  Take-profit: {RISK.take_profit_pct}%\n"
             f"  Max position size: {RISK.max_position_pct}%\n"
             f"  Max open positions: {RISK.max_open_positions}\n"
             f"  RSI period/oversold/overbought: {RISK.rsi_period} / {RISK.rsi_oversold} / {RISK.rsi_overbought}\n"
             f"  MACD fast/slow/signal: {RISK.ema_fast}/{RISK.ema_slow}/{RISK.ema_signal}\n"
             f"  EMA trend: {RISK.ema_trend}",
             parse_mode="HTML")

    elif cmd == "/setrisk":
        if len(args) != 4:
            send(chat_id, "Usage: <code>/setrisk &lt;sl%&gt; &lt;tp%&gt; &lt;pos%&gt; &lt;max_pos&gt;</code>\nExample: /setrisk 2 4 5 3", parse_mode="HTML")
            return
        try:
            sl, tp, pos, mx = float(args[0]), float(args[1]), float(args[2]), int(args[3])
            if sl <= 0 or tp <= 0 or pos <= 0 or pos > 100 or mx < 1 or mx > 20:
                raise ValueError
            RISK.stop_loss_pct = sl
            RISK.take_profit_pct = tp
            RISK.max_position_pct = pos
            RISK.max_open_positions = mx
            send(chat_id, "✅ Settings updated.\n" + _status_text(), parse_mode="HTML")
        except Exception:
            send(chat_id, "❌ Invalid arguments.")

    elif cmd == "/reset":
        PORTFOLIO.reset()
        send(chat_id, "🔄 Account reset to starting balance.", parse_mode="HTML")

    elif cmd == "/myid":
        send(chat_id,
             f"👤 <b>Your Telegram info:</b>\n"
             f"  ID: <code>{uid}</code>\n"
             f"  Username: @{html.escape(uname)}\n"
             f"  Name: {html.escape(msg['from'].get('first_name',''))}",
             parse_mode="HTML")

    else:
        send(chat_id, f"Unknown command: {html.escape(cmd)}\nSend /help for the command list.")


class TelegramPoller(threading.Thread):
    """Simple long-polling loop — runs in a daemon thread."""

    def __init__(self):
        super().__init__(daemon=True)
        self._offset = 0

    def run(self):
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
            logger.warning("No TELEGRAM_BOT_TOKEN set — Telegram disabled.")
            return
        # Delete any existing webhook to ensure polling works
        try:
            requests.get(f"{API}/deleteWebhook", timeout=10)
            me = requests.get(f"{API}/getMe", timeout=10).json()
            logger.info("Telegram bot: @%s (%s)", me["result"].get("username"), me["result"].get("first_name"))
        except Exception as e:
            logger.error("Failed to contact Telegram API: %s", e)
            return

        logger.info("Long-polling started")
        while True:
            try:
                r = requests.post(
                    f"{API}/getUpdates",
                    json={"offset": self._offset, "timeout": 30, "allowed_updates": ["message"]},
                    timeout=35,
                )
                if not r.ok:
                    logger.error("getUpdates %s: %s", r.status_code, r.text[:200])
                    time.sleep(3)
                    continue
                data = r.json()
                for upd in data.get("result", []):
                    upd_id = upd["update_id"]
                    self._offset = upd_id + 1
                    if "message" in upd:
                        try:
                            handle_message(upd["message"])
                        except Exception as e:
                            logger.exception("Handler error: %s", e)
                            # Try to notify the user
                            try:
                                send(upd["message"]["chat"]["id"],
                                     f"⚠️ Error handling command: {html.escape(str(e))}\nCheck server logs.")
                            except Exception:
                                pass
            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                logger.exception("Polling error: %s", e)
                time.sleep(3)


def start_polling():
    if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "your_telegram_bot_token_here":
        t = TelegramPoller()
        t.start()
        return True
    return False
