import React from 'react';
import { useChat } from '../../hooks';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

const ChatContainer: React.FC = () => {
  const { messages, question, isLoading, setQuestion, handleSubmit } = useChat();

  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
      <MessageList messages={messages} isLoading={isLoading} />
      <ChatInput
        question={question}
        isLoading={isLoading}
        onQuestionChange={setQuestion}
        onSubmit={handleSubmit}
      />
    </div>
  );
};

export default ChatContainer;