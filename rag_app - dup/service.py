import os
import math
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
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
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
    # Expanded set of keywords to better detect finance-related questions
    finance_keywords = {
        "loan", "interest", "payment", "debt", "finance", "money", "credit", 
        "budget", "financial", "invest", "market", "stock", "tax", "mortgage",
        "student loan", "total sl", "csv data", "loan data"
    }

    question_text = q.question.lower()
    
    # If the question seems finance-related, use the specialized RAG chain
    if any(keyword in question_text for keyword in finance_keywords):
        try:
            # Using .invoke() which is the recommended way over .run()
            result = qa_chain.invoke(q.question)
            return {"answer": result.get("result", "No specific answer found in the provided documents.")}
        except Exception as e:
            # Log the error for debugging
            print(f"Error during RAG chain execution: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while processing your question.")
    
    # For non-financial questions, provide a clear and helpful response
    return {
        "answer": "I am a specialized financial assistant. My knowledge is focused on topics like loans, debt, and financial calculations based on the provided data. Please ask me a finance-related question."
    }

@app.post("/calculate_payoff_time")
async def calculate_payoff_time(req: DebtCalculationRequest):
    try:
        loan_amount = req.debt_amount
        monthly_interest_rate = req.interest_rate / 100 / 12
        monthly_payment = req.monthly_payment

        if monthly_payment <= 0:
            return {"answer": "The monthly payment must be a positive amount."}

        if monthly_interest_rate <= 0:
            total_months = math.ceil(loan_amount / monthly_payment)
            years, months_rem = divmod(total_months, 12)
            return {
                "answer": f"With no interest, it will take {years} years and {months_rem} months to pay off this debt. "
                          f"You will pay a total of ${loan_amount:,.2f}, which includes $0.00 in interest."
            }

        monthly_interest_accrued = loan_amount * monthly_interest_rate
        if monthly_payment <= monthly_interest_accrued:
            suggested = round(monthly_interest_accrued, 2) + 1
            return {"answer": f"Your payment is too low. You need at least ${suggested:,.2f} to reduce the principal."}

        numerator = -math.log(1 - (monthly_interest_rate * loan_amount) / monthly_payment)
        denominator = math.log(1 + monthly_interest_rate)
        total_months = math.ceil(numerator / denominator)

        if total_months > 1200: # 100 years
            return {"answer": "With that payment, this loan will take over 100 years to pay off."} # Or raise an error

        years, months_rem = divmod(total_months, 12)
        total_paid = monthly_payment * total_months
        total_interest_paid = total_paid - loan_amount

        return {
            "answer": f"It will take approximately {years} years and {months_rem} months to pay off this debt. "
                          f"You will pay a total of ${total_paid:,.2f}, which includes ${total_interest_paid:,.2f} in interest."
            }

    except ValueError: # This can happen if the log argument is negative or zero
        return {"answer": "The monthly payment is too low to cover the interest. The debt will never be paid off with this payment amount."}
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
