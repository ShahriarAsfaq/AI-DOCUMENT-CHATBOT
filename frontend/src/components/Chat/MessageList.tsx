import React from 'react';
import { ChatMessage } from '../../types';
import MessageItem from './MessageItem';
import LoadingIndicator from './LoadingIndicator';

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

const MessageList: React.FC<MessageListProps> = ({ messages, isLoading }) => {
  return (
    <div className="h-96 overflow-y-auto p-4 space-y-4">
      {messages.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <p>No messages yet. Upload a document and start asking questions!</p>
        </div>
      ) : (
        messages.map((message) => (
          <MessageItem key={message.id} message={message} />
        ))
      )}

      {isLoading && <LoadingIndicator />}
    </div>
  );
};

export default MessageList;