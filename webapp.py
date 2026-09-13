"""Flask web dashboard."""
import json
import time
from datetime import datetime, timezone
import os
from flask import Flask, render_template, jsonify, request

from config import RISK, SYMBOL
from market_data import fetch_latest_candles, get_current_price
from portfolio import PORTFOLIO
from indicators import compute_indicators
from strategy import evaluate as run_strategy


def create_app() -> Flask:
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"), static_folder=None)

    @app.route("/")
    def index():
        return render_template("index.html", symbol=SYMBOL)

    @app.route("/healthz")
    def healthz():
        return {"ok": True, "running": PORTFOLIO.running, "price": get_current_price()}

    @app.route("/api/state")
    def api_state():
        price = get_current_price()
        ind = {}
        df = compute_indicators(fetch_latest_candles(200), RISK)
        if len(df) > 0:
            c = df.iloc[-1]
            ind = {
                "rsi": round(float(c["rsi"]), 2),
                "macd": round(float(c["macd"]), 4),
                "macd_signal": round(float(c["macd_signal"]), 4),
                "ema_trend": round(float(c["ema_trend"]), 2),
            }
        positions = []
        for p in PORTFOLIO.positions:
            cur_pnl = (price - p.entry_price) * p.quantity
            positions.append({
                "id": p.id,
                "entry_price": p.entry_price,
                "quantity": p.quantity,
                "size_usdt": p.size_usdt,
                "stop_loss": p.stop_loss,
                "take_profit": p.take_profit,
                "pnl": round(cur_pnl, 2),
                "pnl_pct": round((price - p.entry_price) / p.entry_price * 100, 2),
                "entry_time": datetime.fromtimestamp(p.entry_time, tz=timezone.utc).isoformat(),
            })
        trades = []
        for t in PORTFOLIO.trades[-30:]:
            trades.append({
                "id": t.id,
                "side": t.side,
                "price": t.price,
                "quantity": t.quantity,
                "pnl": round(t.pnl, 2),
                "reason": t.reason,
                "time": datetime.fromtimestamp(t.timestamp, tz=timezone.utc).isoformat(),
            })
        # equity curve (approximate from trades + current price —
        # paper track: rebuild by walking trade history)
        equity_curve = []
        cash = PORTFOLIO.initial_balance
        # We can't perfectly reconstruct history without candles, so emit a simple
        # series: initial balance -> current equity, marking realized pnl points.
        equity_curve.append({"t": PORTFOLIO.initial_balance and 0, "eq": PORTFOLIO.initial_balance})
        realized_pnl = sum(t.pnl for t in PORTFOLIO.trades if t.side == "sell")
        equity_curve.append({"t": time.time()*1000, "eq": round(PORTFOLIO.equity(price), 2)})

        return jsonify({
            "running": PORTFOLIO.running,
            "symbol": SYMBOL,
            "price": price,
            "cash": round(PORTFOLIO.cash, 2),
            "equity": round(PORTFOLIO.equity(price), 2),
            "pnl_pct": round(PORTFOLIO.total_pnl_pct(price), 2),
            "initial_balance": PORTFOLIO.initial_balance,
            "positions_open": len(PORTFOLIO.positions),
            "max_positions": RISK.max_open_positions,
            "last_signal": PORTFOLIO.last_signal,
            "indicators": ind,
            "positions": positions,
            "trades": list(reversed(trades)),
            "candles": _candles_json(df.tail(100)),
            "risk": {
                "stop_loss_pct": RISK.stop_loss_pct,
                "take_profit_pct": RISK.take_profit_pct,
                "max_position_pct": RISK.max_position_pct,
                "max_open_positions": RISK.max_open_positions,
            },
        })

    @app.route("/api/control", methods=["POST"])
    def api_control():
        data = request.get_json(force=True) or {}
        action = data.get("action")
        if action == "start":
            PORTFOLIO.running = True
        elif action == "stop":
            PORTFOLIO.running = False
        elif action == "reset":
            PORTFOLIO.reset()
        elif action == "tick":
            # manual trigger (debug)
            from market_data import tick_market
            tick_market()
            run_strategy()
        PORTFOLIO.save()
        return jsonify({"ok": True, "running": PORTFOLIO.running})

    return app


def _candles_json(df):
    out = []
    for _, r in df.iterrows():
        out.append({
            "t": int(r["timestamp"] * 1000),
            "o": float(r["open"]),
            "h": float(r["high"]),
            "l": float(r["low"]),
            "c": float(r["close"]),
            "v": float(r["volume"]),
        })
    return out
