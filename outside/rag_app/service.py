import os
import math
import json
import re
import bcrypt
import mysql.connector
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI

from rag_app.retriever import create_retriever, get_qa_chain
from rag_app.database import create_tables, get_db
from rag_app.debt_calculator import calculate_debt_payoff, calculate_monthly_payment, InsufficientPaymentError, PayoffResult

# Load env vars
load_dotenv()

# Create DB tables on startup
create_tables()

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Initialize LLM & Retriever ---
retriever = create_retriever(embedding_model_name="gemini")
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
qa_chain = get_qa_chain(llm=llm, retriever=retriever)

# --- Pydantic Models ---
class User(BaseModel):
    username: str
    password: str

class Debt(BaseModel):
    user_id: int
    name: str
    amount: float
    interest_rate: float

class Question(BaseModel):
    question: str

class RepaymentPlanRequest(BaseModel):
    debt_id: int
    monthly_payment: float

class DebtCalculationRequest(BaseModel):
    debt_amount: float
    interest_rate: float
    monthly_payment: float

class PaymentCalculationRequest(BaseModel):
    debt_amount: float
    interest_rate: float
    months: int

# --- Routes ---
@app.post("/register")
async def register(user: User, conn=Depends(get_db)):
    hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (user.username, hashed_password)
            )
        conn.commit()
        return {"message": "User registered successfully"}
    except mysql.connector.Error as err:
        if err.errno == 1062: # Duplicate entry
            raise HTTPException(status_code=400, detail="Username already exists")
        raise HTTPException(status_code=500, detail="Database error")


@app.post("/login")
async def login(user: User, conn=Depends(get_db)):
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
        db_user = cursor.fetchone()
    
    if not db_user or not bcrypt.checkpw(user.password.encode(), db_user['password'].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"message": "Login successful", "user_id": db_user['id']}

@app.post("/debts")
async def create_debt(debt: Debt, conn=Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO debts (user_id, name, amount, interest_rate) VALUES (%s, %s, %s, %s)",
            (debt.user_id, debt.name, debt.amount, debt.interest_rate)
        )
    conn.commit()
    return debt

@app.get("/debts/{user_id}")
async def get_debts(user_id: int, conn=Depends(get_db)):
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM debts WHERE user_id = %s", (user_id,))
        result = cursor.fetchall()
    return result

@app.post("/calculate_repayment_plan", response_model=PayoffResult)
async def calculate_repayment_plan(request: RepaymentPlanRequest, conn=Depends(get_db)):
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT amount, interest_rate FROM debts WHERE id = %s", (request.debt_id,))
        debt = cursor.fetchone()

    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found.")
    
    try:
        return calculate_debt_payoff(debt['amount'], debt['interest_rate'], request.monthly_payment)
    except InsufficientPaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/users/{user_id}")
async def delete_user(user_id: int, conn=Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM debts WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found.")
    conn.commit()
    return {"message": "User and associated debts deleted successfully."}

@app.post("/ask")
async def ask_question(q: Question):
    # Attempt to treat the question as a request for calculation
    extraction_prompt = '''
    Analyze the user's question to extract the following financial parameters: principal (total loan amount), annual_interest_rate (as a percentage), and monthly_payment.
    Your response MUST be a single, valid JSON object with the keys "principal", "interest_rate", and "monthly_payment".
    If a value cannot be found for any of these keys, its value MUST be null.
    Do not include any explanatory text, markdown formatting, or anything else outside of the JSON object.

    Examples:
    - User Question: "i have 23980 debt with 13% interest rate, i will pay 3500 a month, how long will it take to pay it off"
    - Your Response: {{\"principal\": 23980, \"interest_rate\": 13, \"monthly_payment\": 3500}}

    - User Question: "My total outstanding educational debt is a staggering $785,900. The weighted average annual interest rate on this colossal sum is 6.875%. If I am absolutely committed to making a consistent monthly payment of $4,500, what is the repayment duration and total cost?"
    - Your Response: {{\"principal\": 785900, \"interest_rate\": 6.875, \"monthly_payment\": 4500}}

    - User Question: "What are the current student loan interest rates?"
    - Your Response: {{\"principal\": null, \"interest_rate\": null, \"monthly_payment\": null}}

    - User Question: "Given a debt amount of $23,980 with an annual interest rate of 13%, and a fixed monthly payment of $3,500, how long will it take to fully repay the loan?"
    - Your Response: {{\"principal\": 23980, \"interest_rate\": 13, \"monthly_payment\": 3500}}

    Now, process the following question.
    User Question: "{question}"
    Your Response:
    '''.format(question=q.question)
    
    try:
        extraction_result_str = llm.invoke(extraction_prompt).content
        print(f"LLM extraction result: {extraction_result_str}")

        # Use regex to find the JSON block, handling optional markdown
        json_match = re.search(r"```json\s*(\{.*?\})\s*```|(\{.*?\})", extraction_result_str, re.DOTALL)
        
        json_str = None
        if json_match:
            # Extract the JSON string from the first non-empty group
            json_str = next((g for g in json_match.groups() if g is not None), None)
        
        if json_str:
            params = json.loads(json_str)
            principal = params.get("principal")
            interest_rate = params.get("interest_rate")
            monthly_payment = params.get("monthly_payment")

            # Check if all required parameters for calculation are present and are numbers
            if isinstance(principal, (int, float)) and \
               isinstance(interest_rate, (int, float)) and \
               isinstance(monthly_payment, (int, float)):
                
                # Sanity check for interest rate: if it's between 0 and 1, assume it's a decimal
                if 0 < interest_rate < 1:
                    interest_rate *= 100

                try:
                    if not (0 <= interest_rate < 100):
                        return {"answer": f"The extracted interest rate ({interest_rate}) is not a valid percentage between 0 and 100."}

                    result = calculate_debt_payoff(principal, interest_rate, monthly_payment)
                    total_interest_paid = result.total_paid - principal
                    
                    return {
                        "answer": f"It will take approximately {result.years} years and {result.months} months to pay off this debt. "
                                  f"You will pay a total of ${result.total_paid:,.2f}, which includes ${total_interest_paid:,.2f} in interest."
                    }

                except InsufficientPaymentError:
                    monthly_interest_accrued = principal * (interest_rate / 100 / 12)
                    suggested = round(monthly_interest_accrued, 2) + 1
                    return {"answer": f"Your monthly payment of ${monthly_payment:,.2f} is too low to cover the interest. "
                                      f"You need to pay at least ${suggested:,.2f} per month to start reducing the principal."}
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        print(f"Could not extract calculation parameters, falling back to RAG. Error: {e}")
        # Fallback to RAG if extraction or parsing fails
        pass

    # Fallback to the original RAG logic for informational questions
    finance_keywords = {
        "loan", "interest", "payment", "debt", "finance", "money", "credit", 
        "budget", "financial", "invest", "market", "stock", "tax", "mortgage",
        "student loan", "total sl", "csv data", "loan data"
    }

    question_text = q.question.lower()
    
    if any(keyword in question_text for keyword in finance_keywords):
        try:
            result = qa_chain.invoke(q.question)
            return {"answer": result.get("result", "No specific answer found in the provided documents.")}
        except Exception as e:
            print(f"Error during RAG chain execution: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while processing your question.")
    
    return {
        "answer": "I am a specialized financial assistant. My knowledge is focused on topics like loans, debt, and financial calculations based on the provided data. Please ask me a finance-related question."
    }

@app.post("/calculate_payoff_time")
async def calculate_payoff_time(req: DebtCalculationRequest):
    try:
        if not (0 <= req.interest_rate < 100):
            return {"answer": "Interest rate must be a percentage between 0 and 100."}

        result = calculate_debt_payoff(req.debt_amount, req.interest_rate, req.monthly_payment)
        
        total_interest_paid = result.total_paid - req.debt_amount
        
        return {
            "answer": f"It will take approximately {result.years} years and {result.months} months to pay off this debt. "
                      f"You will pay a total of ${result.total_paid:,.2f}, which includes ${total_interest_paid:,.2f} in interest."
        }

    except InsufficientPaymentError:
        monthly_interest_accrued = req.debt_amount * (req.interest_rate / 100 / 12)
        suggested = round(monthly_interest_accrued, 2) + 1
        return {"answer": f"Your payment is too low. You need at least ${suggested:,.2f} to reduce the principal."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {e}")

@app.post("/calculate_monthly_payment")
async def get_monthly_payment(req: PaymentCalculationRequest):
    try:
        payment = calculate_monthly_payment(req.debt_amount, req.interest_rate, req.months)
        if payment == float('inf'):
            return {"answer": "The number of months must be greater than zero."}
        return {"answer": f"You would need to pay approximately ${payment:.2f} per month to pay off the debt in {req.months} months."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)