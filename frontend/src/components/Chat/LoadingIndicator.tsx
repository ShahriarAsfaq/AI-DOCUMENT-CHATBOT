import React from 'react';

const LoadingIndicator: React.FC = () => {
  return (
    <div className="flex justify-start">
      <div className="bg-gray-100 rounded-lg px-4 py-3">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
          <span className="text-gray-600">Thinking...</span>
        </div>
      </div>
    </div>
  );
};

export default LoadingIndicator;