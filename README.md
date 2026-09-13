# X-NOVA Paper-Trading Bot 🚀

A transparent, self-hosted crypto auto-trading bot for **paper trading**
(simulated funds). Built with:

- ✅ Technical indicator strategy (RSI, MACD, EMA crossover)
- ✅ Risk management (stop-loss, take-profit, max position size)
- ✅ Telegram bot control interface
- ✅ Live web dashboard with candlestick charts
- ✅ 100% Python — runs anywhere
- ✅ Simulated market feed (swap for real Binance/Bybit data in 3 lines)

> ⚠️ **Paper trading only.** Algorithmic trading carries significant financial
> risk. Never deploy with real money without extensive testing.

![Status](https://img.shields.io/badge/status-paper%20trading-yellow)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Quick start (local)

```bash
pip install -r requirements.txt
cp .env.example .env    # add your Telegram bot token here
python run.py
```

Then message your bot on Telegram or open http://localhost:5050.

## Telegram commands

`/start` `/status` `/trades` `/startbot` `/stopbot` `/settings`
`/setrisk <sl%> <tp%> <pos%> <max_pos>` `/reset` `/help`

## Deploy 24/7

See [DEPLOY.md](./DEPLOY.md) for step-by-step deployment to:
- **Fly.io** (recommended — free tier, truly 24/7, Johannesburg region)
- Render.com (no credit card, but sleeps)
- Your own PC / VPS / Raspberry Pi

## Strategy defaults

- **BUY** when RSI(14) < 35 AND MACD bullish cross AND price above EMA(50)
- **SELL** on RSI > 65, MACD bear cross, stop-loss (-2%), or take-profit (+4%)
- Max 5% of balance per position, max 3 open positions
- All parameters configurable via Telegram `/setrisk` or `.env`

## Project structure

```
xnova_trading_bot/
├── run.py                    # Entry point
├── trading/
│   ├── config.py             # Settings (loaded from .env)
│   ├── indicators.py         # RSI, MACD, EMA
│   ├── market_data.py        # Simulated price feed (swap for real API)
│   ├── portfolio.py          # Cash, positions, trades
│   └── strategy.py           # Entry/exit rules
├── bot/
│   └── telegram_bot.py       # Telegram command handlers (simple HTTP polling)
├── web/
│   ├── app.py                # Flask dashboard API
│   └── templates/index.html  # Live dashboard (candlesticks, positions)
├── Dockerfile                # Container image
├── fly.toml                  # Fly.io config
├── render.yaml               # Render.com config
└── DEPLOY.md                 # Deployment guide
```
