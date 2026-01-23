import React from 'react';

const Message = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-content">
        {!isUser && (
          <div className="message-sources">
            FinQuery
          </div>
        )}
        <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
      </div>
    </div>
  );
};

export default Message;