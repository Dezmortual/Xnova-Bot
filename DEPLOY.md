# 🚀 Deploying X-NOVA to 24/7 Free Cloud Hosting

Your bot runs locally right now. To get it running **24/7** like real Telegram bots do, deploy it to a cloud host. Below are two options.

---

## 🏆 Option A: Fly.io (Recommended — truly 24/7, free tier)

**Pros:**
- ✅ Actually stays running 24/7 (no sleep)
- ✅ 256MB free VM — more than enough
- ✅ Deploys via Docker in minutes
- ✅ Persistent volume for your trade state
- ✅ Has servers in South Africa (jnb region — low latency)

**Cons:**
- ❌ Requires credit card (to prevent abuse). They DO NOT charge as long as you stay on free tier. You can set a hard spending limit of $0.

### Step-by-step:

1. **Install Fly CLI** (one-time, on your own computer):
   - macOS/Linux: `curl -L https://fly.io/install.sh | sh`
   - Windows: `powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"`
   - Or download from https://fly.io/docs/hands-on/install-flyctl/

2. **Sign up / log in:**
   ```bash
   fly auth signup     # if you don't have an account
   fly auth login      # if you already have one
   ```
   This will open a browser — you can use GitHub/Google to sign up. You'll need to add a credit card (use a spare one or virtual card if you want to be safe). The free tier won't bill you, and you can set a $0 spending limit in the dashboard.

3. **Copy the project folder** to your own computer (download the `xnova_trading_bot` folder from your workspace).

4. **Open a terminal in that folder** and run:
   ```bash
   fly launch
   ```
   - When asked "Would you like to copy its configuration to the new app?" → **Yes** (it will detect fly.toml)
   - Choose app name (or default), pick a region close to you (Johannesburg `jnb` is suggested for SA users)
   - When asked "Would you like to set up a Postgresql database?" → **No**
   - When asked "Would you like to deploy now?" → **Yes**
   - When asked "Would you like to create a volume now?" → **Yes** (name it `xnovadata`, size 1GB)

5. **Set your secrets (environment variables):**
   ```bash
   fly secrets set TELEGRAM_BOT_TOKEN=8707103542:AAFTTL9w35Cc2MGCEmqm_nbtvGzHcujFvM8
   fly secrets set ALLOWED_USER_IDS=5719761722
   ```

6. **Wait for deploy**, then open the dashboard:
   ```bash
   fly open      # opens your web dashboard URL
   ```
   Your bot is now running 24/7! Send `/startbot` on Telegram from anywhere.

7. **Useful commands:**
   ```bash
   fly logs          # watch live logs to confirm trades
   fly status        # check if machine is running
   fly ssh console   # shell into the VM
   fly deploy        # push new code after you edit strategy
   ```

---

## 🆓 Option B: Render.com (No credit card, but sleeps)

**Pros:**
- ✅ No credit card required
- ✅ Git-based deploy (push to GitHub → auto deploy)
- ✅ Free

**Cons:**
- ❌ Free tier **sleeps after 15 minutes of inactivity** — bad for 24/7 trading (bot won't receive messages or trade when asleep)
- ❌ When it wakes up, there's a ~30 second cold start delay
- ❌ No persistent disk (state resets on deploy, though Telegram commands like /reset still work)

### Step-by-step:

1. Push this project to a GitHub repository (create a free GitHub account if you don't have one).
2. Go to https://render.com → Sign up with GitHub → "New +" → "Blueprint"
3. Select your repo → Render auto-reads `render.yaml`
4. It will prompt you for `TELEGRAM_BOT_TOKEN` — paste your token
5. Click Apply. It deploys in ~2 minutes.
6. You get a URL like `https://xnova-trading-bot.onrender.com` for your dashboard.

⚠️ Render free tier will spin down after 15 minutes. You could work around this by using a free uptime monitor (like https://cron-job.org) to ping your dashboard URL every 5 minutes, which keeps it awake. This is against Render's TOS long-term but works for testing.

---

## 💻 Option C: Run it on your own computer (Free, 24/7 while PC is on)

1. Download the `xnova_trading_bot` folder from this workspace to your PC.
2. Install Python 3.10+ from https://python.org (tick "Add to PATH" during install).
3. Open a terminal/Command Prompt in the folder:
   ```bash
   pip install -r requirements.txt
   python run.py
   ```
4. The bot runs as long as your PC is on and terminal is open.
5. (Optional) Use Task Scheduler (Windows) or systemd (Linux/Mac) to auto-start on boot.

---

## 🥧 Option D: Raspberry Pi (One-time cost ~$35-60, 24/7)

If you have or buy a Raspberry Pi, you can run the bot at home 24/7 for pennies of electricity.
1. Install Raspberry Pi OS
2. Copy the project over
3. Install Python + dependencies (same as Option C)
4. Set up a systemd service to auto-start on boot:
   ```ini
   # /etc/systemd/system/xnova.service
   [Unit]
   Description=X-NOVA Trading Bot
   After=network.target

   [Service]
   User=pi
   WorkingDirectory=/home/pi/xnova_trading_bot
   ExecStart=/usr/bin/python3 run.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
5. `sudo systemctl enable --now xnova`

---

## ⚠️ Important reminders

- **This is still paper trading** with fake prices. Don't deposit real money yet — test extensively.
- **NEVER commit `.env` to GitHub** — it has your bot token in it. The `.gitignore` already excludes it.
- **Rotate your bot token if you accidentally leak it** (message @BotFather → `/revoke`)
- When you're ready for real prices (still paper balance), ask me and I'll swap `market_data.py` to use Binance/Bybit public API (read-only, no API key needed for price data).
- For real money trading (which I don't recommend until you've paper traded successfully for weeks/months), you'd create API keys on an exchange with trading permissions (and ALWAYS enable IP whitelisting + withdrawal blocking).

## Quick test after deploy

Send these commands on Telegram to verify everything works in the cloud:
1. `/status` → should reply with price & balance
2. `/startbot` → starts trading
3. Send `/status` again a minute later → "Last signal" should update every tick

If you get stuck deploying, just tell me which step you're at and I'll help.
