export const API_BASE_URL = 'http://127.0.0.1:8000/api';

export const API_ENDPOINTS = {
  DOCUMENTS: `${API_BASE_URL}/documents/documents/`,
  CHAT: `${API_BASE_URL}/chat/`,
} as const;

export const FILE_CONSTRAINTS = {
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_TYPES: [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  ],
  ALLOWED_EXTENSIONS: ['.pdf', '.docx'],
} as const;

export const STORAGE_KEYS = {
  CHAT_SESSION_ID: 'chat_session_id',
} as const;