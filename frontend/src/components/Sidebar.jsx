import React, { useRef, useState } from 'react';

const Sidebar = ({ documents, selectedDocs, onSelectDoc, onUpload, onDelete, isUploading }) => {
  const fileInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
      e.target.value = '';
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files?.[0];
    if (file && file.name.endsWith('.pdf')) {
      onUpload(file);
    } else {
      alert('Please upload a PDF file');
    }
  };

  const handleDelete = (e, docName) => {
    e.stopPropagation();
    if (window.confirm(`Delete ${docName}?`)) {
      onDelete(docName);
    }
  };

  return (
    <div className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-logo">FinQuery</div>
        <div className="sidebar-tagline">Financial Document Q&A</div>
      </div>

      {/* Documents List */}
      <div className="sidebar-content">
        <div className="documents-section-title">Documents</div>
        
        {documents.length === 0 ? (
          <div className="empty-state">
            No documents uploaded yet
          </div>
        ) : (
          <div className="document-list">
            {documents.map((doc) => {
              const isSelected = selectedDocs.includes(doc.name);
              return (
                <div
                  key={doc.name}
                  onClick={() => onSelectDoc(doc.name)}
                  className={`document-item ${isSelected ? 'selected' : ''}`}
                >
                  <div className="document-name">{doc.name}</div>
                  <div className="document-meta">
                    <div className="document-stats">
                      <span>{doc.pages || 0} pages</span>
                      <span>•</span>
                      <span>{doc.count} chunks</span>
                    </div>
                    <button
                      className="delete-btn"
                      onClick={(e) => handleDelete(e, doc.name)}
                      title="Delete document"
                    >
                      ×
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Upload Area - EXACTLY like PDFtoChat */}
      <div className="upload-section">
        <div
          className={`upload-area ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleUploadClick}
        >
          <div className="upload-content">
            <button
              className="upload-button"
              disabled={isUploading}
              onClick={(e) => {
                e.stopPropagation();
                handleUploadClick();
              }}
            >
              {isUploading ? 'Uploading...' : 'Upload a File'}
            </button>
            <div className="upload-subtext">...or drag and drop a file.</div>
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
      </div>
    </div>
  );
};

export default Sidebar;