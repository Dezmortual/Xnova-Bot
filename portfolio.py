"""Paper-trading portfolio: cash balance, positions, P&L, trade history."""
import time
import json
import os
from dataclasses import dataclass, asdict, field
from typing import List, Optional
from threading import Lock

from config import START_BALANCE, RISK

# Allow state directory override for Docker/cloud persistence
_STATE_DIR = os.environ.get("STATE_DIR", os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(_STATE_DIR, "portfolio_state.json")


@dataclass
class Position:
    id: int
    symbol: str
    side: str          # "long"
    entry_price: float
    quantity: float
    entry_time: float
    stop_loss: float
    take_profit: float
    size_usdt: float


@dataclass
class Trade:
    id: int
    symbol: str
    side: str          # "buy" / "sell"
    price: float
    quantity: float
    pnl: float
    reason: str
    timestamp: float


class Portfolio:
    def __init__(self):
        self.lock = Lock()
        self.cash: float = START_BALANCE
        self.initial_balance: float = START_BALANCE
        self.positions: List[Position] = []
        self.trades: List[Trade] = []
        self._next_id: int = 1
        self._next_trade_id: int = 1
        self.running: bool = False
        self.last_signal: str = "no signal yet"
        self.load()

    # ---- state persistence ----
    def save(self):
        try:
            data = {
                "cash": self.cash,
                "initial_balance": self.initial_balance,
                "positions": [asdict(p) for p in self.positions],
                "trades": [asdict(t) for t in self.trades[-500:]],
                "_next_id": self._next_id,
                "_next_trade_id": self._next_trade_id,
                "running": self.running,
            }
            with open(STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[portfolio] save failed: {e}")

    def load(self):
        if not os.path.exists(STATE_FILE):
            return
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            self.cash = data.get("cash", START_BALANCE)
            self.initial_balance = data.get("initial_balance", START_BALANCE)
            self.positions = [Position(**p) for p in data.get("positions", [])]
            self.trades = [Trade(**t) for t in data.get("trades", [])]
            self._next_id = data.get("_next_id", 1)
            self._next_trade_id = data.get("_next_trade_id", 1)
            self.running = data.get("running", False)
        except Exception as e:
            print(f"[portfolio] load failed, starting fresh: {e}")

    def reset(self):
        with self.lock:
            self.cash = START_BALANCE
            self.positions = []
            self.trades = []
            self._next_id = 1
            self._next_trade_id = 1
            self.running = False
            self.last_signal = "account reset"
            self.save()

    # ---- queries ----
    def equity(self, current_price: float) -> float:
        pos_value = sum(p.quantity * current_price for p in self.positions)
        return self.cash + pos_value

    def total_pnl_pct(self, current_price: float) -> float:
        eq = self.equity(current_price)
        return (eq - self.initial_balance) / self.initial_balance * 100

    def open_long_count(self) -> int:
        return len(self.positions)

    # ---- execution ----
    def open_long(self, symbol: str, price: float, reason: str) -> Optional[Position]:
        with self.lock:
            if len(self.positions) >= RISK.max_open_positions:
                self.last_signal = f"skip BUY: max positions ({RISK.max_open_positions}) reached"
                return None
            # position sizing
            risk_pct = RISK.max_position_pct / 100.0
            size_usdt = self.cash * risk_pct
            if size_usdt < 1.0:
                self.last_signal = "skip BUY: not enough cash"
                return None
            quantity = size_usdt / price
            sl = price * (1 - RISK.stop_loss_pct / 100.0)
            tp = price * (1 + RISK.take_profit_pct / 100.0)
            pos = Position(
                id=self._next_id,
                symbol=symbol,
                side="long",
                entry_price=price,
                quantity=quantity,
                entry_time=time.time(),
                stop_loss=sl,
                take_profit=tp,
                size_usdt=size_usdt,
            )
            self._next_id += 1
            self.cash -= size_usdt
            self.positions.append(pos)
            self.trades.append(Trade(
                id=self._next_trade_id,
                symbol=symbol, side="buy", price=price, quantity=quantity,
                pnl=0.0, reason=reason, timestamp=time.time(),
            ))
            self._next_trade_id += 1
            self.last_signal = f"BUY @ {price:.2f} ({reason})"
            self.save()
            return pos

    def close_position(self, pos: Position, price: float, reason: str) -> Trade:
        with self.lock:
            proceeds = pos.quantity * price
            pnl = (price - pos.entry_price) * pos.quantity
            self.cash += proceeds
            self.positions = [p for p in self.positions if p.id != pos.id]
            t = Trade(
                id=self._next_trade_id,
                symbol=pos.symbol, side="sell", price=price, quantity=pos.quantity,
                pnl=pnl, reason=reason, timestamp=time.time(),
            )
            self._next_trade_id += 1
            self.trades.append(t)
            self.last_signal = f"SELL @ {price:.2f} PnL {pnl:+.2f} ({reason})"
            self.save()
            return t


PORTFOLIO = Portfolio()
