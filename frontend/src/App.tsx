import React, { useState, useRef } from 'react';

interface ChatMessage {
  id: string;
  question: string;
  answer: string;
  sources: Array<{
    page: number;
    source: string;
    chunk_text: string;
  }>;
  similarity_scores: number[];
  context_count: number;
  used_fallback: boolean;
  session_id: string;
  message_id: number;
}

interface ChatResponse {
  success: boolean;
  answer: string;
  question: string;
  sources: Array<{
    page: number;
    source: string;
    chunk_text: string;
  }>;
  similarity_scores: number[];
  context_count: number;
  used_fallback: boolean;
  session_id: string;
  message_id: number;
}

const App: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const allowedTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ];

    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

    if (!allowedTypes.includes(file.type) && !file.name.endsWith(".pdf") && !file.name.endsWith(".docx")) {
      alert("Please upload a PDF or DOCX file");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      alert("File must be smaller than 10MB");
      return;
    }

    setSelectedFile(file);
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", file.name);

      const response = await fetch("http://127.0.0.1:8000/api/documents/documents/", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      console.log("Server response:", data);

      if (!response.ok) {
        throw new Error(JSON.stringify(data));
      }
      alert(`File uploaded successfully: ${data.title}`);

    } catch (error) {
      console.error("Upload error:", error);
      alert("Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;

    const currentQuestion = question.trim();
    setQuestion('');
    setIsLoading(true);

    let sessionId = localStorage.getItem("chat_session_id");

    if (!sessionId) {
      sessionId = crypto.randomUUID();
      localStorage.setItem("chat_session_id", sessionId);
    }

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: currentQuestion,
          session_id: sessionId
        }),
      });

      const data: ChatResponse = await response.json();

      if (response.ok && data.success) {
        const newMessage: ChatMessage = {
          id: Date.now().toString(),
          question: data.question,
          answer: data.answer,
          sources: data.sources,
          similarity_scores: data.similarity_scores,
          context_count: data.context_count,
          used_fallback: data.used_fallback,
          session_id: data.session_id,
          message_id: data.message_id,
        };

        setMessages(prev => [...prev, newMessage]);
      } else {
        alert('Error: ' + (data.error || 'Unknown error occurred'));
      }
    } catch (error) {
      console.error('Chat error:', error);
      alert('Failed to send message. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">AI Document Chatbot</h1>
          <p className="text-gray-600 mt-1">Ask questions about your documents</p>
        </div>
      </header>

      <div className="max-w-4xl mx-auto p-4">
        {/* File Upload Section */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Upload Document</h2>
          <div className="flex items-center space-x-4">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? 'Uploading...' : 'Choose File'}
            </button>
            {selectedFile && (
              <span className="text-gray-700">
                Selected: {selectedFile.name}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Supported formats: PDF, DOCX
          </p>
        </div>

        {/* Chat Section */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          {/* Messages */}
          <div className="h-96 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <p>No messages yet. Upload a document and start asking questions!</p>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className="space-y-4">
                  {/* User Question */}
                  <div className="flex justify-end">
                    <div className="bg-blue-600 text-white rounded-lg px-4 py-2 max-w-xs">
                      {message.question}
                    </div>
                  </div>

                  {/* AI Answer */}
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg px-4 py-3 max-w-2xl">
                      <div className="text-gray-900 mb-3">{message.answer}</div>

                      {/* Sources */}
                      {message.sources.length > 0 && (
                        <div className="border-t pt-3">
                          <h4 className="text-sm font-semibold text-gray-700 mb-2">Sources:</h4>
                          <div className="space-y-2">
                            {message.sources.map((source, index) => (
                              <div key={index} className="bg-white rounded p-3 border">
                                <div className="flex justify-between items-start">
                                  <div className="flex-1">
                                    <p className="text-sm text-gray-600">
                                      <strong>Page {source.page}</strong> - {source.source}
                                    </p>
                                    <p className="text-sm text-gray-800 mt-1">
                                      {source.chunk_text.substring(0, 100)}...
                                    </p>
                                  </div>
                                  <div className="ml-4 text-xs text-gray-500">
                                    Score: {(message.similarity_scores[index] * 100).toFixed(1)}%
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Fallback Message */}
                      {message.used_fallback && (
                        <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded">
                          <p className="text-sm text-yellow-800">
                            ⚠️ This response uses fallback mode due to insufficient context.
                          </p>
                        </div>
                      )}

                      {/* Metadata */}
                      <div className="mt-3 text-xs text-gray-500">
                        Context chunks: {message.context_count} | Session: {message.session_id.substring(0, 8)}...
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                    <span className="text-gray-600">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input Form */}
          <div className="border-t p-4">
            <form onSubmit={handleSubmit} className="flex space-x-4">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question about your document..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={!question.trim() || isLoading}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Sending...' : 'Send'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;