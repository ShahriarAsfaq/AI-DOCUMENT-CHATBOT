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
        from ai_chatbot.rag.llm_service import MockLLMService
        from ai_chatbot.rag.vector_store import FaissVectorStore
        from ai_chatbot.rag.retriever import create_retriever
        from ai_chatbot.rag.chat_service import create_chat_service
        import os
        
        # For now, use mock LLM for testing
        # To use OpenAI instead:
        # from ai_chatbot.rag.llm_service import OpenAILLMService
        # llm_service = OpenAILLMService(api_key=OPENAI_API_KEY)
        
        llm_service = MockLLMService()
        
        # Initialize vector store (empty for now - will be populated via API)
        vector_store = FaissVectorStore()
        
        # Try to load existing vector store if available
        vector_store_path = VECTOR_STORE_PATH
        if os.path.exists(vector_store_path / "faiss.index"):
            try:
                vector_store.load_index(str(vector_store_path))
            except Exception as e:
                import logging
                logging.warning(f"Could not load vector store: {e}")
                # Create empty vector store with dummy data for testing
                import numpy as np
                dummy_embeddings = np.random.randn(1, 384).astype(np.float32)
                dummy_metadata = [{"page": 1, "source": "test.pdf", "chunk_text": "Sample document content"}]
                vector_store.build_index(dummy_embeddings, dummy_metadata)
        else:
            # Create empty vector store with dummy data for testing
            import numpy as np
            dummy_embeddings = np.random.randn(1, 384).astype(np.float32)
            dummy_metadata = [{"page": 1, "source": "test.pdf", "chunk_text": "Sample document content"}]
            vector_store.build_index(dummy_embeddings, dummy_metadata)
        
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