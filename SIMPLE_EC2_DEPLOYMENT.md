# Simple EC2 Deployment - edu-scraper

**Simple step-by-step guide (no Terraform needed)**

---

## Step 1: Launch EC2 Instance on AWS

1. Go to: https://console.aws.amazon.com/ec2
2. Click **"Launch Instances"**
3. Select **Ubuntu Server 22.04 LTS** (free tier eligible)
4. Instance Type: **t3.small** (recommended for good performance)
   - Alternative: t3.micro if on budget (~$7.50/month)
5. Storage: **30 GB** (default is fine)
6. Click **"Launch"**

---

## Step 2: Configure Security Settings

When prompted for security group:

1. Create new security group named: `edu-scraper-sg`
2. Add these rules:
   - **SSH (Port 22)**: From your IP only
   - **HTTP (Port 80)**: From anywhere (0.0.0.0/0)
   - **HTTPS (Port 443)**: From anywhere (0.0.0.0/0)

3. **Create Key Pair**
   - Name: `edu-scraper-key`
   - Type: RSA
   - Format: `.pem`
   - Download and save it safely

4. Click **"Launch Instance"**

---

## Step 3: Wait for Instance to Start

- Go to **Instances** in AWS Console
- Look for your instance
- Wait until **Status** shows "Running" and **Status Checks** show "2/2"
- Copy the **Public IPv4 address** (e.g., `52.12.34.56`)

---

## Step 4: Connect via SSH

### On Windows (PowerShell):
```powershell
# Go to where you saved the key
cd C:\Users\YourName\Downloads

# Connect to instance
ssh -i edu-scraper-key.pem ubuntu@52.12.34.56
```

### On Mac/Linux:
```bash
chmod 400 ~/Downloads/edu-scraper-key.pem
ssh -i ~/Downloads/edu-scraper-key.pem ubuntu@52.12.34.56
```

**If connection fails:** Wait 2-3 minutes and retry (instance might still be booting)

---

## Step 5: One-Line Deployment

Once connected via SSH, paste this single command:

```bash
curl -fsSL https://raw.githubusercontent.com/msubham193/edu-scraper/main/deploy.sh | sudo bash
```

**This does everything:**
- Updates system
- Installs all dependencies
- Clones your app
- Sets up Python environment
- Installs Playwright
- Configures Nginx + Supervisor
- Starts the app

**Takes ~15-20 minutes** (first time only)

---

## Step 6: Access Your App

Open in browser:
```
http://52.12.34.56
```

Replace `52.12.34.56` with your actual **Public IPv4 address**

---

## Done! ✅

Your app is now running. Test by:
1. Go to `http://52.12.34.56`
2. Search for: "engineering colleges in Delhi"
3. Wait 20-30 seconds for results
4. Download the Excel file

---

## Useful Commands

### Check if app is running:
```bash
sudo supervisorctl status edu-scraper
```

### View logs:
```bash
sudo tail -f /var/log/edu-scraper.log
```

### Restart app:
```bash
sudo supervisorctl restart edu-scraper
```

### Update code from GitHub:
```bash
cd /home/scraper/app
git pull origin main
sudo supervisorctl restart edu-scraper
```

### Stop instance (to save money):
- Go to AWS Console → Instances
- Right-click your instance → Instance State → Stop
- When ready to use again, click → Instance State → Start

---

## Cost

- **t3.small**: ~$16-20/month (good performance)
- **t3.micro**: ~$7.50/month (slow but works)
- **Stop when not using** to save money

---

## Troubleshooting

### Can't SSH?
- Verify security group allows SSH from your IP
- Check instance is running (AWS console)
- Wait 2-3 min after launch

### App not responding (502 error)?
```bash
sudo supervisorctl restart edu-scraper
sudo tail -20 /var/log/edu-scraper.log
```

### Search taking too long?
- This is normal (20-30 seconds on t3.small)
- Upgrade to t3.medium for faster searches

### Out of disk space?
```bash
# Delete old results
sudo rm /home/scraper/app/outputs/*.xlsx
```

---

## That's It!

Your app is deployed. You can now:
- Use it for scraping
- Update code (git pull + restart)
- Scale up instance type if needed
- Stop instance when not using to save $

Questions? Check the logs: `sudo tail -f /var/log/edu-scraper.log`
