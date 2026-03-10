# slim base image for small footprint
FROM python:3.10-slim

# make Python behave in production-friendly way
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_ENV=production

WORKDIR /app

# install minimal system libraries for building wheels & image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libsm6 \
        libxrender1 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

# we'll remove the build-essential package after pip install to reduce final image size

# leverage Docker cache by copying only requirements initially
COPY requirements.txt ./

# install Python dependencies without cache
# keep root here so we can remove build tools afterwards
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    # drop build tools once packages are in place
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# create non-root user and switch
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# copy application code
COPY . .

# create runtime directories
RUN mkdir -p logs staticfiles media

# expose port provided by Railway or default
EXPOSE $PORT

# startup routine: migrations, build vectors, collect static, then serve
CMD python manage.py migrate --noinput \
    && python manage.py process_documents \
    && python manage.py collectstatic --noinput \
    && gunicorn ai_chatbot.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1
