import { useState, useRef } from 'react';
import { uploadDocument, validateFile } from '../utils/api';

export const useFileUpload = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const validationError = validateFile(file);
    if (validationError) {
      alert(validationError);
      return;
    }

    setSelectedFile(file);
    setIsUploading(true);

    try {
      const data = await uploadDocument(file);
      alert(`File uploaded successfully: ${data.title}`);
    } catch (error) {
      console.error("Upload error:", error);
      alert("Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  return {
    selectedFile,
    isUploading,
    fileInputRef,
    handleFileUpload,
    openFileDialog,
  };
};