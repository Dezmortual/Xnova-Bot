"""Central configuration — loaded from .env, overridable at runtime."""
import os
from dotenv import load_dotenv

load_dotenv()


def _float(key: str, default: float) -> float:
    v = os.getenv(key)
    return float(v) if v else default


def _int(key: str, default: int) -> int:
    v = os.getenv(key)
    return int(v) if v else default


def _str(key: str, default: str) -> str:
    return os.getenv(key, default)


def _id_list(key: str) -> set:
    v = os.getenv(key, "").strip()
    if not v:
        return set()
    return {int(x.strip()) for x in v.split(",") if x.strip().isdigit()}


# --- Telegram ---
TELEGRAM_BOT_TOKEN = _str("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_IDS = _id_list("ALLOWED_USER_IDS")

# --- Web ---
WEB_PORT = _int("WEB_PORT", 5050)

# --- Account ---
START_BALANCE = _float("START_BALANCE", 10000.0)
SYMBOL = _str("SYMBOL", "BTC/USDT")

# --- Risk (mutable at runtime via settings) ---
class RiskConfig:
    stop_loss_pct: float = _float("STOP_LOSS_PCT", 2.0)
    take_profit_pct: float = _float("TAKE_PROFIT_PCT", 4.0)
    max_position_pct: float = _float("MAX_POSITION_PCT", 5.0)
    max_open_positions: int = _int("MAX_OPEN_POSITIONS", 3)
    rsi_period: int = _int("RSI_PERIOD", 14)
    rsi_oversold: float = _float("RSI_OVERSOLD", 35.0)
    rsi_overbought: float = _float("RSI_OVERBOUGHT", 65.0)
    ema_fast: int = _int("EMA_FAST", 12)
    ema_slow: int = _int("EMA_SLOW", 26)
    ema_signal: int = _int("EMA_SIGNAL", 9)
    ema_trend: int = _int("EMA_TREND", 50)


RISK = RiskConfig()
