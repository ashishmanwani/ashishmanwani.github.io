FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

# Copy application code
COPY api/ /app/api/
COPY scraper/ /app/scraper/
COPY proxy/ /app/proxy/
COPY notifications/ /app/notifications/
COPY migrations/ /app/migrations/
COPY alembic.ini /app/alembic.ini
COPY scripts/ /app/scripts/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
