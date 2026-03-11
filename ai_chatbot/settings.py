# ai_chatbot/settings.py
import os
from pathlib import Path
import environ
import sys

print("=== DJANGO SETTINGS DEBUG ===", file=sys.stderr)
print(f"Current settings file: {__file__}", file=sys.stderr)
print(f"DJANGO_SETTINGS_MODULE: {os.environ.get('DJANGO_SETTINGS_MODULE', 'Not set')}", file=sys.stderr)

BASE_DIR = Path(__file__).resolve().parent.parent

# read .env file
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ''),
    ALLOWED_HOSTS=(list, []),
)
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env('SECRET_KEY', default='replace-this-with-a-secure-key')
DEBUG = env('DEBUG')

# ===== ALLOWED_HOSTS CONFIGURATION =====
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
        "ai-document-chatbot-production.up.railway.app",
        '.railway.app',
    ],
)

RAILWAY_URL = os.environ.get('RAILWAY_STATIC_URL')
if RAILWAY_URL:
    railway_domain = RAILWAY_URL.replace('https://', '').replace('http://', '')
    if railway_domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(railway_domain)

print(f"✓ FINAL ALLOWED_HOSTS: {ALLOWED_HOSTS}", file=sys.stderr)
# ===== END ALLOWED_HOSTS CONFIGURATION =====

# ===== DATABASE CONFIGURATION =====
# Use PostgreSQL on Railway (via DATABASE_URL env var), SQLite for local development
DATABASES = {
    'default': env.db(default='sqlite:///db.sqlite3')
}

# Print database info for debugging
db_engine = DATABASES['default']['ENGINE']
db_type = 'PostgreSQL' if 'postgresql' in db_engine else 'SQLite'
print(f"✓ Using database: {db_type}", file=sys.stderr)
# ===== END DATABASE CONFIGURATION =====

# CSRF settings for API
CSRF_TRUSTED_ORIGINS = [
    'https://ai-document-chatbot-production.up.railway.app',
    'http://localhost:3000',
    'http://localhost:8000',
]

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8000',
    'https://ai-document-chatbot-production.up.railway.app',
]

CORS_ALLOW_CREDENTIALS = True

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # third party
    'rest_framework',
    'corsheaders',
    # local apps
    'ai_chatbot.chat',
    'ai_chatbot.documents',
    'ai_chatbot.rag',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ai_chatbot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ai_chatbot.wsgi.application'
ASGI_APPLICATION = 'ai_chatbot.asgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=True)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

OPENAI_API_KEY = env('OPENAI_API_KEY', default='')
HUGGINGFACE_TOKEN = env('HUGGINGFACE_TOKEN', default='')
GROQ_API_KEY = env('GROQ_API_KEY', default='')

VECTOR_STORE_PATH = BASE_DIR / 'vectors'

# ============================================================================
# RAG & Chat Service Configuration
# ============================================================================

CHAT_SERVICE = None

def get_or_create_chat_service():
    """Lazily initialize ChatService."""
    global CHAT_SERVICE
    
    if CHAT_SERVICE is not None:
        return CHAT_SERVICE
    
    try:
        from ai_chatbot.rag.llm_service import GroqLLMService
        from ai_chatbot.rag.vector_store import FaissVectorStore
        from ai_chatbot.rag.retriever import create_retriever
        from ai_chatbot.rag.chat_service import create_chat_service
        import logging
        
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        llm_service = GroqLLMService(api_key=GROQ_API_KEY, model="llama-3.1-8b-instant")
        vector_store = FaissVectorStore()
        
        # Try to load vector store
        processed_store_path = VECTOR_STORE_PATH / "faiss_store"
        if os.path.exists(processed_store_path / "faiss.index"):
            try:
                vector_store.load_index(str(processed_store_path))
                logging.info(f"Loaded processed vector store with {vector_store.get_index_size()} documents")
            except Exception as e:
                logging.warning(f"Could not load processed vector store: {e}")
        
        if vector_store.get_index_size() == 0:
            vector_store_path = VECTOR_STORE_PATH
            if os.path.exists(vector_store_path / "faiss.index"):
                try:
                    vector_store.load_index(str(vector_store_path))
                    logging.info(f"Loaded legacy vector store with {vector_store.get_index_size()} documents")
                except Exception as e:
                    logging.warning(f"Could not load legacy vector store: {e}")
        
        if vector_store.get_index_size() == 0:
            raise ValueError("No vector store found")
        
        retriever = create_retriever(vector_store, use_reranking=True, top_k=10)
        
        CHAT_SERVICE = create_chat_service(
            retriever,
            llm_service,
            context_threshold=0.15,
        )
        
        logging.info("ChatService initialized successfully")
        
    except Exception as e:
        import logging
        logging.error(f"Failed to initialize ChatService: {e}")
        CHAT_SERVICE = None
    
    return CHAT_SERVICE


# CORS allowed origins for frontend
CORS_ALLOWED_ORIGINS = [
    "https://ai-document-chatbotfrontend-h1q06q4j4-shahriarasfaqs-projects.vercel.app",
    "https://ai-document-chatbotfrontend.vercel.app"
]

# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# WhiteNoise static files configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'