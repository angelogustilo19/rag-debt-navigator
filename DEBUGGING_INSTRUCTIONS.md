# FastAPI Server Debugging Guide

Follow these steps to identify and fix the problem with your backend server.

### Step 1: Check the Terminal for Errors

1.  Go to the terminal window where you ran the command `uvicorn rag_app.service:app --reload`.
2.  Look carefully for any lines that contain `Error`, `Exception`, or `Traceback`. This is the most important step, as the error message will tell you exactly what is wrong.

### Step 2: Make Sure Your Virtual Environment is Active

The application requires specific Python packages that are installed in your virtual environment. Make sure it's active before running the server.

1.  Open your terminal.
2.  Navigate to your project folder:
    ```bash
    cd C:\Users\angel\rag-debt-navigator
    ```
3.  Run the activation script:
    ```bash
    .\venv\Scripts\activate
    ```
4.  You should see `(venv)` at the beginning of your command prompt.

### Step 3: Verify Your Environment Variables (`.env` file)

The application needs an API key to connect to the AI service. This is stored in a `.env` file.

1.  In your project directory `C:\Users\angel\rag-debt-navigator`, make sure you have a file named `.env`.
2.  Open the `.env` file with a text editor.
3.  Confirm that it contains the following line, with your actual API key pasted in:
    ```
    GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```
4.  If the file is missing or the key is incorrect, the application will fail to start.

### Step 4: Re-install Dependencies

Sometimes, package installations can get corrupted. It's good practice to reinstall them.

1.  Make sure your virtual environment is active (see Step 2).
2.  Run the following command to reinstall all required packages:
    ```bash
    pip install -r requirements.txt
    ```

### Step 5: Try Running the Server Again

Once you have completed the steps above, try to start the server again.

1.  Make sure you are in the correct directory and your virtual environment is active.
2.  Run the command:
    ```bash
    uvicorn rag_app.service:app --reload
    ```

If it starts successfully, you will see lines indicating that the server is running, like:
`Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)`
