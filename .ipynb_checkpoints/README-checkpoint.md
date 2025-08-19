# Momentum AI - A Conversational AI Assistant

Momentum AI is a sophisticated, conversational AI assistant built with FastAPI and React. It leverages Google's Gemini models to provide intelligent answers to a wide range of questions, while also offering precise financial calculation tools.

## Core Features

*   **Conversational Interface:** Engage in natural, human-like conversations on almost any topic.
*   **Intelligent Financial Calculations:** Ask complex financial questions in plain English. The app automatically detects your intent, performs accurate calculations, and provides comprehensive, easy-to-understand explanations.
*   **Helpful Resources:** Get suggestions for reputable websites to learn more about the topics you're interested in.
*   **User Authentication:** Secure user registration and login functionality.

## How It Works

Momentum AI uses a powerful hybrid approach to answer your questions:

1.  **Intent Detection:** When you ask a question, the backend first determines if your query is a financial calculation or a general knowledge question.
2.  **Financial Path:** For financial questions, it extracts the key parameters (like loan amounts, interest rates, etc.), calculates the answer with a high-precision Python script, and then uses the Gemini LLM to explain the results in a comprehensive, conversational way.
3.  **General Knowledge Path:** For all other questions, it directly queries the Gemini LLM to provide an answer based on its vast, pre-trained knowledge.

This method ensures you get the best of both worlds: the mathematical accuracy of dedicated code and the conversational power of a leading large language model.

## Application Setup and Running

To run the full Momentum AI application (both backend and frontend), follow these steps:

### 1. Backend Setup

1.  **Navigate to the project root directory.**
2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set your GEMINI_API_KEY environment variable.**
    *   **For PowerShell:**
        ```powershell
        $env:GEMINI_API_KEY="your_gemini_api_key_here"
        ```
    *   **For Command Prompt (CMD):**
        ```cmd
        set GEMINI_API_KEY=your_gemini_api_key_here
        ```
4.  **Run the FastAPI application:**
    ```bash
    uvicorn rag_app.service:app --reload
    ```
    The backend will be accessible at `http://127.0.0.1:8000`.

### 2. Frontend Setup

1.  **Open a new terminal window.**
2.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```
3.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```
4.  **Run the React development server:**
    ```bash
    npm start
    ```
    This will open your browser to `http://localhost:3000`.

## API Endpoints

The backend provides several RESTful API endpoints for interacting with the application.

### Authentication

#### `POST /register`

*   **Description:** Registers a new user.
*   **Request Body:**
    ```json
    {
        "username": "your_username",
        "password": "your_password"
    }
    ```
*   **Response:**
    ```json
    {
        "message": "User registered successfully"
    }
    ```

#### `POST /login`

*   **Description:** Logs in an existing user.
*   **Request Body:**
    ```json
    {
        "username": "your_username",
        "password": "your_password"
    }
    ```
*   **Response:**
    ```json
    {
        "message": "Login successful",
        "user_id": 1
    }
    ```

### Debt Management

#### `POST /debts`

*   **Description:** Creates a new debt entry for a user.
*   **Request Body:**
    ```json
    {
        "user_id": 1,
        "name": "Credit Card",
        "amount": 5000,
        "interest_rate": 18.0
    }
    ```
*   **Response:** The created debt object.

#### `GET /debts/{user_id}`

*   **Description:** Retrieves all debts for a specific user.
*   **Response:** A list of debt objects.

### Financial Calculations

#### `POST /ask`

*   **Description:** A multi-purpose endpoint that can answer general knowledge questions or perform financial calculations based on natural language input.
*   **Request Body:**
    ```json
    {
        "question": "How long will it take to pay off a $5000 loan with an 18% interest rate if I pay $150 a month?"
    }
    ```
*   **Response:** A conversational answer with the calculation results.

#### `POST /calculate_repayment_plan`

*   **Description:** Calculates a repayment plan for a specific debt.
*   **Request Body:**
    ```json
    {
        "debt_id": 1,
        "monthly_payment": 150
    }
    ```
*   **Response:**
    ```json
    {
        "years": 3,
        "months": 10,
        "total_paid": 6968.34
    }
    ```

#### `POST /calculate_payoff_time`

*   **Description:** Calculates the time it will take to pay off a debt.
*   **Request Body:**
    ```json
    {
        "debt_amount": 5000,
        "interest_rate": 18.0,
        "monthly_payment": 150
    }
    ```
*   **Response:** A string describing the payoff time and total interest.

#### `POST /calculate_monthly_payment`

*   **Description:** Calculates the required monthly payment to pay off a debt in a given number of months.
*   **Request Body:**
    ```json
    {
        "debt_amount": 5000,
        "interest_rate": 18.0,
        "months": 48
    }
    ```
*   **Response:** A string describing the required monthly payment.

### User Management

#### `DELETE /users/{user_id}`

*   **Description:** Deletes a user and all their associated debts.
*   **Response:**
    ```json
    {
        "message": "User and associated debts deleted successfully."
    }
    ```

### System

#### `GET /health`

*   **Description:** A basic health check endpoint.
*   **Response:**
    ```json
    {
        "status": "healthy",
        "message": "Momentum AI is running"
    }
    ```

#### `GET /llm_status`

*   **Description:** Checks the status of the available Large Language Models (LLMs).
*   **Response:**
    ```json
    {
        "Gemini": " Available",
        "OpenAI": " Not configured",
        "Ollama": " Available"
    }
    ```
