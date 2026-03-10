"""Production-specific Django settings."""

from .settings import *  # import base settings

# override any insecure defaults
DEBUG = False

# ALLOWED_HOSTS should be defined in environment; default to wildcard for cloud platforms
# Railway/Render populate ALLOWED_HOSTS via env, but fallback to '*' so the container starts.
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=["*"])

# Vector store location (persisted volume)
VECTOR_STORE_PATH = Path(os.environ.get('VECTOR_STORE_PATH', BASE_DIR / 'vectors'))

# Make sure static root is set (already set in base settings)
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Other production hardening can go here (e.g. SECURE_SSL_REDIRECT)
