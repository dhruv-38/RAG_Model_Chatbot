import React from 'react';

function ChatInput({ message, setMessage, handleSend, isLoading, isRecording, startRecording, stopRecording, transcribing }) {
  return (
    <form className="chat-input-area" onSubmit={handleSend}>
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type your message here..."
        className="chat-input"
      />
      <button
        type="button"
        onClick={isRecording ? stopRecording : startRecording}
        className={`mic-button ${isRecording ? 'recording' : ''}`}
      >
        {isRecording ? '🛑 Stop' : '🎙️'}
      </button>
      {transcribing && <span>Transcribing...</span>}
      <button type="submit" className="send-btn" disabled={isLoading}>
        {isLoading ? 'Sending...' : 'Send'}
      </button>
    </form>
  );
}

export default ChatInput;
