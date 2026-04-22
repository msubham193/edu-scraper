# EC2 Deployment - Quick Reference

## 🚀 Fastest Way (5 minutes)

### Step 1: Launch EC2 Instance
```
1. Go to https://console.aws.amazon.com/ec2
2. Click "Launch Instances"
3. Select: Ubuntu Server 22.04 LTS
4. Instance Type: t3.small (or t3.micro for minimum)
5. Storage: 30GB (default)
6. Security Group:
   - SSH (22) from your IP
   - HTTP (80) from anywhere
   - HTTPS (443) from anywhere
7. Create key pair "edu-scraper-key" and download
8. Click "Launch"
```

### Step 2: Connect & Deploy (Single Command)
```powershell
# On Windows PowerShell
$key = "C:\path\to\edu-scraper-key.pem"
$ip = "YOUR_EC2_PUBLIC_IP"

ssh -i $key ubuntu@$ip

# Once connected via SSH, paste this ONE command:
sudo bash -c 'apt update && apt install -y git && cd /tmp && git clone https://github.com/msubham193/edu-scraper.git && cd edu-scraper && sudo bash deploy.sh'
```

### Step 3: Access Your App
```
http://<YOUR_EC2_PUBLIC_IP>
```

---

## 📋 Commands Reference

### Connection
```bash
# SSH into instance
ssh -i edu-scraper-key.pem ubuntu@EC2_PUBLIC_IP

# If connection refused, wait 2-3 minutes for instance to boot
```

### Check Status
```bash
# Is app running?
sudo supervisorctl status edu-scraper

# Is Nginx running?
sudo systemctl status nginx

# View real-time logs
sudo tail -f /var/log/edu-scraper.log

# Check ports
sudo lsof -i :80  # Nginx
sudo lsof -i :5000  # Flask app
```

### Restart/Stop
```bash
# Restart app
sudo supervisorctl restart edu-scraper

# Stop app
sudo supervisorctl stop edu-scraper

# Start app
sudo supervisorctl start edu-scraper

# Reload Nginx
sudo systemctl reload nginx
```

### Update Code
```bash
cd /home/scraper/app
git pull origin main
sudo supervisorctl restart edu-scraper
```

### View Logs
```bash
# Last 50 lines
sudo tail -50 /var/log/edu-scraper.log

# Last 100 lines
sudo tail -100 /var/log/edu-scraper.log

# Follow live (Ctrl+C to exit)
sudo tail -f /var/log/edu-scraper.log

# Search for errors
sudo grep "error" /var/log/edu-scraper.log
```

### Disk Space
```bash
# Check free space
df -h

# Check app folder size
du -sh /home/scraper/app

# Clean old results
sudo rm /home/scraper/app/outputs/*.xlsx
```

---

## 💰 Cost Breakdown

| Instance | Monthly | Performance |
|----------|---------|-------------|
| t3.micro | ~$7.50 | Minimal (45+ sec searches) |
| t3.small | ~$16-20 | Good (20-30 sec searches) |
| t3.medium | ~$35 | Excellent (5-10 sec searches) |

---

## 🐛 Troubleshooting

### App not responding (502 Bad Gateway)
```bash
# Check if Flask is running
sudo supervisorctl status edu-scraper

# If stopped, restart
sudo supervisorctl restart edu-scraper

# Check logs
sudo tail -50 /var/log/edu-scraper.log
```

### Search timeout (>60 seconds)
- Upgrade instance size (t3.small → t3.medium)
- Reduce num_results to 10-15 in UI
- Check instance CPU/memory: `top`

### Can't connect via SSH
- Verify security group allows SSH (port 22)
- Verify EC2 instance is running
- Verify you're using correct public IP
- Wait 2-3 min after launch for instance to boot

### Nginx not working
```bash
# Check nginx config
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

# Check logs
sudo tail -50 /var/log/nginx/error.log
```

### Out of memory
```bash
# Check memory
free -h

# If full, restart Supervisor
sudo supervisorctl stop edu-scraper
sudo supervisorctl start edu-scraper
```

---

## 📝 Important Notes

- **Playwright install is slow** (5-10 min) on first deploy - this is normal
- **Search takes 20-30 seconds** on t3.small - this is normal for browser automation
- **First app startup takes 10-15 seconds** - Flask loads Playwright
- **Keep instance running** or use Auto-stop to save costs
- **Regular backups** of outputs folder recommended

---

## 🔐 Security

✅ Use SSH key pairs (never password)
✅ Restrict SSH to your IP only
✅ Enable firewall (UFW)
✅ Use SSL/HTTPS when possible
✅ Keep system updated: `sudo apt update && sudo apt upgrade -y`

---

## 📞 Need Help?

1. Check logs first: `sudo tail -f /var/log/edu-scraper.log`
2. Verify instance is running (AWS console)
3. Verify security group allows ports 22, 80, 443
4. Check EC2 instance CPU/memory: `top`
5. Verify public IP is correct
