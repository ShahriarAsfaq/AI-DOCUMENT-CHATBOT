# syntax=docker/dockerfile:1

FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_ENV=production

WORKDIR /app

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr-eng \
        poppler-utils \
        libgl1 \
        libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code only
COPY ai_chatbot ./ai_chatbot
COPY manage.py .

# Create non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Railway 1GB RAM → single worker, multiple threads
CMD ["gunicorn","ai_chatbot.wsgi:application","--bind","0.0.0.0:$PORT","--workers","1","--threads","4","--timeout","120"]