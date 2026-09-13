"""
Market data feed.
- Default: simulated random-walk candles (great for testing, no API key needed).
- To use real data, replace `fetch_latest_candles` with a call to your exchange
  (Binance /api/v3/klines, Bybit /v5/market/kline, etc.) keeping the same schema.
"""
import time
import random
import math
from collections import deque
from dataclasses import dataclass
from typing import List, Tuple
import pandas as pd


@dataclass
class Candle:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


class SimulatedMarket:
    """Geometric Brownian Motion style random walk around a base price."""

    def __init__(self, start_price: float = 65000.0, seed: int = 42):
        self.price = start_price
        self.volatility = 0.0015  # per-tick vol (~0.15% per candle)
        self.drift = 0.0
        self.candles: deque = deque(maxlen=500)
        self._rng = random.Random(seed)
        # seed some history so indicators warm up
        self._bootstrap(200)

    def _bootstrap(self, n: int):
        for _ in range(n):
            self._advance(append=True)

    def _advance(self, append: bool = True):
        # geometric brownian motion step
        shock = self._rng.gauss(self.drift, self.volatility)
        new_price = self.price * math.exp(shock)
        # occasionally inject a trend pulse for realism
        if self._rng.random() < 0.02:
            self.drift = self._rng.gauss(0, 0.0003)
        o = self.price
        c = new_price
        h = max(o, c) * (1 + abs(self._rng.gauss(0, self.volatility * 0.5)))
        l = min(o, c) * (1 - abs(self._rng.gauss(0, self.volatility * 0.5)))
        v = abs(self._rng.gauss(100, 20))
        ts = time.time()
        candle = Candle(ts, o, h, l, c, v)
        self.price = c
        if append:
            self.candles.append(candle)
        return candle

    def tick(self) -> Candle:
        """Produce one new candle (call once per interval)."""
        return self._advance(append=True)

    def to_df(self) -> pd.DataFrame:
        data = [
            {
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in self.candles
        ]
        return pd.DataFrame(data)

    def current_price(self) -> float:
        return self.price


# Singleton market instance
_market = SimulatedMarket()


def fetch_latest_candles(n: int = 200) -> pd.DataFrame:
    """Return the last n candles as a DataFrame."""
    df = _market.to_df()
    return df.tail(n).reset_index(drop=True)


def tick_market() -> Candle:
    """Produce one new candle (called by the scheduler each interval)."""
    return _market.tick()


def get_current_price() -> float:
    return _market.current_price()
