# syntax=docker/dockerfile:1

########################################
# Builder stage
########################################
FROM python:3.10-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# build wheels to reduce final image size
RUN pip install --upgrade pip wheel && \
    pip wheel --no-cache-dir -r requirements.txt -w /wheels


########################################
# Runtime stage
########################################
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_ENV=production

WORKDIR /app

# runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# install python dependencies
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# create non-root user
RUN useradd --create-home appuser

# copy project files
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# railway recommends single worker for low memory
CMD ["gunicorn", "ai_chatbot.wsgi:application", \
     "--bind", "0.0.0.0:$PORT", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "120"]