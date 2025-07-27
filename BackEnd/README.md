# RAG Chatbot Backend

This backend has been refactored to use Google's Gemini API and BGE embeddings instead of OpenAI.

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Create a `.env` file in the BackEnd directory with:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   FRONTEND_ORIGIN=http://localhost:3000
   ```

3. **Get Google API Key**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Add it to your `.env` file

4. **Run the Backend**
   ```bash
   uvicorn main:app --reload
   ```

## Changes Made

- **LLM**: Replaced OpenAI GPT-4 with Google Gemini 2.5 flash
- **Embeddings**: Replaced OpenAI embeddings with BGE-large-en-v1.5
- **TTS**: Replaced OpenAI TTS with pyttsx3 (local)
- **STT**: Replaced OpenAI Whisper with speech_recognition (Google Speech API)

## Features

- Document processing and chunking
- Vector database with BGE embeddings
- RAG-based question answering
- Text-to-Speech (local)
- Speech-to-Text (Google Speech API)
- File upload and management 