# AI-Powered Debt Navigator – Lightweight RAG Edition

This project implements a minimal Retrieval-Augmented Generation (RAG) application using FastAPI and LangChain. It allows users to ask questions about student loan data stored in `TOTALSL.csv`.

## Folder Structure

```
rag-debt-navigator/
├── data/
│   └── TOTALSL.csv               # Student loan CSV file
├── rag_app/
│   ├── retriever.py              # Load CSV, chunk rows, embed, create retriever
│   ├── service.py                # FastAPI app with POST /ask
│   ├── utils.py                  # Helper functions for chunking and embedding
│   └── debt_calculator.py        # Debt repayment calculation logic
├── frontend/                     # React frontend application
├── .env.template                 # Template file for API key
├── requirements.txt              # All required Python dependencies
└── README.md
```

## Full Application Setup and Running

To run the full Debt Navigator application (both backend and frontend), follow these steps:

### 1. Environment and Database Setup

*   **Create an Environment File:**
    *   In the root directory (`rag-debt-navigator`), create a copy of `.env.template` and name it `.env`.
    *   Open the `.env` file and fill in your credentials for the `GEMINI_API_KEY` and your MySQL database.

*   **Database Creation:**
    *   Ensure your MySQL server is running.
    *   Create the database `rag_db` if it doesn't already exist:
        ```sql
        CREATE DATABASE rag_db;
        ```
    *   The application will automatically create the necessary tables when it starts.

### 2. Backend Setup and Running

1.  **Navigate to the project root directory:**
    ```bash
    cd C:\Users\angel\rag-debt-navigator
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set your GEMINI_API_KEY environment variable.** (This is used by the RAG part of the backend).
    *   **For PowerShell:**
        ```powershell
        $env:GEMINI_API_KEY="your_gemini_api_key_here"
        ```
    *   **For Command Prompt (CMD):**
        ```cmd
        set GEMINI_API_KEY=your_gemini_api_key_here
        ```
    *   Replace `your_gemini_api_key_here` with your actual Gemini API key.

4.  **Run the FastAPI application:**
    ```bash
    uvicorn rag_app.service:app --reload
    ```
    Leave this terminal window open and running. The backend will be accessible at `http://127.0.0.1:8000`.

### 3. Frontend Setup and Running

1.  **Open a new terminal window.**

2.  **Navigate to the frontend directory:**
    ```bash
    cd C:\Users\angel\rag-debt-navigator\frontend
    ```

3.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```

4.  **Run the React development server:**
    ```bash
    npm start
    ```
    This will usually open your browser to `http://localhost:3000`. Leave this terminal window open and running.

## Application Usage

Once both the backend and frontend servers are running:

1.  Open your web browser and go to `http://localhost:3000`.
2.  **Register** a new user.
3.  **Log in** with your new user credentials.
4.  **Add Debts** using the provided form.
5.  **Calculate Repayment Plan** by entering a monthly payment amount and clicking the button.
6.  **Delete Account** (if desired) to remove your user and all associated debts.

## API Usage (Backend Only)

If you only want to interact with the backend API, you can use tools like `curl`, Postman, Insomnia, or directly from the FastAPI interactive documentation at `http://127.0.0.1:8000/docs`.

**Example Endpoints:**

*   `POST /register`
*   `POST /login`
*   `POST /debts`
*   `GET /debts/{user_id}`
*   `POST /calculate_repayment_plan`
*   `DELETE /users/{user_id}`
*   `POST /ask` (for RAG functionality)

## RAG Flow Overview

1.  `TOTALSL.csv` is loaded using Pandas.
2.  Rows are preprocessed into text chunks (e.g., yearly totals).
3.  Vector embeddings are generated using either OpenAI or Gemini.
4.  Vectors are stored in FAISS for efficient similarity search.
5.  For a user's question, relevant chunks are retrieved from FAISS.
6.  The retrieved chunks and the user's question are sent to the chosen LLM (OpenAI or Gemini).
7.  The generated answer is returned via the FastAPI `/ask` endpoint.
