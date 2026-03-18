FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Chromium + driver (modern way)
RUN apt-get update && apt-get install -y \
    wget unzip curl \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Testing (includes matching driver)
RUN wget -q https://storage.googleapis.com/chrome-for-testing-public/last-known-good-versions-with-downloads.json -O /tmp/versions.json && \
    DRIVER_URL=$(cat /tmp/versions.json | grep -oP '"chromedriver":\s*{\s*"url":\s*"\K[^"]+') && \
    CHROME_URL=$(cat /tmp/versions.json | grep -oP '"chrome":\s*{\s*"url":\s*"\K[^"]+') && \
    wget -O /tmp/chrome.zip $CHROME_URL && \
    wget -O /tmp/driver.zip $DRIVER_URL && \
    unzip /tmp/chrome.zip -d /opt/chrome && \
    unzip /tmp/driver.zip -d /opt/chromedriver && \
    mv /opt/chrome/*/chrome /usr/bin/chrome && \
    mv /opt/chromedriver/*/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver

# Set env
ENV CHROME_BIN=/usr/bin/chromium
ENV PORT=10000

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 10000

CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
