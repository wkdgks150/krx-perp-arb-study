"""
Gap FADE Bot Configuration
"""
import os
from pathlib import Path

# ─── Paths ───
BOT_DIR = Path(__file__).parent
DB_PATH = BOT_DIR / "trades.db"
ENV_PATH = BOT_DIR / ".env"

# ─── Load .env ───
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# ─── Alpaca ───
ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = os.environ.get("ALPACA_PAPER", "true").lower() == "true"
ALPACA_BASE_URL = (
    "https://paper-api.alpaca.markets" if ALPACA_PAPER
    else "https://api.alpaca.markets"
)

# ─── Telegram ───
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ─── Strategy ───
TICKERS = ["GOOGL", "NVDA", "MSFT"]
GAP_THRESHOLD = 0.3       # %  (Safe: 0.3)
BODY_THRESHOLD = 1.0      # %
CONSECUTIVE_GAP = True
MA_DISTANCE = 3.0         # %  (Safe: 3.0 — only enter when far from MA)
MIN_SCORE = 4             #    (Safe: 4/4 — all conditions must match)
LEVERAGE = 10.0           # 10x leverage
FEE_PCT = 0.07            # round-trip %
SLIPPAGE_PCT = 0.05       # per side
MAX_POSITION_PCT = 0.95   # use 95% of capital (keep 5% buffer)
MAX_DAILY_LOSS_PCT = 20.0 # stop bot if daily loss exceeds this %

# ─── Mode ───
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"  # log only, no real trades
