# AI Document Chatbot

This repository contains a production-ready Django backend for an AI document chatbot with a React + TypeScript frontend. It exposes REST APIs for chat, document management, and retrieval-augmented generation (RAG).

## Features

- Django 4.2 backend with Django REST Framework
- React + TypeScript frontend with Vite
- Modular apps: `chat`, `documents`, `rag`
- Custom RAG implementation (no LangChain dependency)
- FAISS vector store configuration
- OpenAI embeddings support
- Environment-based configuration using `django-environ`
- CORS enabled for React frontend compatibility
- File upload (PDF/DOCX)
- Chat interface with source citations
- Document summary and topic extraction during ingestion
- Intent detection for generic queries (summary, topic count/list)
- Automatic question rewriting using conversation history before retrieval
- Similarity scores and fallback indicators

## Setup

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
   # then edit .env with real values
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

## Quick Start

To run both backend and frontend together:

**Windows:**
```bash
./start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

## API Endpoints

- `POST /api/chat/` - Send chat messages
- `GET /api/chat/history/` - Get chat history (TODO)
- `POST /api/documents/upload/` - Upload documents (TODO)

## Project Structure

```
ai-document-chatbot/
├── ai_chatbot/           # Django project
│   ├── chat/            # Chat app with models and APIs
│   ├── documents/       # Document management (TODO)
│   ├── rag/             # RAG components and services
│   └── settings.py      # Django configuration
├── frontend/            # React + TypeScript frontend
│   ├── src/
│   │   ├── App.tsx      # Main chat interface
│   │   └── ...
│   └── package.json
├── requirements.txt     # Python dependencies
└── README.md
```

## Notes

- Add your AI logic in respective apps when extending the custom RAG and FAISS components.
- Vector store path is configured in `settings.py` as `VECTOR_STORE_PATH`.
- Frontend includes mock implementations for testing without full backend integration.

---

Happy coding!
