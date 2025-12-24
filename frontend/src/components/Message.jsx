import React from 'react';

const Message = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-content">
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="message-sources">
            Sources: {message.sources.map(s => `Page ${s.page}`).join(', ')}
          </div>
        )}
        <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
      </div>
    </div>
  );
};

export default Message;