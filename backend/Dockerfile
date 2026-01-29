# Python base image
FROM python:3.11-slim

# Install system dependencies for Chrome and psycopg2
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    libpq-dev \
    gcc \
    curl \
    --no-install-recommends \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update && apt-get install -y \
    google-chrome-stable \
    --no-install-recommends \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Environment variables setup (can be overridden at runtime)
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app.py"]
