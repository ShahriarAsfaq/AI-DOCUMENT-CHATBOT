import React from 'react';
import { Header, FileUpload, ChatContainer } from './components';

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="max-w-4xl mx-auto p-4">
        <FileUpload />
        <ChatContainer />
      </div>
    </div>
  );
};

export default App;