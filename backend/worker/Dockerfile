FROM python:3.11-slim

WORKDIR /app

# System deps for Playwright + curl_cffi
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    ca-certificates \
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY worker/requirements.txt /app/worker/requirements.txt
RUN pip install --no-cache-dir -r /app/worker/requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy application code
COPY worker/ /app/worker/
COPY scraper/ /app/scraper/
COPY proxy/ /app/proxy/
COPY notifications/ /app/notifications/
COPY api/config.py /app/api/config.py
COPY api/models/ /app/api/models/
COPY api/db/ /app/api/db/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
