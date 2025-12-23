import React, { useRef } from 'react';

const Sidebar = ({ documents, selectedDocs, onSelectDoc, onUpload, isUploading }) => {
  const fileInputRef = useRef(null);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
      e.target.value = ''; // Reset input
    }
  };

  return (
    <div
      style={{
        width: '280px',
        height: '100vh',
        backgroundColor: '#1f2937',
        borderRight: '1px solid #374151',
        display: 'flex',
        flexDirection: 'column',
        padding: '1rem',
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ color: 'white', fontSize: '1.25rem', marginBottom: '1rem' }}>
          Documents
        </h2>
        
        {/* Upload Button */}
        <button
          onClick={handleUploadClick}
          disabled={isUploading}
          style={{
            width: '100%',
            padding: '0.75rem',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: isUploading ? 'not-allowed' : 'pointer',
            fontSize: '0.875rem',
            fontWeight: '500',
            opacity: isUploading ? 0.6 : 1,
          }}
        >
          {isUploading ? 'Uploading...' : '+ Upload Document'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
      </div>

      {/* Documents List */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {documents.length === 0 ? (
          <div style={{ color: '#9ca3af', fontSize: '0.875rem', textAlign: 'center' }}>
            No documents uploaded
          </div>
        ) : (
          documents.map((doc) => {
            const isSelected = selectedDocs.includes(doc.name);
            return (
              <div
                key={doc.name}
                onClick={() => onSelectDoc(doc.name)}
                style={{
                  padding: '0.75rem',
                  marginBottom: '0.5rem',
                  backgroundColor: isSelected ? '#2563eb' : '#374151',
                  color: 'white',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  transition: 'all 0.2s',
                  border: isSelected ? '2px solid #60a5fa' : '2px solid transparent',
                }}
              >
                <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                  {doc.name}
                </div>
                <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                  {doc.count} chunks
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default Sidebar;