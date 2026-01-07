FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy config (changes rarely)
COPY config.py .
COPY config_v2.py .

# Copy main entry point
COPY main.py .

# Copy core modules (changes often - separate layer)
COPY core/ ./core/
COPY database/ ./database/
COPY web/ ./web/

# Copy ML models and data directories (will use volumes)
COPY ml_training/ ./ml_training/
COPY ml_data/ ./ml_data/

# Copy utility scripts
COPY check_self_learning.py .
COPY full_system_check.py .

# Copy settings
COPY settings.json .

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Disable Python bytecode caching (prevents stale .pyc files)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default command (will be overridden in docker-compose)
CMD ["python", "-u", "core/loop.py"]
