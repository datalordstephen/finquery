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

  const placeholder = selectedDocs.length === 0
    ? 'Ask a question (will search all documents)...'
    : `Ask about ${selectedDocs.join(', ')}...`;

  return (
    <div className="input-area">
      <div className="input-container">
        {selectedDocs.length > 0 && (
          <div className="selected-docs-pills">
            {selectedDocs.map((docName) => (
              <div key={docName} className="doc-pill">
                <span>{docName}</span>
                <button
                  className="pill-remove"
                  onClick={() => onRemoveDoc(docName)}
                  title="Remove document"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit} className="input-form">
          <div className="input-wrapper">
            <textarea
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
            />
          </div>
          <button
            type="submit"
            className="send-button"
            disabled={disabled || !input.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

export default InputBar;