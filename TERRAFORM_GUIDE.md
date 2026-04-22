# Terraform Automated Deployment Guide

Deploy entire AWS infrastructure with a single command!

---

## Prerequisites

1. **AWS Account** - with billing enabled
2. **AWS Credentials** - configured locally
3. **Terraform** - installed on your machine
4. **SSH Key** - for EC2 access

---

## Setup (One-time)

### 1. Install Terraform

**Windows:**
```powershell
# Using Chocolatey
choco install terraform

# Or download: https://www.terraform.io/downloads
```

**Mac:**
```bash
brew install terraform
```

**Linux:**
```bash
wget https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip
unzip terraform_1.5.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

### 2. Configure AWS Credentials

**Option A: AWS CLI (Recommended)**
```bash
aws configure

# Enter:
# - AWS Access Key ID: your_key
# - AWS Secret Access Key: your_secret
# - Default region: us-east-1
# - Default output format: json
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_DEFAULT_REGION="us-east-1"
```

### 3. Get Your Public IP

Go to: https://whatismyipaddress.com and copy your IP address.

---

## Deployment Steps

### Step 1: Clone the Repository
```bash
cd c:\Users\HP\Desktop\edu-scraper
```

### Step 2: Configure Variables

Edit `terraform.tfvars`:
```hcl
aws_region   = "us-east-1"
instance_type = "t3.small"  # or t3.micro or t3.medium
your_ip = "YOUR_PUBLIC_IP_HERE"  # Replace with your IP!
```

### Step 3: Initialize Terraform

```bash
terraform init
```

Output:
```
Terraform has been successfully configured!
```

### Step 4: Review Plan

```bash
terraform plan
```

This shows what will be created without actually creating anything.

Output:
```
Plan: 6 to add, 0 to change, 0 to destroy.
```

### Step 5: Deploy!

```bash
terraform apply
```

**When prompted, type:** `yes`

This will:
- Create security group
- Create EC2 instance
- Create Elastic IP
- Run deployment script
- Create CloudWatch alarms

Takes ~5-10 minutes...

### Step 6: Get Output

After completion, you'll see:
```
Outputs:

app_url = "http://52.12.34.56"
instance_id = "i-0abc123def456"
public_ip = "52.12.34.56"
ssh_command = "ssh -i YOUR_KEY ubuntu@52.12.34.56"
```

### Step 7: Access Your App

Open: `http://52.12.34.56` in your browser

---

## Common Terraform Commands

### Check Status
```bash
terraform state list
terraform state show aws_instance.edu_scraper
```

### Modify Configuration

Edit `terraform.tfvars`, then:
```bash
terraform plan
terraform apply
```

### Scale Up Instance

```hcl
# In terraform.tfvars:
instance_type = "t3.medium"  # Upgrade from t3.small

# Apply changes:
terraform plan
terraform apply
```

### View All Resources

```bash
terraform show
```

### Destroy Everything (Delete All Resources)

⚠️ **WARNING: This deletes everything!**

```bash
terraform destroy
```

When prompted: type `yes`

---

## Cost Estimation

### Calculate Before Deploy

```bash
terraform plan -out=plan.out
# Then use AWS cost calculator at: https://calculator.aws/
```

### By Instance Type

| Instance | Monthly | Performance |
|----------|---------|-------------|
| t3.micro | ~$7.50 | Slow (45+ sec) |
| t3.small | ~$16-20 | Good (20-30 sec) |
| t3.medium | ~$35 | Excellent (5-10 sec) |

---

## Troubleshooting

### "Error: No valid credentials found"

```bash
# Solution: Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
```

### "Error: InvalidGroup.NotFound"

Solution: The security group name is already in use. Change in `terraform.tf`:
```hcl
name = "edu-scraper-sg-${timestamp()}"
```

### "terraform init" fails

```bash
# Try:
rm -rf .terraform
terraform init -upgrade
```

### Instance created but app not running

```bash
# Wait 5-10 minutes for deployment script to complete
# Then SSH in:
ssh -i YOUR_KEY ubuntu@YOUR_PUBLIC_IP

# Check status:
sudo supervisorctl status edu-scraper
```

### Can't SSH into instance

```bash
# Verify:
# 1. Security group allows SSH (port 22) from your IP
# 2. You're using correct key pair
# 3. Instance is running (check AWS console)
# 4. Wait 2-3 min after creation
```

---

## Updating Your Code

When you push code changes to GitHub:

### Option 1: Manual Restart
```bash
ssh -i YOUR_KEY ubuntu@YOUR_PUBLIC_IP

# In instance:
cd /home/scraper/app
git pull origin main
sudo supervisorctl restart edu-scraper
```

### Option 2: Auto-Deploy (Advanced)

Set up GitHub Actions + AWS CodeDeploy for automatic deployments on push.

---

## Backing Up

### Export Infrastructure State
```bash
terraform state pull > backup.tfstate
```

### Export Configuration
```bash
cp terraform.tfstate backup-$(date +%Y%m%d).tfstate
cp terraform.tfvars backup-vars.tfvars
```

---

## Advanced: Multiple Environments

### Create staging environment:

```bash
# Create new directory
mkdir staging
cd staging

# Copy Terraform files
cp ../terraform.tf .
cp ../deploy.sh .

# Create separate vars
cat > terraform.tfvars << EOF
aws_region    = "us-east-1"
instance_type = "t3.micro"
instance_name = "edu-scraper-staging"
your_ip       = "YOUR_IP"
EOF

# Deploy
terraform init
terraform apply
```

---

## Clean Up (Delete Everything)

When done or want to stop paying:

```bash
terraform destroy
```

This deletes:
- EC2 instance
- Security group
- Elastic IP
- CloudWatch alarms
- IAM role

**All data in `/home/scraper/app/outputs/` will be lost!**

Backup first if needed:
```bash
scp -i YOUR_KEY -r ubuntu@YOUR_IP:/home/scraper/app/outputs ./backup/
terraform destroy
```

---

## Getting Help

### Terraform Docs
```bash
terraform help
terraform apply -help
```

### AWS Documentation
- https://docs.aws.amazon.com/ec2/
- https://docs.aws.amazon.com/security_groups/

### My Setup
- https://registry.terraform.io/providers/hashicorp/aws/

---

## Next Steps

1. Deploy with: `terraform apply`
2. Access app at: `http://YOUR_PUBLIC_IP`
3. Test with search query
4. Monitor logs: `tail -f /var/log/edu-scraper.log`
5. Scale up if needed: Change `instance_type` in vars

**Questions?** Check the logs or AWS console for error details.
