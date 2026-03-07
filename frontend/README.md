# AI Document Chatbot Frontend

A React + TypeScript frontend for the AI Document Chatbot with file upload and chat functionality.

## Features

- 📁 File upload (PDF/DOCX)
- 💬 Chat interface with AI responses
- 📄 Source citations with page numbers
- 📊 Similarity scores display
- ⚠️ Fallback message indicators
- 🎨 Clean UI with Tailwind CSS

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000` and proxy API requests to the Django backend on `http://localhost:8000`.

## API Integration

The frontend connects to the Django backend using the following endpoints:

- `POST /api/chat/` - Send chat messages
- `POST /api/upload/` (TODO) - Upload documents

## File Structure

```
frontend/
├── src/
│   ├── App.tsx          # Main chat interface
│   ├── main.tsx         # React entry point
│   ├── index.css        # Tailwind CSS imports
│   └── App.css          # Additional styles
├── index.html           # HTML template
├── package.json         # Dependencies and scripts
├── vite.config.ts       # Vite configuration
├── tsconfig.json        # TypeScript configuration
└── tailwind.config.js   # Tailwind CSS configuration
```

## Usage

1. Upload a PDF or DOCX document
2. Ask questions about the document in the chat
3. View AI responses with source citations and similarity scores
4. Fallback messages are highlighted when context is insufficient