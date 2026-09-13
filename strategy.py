"""
Strategy engine: evaluates indicators on the latest candle and
emits buy / sell / hold decisions. Drives the Portfolio.
"""
from config import RISK, SYMBOL
from indicators import compute_indicators
from market_data import fetch_latest_candles, get_current_price
from portfolio import PORTFOLIO


def evaluate():
    """Called every minute by the scheduler."""
    if not PORTFOLIO.running:
        return

    df = fetch_latest_candles(n=200)
    if len(df) < RISK.ema_trend + 5:
        PORTFOLIO.last_signal = "warming up indicators..."
        return

    df = compute_indicators(df, RISK)
    cur = df.iloc[-1]
    prev = df.iloc[-2]
    price = float(cur["close"])

    # ---- check existing positions for SL / TP / sell signals ----
    for pos in list(PORTFOLIO.positions):  # iterate over copy
        if price <= pos.stop_loss:
            PORTFOLIO.close_position(pos, price, "STOP-LOSS")
            continue
        if price >= pos.take_profit:
            PORTFOLIO.close_position(pos, price, "TAKE-PROFIT")
            continue
        # indicator-based exit
        sell_sig = (
            float(cur["rsi"]) > RISK.rsi_overbought
            or (float(prev["macd"]) >= float(prev["macd_signal"])
                and float(cur["macd"]) < float(cur["macd_signal"]))
        )
        if sell_sig:
            PORTFOLIO.close_position(pos, price, f"SIGNAL RSI={float(cur['rsi']):.1f}")

    # ---- entry signal ----
    already_in = any(p.symbol == SYMBOL for p in PORTFOLIO.positions)
    if not already_in:
        rsi_ok = float(cur["rsi"]) < RISK.rsi_oversold
        macd_cross_up = (
            float(prev["macd"]) <= float(prev["macd_signal"])
            and float(cur["macd"]) > float(cur["macd_signal"])
        )
        trend_ok = price > float(cur["ema_trend"])
        if rsi_ok and macd_cross_up and trend_ok:
            PORTFOLIO.open_long(SYMBOL, price,
                                f"RSI={float(cur['rsi']):.1f} MACD cross above EMA-trend")
        else:
            reasons = []
            if not rsi_ok: reasons.append(f"RSI({float(cur['rsi']):.1f}) not oversold")
            if not macd_cross_up: reasons.append("no MACD bull cross")
            if not trend_ok: reasons.append("below EMA-trend")
            PORTFOLIO.last_signal = "HOLD — " + "; ".join(reasons)


def latest_indicator_readout() -> dict:
    """For the dashboard / status messages."""
    df = compute_indicators(fetch_latest_candles(n=200), RISK)
    if len(df) == 0:
        return {}
    c = df.iloc[-1]
    return {
        "price": float(c["close"]),
        "rsi": float(c["rsi"]),
        "macd": float(c["macd"]),
        "macd_signal": float(c["macd_signal"]),
        "ema_trend": float(c["ema_trend"]),
    }
