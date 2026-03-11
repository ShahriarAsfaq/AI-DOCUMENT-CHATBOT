"""Production-specific Django settings."""

from .settings import *  # import base settings

# override any insecure defaults
DEBUG = False

# ALLOWED_HOSTS should be defined in environment (Render provides RENDER_EXTERNAL_HOSTNAME)
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
        "ai-document-chatbot-production.up.railway.app",
    ],
)

# Vector store location (persisted volume)
VECTOR_STORE_PATH = Path(os.environ.get('VECTOR_STORE_PATH', BASE_DIR / 'vectors'))

# Make sure static root is set (already set in base settings)
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Other production hardening can go here (e.g. SECURE_SSL_REDIRECT)
INSTALLED_APPS += ["corsheaders"]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware"] + MIDDLEWARE

CORS_ALLOWED_ORIGINS = [
    "https://ai-document-chatbotfrontend-h1q06q4j4-shahriarasfaqs-projects.vercel.app",
    "https://ai-document-chatbotfrontend.vercel.app"
]