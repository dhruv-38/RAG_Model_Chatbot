from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from fastapi.staticfiles import StaticFiles
import google.generativeai as genai
from fastapi.responses import FileResponse
import shutil
import uuid
import subprocess
import pyttsx3
import tempfile
import io
from faster_whisper import WhisperModel


load_dotenv()

# --- FastAPI APP ---
app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASE_DIR, "build")
STATIC_DIR = os.path.join(BUILD_DIR, "static")

# --- Static files (PDFs) ---
app.mount("/pdfs", StaticFiles(directory="./pdfs"), name="pdfs")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Input schema ---
class Query(BaseModel):
    question: str

# --- Vector DB and LLM Setup ---
api_key = os.getenv("GOOGLE_API_KEY")
persist_dir = "./vector_db"

# Configure Gemini
genai.configure(api_key=api_key)

# Use BGE embeddings instead of OpenAI
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer('BAAI/bge-large-en-v1.5')

# Custom embedding function for Chroma
class BGEEmbeddings:
    def __init__(self, model_name='BAAI/bge-large-en-v1.5'):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
    
    def embed_query(self, text):
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()

embedding = BGEEmbeddings()
vectorstore = Chroma(
    persist_directory=persist_dir,
    embedding_function=embedding,
    collection_name="multi_modal_chunks"
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.5, google_api_key=api_key)

# --- Prompt construction ---
def build_prompt(context_docs, question):
    context_parts = []
    for doc in context_docs:
        part = f"\n---\n{doc.page_content}\n(Source: {doc.metadata.get('source_file', 'N/A')} - Page {doc.metadata.get('page_number', 'N/A')})"
        context_parts.append(part)
    context_text = "\n".join(context_parts)
    prompt = f"""[Persona]
    You are a specialized AI assistant designed for high-accuracy question answering. Your core function is to act as a document analysis engine. You are forbidden from using any external knowledge or information not explicitly provided in the context.

    [Context]
    You will be given a body of text ("context_text") and a specific question ("question"). This context is your entire universe of knowledge for this task; you must operate as if no other information exists.

    {context_text}: The provided documents or text to be analyzed.

    {question}: The user's query that must be answered based on the context.

    [Task]
    Your task is to answer the "question" based only on the information available in the "context_text". You must follow a strict process:

    Analyze the Question: First, understand the user's specific query.

    Exhaustive Search: Scrutinize all provided documents to find any and all relevant passages.

    Synthesize or Infer:

    If the answer is directly stated, synthesize the information into a comprehensive answer.

    If the answer is not directly stated, attempt to logically infer a conclusion based on the available evidence. You must explain your reasoning for the inference.

    If the information required to answer the question does not exist in the context, you must state that the answer cannot be found. Do not guess.

    [Format]
    Your final output must adhere to the following structure precisely:

    Answer: Provide a full explanation of the answer, elaborating on the requirement of the question. MOST IMPORTANT- Dont write something like this "This content is explicitly provided in the/not explicitly provided in the/is gathered from the context provided." at any point of you answer.

    Source: Every piece of information drawn from the context must be followed by a citation. The required citation format is: (Document: [Document number], File: [Source filename], Page: [Page number(s)]).

    [Exampler]
    Here is a sample of the desired output structure:

    Answer: The Post Retirement Benefit Scheme (PRBS) section outlines that ONGC operates a defined contribution pension scheme for employees, administered via a separate trust. The company contributes an amount up to 30% of basic pay and dearness allowance, reduced by its contributions toward provident fund, gratuity, post-retirement medical benefits (PRMB), or any other retirement benefits. The Trust is responsible for investing surplus funds, setting contribution and interest rates, and purchasing annuities for employees. While not listed as a bullet-point summary, these details together describe a comprehensive post-retirement package covering pension, medical care, and annuity security.

    Source: (Document: 1, File: ONGC Annual Report 2023-2024.pdf, Page  Section: 42.1.1)

    [Tone]
    The tone must be objective, factual, and informational. Avoid any creative or conversational language. Your purpose is to report findings from the documents accurately and dispassionately."""
    return prompt

# --- Main assistant endpoint ---
@app.post("/ask")
async def ask_question(query: Query):
    print("Received question:", query.question)
    try:
        docs = await retriever.ainvoke(query.question)
        print(f"Retrieved {len(docs)} documents for query: {query.question}")
        for i, doc in enumerate(docs):
            print(f"Doc {i}: {doc.page_content[:200]}... (Source: {doc.metadata.get('source_file', 'N/A')})")
        if not docs:
            print(f"No documents found for query: {query.question}")
            return {
                "response": "No relevant documents found for your query.",
                "pdf": None
            }
        prompt = build_prompt(docs, query.question)
        response = llm.invoke(prompt)
        print(f"LLM response: {response.content[:200]}..." if response.content else "Empty response")
        if not response.content or response.content.strip() == "":
            return {
                "response": "I'm sorry, I couldn't generate a response. Please try rephrasing your question.",
                "pdf": None
            }
        pdf_reference = docs[0].metadata.get('source_file', None) if docs else None
        if pdf_reference:
            pdf_reference = f"/pdfs/{os.path.basename(pdf_reference)}"
        return {
            "response": response.content,
            "pdf": pdf_reference
        }
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        return {
            "error": str(e),
            "pdf": None
        }

# --- Transcription endpoint ---
@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        print(f"Received audio file: {file.filename}, size: {len(contents)} bytes")
        
        # Save the uploaded file temporarily with proper path
        temp_file_path = os.path.join(tempfile.gettempdir(), f"audio_{uuid.uuid4()}.webm")
        print(f"Saving to: {temp_file_path}")
        
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(contents)
        
        print(f"File saved successfully. File exists: {os.path.exists(temp_file_path)}")
        print(f"File size: {os.path.getsize(temp_file_path)} bytes")

        # Load Faster Whisper model (will download on first use)
        print("Loading Faster Whisper model...")
        model = WhisperModel("base", device="cpu", compute_type="int8")
        print("Faster Whisper model loaded successfully")
        
        # Transcribe using Faster Whisper
        print("Starting transcription...")
        segments, info = model.transcribe(temp_file_path, beam_size=5)
        print("Transcription completed")
        
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print("Temporary file cleaned up")
        
        # Return transcribed text
        text = " ".join([segment.text for segment in segments]).strip()
        print(f"Transcribed text: {text}")
        return {"text": text}
            
    except Exception as e:
        print(f"Transcription error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        # Clean up file if it exists
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        return {"error": str(e)}

# --- TTS endpoint ---
TTS_INSTRUCTIONS = """Voice: Clear, authoritative, and composed, projecting confidence and professionalism.
Tone: Neutral and informative, maintaining a balance between formality and approachability.
Punctuation: Structured with commas and pauses for clarity, ensuring information is digestible and well-paced.
Delivery: Steady and measured, with slight emphasis on key figures and deadlines to highlight critical points."""

class SpeakRequest(BaseModel):
    text: str



@app.post("/speak")
async def speak(data: SpeakRequest, background_tasks: BackgroundTasks):
    audio_filename = f"temp_audio_{uuid.uuid4()}.wav"
    audio_path = os.path.join(os.getcwd(), audio_filename)
    try:
        # Initialize TTS engine
        engine = pyttsx3.init()
        
        # Configure voice settings
        engine.setProperty('rate', 150)    # Speed of speech
        engine.setProperty('volume', 0.9)  # Volume level
        
        # Get available voices and set to a good one
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)  # Use first available voice
        
        # Save to file
        engine.save_to_file(data.text, audio_path)
        engine.runAndWait()
        
        background_tasks.add_task(os.remove, audio_path)
        return FileResponse(audio_path, media_type="audio/wav", filename="speech.wav")
    except Exception as e:
        print(f"Error during speech generation: {e}")
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return {"error": "Failed to generate speech", "details": str(e)}

# --- File upload (admin) ---
UPLOAD_DIR = "pdfs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        return {"error": "File size exceeds 5MB limit."}
    filename = os.path.basename(file.filename)
    file_location = os.path.join(UPLOAD_DIR, filename)
    with open(file_location, "wb") as f:
        f.write(contents)
    return {"message": "File uploaded successfully", "filename": filename}

# --- Chunking endpoint ---
@app.post("/run-chunk-file")
async def run_chunk_file():
    try:
        result = subprocess.run(
            ["python", "Chunk.py"],
            capture_output=True,
            text=True,
            check=True
        )
        print("Chunk.py stdout:", result.stdout)
        if result.stderr:
            print("Chunk.py stderr:", result.stderr)
        return {"message": "Chunk.py executed successfully!", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        print(f"Error running Chunk.py: {e.stderr}")
        return {"message": f"Error running Chunk.py: {e.stderr}", "error": True}
    except FileNotFoundError:
        return {"message": "Error: Chunk.py or python interpreter not found.", "error": True}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"message": f"An unexpected error occurred: {str(e)}", "error": True}

# --- API credits test endpoint ---
@app.get("/test/credits")
async def test_api_credits():
    try:
        test_response = llm.invoke("Hello")
        return {
            "status": "success",
            "message": "Gemini API is working",
            "response_preview": test_response.content[:50] + "..."
        }
    except Exception as e:
        error_message = str(e).lower()
        if "quota" in error_message or "insufficient" in error_message:
            return {
                "status": "quota_exceeded",
                "message": "API credits exhausted",
                "error": str(e)
            }
        elif "rate" in error_message:
            return {
                "status": "rate_limited",
                "message": "Rate limit hit",
                "error": str(e)
            }
        else:
            return {
                "status": "error",
                "message": "Other API error",
                "error": str(e)
            }

# Serve React index.html at root
@app.get("/")
async def serve_root():
    return FileResponse(os.path.join(BUILD_DIR, "index.html"))

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    file_path = os.path.join(BUILD_DIR, full_path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(BUILD_DIR, "index.html"))