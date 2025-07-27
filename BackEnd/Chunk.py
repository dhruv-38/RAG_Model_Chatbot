from pathlib import Path
from unstructured.partition.pdf import partition_pdf
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json, hashlib
import os
import base64
from PIL import Image
import google.generativeai as genai
import uuid
from dotenv import load_dotenv
import shutil # Import shutil for directory removal

# --- Load API Key ---
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Config Paths ---
PDF_INPUT_DIR = Path("pdfs/") # Directory containing PDF files

# Define the base directory for all outputs
OUTPUT_BASE_DIR = Path("processing_output")
os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

COMPRESSED_IMAGE_DIR = OUTPUT_BASE_DIR / "compressed_images"
os.makedirs(COMPRESSED_IMAGE_DIR, exist_ok=True)

# This will be the parent for all temporary raw image directories
TEMP_RAW_IMAGES_PARENT_DIR = OUTPUT_BASE_DIR / "temp_raw_images_by_pdf"
os.makedirs(TEMP_RAW_IMAGES_PARENT_DIR, exist_ok=True)


# --- Text Splitter ---
splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)

# --- Helper Functions ---
def compress_image(image_path, output_dir, quality=85):
    try:
        with Image.open(image_path) as img:
            file_name = os.path.basename(image_path)
            compressed_path = os.path.join(output_dir, f"compressed_{file_name}")
            img.convert("RGB").save(compressed_path, "JPEG", quality=quality)
            return compressed_path
    except Exception as e:
        print(f"Error compressing {image_path}: {e}")
        return None

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def hash_b64(b64string):
    return hashlib.sha256(b64string.encode()).hexdigest()

# Define the figures_is_empty helper function here, before it's used
def figures_is_empty(path):
    """Checks if a directory is empty."""
    # Use path.iterdir() to check if there are any entries
    return not any(path.iterdir())

# --- PDF Processing Function ---
def process_pdf(pdf_path):
    print(f"Starting processing for: {pdf_path.name}")
    
    # Create a temporary directory for raw images for the current PDF under TEMP_RAW_IMAGES_PARENT_DIR
    temp_raw_image_dir = TEMP_RAW_IMAGES_PARENT_DIR / pdf_path.stem
    os.makedirs(temp_raw_image_dir, exist_ok=True)

    raw_elements = partition_pdf(
        filename=str(pdf_path),
        infer_table_structure=True,
        extract_images_in_pdf=True,
        image_output_dir_path=str(temp_raw_image_dir), # Use the temporary directory
        strategy="hi_res",
    )

    output = []
    seen_images = set()
    source_file = pdf_path.name

    for el in raw_elements:
        page = getattr(el.metadata, 'page_number', None)
        el_type = str(type(el))

        if "Table" in el_type:
            output.append({
                "uuid": str(uuid.uuid4()),
                "type": "table",
                "source_file": source_file,
                "page_number": page,
                "content": (el.metadata.text_as_html if hasattr(el.metadata, 'text_as_html') else el.text)
            })
            print(f"Processing table from {source_file}, page {page}....")

        elif "Image" in el_type and hasattr(el.metadata, "image_path"):
            image_path = el.metadata.image_path
            if image_path and os.path.exists(image_path):
                compressed_path = compress_image(image_path, COMPRESSED_IMAGE_DIR)
                if compressed_path:
                    b64 = encode_image(compressed_path)
                    hash_val = hash_b64(b64)
                    if hash_val not in seen_images:
                        seen_images.add(hash_val)

                        try:
                            # Create the image part for Gemini
                            image_part = {
                                "mime_type": "image/jpeg",
                                "data": base64.b64decode(b64)
                            }
                            
                            response = genai.generate_content(
                                model="gemini-pro-vision",
                                contents=[
                                    {
                                        "parts": [
                                            {"text": """Analyze the image carefully. If it contains any charts, diagrams, tables, or visible text, 
                                            summarize *all* of its contents in complete detail. Include any labels, legends, axes, or numbers 
                                            visible. Be exhaustive — assume there's no limit to output size.\n\n
                                            If the image appears to be a photograph or illustration with no diagrams, summarize it briefly, focusing 
                                            only on key visual elements."""},
                                            image_part
                                        ]
                                    }
                                ]
                            )
                            image_description = response.text
                        except Exception as e:
                            print(f"Gemini API error for image on page {page} in {source_file}: {e}")
                            image_description = "[Error in image description]"

                        output.append({
                            "uuid": str(uuid.uuid4()),
                            "type": "image",
                            "source_file": source_file,
                            "page_number": page,
                            "content": image_description
                        })
            print(f"Processing image from {source_file}, page {page}....")
            
        elif hasattr(el, "text") and isinstance(el.text, str) and el.text.strip():
            splits = splitter.split_text(el.text)
            for text_chunk in splits:
                output.append({
                    "uuid": str(uuid.uuid4()),
                    "type": "text",
                    "source_file": source_file,
                    "page_number": page,
                    "content": text_chunk
                })
            print(f"Processing text from {source_file}, page {page}....")
    
    # Clean up temporary raw image directory for the current PDF
    shutil.rmtree(temp_raw_image_dir)

    return output

# --- Main execution ---
all_processed_data = []
for pdf_file in PDF_INPUT_DIR.glob("*.pdf"):
    processed_data_for_pdf = process_pdf(pdf_file)
    all_processed_data.extend(processed_data_for_pdf)

# --- Write combined JSON ---
output_json = OUTPUT_BASE_DIR / "output_combined.json" # Output JSON also inside the base directory
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(all_processed_data, f, indent=2, ensure_ascii=False)

print(f"\nAll chunks from all PDFs are made and stored in: {output_json}")

# --- Clean up temp folder if it was created ---
folders_to_delete = [
    Path("figures"),
    Path("processing_output/compressed_images"),
    Path("processing_output/temp_raw_images_by_pdf")
]

for folder in folders_to_delete:
    if folder.exists() and folder.is_dir():
        shutil.rmtree(folder)
        print(f"Deleted folder: {folder}")
    else:
        print(f"Folder does not exist: {folder}")




from langchain.vectorstores import Chroma
from langchain_core.documents import Document
import tiktoken
from sentence_transformers import SentenceTransformer

# --- Load Environment Variables ---
load_dotenv()

# --- Tokenizer and Vectorstore Setup ---
encoding = tiktoken.encoding_for_model("text-embedding-3-small")

# Use BGE embeddings instead of OpenAI
class BGEEmbeddings:
    def __init__(self, model_name='BAAI/bge-large-en-v1.5'):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
    
    def embed_query(self, text):
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()

embeddings = BGEEmbeddings()
persist_dir = "vector_db"
os.makedirs(persist_dir, exist_ok=True)

vectorstore = Chroma(
    collection_name="multi_modal_chunks",
    embedding_function=embeddings,
    persist_directory=persist_dir
)

# --- Smart Batch Helper ---
def smart_batch(docs, tokenizer, max_tokens=280000, max_docs=5460):
    batch = []
    total_tokens = 0
    for doc in docs:
        text = doc.page_content if hasattr(doc, "page_content") else doc["content"]
        tokens = len(tokenizer.encode(text))
        if total_tokens + tokens > max_tokens or len(batch) >= max_docs:
            yield batch
            batch = []
            total_tokens = 0
        batch.append(doc)
        total_tokens += tokens
    if batch:
        yield batch

# --- Process All JSON Files ---
json_folder = "processing_output"
for filename in os.listdir(json_folder):
    if filename.endswith(".json"):
        filepath = os.path.join(json_folder, filename)
        print(f"Loading {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        all_text_docs = []
        all_table_docs = []
        all_image_docs = []

        for chunk in chunks:
            doc = Document(
                page_content=chunk["content"],
                metadata={
                    "uuid": chunk["uuid"],
                    "type": chunk["type"],
                    "page_number": chunk.get("page_number"),
                    "source_file": chunk.get("source_file", filename)
                }
            )
            if chunk["type"] == "text":
                all_text_docs.append(doc)
            elif chunk["type"] == "table":
                all_table_docs.append(doc)
            elif chunk["type"] == "image":
                all_image_docs.append(doc)

        print(f"Embedding text chunks from {filename}...")
        for batch in smart_batch(all_text_docs, encoding):
            vectorstore.add_documents(batch)

        print(f"Embedding table chunks from {filename}...")
        for batch in smart_batch(all_table_docs, encoding):
            vectorstore.add_documents(batch)

        print(f"Embedding image chunks from {filename}...")
        for batch in smart_batch(all_image_docs, encoding):
            vectorstore.add_documents(batch)

# --- Save the Vectorstore ---
vectorstore.persist()
print("All documents embedded and saved in ChromaDB.")
