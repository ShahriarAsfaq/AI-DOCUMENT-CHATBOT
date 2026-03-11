# syntax=docker/dockerfile:1

FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr-eng \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code only
COPY ai_chatbot ./ai_chatbot
COPY manage.py .

# Create non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Gunicorn memory-safe config for Railway 1GB
CMD ["gunicorn","ai_chatbot.wsgi:application","--bind","0.0.0.0:$PORT","--workers","1","--threads","4","--timeout","120"]