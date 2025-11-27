FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Default command (will be overridden in docker-compose)
CMD ["python", "-u", "core/loop.py"]
