FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/

# Set environment variables
ENV PYTHONPATH=/app
ENV MATCHFLIX_DB_PATH=/app/data/matchflix.db
ENV MATCHFLIX_ICLOUD_BASE=/app/data/matchflix

# Create data directory
RUN mkdir -p /app/data/matchflix/kandidaten \
    /app/data/matchflix/werkgeversvragen \
    /app/data/matchflix/match-rapporten \
    /app/data/matchflix/.match_cache

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
