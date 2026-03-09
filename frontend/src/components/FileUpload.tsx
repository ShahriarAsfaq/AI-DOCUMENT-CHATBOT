import React from 'react';
import { useFileUpload } from '../hooks';

const FileUpload: React.FC = () => {
  const { selectedFile, isUploading, fileInputRef, handleFileUpload, openFileDialog } = useFileUpload();

  return (
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
          onClick={openFileDialog}
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
  );
};

export default FileUpload;