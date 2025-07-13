import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import '../../styles/Chatbot.css';
import chatbotIcon from '../../assets/chatbot_icon.png';
import { TTSButton } from '../TTS/TTSButton';
import FileUploadButton from '../UploadFile/FileUploadButton';
import RunChunkFileButton from '../UploadFile/RunChunkFileButton';

function ChatContainer() {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chat, setChat] = useState([
    { id: 1, text: 'Hi!', isUser: true, pdf: null },
    { id: 2, text: 'Please create a chat session first', isUser: false, pdf: null }
  ]);
  const [showPDF, setShowPDF] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat]);

  // Assistant message send
  const sendMessage = async (e, customMessage = null) => {
    if (e && e.preventDefault) e.preventDefault();
    const msgToSend = customMessage ?? message;
    if (!msgToSend.trim() || isLoading) return;

    const userMessage = { id: chat.length + 1, text: msgToSend, isUser: true, pdf: null };
    setChat([...chat, userMessage]);
    setMessage('');
    setIsLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/ask', {
        question: msgToSend
      });

      const botMessage = {
        id: chat.length + 2,
        text: response.data.response || 'Sorry, I couldn\'t process that.',
        isUser: false,
        pdf: response.data.pdf || null
      };
      setChat(prevChat => [...prevChat, botMessage]);
    } catch (error) {
      const errorMessage = {
        id: chat.length + 2,
        text: 'Error connecting to the server. Please ensure the backend is running.',
        isUser: false,
        pdf: null
      };
      setChat(prevChat => [...prevChat, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Voice recording logic
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);

  const startRecording = async () => {
    setIsRecording(true);
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    // Try to use MP3 format, fallback to default if not supported
    let mimeType = 'audio/mp3';
    if (!MediaRecorder.isTypeSupported('audio/mp3')) {
      mimeType = 'audio/webm;codecs=opus';
    }
    
    const recorder = new window.MediaRecorder(stream, {
      mimeType: mimeType
    });
    setMediaRecorder(recorder);

    let chunks = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);

    recorder.onstop = async () => {
      stream.getTracks().forEach(track => track.stop());
      
      // Create blob with detected format
      const audioBlob = new Blob(chunks, { type: mimeType });
      setTranscribing(true);
      const formData = new FormData();
      formData.append("file", audioBlob, `recording.${mimeType.includes('mp3') ? 'mp3' : 'webm'}`);

      try {
        const res = await axios.post("http://localhost:8000/transcribe", formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });
        const transcribedText = res.data.text;
        setMessage(transcribedText);
        await sendMessage(undefined, transcribedText);
      } catch (err) {
        alert("Transcription failed");
        console.error(err);
      } finally {
        setTranscribing(false);
      }
    };

    recorder.start();
  };

  const stopRecording = () => {
    setIsRecording(false);
    mediaRecorder && mediaRecorder.stop();
  };

  return (
    <div className="chatbot-container">
      {/* Header */}
      <div className="chatbot-header">
        <div className="chatbot-logo">
          <img src={chatbotIcon} alt="Chatbot" className="logo-img" />
        </div>
        <div className="chatbot-branding">
          <div>
            Atlasic
          </div>
        </div>
        <div className="logout-btn">
          <button className="logout">Logout</button>
        </div>
      </div>

      {/* Main */}
      <div className="chatbot-main">
        {showPDF && (
          <div className="chatbot-pdf-panel">
            <div className="pdf-viewer-container">
              <iframe src={pdfUrl} title="PDF Viewer" style={{ width: '100%', height: '100%', border: 'none' }} />
              <button className="close-pdf-btn" onClick={() => setShowPDF(false)}>Close PDF</button>
            </div>
          </div>
        )}

        <div className={`chatbot-right${showPDF ? ' slide-right' : ''}`}>
          <div className="chat-container">
            {/* Upload and chunk */}
            <div className="chat-header">
              <div className='upload-run'>
                <FileUploadButton chat={chat} setChat={setChat} />
                <RunChunkFileButton setChat={setChat} />
              </div>
            </div>
            {/* Chat Messages */}
            <div className="chat-messages">
              {chat.map((msg) => (
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
            {/* Input Area */}
            <form
              className="chat-input-area"
              onSubmit={sendMessage}
            >
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
              <button
                type="submit"
                className="send-btn"
                disabled={isLoading}
              >
                {isLoading ? 'Sending...' : 'Send'}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="chatbot-footer">
        <div className="footer-left">
          <span>Developed by Me</span>
        </div>
        <div className="footer-right">
          <span>© {new Date().getFullYear()} All Rights Reserved.</span>
        </div>
      </div>
    </div>
  );
}

export default ChatContainer;
