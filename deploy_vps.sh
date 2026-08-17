#!/bin/bash
# =========================================================
# CORE MARKET BOT — CONTABO VPS 1-CLICK DEPLOYMENT SCRIPT
# =========================================================

echo "🚀 [1/4] Updating system packages..."
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv git curl

echo "📦 [2/4] Setting up project directory..."
cd /root || cd ~
if [ ! -d "Core-Market-Bot" ]; then
    git clone https://github.com/masheeee34/Core-Market-Bot.git
fi
cd Core-Market-Bot || exit
git pull origin main

echo "🐍 [3/4] Creating virtual environment & installing dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "⚙️ [4/4] Creating 24/7 Systemd Background Service..."
sudo tee /etc/systemd/system/coremarket.service > /dev/null <<EOF
[Unit]
Description=Core Market Discord Bot 24/7 Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile=$(pwd)/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable coremarket
sudo systemctl restart coremarket

echo "========================================================="
echo "✅ CORE MARKET BOT IS NOW RUNNING 24/7 ON YOUR VPS !"
echo "▸ Check Status : sudo systemctl status coremarket"
echo "▸ View Live Logs : sudo journalctl -u coremarket -f"
echo "▸ Restart Bot  : sudo systemctl restart coremarket"
echo "========================================================="
