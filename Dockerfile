# Use Python 3.12 as base image
ARG TARGETPLATFORM=linux/amd64
FROM --platform=$TARGETPLATFORM python:3.12-slim
# Set working directory
WORKDIR /app

# Install system dependencies and Chrome
RUN apt-get update && apt-get install -y \
    git \
    sqlite3 \
    wget \
    gnupg2 \
    curl \
    unzip \
    apt-transport-https \
    ca-certificates \
    software-properties-common \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN wget -q "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/linux64/chromedriver-linux64.zip" \
    && mkdir -p chromedriver \
    && unzip chromedriver-linux64.zip -d chromedriver/ \
    && mv chromedriver/chromedriver-linux64/chromedriver chromedriver/ \
    && chmod +x chromedriver/chromedriver \
    && rm chromedriver-linux64.zip

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directories
RUN mkdir -p /app/data
RUN mkdir -p /app/etc

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Command to run an interactive shell
# CMD ["/bin/bash"]
CMD ["python", "curator.py"]