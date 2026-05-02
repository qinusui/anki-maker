import { useState, useRef } from 'react';
import { Upload, X, FileVideo, FileText } from 'lucide-react';
import { cn } from '../utils/cn';

interface FileUploadProps {
  accept: string;
  onFileSelect: (file: File) => void;
  selectedFile?: File | null;
  onClear?: () => void;
  label: string;
  icon?: 'video' | 'text';
}

export const FileUpload = ({
  accept,
  onFileSelect,
  selectedFile,
  onClear,
  label,
  icon = 'text',
}: FileUploadProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  const Icon = icon === 'video' ? FileVideo : FileText;

  return (
    <div className="w-full">
      <p className="text-sm font-medium text-gray-700 mb-2">{label}</p>

      {selectedFile ? (
        <div className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <Icon className="w-5 h-5 text-gray-500 flex-shrink-0" />
            <span className="text-sm text-gray-700 truncate">{selectedFile.name}</span>
          </div>
          {onClear && (
            <button
              onClick={onClear}
              className="ml-2 p-1 hover:bg-gray-200 rounded-md transition-colors"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          )}
        </div>
      ) : (
        <div
          onClick={handleClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
            isDragging
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-gray-400'
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            onChange={handleFileChange}
            className="hidden"
          />
          <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-600">
            点击上传或拖拽文件到此处
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {accept.replace(/,/g, ', ').toUpperCase()}
          </p>
        </div>
      )}
    </div>
  );
};
