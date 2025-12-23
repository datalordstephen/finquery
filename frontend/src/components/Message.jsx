import React from 'react';

const Message = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '1rem',
        padding: '0 1rem',
      }}
    >
      <div
        style={{
          maxWidth: '70%',
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          backgroundColor: isUser ? '#2563eb' : '#374151',
          color: 'white',
        }}
      >
        {!isUser && message.sources && message.sources.length > 0 && (
          <div
            style={{
              fontSize: '0.75rem',
              opacity: 0.7,
              marginBottom: '0.5rem',
            }}
          >
            Sources: {message.sources.map(s => `Page ${s.page}`).join(', ')}
          </div>
        )}
        <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
      </div>
    </div>
  );
};

export default Message;