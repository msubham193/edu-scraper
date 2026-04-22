# Use the official Microsoft Playwright image as base
# This image comes with Python and all necessary browser dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 5000
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD 1

# Set working directory
WORKDIR /app

# Install system dependencies (including additional packages for stability)
RUN apt-get update && apt-get install -y \
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
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only to save space)
RUN playwright install chromium

# Copy the rest of the application
COPY . .

# Create outputs directory if it doesn't exist
RUN mkdir -p outputs && chmod 777 outputs

# Expose the port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start the server with better error logging
CMD ["python", "-u", "server.py"]
