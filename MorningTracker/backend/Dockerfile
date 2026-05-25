# Optimized Production Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

# Minimal system dependencies (keep image small)
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (leverage cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# NOTE: We intentionally do NOT run `playwright install` here.
# The core pipeline (Google RSS + httpx/trafilatura) does not require browsers,
# and Playwright downloads can fail in some networks (DNS/proxy restrictions).

# Copy backend application code
COPY . .

# Default command: Production-grade Uvicorn with workers
# Explicit sh -c ensures Railway's $PORT environment variable is correctly expanded at runtime
CMD ["sh", "-c", "gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120"]
