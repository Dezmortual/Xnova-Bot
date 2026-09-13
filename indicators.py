"""Technical indicators: RSI, MACD, EMA — pure numpy/pandas."""
import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def compute_indicators(df: pd.DataFrame, risk) -> pd.DataFrame:
    """Add indicator columns to a DataFrame that has a 'close' column."""
    df = df.copy()
    df["ema_fast"] = ema(df["close"], risk.ema_fast)
    df["ema_slow"] = ema(df["close"], risk.ema_slow)
    df["ema_trend"] = ema(df["close"], risk.ema_trend)
    df["rsi"] = rsi(df["close"], risk.rsi_period)
    df["macd"], df["macd_signal"], df["macd_hist"] = macd(
        df["close"], risk.ema_fast, risk.ema_slow, risk.ema_signal
    )
    return df
