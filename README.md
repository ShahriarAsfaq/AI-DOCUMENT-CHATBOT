# AI Document Chatbot

This repository contains a production-ready Django backend for an AI document chatbot with a React + TypeScript frontend. It implements a Retrieval-Augmented Generation (RAG) system for intelligent document querying, exposing REST APIs for chat, document management, and vector-based retrieval.

## Features

- Django 4.2 backend with Django REST Framework
- React + TypeScript frontend with Vite
- Modular RAG pipeline: document ingestion, chunking, embedding, vector storage, retrieval, reranking, and LLM generation
- FAISS vector store for efficient similarity search
- SentenceTransformers for document embeddings
- Groq LLM for chat responses
- Document summary and topic extraction during ingestion
- Intent detection for generic queries (e.g., "summarize document", "list topics")
- Automatic question rewriting using conversation history before retrieval
- Source citations and similarity scores in responses
- File upload support for PDF/DOCX with OCR capabilities
- Environment-based configuration
- CORS enabled for frontend integration
- Dockerized deployment with persistent volumes
- Management commands for document processing and vector verification

## Chosen Architecture

The application follows a modular, microservices-inspired architecture within a Django monolith:

- **Backend (Django)**: Handles API endpoints, business logic, and RAG pipeline.
- **Frontend (React + TypeScript)**: Provides the user interface for chat and document upload.
- **RAG Pipeline**: A custom-built pipeline without external frameworks like LangChain, consisting of:
  - Document Loader: Parses PDFs/DOCX, extracts text via PyMuPDF and OCR.
  - Chunker: Splits documents into semantic chunks.
  - Embeddings: Generates vector representations using SentenceTransformers.
  - Vector Store: FAISS for indexing and similarity search.
  - Retriever: Fetches relevant chunks based on query embeddings.
  - Reranker: Reorders results by relevance.
  - Chat Service: Integrates LLM (Groq) with prompt building and response generation.
- **Database**: SQLite for simplicity, with models for chats, documents, and metadata.
- **Deployment**: Docker container with Gunicorn, persistent FAISS volumes.

## Technical Explanation

The RAG system enhances LLM responses by retrieving relevant context from uploaded documents:

1. **Ingestion**: Documents are uploaded via API and processed on startup to rebuild the vector store; there is no separate queuing service.
2. **Query Processing**: User queries are rewritten using chat history for context, then embedded and searched against the vector store.
3. **Retrieval & Generation**: Top chunks are retrieved, reranked, and fed into a prompt for the LLM to generate cited answers.
4. **Intent Handling**: Detects non-retrieval intents (e.g., summary requests) and responds accordingly without vector search.
5. **Persistence**: Vectors and metadata are saved to disk, reloaded on startup for continuity.

This approach ensures accurate, source-backed responses while handling large document sets efficiently.

## Libraries Used

### Backend
- **Python 3.10**: Core language.
- **Django 4.2**: Web framework for API and ORM.
- **Django REST Framework**: API serialization and views.
- **FAISS**: Vector similarity search library.
- **SentenceTransformers**: Pre-trained models for text embeddings.
- **Groq**: LLM API for chat generation.
- **PyMuPDF (Fitz)**: PDF text extraction.
- **Pytesseract**: OCR for image-based text in PDFs.
- **django-environ**: Environment variable management.
- **django-cors-headers**: Cross-origin resource sharing.

### Frontend
- **React**: UI library.
- **TypeScript**: Type-safe JavaScript.
- **Vite**: Build tool and dev server.
- **Tailwind CSS**: Utility-first CSS framework.
- **Axios**: HTTP client for API calls.

### Deployment
- **Docker**: Containerization.
- **Gunicorn**: WSGI server for production.
- **Render/Railway**: Cloud hosting platforms.
- DUE to resourse constraints, the frontend and backend are seperatly deployed. And the backend's heavy dependencies are being downloaded runtime to make the docker image small.

## Justification of Technical Decisions

- **Django over Flask/FastAPI**: Provides built-in ORM, admin interface, and security features, suitable for a full-stack app with database models.
- **Custom RAG over LangChain**: Avoids bloat and dependencies, allowing fine-tuned control over the pipeline for better performance and customization.
- **FAISS over Pinecone/Weaviate**: Lightweight, self-hosted vector store that integrates seamlessly with Python, no external API costs.
- **SentenceTransformers over OpenAI Embeddings**: Open-source, cost-free, and performant for general-purpose text embedding without API rate limits.
- **Groq over OpenAI GPT**: Faster inference for real-time chat, lower latency, and competitive pricing.
- **Celery + Redis**: Handles long-running document processing asynchronously, preventing API timeouts.
- **React + TypeScript**: Type safety reduces bugs; Vite provides fast development experience.
- **Docker**: Ensures consistent environments across development and production, simplifies deployment.
- **SQLite**: Simple, file-based database for prototyping; can be swapped for PostgreSQL in production.
- **OCR Integration**: Supports scanned PDFs, broadening document compatibility without relying on external services.

## Setup
### Due to some production deployemnt problem, to run in local device, use the code of local_branch

### Backend Setup

1. **Create virtual environment & install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .\\venv\\Scripts\\activate on Windows
   pip install -r requirements.txt
   ```

2. **Copy env example and adjust**
   ```bash
   cp .env.example .env
   # then edit .env with real values (e.g., GROQ_API_KEY)
   ```

3. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

4. **Run development server**
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

The frontend will run on `http://localhost:3000` and proxy API requests to the Django backend.


## Deployment

### Local Docker Test
1. Build the image:
   ```bash
   docker build -t ai-document-chatbot:latest .
   ```
2. Run with docker-compose:
   ```bash
   docker-compose up
   ```

### Cloud Deployment
- Use `render.yaml` for Render deployment.
- Ensure persistent disk for `/app/vectors/faiss_store`.
- Set environment variables: `DJANGO_SETTINGS_MODULE=settings_prod`, `SECRET_KEY`, `GROQ_API_KEY`, etc.
- Upgrade to at least 1GB RAM plan to avoid memory issues.

## API Endpoints

- `POST /api/chat/` - Send chat messages with history
- `GET /api/chat/history/` - Retrieve chat history
- `POST /api/documents/upload/` - Upload and process documents
- `GET /api/documents/` - List uploaded documents

## Project Structure

```
ai-document-chatbot/
├── ai_chatbot/                      # Django project root
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py                 # Base settings
│   ├── settings_prod.py            # Production settings
│   ├── urls.py                     # Main URL configuration
│   ├── wsgi.py
│   ├── __pycache__/
│   ├── chat/                       # Chat app
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py               # Chat models
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py                # Chat API views
│   │   └── __pycache__/
│   ├── documents/                  # Document management app
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py               # Document models
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py                # Document upload/views
│   │   ├── __pycache__/
│   │   ├── management/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   └── commands/
│   │   │       ├── __init__.py
│   │   │       ├── process_documents.py  # Document ingestion command
│   │   │       └── __pycache__/
│   │   └── migrations/
│   │       ├── __init__.py
│   │       ├── 0001_initial.py
│   │       └── __pycache__/
│   └── rag/                        # RAG components
│       ├── __init__.py
│       ├── admin.py
│       ├── apps.py
│       ├── chat_service.py          # Main chat logic with LLM
│       ├── chunker.py               # Document chunking
│       ├── document_loader.py       # PDF/DOCX parsing
│       ├── document.py              # Document utilities
│       ├── embeddings.py            # Embedding generation
│       ├── hallucination_guard.py   # Response validation
│       ├── llm_service.py           # LLM integration
│       ├── models.py                # RAG models
│       ├── prompt_builder.py        # Prompt construction
│       ├── query_expansion.py       # Question rewriting
│       ├── reranker.py              # Result reranking
│       ├── retriever.py             # Vector retrieval
│       ├── security.py              # Input sanitization
│       ├── serializers.py
│       ├── urls.py
│       ├── utils.py                 # Helper functions
│       ├── vector_store.py          # FAISS management
│       ├── views.py
│       └── __pycache__/
├── db.sqlite3                       # SQLite database
├── docs/                            # Documentation (if any)
├── frontend/                        # React frontend
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── README.md
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── public/
│   └── src/
│       ├── App.css
│       ├── App.tsx                 # Main React app
│       ├── index.css
│       └── main.tsx
├── logs/                            # Application logs
├── manage.py                        # Django management script
├── media/                           # Uploaded files
│   └── docs/                        # Document storage
├── requirements.txt                 # Python dependencies
├── start.bat                        # Windows startup script
├── start.sh                         # Linux/Mac startup script
├── vectors/                         # Vector data
│   └── faiss_store/
│       └── faiss.index              # FAISS index file
├── .env                             # Environment variables (local)
├── .env.example                     # Example env file
├── .dockerignore                    # Docker ignore file
├── .gitignore                       # Git ignore
├── docker-compose.yml               # Docker compose config
├── Dockerfile                       # Docker build file
├── README.md                        # This file
└── render.yaml                      # Render deployment config
```

## Notes

- Vector store and document metadata persist across restarts.
- Use `python manage.py verify_vector` to check and rebuild vectors if needed.
- For production, ensure `ALLOWED_HOSTS` and `SECRET_KEY` are set securely.
- Frontend is served separately; integrate with Django static files for full-stack deployment if desired.

---

