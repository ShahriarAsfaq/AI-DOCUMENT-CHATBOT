import { ChatRequest, ChatResponse, DocumentUploadResponse } from '../types';
import { API_ENDPOINTS, FILE_CONSTRAINTS } from './constants';

export const uploadDocument = async (file: File): Promise<DocumentUploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", file.name);

  const response = await fetch(API_ENDPOINTS.DOCUMENTS, {
    method: "POST",
    body: formData,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(JSON.stringify(data));
  }

  return data;
};

export const sendChatMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  const response = await fetch(API_ENDPOINTS.CHAT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || 'Unknown error occurred');
  }

  return data;
};

export const validateFile = (file: File): string | null => {
  const { MAX_SIZE, ALLOWED_TYPES, ALLOWED_EXTENSIONS } = FILE_CONSTRAINTS;

  if (!ALLOWED_TYPES.includes(file.type as any) && !ALLOWED_EXTENSIONS.some(ext => file.name.toLowerCase().endsWith(ext))) {
    return "Please upload a PDF or DOCX file";
  }

  if (file.size > MAX_SIZE) {
    return "File must be smaller than 10MB";
  }

  return null;
};