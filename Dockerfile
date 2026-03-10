# Production-ready Dockerfile for Django project

FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DJANGO_ENV=production

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . /app/

# Collect static files and run migrations during build (optional)
# NOTE: in some deployments you might prefer to run these at container start
RUN python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput

# Expose port for gunicorn
EXPOSE 8000

# Start gunicorn
CMD ["gunicorn", "ai_chatbot.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
