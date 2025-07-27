import React,{useState} from 'react';
import axios from 'axios';
import "../../styles/Chatbot.css";

function RunChunkFileButton({ setChat }) {
  const [running, setRunning] = useState(false);
  const handleRunChunkFile = async () => {
    setRunning(true);
    try {
      const response = await axios.post('https://atlasic.onrender.com/run-chunk-file');
      setChat(prevChat => [...prevChat, {
        id: prevChat.length + 1,
        text: response.data.message || "File processed.",
        isUser: false
      }]);
    } catch (error) {
      setChat(prevChat => [...prevChat, {
        id: prevChat.length + 1,
        text: 'Error running Chunk.py. Please check the backend logs.',
        isUser: false
      }]);
    } finally {
      setRunning(false);
    }
  };

  return (
    <button className="run-btn" onClick={handleRunChunkFile} disabled={running}>{running ? "Running..." : "Run File 🏃‍♂️"}</button>
  );
}

export default RunChunkFileButton;
