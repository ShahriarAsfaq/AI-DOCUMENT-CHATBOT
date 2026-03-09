import React from 'react';
import { ChatMessage } from '../../types';

interface MessageItemProps {
  message: ChatMessage;
}

const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  return (
    <div className="space-y-4">
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

          {/* Citations */}
          {message.citations && message.citations.trim() && (
            <div className="mb-3 p-3 bg-blue-50 border-l-4 border-blue-400">
              <h4 className="text-sm font-semibold text-blue-800 mb-2">Citations:</h4>
              <div className="text-sm text-blue-700 whitespace-pre-line">
                {message.citations}
              </div>
            </div>
          )}

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
  );
};

export default MessageItem;