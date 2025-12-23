import React, { useState } from 'react';

const InputBar = ({ selectedDocs, onRemoveDoc, onSendMessage, disabled }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div
      style={{
        padding: '1rem',
        backgroundColor: '#1f2937',
        borderTop: '1px solid #374151',
      }}
    >
      {/* Selected Documents Pills */}
      {selectedDocs.length > 0 && (
        <div style={{ marginBottom: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {selectedDocs.map((docName) => (
            <div
              key={docName}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.375rem 0.75rem',
                backgroundColor: '#374151',
                color: 'white',
                borderRadius: '16px',
                fontSize: '0.875rem',
                border: '1px solid #4b5563',
              }}
            >
              <span>{docName}</span>
              <button
                onClick={() => onRemoveDoc(docName)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#9ca3af',
                  cursor: 'pointer',
                  padding: '0',
                  fontSize: '1rem',
                  lineHeight: 1,
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem' }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            selectedDocs.length === 0
              ? 'Ask a question (will search all documents)...'
              : `Ask about ${selectedDocs.join(', ')}...`
          }
          disabled={disabled}
          rows={1}
          style={{
            flex: 1,
            padding: '0.75rem',
            backgroundColor: '#374151',
            color: 'white',
            border: '1px solid #4b5563',
            borderRadius: '8px',
            fontSize: '0.875rem',
            resize: 'none',
            outline: 'none',
          }}
        />
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: disabled || !input.trim() ? '#4b5563' : '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: disabled || !input.trim() ? 'not-allowed' : 'pointer',
            fontSize: '0.875rem',
            fontWeight: '500',
          }}
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default InputBar;