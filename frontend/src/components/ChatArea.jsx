import React, { useRef, useEffect } from 'react';
import Message from './Message';

const ChatArea = ({ messages, isLoading, onExampleClick }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Example questions
  const exampleQuestions = [
    "Hi, what's up?",
    "What do you do?",
    "What was my highest expense?",
    "How much did I spend at bokku?",
  ];

  return (
    <div className="chat-area">
      {messages.length === 0 ? (
        <div className="chat-empty">
          <div className="chat-empty-icon">
            <svg viewBox="0 0 24 24">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <div className="chat-empty-text">Ready when you are.</div>
          
          {/* Example Questions */}
          <div className="example-questions">
            <div className="example-title">Try asking:</div>
            <div className="example-grid">
              {exampleQuestions.map((question, idx) => (
                <button
                  key={idx}
                  className="example-button"
                  onClick={() => onExampleClick(question)}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <>
          {messages.map((message, index) => (
            <Message key={index} message={message} />
          ))}
          {isLoading && (
            <div className="loading-message">
              <div className="loading-content">
                Thinking<span className="loading-dots"></span>
              </div>
            </div>
          )}
        </>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatArea;