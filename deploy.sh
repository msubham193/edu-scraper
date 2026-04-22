#!/bin/bash

# Auto-deployment script for edu-scraper on Ubuntu EC2
# Usage: bash deploy.sh

set -e  # Exit on error

echo "=========================================="
echo "   edu-scraper EC2 Auto-Deploy Script"
echo "=========================================="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root"
   echo "   Run: sudo bash deploy.sh"
   exit 1
fi

echo "📦 Step 1: Updating system packages..."
apt update && apt upgrade -y

echo "📦 Step 2: Installing dependencies..."
apt install -y \
  python3.10 \
  python3-pip \
  python3-venv \
  git \
  curl \
  wget \
  nginx \
  supervisor \
  libnss3 \
  libatk-bridge2.0-0 \
  libxcomposite1 \
  libxdamage1 \
  libxrandr2 \
  libgbm1 \
  libpango-1.0-0 \
  libcairo2 \
  libxkbcommon0 \
  libx11-6 \
  libx11-xcb1

echo "👤 Step 3: Creating scraper user..."
if ! id "scraper" &>/dev/null; then
    useradd -m -s /bin/bash scraper
    echo "✅ User 'scraper' created"
else
    echo "✅ User 'scraper' already exists"
fi

echo "📁 Step 4: Setting up application directory..."
APP_DIR="/home/scraper/app"
mkdir -p $APP_DIR
chown -R scraper:scraper $APP_DIR
chmod 755 $APP_DIR

echo "🔄 Step 5: Cloning repository..."
sudo -u scraper bash -c "
  cd $APP_DIR
  if [ ! -d .git ]; then
    git clone https://github.com/msubham193/edu-scraper.git .
    echo '✅ Repository cloned'
  else
    git pull origin main
    echo '✅ Repository updated'
  fi
"

echo "🐍 Step 6: Setting up Python virtual environment..."
sudo -u scraper bash -c "
  cd $APP_DIR
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  echo '✅ Python dependencies installed'
"

echo "🎯 Step 7: Installing Playwright browsers..."
sudo -u scraper bash -c "
  cd $APP_DIR
  source venv/bin/activate
  playwright install chromium
  echo '✅ Playwright installed'
"

echo "📂 Step 8: Creating outputs directory..."
sudo -u scraper bash -c "
  mkdir -p $APP_DIR/outputs
  chmod 777 $APP_DIR/outputs
  echo '✅ Outputs directory created'
"

echo "🔧 Step 9: Configuring Supervisor..."
cat > /etc/supervisor/conf.d/edu-scraper.conf << 'EOF'
[program:edu-scraper]
directory=/home/scraper/app
command=/home/scraper/app/venv/bin/python server.py
user=scraper
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/edu-scraper.log
environment=PATH="/home/scraper/app/venv/bin",PYTHONUNBUFFERED="1"
EOF

supervisorctl reread
supervisorctl update
supervisorctl start edu-scraper
echo "✅ Supervisor configured"

echo "🌐 Step 10: Configuring Nginx..."
cat > /etc/nginx/sites-available/edu-scraper << 'EOF'
upstream flask_app {
    server 127.0.0.1:5000;
}

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name _;
    client_max_body_size 50M;

    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Important for streaming responses (SSE)
        proxy_buffering off;
        proxy_request_buffering off;
        
        # Timeouts for long-running searches
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias /home/scraper/app/static/;
        expires 7d;
    }
}
EOF

# Remove default site if exists
rm -f /etc/nginx/sites-enabled/default

# Enable our site
ln -sf /etc/nginx/sites-available/edu-scraper /etc/nginx/sites-enabled/edu-scraper

# Test nginx config
nginx -t

# Start/restart nginx
systemctl restart nginx
systemctl enable nginx
echo "✅ Nginx configured"

echo "🔥 Step 11: Configuring Firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo "✅ Firewall configured"

echo ""
echo "=========================================="
echo "   ✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "📌 Important Information:"
echo ""
echo "1. Get your EC2 instance's Public IP:"
echo "   Go to AWS Console → EC2 → Instances"
echo ""
echo "2. Access your app:"
echo "   http://<YOUR_EC2_PUBLIC_IP>"
echo ""
echo "3. Check app status:"
echo "   supervisorctl status edu-scraper"
echo ""
echo "4. View logs:"
echo "   tail -f /var/log/edu-scraper.log"
echo ""
echo "5. Restart app if needed:"
echo "   supervisorctl restart edu-scraper"
echo ""
echo "6. Update code from GitHub:"
echo "   cd /home/scraper/app && git pull origin main"
echo "   supervisorctl restart edu-scraper"
echo ""
echo "=========================================="
