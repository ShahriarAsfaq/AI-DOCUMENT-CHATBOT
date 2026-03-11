# syntax=docker/dockerfile:1

############################
# builder
############################
FROM python:3.10-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip wheel && \
    pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels


############################
# runtime
############################
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

RUN useradd --create-home appuser

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

CMD python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn ai_chatbot.wsgi:application --bind 0.0.0.0:$PORT --workers 1