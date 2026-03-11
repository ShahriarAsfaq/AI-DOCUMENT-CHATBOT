# syntax=docker/dockerfile:1

############################
# Stage 1 — Builder
############################
FROM python:3.10-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# install uv (fast pip replacement)
RUN pip install --no-cache-dir uv

COPY requirements.txt .

# build wheels
RUN uv pip wheel -r requirements.txt -w /wheels

############################
# Stage 2 — OCR runtime
############################
FROM python:3.10-slim AS ocr

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

############################
# Stage 3 — Distroless runtime
############################
FROM gcr.io/distroless/python3-debian11

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# copy python wheels
COPY --from=builder /wheels /wheels

# install dependencies
RUN python -m pip install --no-cache-dir /wheels/*

# copy OCR binaries
COPY --from=ocr /usr/bin/tesseract /usr/bin/
COPY --from=ocr /usr/bin/pdftoppm /usr/bin/
COPY --from=ocr /usr/share/tesseract-ocr /usr/share/tesseract-ocr

# copy project
COPY . .

EXPOSE 8000

CMD ["gunicorn", "ai_chatbot.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1"]