# Deployment Guide for Render

## Issue Fixed: "Bing bing data" showing instead of Google Search results

### Root Cause
On Render (cloud platform), the Google search was timing out or failing silently, causing the system to fall back to Bing search, resulting in poor/duplicate data.

### Changes Made

1. **Enhanced Google Search with Better Error Handling**
   - Increased timeouts: 30s → 45s for page load
   - Added retry logic for browser launch (2 attempts)
   - Improved search box interaction with multiple retries
   - Better error logging and messages

2. **Improved Deployment Configuration**
   - Render-specific environment detection
   - Better error reporting through logs
   - Additional browser launch arguments for stability

3. **Dockerfile Optimizations**
   - Using Microsoft's official Playwright Python image
   - Includes all necessary browser dependencies
   - Proper working directory and outputs folder setup

## Deployment Steps for Render

### Step 1: Connect Your Repository
1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository

### Step 2: Configure the Service
- **Name**: edu-scraper
- **Region**: Oregon (or your preferred region)
- **Branch**: main
- **Runtime**: Docker
- **Build Command**: (leave empty - uses Dockerfile)
- **Start Command**: `python server.py`

### Step 3: Environment Variables (Optional)
Add in the Render dashboard if needed:
```
PYTHONUNBUFFERED=1
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
```

### Step 4: Instance Settings
- **Instance Type**: Standard (minimum recommended)
- **Plan**: Standard or higher (free tier may timeout on searches)

### Step 5: Deploy
Click "Create Web Service" and wait for deployment to complete.

## Testing the Fix

1. Go to your deployed service URL
2. Test with search query: "engineering colleges in Mumbai"
3. Wait for results - it may take 30-45 seconds
4. Verify results are from actual college websites (not Bing aggregator pages)

## Troubleshooting

### Issue: Still showing Bing results
**Solution**: 
- Check logs in Render dashboard for detailed error messages
- Look for "Google search error:" messages
- May indicate Google is blocking the IP - try a different region in Render

### Issue: Search timeout
**Solution**:
- Upgrade from Free tier to Standard tier
- Free tier instances are too slow for browser automation

### Issue: Browser crash
**Solution**:
- The Dockerfile now includes `--disable-dev-shm-usage` flag
- This prevents memory issues in containerized environments
- If still failing, check Render logs for OOM errors

## Monitoring

Watch the deployment logs for:
- ✅ "Found X valid URLs to scrape" = Success
- ❌ "Google search error" = Issues detected
- ⚠️ "Google returned nothing, trying Bing" = Fallback activated

## Performance Tips

1. Use reasonable num_results (20-30) for faster searches
2. The scraper will naturally add a 1-2 second delay between requests
3. First run may be slower while Render boots the instance

## Need Help?

If you're still having issues:
1. Check the Render deployment logs
2. Look for specific error messages
3. Try a simpler search query
4. Verify Playwright is properly installed by checking build logs
