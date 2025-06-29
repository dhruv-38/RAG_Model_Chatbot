import React, { useRef, useEffect } from 'react';
import { TTSButton } from '../TTS/TTSButton';

function ChatMessages({ messages, showPDF, setPdfUrl, setShowPDF }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="chat-messages">
      {messages.map((msg) => (
        <div key={msg.id} className={`message ${msg.isUser ? 'user-message' : 'bot-message'}`}>
          <div className="message-content">
            {msg.text}
            <br />
            {!msg.isUser && msg.pdf && (
              <>
                <button
                  className="view-pdf-btn"
                  onClick={() => {
                    setPdfUrl(msg.pdf.startsWith('http') ? msg.pdf : `http://localhost:8000${msg.pdf}`);
                    setShowPDF(true);
                  }}
                >
                  View PDF
                </button>
                <TTSButton text={msg.text} />
              </>
            )}
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}

export default ChatMessages;
