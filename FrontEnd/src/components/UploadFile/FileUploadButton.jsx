import React, { useRef } from "react";
import axios from "axios";
import "../../styles/Chatbot.css";

const MAX_FILE_SIZE = 5 * 1024 * 1024; 

const FileUploadButton = ({ chat, setChat }) => {
  const fileInputRef = useRef(null);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > MAX_FILE_SIZE) {
      alert("File size exceeds 5MB. Please choose a smaller file.");
      e.target.value = "";
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://localhost:8000/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (response.status === 200) {
        const successMessage = {
          id: chat.length + 1,
          text: `📁 File "${file.name}" uploaded successfully.`,
          isUser: false,
          pdf: null,
        };
        setChat((prev) => [...prev, successMessage]);
      } else {
        const errorMessage = {
          id: chat.length + 1,
          text: `❌ File upload failed with status: ${response.status}.`,
          isUser: false,
          pdf: null,
        };
        setChat((prev) => [...prev, errorMessage]);
      }
    } catch (err) {
      console.error("Upload error:", err);
      const errorMessage = {
        id: chat.length + 1,
        text: `❌ File upload failed. Please try again.`,
        isUser: false,
        pdf: null,
      };
      setChat((prev) => [...prev, errorMessage]);
    }
  };

  return (
    <>
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
      <button
        className="attach-btn"
        type="button"
        onClick={() => fileInputRef.current.click()}
        title="Upload File"
      >
        Upload 📎
      </button>
    </>
  );
};

export default FileUploadButton;
