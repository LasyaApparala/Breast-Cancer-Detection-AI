import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileImage, FileText, AlertCircle } from 'lucide-react';
import { UploadedFile } from '../../types';

interface FileUploadProps {
  onFilesChange: (files: UploadedFile[]) => void;
  acceptedTypes?: string[];
  maxFiles?: number;
  maxSize?: number;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFilesChange,
  acceptedTypes = ['image/*', '.pdf', '.doc', '.docx'],
  maxFiles = 10,
  maxSize = 10 * 1024 * 1024, // 10MB
}) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setError(null);
    
    const newFiles: UploadedFile[] = acceptedFiles.map((file) => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      type: getFileType(file.name, file.type),
      size: file.size,
      uploadedAt: new Date().toISOString(),
      url: URL.createObjectURL(file),
    }));

    const updatedFiles = [...files, ...newFiles].slice(0, maxFiles);
    setFiles(updatedFiles);
    onFilesChange(updatedFiles);
  }, [files, maxFiles, onFilesChange]);

  const removeFile = (id: string) => {
    const updatedFiles = files.filter((file) => file.id !== id);
    setFiles(updatedFiles);
    onFilesChange(updatedFiles);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedTypes.reduce((acc, type) => {
      acc[type] = [];
      return acc;
    }, {} as Record<string, string[]>),
    maxSize,
    maxFiles: maxFiles - files.length,
  });

  const getFileType = (filename: string, mimeType: string): UploadedFile['type'] => {
    if (mimeType.startsWith('image/')) {
      if (filename.toLowerCase().includes('mammo')) return 'mammogram';
      if (filename.toLowerCase().includes('ultrasound')) return 'ultrasound';
      if (filename.toLowerCase().includes('mri')) return 'mri';
      return 'mammogram';
    }
    if (filename.toLowerCase().includes('pathology')) return 'pathology';
    return 'report';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`upload-zone cursor-pointer ${
          isDragActive ? 'border-primary-500 bg-primary-100' : ''
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center space-y-2">
          <Upload className="h-12 w-12 text-primary-400" />
          <div className="text-center">
            <p className="text-lg font-medium text-gray-700">
              {isDragActive ? 'Drop files here' : 'Upload medical documents'}
            </p>
            <p className="text-sm text-gray-500">
              Drag and drop or click to select files
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Max {maxFiles} files, {formatFileSize(maxSize)} each
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="h-4 w-4 text-red-500" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Uploaded Files ({files.length})</h4>
          <div className="max-h-60 overflow-y-auto space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex items-center space-x-3">
                  {file.type.includes('image') ? (
                    <FileImage className="h-5 w-5 text-blue-500" />
                  ) : (
                    <FileText className="h-5 w-5 text-gray-500" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">
                      {file.type} • {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(file.id)}
                  className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
