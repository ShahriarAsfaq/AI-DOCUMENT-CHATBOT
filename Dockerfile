# syntax=docker/dockerfile:1

################################################################################
# builder stage – compile wheels, install build deps
################################################################################
FROM python:3.10-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# build‑time dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        tesseract-ocr \
        poppler-utils \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

################################################################################
# final stage – runtime only
################################################################################
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_ENV=production

WORKDIR /app

# runtime packages (build tools dropped)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        poppler-utils \
        libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*

# create non‑root user
RUN useradd --create-home appuser
USER appuser

# copy python packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# copy source
COPY --chown=appuser:appuser . .

RUN mkdir -p logs staticfiles media

EXPOSE 8000

CMD python manage.py migrate --noinput && \
    python manage.py process_documents && \
    python manage.py collectstatic --noinput && \
    gunicorn ai_chatbot.wsgi:application --bind 0.0.0.0:$PORT --workers 1