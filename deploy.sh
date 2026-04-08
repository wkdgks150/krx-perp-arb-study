#!/bin/bash
# Gap FADE Bot — One-click server deploy
# Run on a fresh Ubuntu 22.04+ VPS:
#   curl -sSL https://raw.githubusercontent.com/.../deploy.sh | bash
# Or: ssh into server, clone repo, run this script.

set -e

echo "================================"
echo "  Gap FADE Bot — Server Setup"
echo "================================"

# 1. System packages
echo "[1/5] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv cron git

# 2. Python dependencies
echo "[2/5] Installing Python packages..."
pip3 install --break-system-packages fastapi uvicorn yfinance pandas numpy hyperliquid-python-sdk eth-account 2>/dev/null || \
pip3 install fastapi uvicorn yfinance pandas numpy hyperliquid-python-sdk eth-account

# 3. Setup bot directory
echo "[3/5] Setting up bot..."
BOT_DIR="$(cd "$(dirname "$0")" && pwd)/bot"
cd "$BOT_DIR"

if [ ! -f .env ]; then
    echo "ERROR: bot/.env not found. Copy .env.example and fill in your keys."
    exit 1
fi

# Init DB
python3 -c "import storage; print('DB initialized')"

# 4. Systemd services
echo "[4/5] Creating systemd services..."

# Dashboard — always running
sudo tee /etc/systemd/system/gapfade-dash.service > /dev/null << EOF
[Unit]
Description=Gap FADE Live Dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=$BOT_DIR
ExecStart=$(which python3) live_dashboard.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Bot scan+execute+trail — daily 22:35 KST (13:35 UTC in summer)
# Runs scan, enters positions, then monitors trailing stop until close
sudo tee /etc/systemd/system/gapfade-scan.service > /dev/null << EOF
[Unit]
Description=Gap FADE Scan + Execute + Trail

[Service]
Type=simple
WorkingDirectory=$BOT_DIR
ExecStart=$(which python3) -u main.py run
Environment=PYTHONUNBUFFERED=1
# Auto-stop after 7 hours (safety — market is 6.5h)
RuntimeMaxSec=25200

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/gapfade-scan.timer > /dev/null << EOF
[Unit]
Description=Gap FADE Scan Timer (daily 13:35 UTC = 22:35 KST)

[Timer]
OnCalendar=Mon..Fri 13:35
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Safety close — daily 04:55 KST (19:55 UTC in summer)
# Backup in case trailer didn't close everything
sudo tee /etc/systemd/system/gapfade-close.service > /dev/null << EOF
[Unit]
Description=Gap FADE Safety Close

[Service]
Type=oneshot
WorkingDirectory=$BOT_DIR
ExecStart=$(which python3) main.py close
EOF

sudo tee /etc/systemd/system/gapfade-close.timer > /dev/null << EOF
[Unit]
Description=Gap FADE Close Timer (daily 19:55 UTC = 04:55 KST)

[Timer]
OnCalendar=Tue..Sat 19:55
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 5. Enable and start
echo "[5/5] Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable --now gapfade-dash
sudo systemctl enable --now gapfade-scan.timer
sudo systemctl enable --now gapfade-close.timer

echo ""
echo "================================"
echo "  DONE!"
echo "================================"
echo ""
echo "  Dashboard:  http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP'):8001"
echo "  Bot scan:   Mon-Fri 22:35 KST"
echo "  Bot close:  Tue-Sat 04:55 KST"
echo ""
echo "  Commands:"
echo "    sudo systemctl status gapfade-dash      # dashboard status"
echo "    sudo systemctl status gapfade-scan.timer # scan timer"
echo "    journalctl -u gapfade-dash -f            # dashboard logs"
echo "    journalctl -u gapfade-scan -f            # bot logs"
echo "    cd $BOT_DIR && python3 main.py status    # manual check"
echo ""
