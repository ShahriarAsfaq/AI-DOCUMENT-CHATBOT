export interface Source {
  page: number;
  source: string;
  chunk_text: string;
}

export interface ChatMessage {
  id: string;
  question: string;
  answer: string;
  citations: string;
  sources: Source[];
  similarity_scores: number[];
  context_count: number;
  used_fallback: boolean;
  session_id: string;
  message_id: number;
}

export interface ChatResponse {
  success: boolean;
  answer: string;
  citations: string;
  question: string;
  sources: Source[];
  similarity_scores: number[];
  context_count: number;
  used_fallback: boolean;
  session_id: string;
  message_id: number;
}

export interface ChatRequest {
  question: string;
  session_id: string;
}

export interface DocumentUploadResponse {
  id: number;
  title: string;
  file: string;
  uploaded_at: string;
}