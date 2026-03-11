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

# Install Python dependencies (WITHOUT heavy ML packages)
COPY requirements.txt .
RUN pip install --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY ai_chatbot ./ai_chatbot
COPY manage.py .

# collect static files during build
RUN python manage.py collectstatic --noinput


# Create non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Gunicorn single worker for Railway 1GB RAM
# CMD ["gunicorn","ai_chatbot.wsgi:application","--bind","0.0.0.0:8000","--workers","1","--threads","4","--timeout","120"]
# start server
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn ai_chatbot.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120"]