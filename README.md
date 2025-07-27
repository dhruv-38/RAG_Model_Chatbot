## 🚀 Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites

-   Python 3.9+
-   Node.js and npm (or yarn)
-   An environment variable file (`.env`) with your Google API Key.

### 1. Clone the Repository

```bash
git clone https://github.com/dhruv-38/RAG_Model_Chatbot.git
cd RAG_Model_Chatbot
git checkout dev # Make sure you are on the dev branch
```

### 2. Backend Setup

First, set up your Python environment and install the required dependencies.

```bash
# From the root directory
cd BackEnd

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows using Git Bash:
source venv/Scripts/activate

# On Windows using Command Prompt:
venv\Scripts\activate.bat

# On Mac/Linux:
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Create a .env file in the root directory
touch .env
```

Add your Google API key to the `.env` file. If you don’t have one, you can create it for free.
```env
GOOGLE_API_KEY="YOUR_API_KEY_HERE"
```

### 3. Frontend Setup

Navigate to the `frontend` directory and install the Node.js dependencies.

```bash
# From the root directory
cd frontend
npm install
```

### 4. Running the Application

You will need two separate terminals to run the backend and frontend servers.

**Terminal 1: Start the FastAPI Backend**

```bash
# From the root directory
cd BackEnd
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

**Terminal 2: Start the React Frontend**

```bash
# From the frontend directory
npm start
```

The user interface will be available at `http://localhost:3000`.

Wait for the process to complete. You can monitor the progress in the backend terminal. Once done, your chatbot is ready to answer questions about the documents!
