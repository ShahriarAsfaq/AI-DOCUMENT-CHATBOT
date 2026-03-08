import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
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

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Application definition

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

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': env.db(default='sqlite:///db.sqlite3')
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=True)

# Django REST Framework config (examples)
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

# FAISS / OpenAI related
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')
HUGGINGFACE_TOKEN = env('HUGGINGFACE_TOKEN', default='')

# path or settings for vector store if needed
VECTOR_STORE_PATH = BASE_DIR / 'vectors'

# ============================================================================
# RAG & Chat Service Configuration
# ============================================================================

# Initialize ChatService (lazy loading to avoid circular imports)
CHAT_SERVICE = None

def get_or_create_chat_service():
    """Lazily initialize ChatService."""
    global CHAT_SERVICE
    
    if CHAT_SERVICE is not None:
        return CHAT_SERVICE
    
    try:
        from ai_chatbot.rag.llm_service import HuggingFaceLLMService
        from ai_chatbot.rag.vector_store import FaissVectorStore
        from ai_chatbot.rag.retriever import create_retriever
        from ai_chatbot.rag.chat_service import create_chat_service
        import os
        
        # Use HuggingFace LLM service (requires HUGGINGFACE_TOKEN in .env)
        if not HUGGINGFACE_TOKEN:
            raise ValueError("HUGGINGFACE_TOKEN environment variable is required")
        
        llm_service = HuggingFaceLLMService(token=HUGGINGFACE_TOKEN, model="HuggingFaceH4/zephyr-7b-alpha")
        
        # Initialize vector store
        vector_store = FaissVectorStore()
        
        # Try to load processed vector store first
        processed_store_path = VECTOR_STORE_PATH / "faiss_store"
        if os.path.exists(processed_store_path / "faiss.index"):
            try:
                vector_store.load_index(str(processed_store_path))
                import logging
                logging.info(f"Loaded processed vector store with {vector_store.get_index_size()} documents")
            except Exception as e:
                import logging
                logging.warning(f"Could not load processed vector store: {e}")
                vector_store = FaissVectorStore()  # Reset
        
        # If no processed store, try to load legacy vector store
        if vector_store.get_index_size() == 0:
            vector_store_path = VECTOR_STORE_PATH
            if os.path.exists(vector_store_path / "faiss.index"):
                try:
                    vector_store.load_index(str(vector_store_path))
                    import logging
                    logging.info(f"Loaded legacy vector store with {vector_store.get_index_size()} documents")
                except Exception as e:
                    import logging
                    logging.warning(f"Could not load legacy vector store: {e}")
        
        # If still no vector store, fail (no dummy data)
        if vector_store.get_index_size() == 0:
            raise ValueError(
                "No vector store found. Run 'python manage.py process_documents' "
                "to process uploaded documents and build the vector store."
            )
        
        # Create retriever
        retriever = create_retriever(vector_store, use_reranking=False, top_k=3)
        
        # Create chat service
        CHAT_SERVICE = create_chat_service(retriever, llm_service)
        
        import logging
        logging.info("ChatService initialized successfully")
        
    except Exception as e:
        import logging
        logging.error(f"Failed to initialize ChatService: {e}")
        CHAT_SERVICE = None
    
    return CHAT_SERVICE

# Initialize ChatService on startup
CHAT_SERVICE = get_or_create_chat_service()

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'rag_retrieval.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'ai_chatbot.rag': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'ai_chatbot.chat': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}