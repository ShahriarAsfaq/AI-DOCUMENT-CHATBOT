import React from 'react';

const Header: React.FC = () => {
  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-4xl mx-auto px-4 py-4">
        <h1 className="text-2xl font-bold text-gray-900">AI Document Chatbot</h1>
        <p className="text-gray-600 mt-1">Ask questions about your documents</p>
      </div>
    </header>
  );
};

export default Header;