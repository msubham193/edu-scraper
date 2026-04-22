# EC2 Ubuntu Deployment Guide - edu-scraper

## Prerequisites

- AWS Account with EC2 access
- Basic SSH knowledge
- ~$5-10/month budget (t3.micro or t3.small instance)

---

## Step 1: Launch EC2 Instance

### 1.1 Go to AWS Console
1. Open https://console.aws.amazon.com/ec2
2. Click "Instances" → "Launch Instances"

### 1.2 Configure Instance

**Name:** `edu-scraper`

**AMI (Image):** Ubuntu Server 22.04 LTS (free tier eligible)

**Instance Type:** `t3.small` (recommended) or `t3.micro` (minimum)
- t3.small: Better performance ($0.022/hour ≈ $16/month)
- t3.micro: Minimum viable ($0.0104/hour ≈ $7.50/month)

**Storage:** 30 GB (default is fine)

**Security Group:** Create new or use existing
- Allow SSH (Port 22) from your IP
- Allow HTTP (Port 80) from anywhere
- Allow HTTPS (Port 443) from anywhere

### 1.3 Key Pair

1. Create new key pair: `edu-scraper-key`
2. Download `.pem` file and **save securely**
3. Set permissions: `chmod 400 edu-scraper-key.pem`

### 1.4 Launch

Click "Launch Instance" and wait 2-3 minutes for startup.

---

## Step 2: Connect to Instance

```powershell
# On Windows (PowerShell)
$keyPath = "C:\path\to\edu-scraper-key.pem"
ssh -i $keyPath ubuntu@<YOUR_EC2_PUBLIC_IP>
```

Replace `<YOUR_EC2_PUBLIC_IP>` with your instance's public IP from AWS console.

---

## Step 3: System Setup

Once logged in via SSH, run these commands:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required dependencies
sudo apt install -y \
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
  libx11-6

# Create application user (best practice)
sudo useradd -m -s /bin/bash scraper
sudo usermod -aG sudo scraper
```

---

## Step 4: Deploy Application

```bash
# Switch to app user
sudo su - scraper

# Create app directory
mkdir -p /home/scraper/app
cd /home/scraper/app

# Clone your repository
git clone https://github.com/msubham193/edu-scraper.git .

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers (critical!)
playwright install chromium

# Create outputs directory
mkdir -p outputs
chmod 777 outputs

# Exit scraper user (back to ubuntu)
exit
```

---

## Step 5: Configure Supervisor (Auto-Start & Restart)

Supervisor will automatically start your app and restart if it crashes.

```bash
# Create supervisor config
sudo nano /etc/supervisor/conf.d/edu-scraper.conf
```

Paste this:

```ini
[program:edu-scraper]
directory=/home/scraper/app
command=/home/scraper/app/venv/bin/python server.py
user=scraper
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/edu-scraper.log
environment=PATH="/home/scraper/app/venv/bin",PYTHONUNBUFFERED="1"
```

Then:

```bash
# Save (Ctrl+X, Y, Enter in nano)
# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start edu-scraper

# Check status
sudo supervisorctl status edu-scraper
```

---

## Step 6: Configure Nginx Reverse Proxy

Nginx will route internet traffic to your Flask app on port 5000.

```bash
# Create nginx config
sudo nano /etc/nginx/sites-available/edu-scraper
```

Paste this:

```nginx
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
    }

    # Static files (if any)
    location /static/ {
        alias /home/scraper/app/static/;
        expires 7d;
    }
}
```

Then:

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/edu-scraper /etc/nginx/sites-enabled/edu-scraper

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test nginx config
sudo nginx -t

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Check status
sudo systemctl status nginx
```

---

## Step 7: Verify Deployment

```bash
# Check Flask app is running on port 5000
sudo lsof -i :5000

# Check Nginx is running on port 80
sudo lsof -i :80

# View logs
sudo tail -f /var/log/edu-scraper.log
sudo tail -f /var/log/nginx/error.log
```

---

## Step 8: Access Your App

In your browser:
```
http://<YOUR_EC2_PUBLIC_IP>
```

Or set a domain name in Route 53 (AWS's DNS) → `your-domain.com`

---

## Step 9: Optional - SSL Certificate (HTTPS)

For free HTTPS with Let's Encrypt:

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain or use IP)
sudo certbot certonly --standalone -d your-domain.com

# Update nginx config to use SSL
sudo nano /etc/nginx/sites-available/edu-scraper
```

Add to nginx config:

```nginx
server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

Reload nginx: `sudo systemctl reload nginx`

---

## Step 10: Firewall (UFW)

```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

---

## Useful Commands

```bash
# View live logs
sudo tail -f /var/log/edu-scraper.log

# Restart app
sudo supervisorctl restart edu-scraper

# Stop app
sudo supervisorctl stop edu-scraper

# Check EC2 instance usage
free -h
df -h
top

# Update code from GitHub
cd /home/scraper/app
git pull origin main
sudo supervisorctl restart edu-scraper
```

---

## Monitoring & Maintenance

### Monitor Disk Space
```bash
df -h
# If outputs folder gets full:
sudo rm /home/scraper/app/outputs/*.xlsx
```

### Monitor Memory/CPU
```bash
top
# Press 'q' to exit
```

### Restart Application
```bash
sudo supervisorctl restart edu-scraper
```

### View Recent Logs
```bash
sudo tail -50 /var/log/edu-scraper.log
```

---

## Cost Breakdown (Monthly)

- **t3.small** EC2: ~$16-20/month
- **Elastic IP** (optional, static IP): $0.05/hour if not attached = free if attached
- **Data transfer**: Free for incoming, ~$0.09/GB for outgoing
- **Total**: ~$16-20/month

---

## Troubleshooting

### 502 Bad Gateway
```bash
# Check if Flask app is running
sudo lsof -i :5000

# Check Flask logs
sudo tail -20 /var/log/edu-scraper.log

# Restart
sudo supervisorctl restart edu-scraper
```

### Search Timeout (45+ seconds)
- This is normal on small instances
- Upgrade to `t3.medium` for better performance
- Or reduce `num_results` in UI to 10-15

### Browser/Playwright Issues
```bash
# SSH into instance
cd /home/scraper/app

# Activate venv
source venv/bin/activate

# Reinstall Playwright
pip install --upgrade playwright
playwright install chromium

# Restart app
sudo supervisorctl restart edu-scraper
```

### Out of Memory
```bash
# Check memory usage
free -h

# If running low, stop supervisor and restart
sudo supervisorctl stop edu-scraper
sudo supervisorctl start edu-scraper
```

---

## Scaling Tips

If getting slow or need better performance:

1. **Upgrade instance type**: `t3.medium` or `t3.large`
2. **Enable auto-scaling**: Set up load balancer + auto-scaling group
3. **Use Celery** for async tasks (advanced)
4. **Add caching**: Redis/Memcached for results

---

## Security Best Practices

1. ✅ Restrict SSH to your IP only
2. ✅ Use SSH keys (not password)
3. ✅ Keep system updated: `sudo apt update && sudo apt upgrade -y`
4. ✅ Use SSL/HTTPS certificate
5. ✅ Set strong passwords if needed
6. ✅ Regular backups of `outputs/` folder

---

## Need Help?

- Check logs: `sudo tail -f /var/log/edu-scraper.log`
- SSH errors? Verify key pair permissions: `chmod 400 edu-scraper-key.pem`
- Port issues? Verify security group allows ports 22, 80, 443
