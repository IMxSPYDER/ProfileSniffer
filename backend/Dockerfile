FROM python:3.10-slim

# Install system dependencies required for Chromium
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libxfixes3 \
    libxext6 \
    libxrender1 \
    wget \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Environment variables
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV PORT=10000

# Set working directory
WORKDIR /app

# Copy project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 10000

# Run with Gunicorn (PRODUCTION READY)
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
