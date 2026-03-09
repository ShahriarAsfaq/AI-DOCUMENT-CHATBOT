import { useState } from 'react';
import { ChatMessage, ChatResponse } from '../types';
import { sendChatMessage } from '../utils/api';
import { STORAGE_KEYS } from '../utils/constants';

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const getSessionId = (): string => {
    let sessionId = localStorage.getItem(STORAGE_KEYS.CHAT_SESSION_ID);

    if (!sessionId) {
      sessionId = crypto.randomUUID();
      localStorage.setItem(STORAGE_KEYS.CHAT_SESSION_ID, sessionId);
    }

    return sessionId;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;

    const currentQuestion = question.trim();
    setQuestion('');
    setIsLoading(true);

    const sessionId = getSessionId();

    try {
      const data: ChatResponse = await sendChatMessage({
        question: currentQuestion,
        session_id: sessionId,
      });

      const newMessage: ChatMessage = {
        id: Date.now().toString(),
        question: data.question,
        answer: data.answer,
        citations: data.citations,
        sources: data.sources,
        similarity_scores: data.similarity_scores,
        context_count: data.context_count,
        used_fallback: data.used_fallback,
        session_id: data.session_id,
        message_id: data.message_id,
      };

      setMessages(prev => [...prev, newMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      alert('Failed to send message. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return {
    messages,
    question,
    isLoading,
    setQuestion,
    handleSubmit,
  };
};