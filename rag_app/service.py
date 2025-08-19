import os
import math
import json
import re
import bcrypt
import mysql.connector
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama

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

# --- LLM Fallback System ---
def create_llm_with_fallback():
    """Create LLM with multiple fallback options when hitting rate limits"""
    
    # Primary LLM (Gemini)
    primary_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=os.getenv("GEMINI_API_KEY")
    )
    
    # Secondary LLM (OpenAI) - Only if key exists
    secondary_llm = None
    if os.getenv("OPENAI_API_KEY"):
        try:
            secondary_llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.7
            )
            print(" OpenAI LLM initialized successfully")
        except Exception as e:
            print(f" Failed to initialize OpenAI: {e}")
            secondary_llm = None
    else:
        print(" OpenAI API key not found - OpenAI LLM will be skipped")
    
    # Tertiary LLM (Ollama - Local)
    tertiary_llm = None
    try:
        tertiary_llm = Ollama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        print(f" Ollama LLM initialized: {os.getenv('OLLAMA_MODEL', 'llama3.1:8b')}")
    except Exception as e:
        print(f" Failed to initialize Ollama: {e}")
        print(" Make sure Ollama is running: 'ollama serve'")
        tertiary_llm = None
    
    return primary_llm, secondary_llm, tertiary_llm

def safe_llm_invoke(prompt, primary_llm, secondary_llm, tertiary_llm, max_retries=2):
    """Try LLMs in order: Gemini -> OpenAI -> Ollama (local)"""
    
    # Create list of available LLMs (skip None values)
    llms = []
    if primary_llm:
        llms.append(("Gemini", primary_llm))
    if secondary_llm:
        llms.append(("OpenAI", secondary_llm))
    if tertiary_llm:
        llms.append(("Ollama", tertiary_llm))
    
    if not llms:
        raise Exception("No LLMs available! Check your configuration.")
    
    for llm_name, llm in llms:
        for attempt in range(max_retries):
            try:
                print(f" Trying {llm_name} (attempt {attempt + 1})...")
                result = llm.invoke(prompt)
                print(f" Success with {llm_name}")
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                print(f" {llm_name} failed: {e}")
                
                # Check if it's a rate limit or quota error
                is_rate_limit = any(keyword in error_msg for keyword in [
                    'rate limit', 'quota', 'limit exceeded', '429', 
                    'too many requests', 'usage limit'
                ])
                
                # For API errors, try next LLM immediately
                if is_rate_limit or llm_name in ["Gemini", "OpenAI"]:
                    print(f"Moving to next LLM due to rate limit or API error...")
                    break
                
                # For local Ollama errors, retry with backoff
                if llm_name == "Ollama" and attempt < max_retries - 1:
                    print(f"Retrying {llm_name} in {2 ** attempt} seconds...")
                    time.sleep(2 ** attempt)
                    continue
                
                # If it's the last attempt on the last LLM, raise the error
                if llm_name == llms[-1][0] and attempt == max_retries - 1:
                    raise Exception(f"All available LLMs failed. Last error from {llm_name}: {e}")
    
    raise Exception("Unexpected error in LLM fallback system")

# --- Initialize LLM & Retriever ---
retriever = create_retriever(embedding_model_name="gemini")
primary_llm, secondary_llm, tertiary_llm = create_llm_with_fallback()
qa_chain = get_qa_chain(llm=primary_llm, retriever=retriever)

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
    # Stage 1: Try to treat as a financial calculation question
    extraction_prompt = f'''
    Analyze the user's question to extract financial parameters: principal (total loan amount), 
    annual_interest_rate (as a percentage), and monthly_payment.
    Your response MUST be a single, valid JSON object with the keys "principal", "interest_rate", and "monthly_payment".
    If a value is not found, it MUST be null. Do not include any text outside the JSON object.
    User Question: "{q.question}"
    '''

    try:
        # Use the fallback system here
        extraction_result = safe_llm_invoke(extraction_prompt, primary_llm, secondary_llm, tertiary_llm)
        extraction_result_str = extraction_result.content
        
        json_match = re.search(r"\{.*?\}", extraction_result_str, re.DOTALL)
        
        if json_match:
            params = json.loads(json_match.group(0))
            principal = params.get("principal")
            interest_rate = params.get("interest_rate")
            monthly_payment = params.get("monthly_payment")

            # If we have all parameters, perform the calculation
            if all(isinstance(i, (int, float)) for i in [principal, interest_rate, monthly_payment]):
                
                # Use the accurate calculator
                result = calculate_debt_payoff(principal, interest_rate, monthly_payment)
                total_interest_paid = result.total_paid - principal

                # Stage 2: Create a comprehensive, conversational response
                comprehensive_prompt = f"""You are a helpful and friendly financial assistant.
A user asked the following question: '{q.question}'

Based on their numbers, I have performed the following calculation:
- Time to Pay Off: {result.years} years and {result.months} months
- Total Amount Paid: ${result.total_paid:,.2f}
- Total Interest Paid: ${total_interest_paid:,.2f}

Now, please present this information back to the user in a comprehensive, conversational, and easy-to-understand way.
Be encouraging and offer one or two general tips for paying off debt faster (like making extra payments or looking for a lower interest rate).
Explain what the numbers mean in a clear and helpful manner.
"""
                final_result = safe_llm_invoke(comprehensive_prompt, primary_llm, secondary_llm, tertiary_llm)
                return {"answer": final_result.content}

    except (json.JSONDecodeError, InsufficientPaymentError) as e:
        # If extraction or calculation fails, fall back to general conversation
        pass
    except Exception as e:
        # Log other unexpected errors if needed
        pass

    # Fallback to general conversation if financial extraction/calculation fails
    general_prompt = f"""You are Momentum AI, a helpful and friendly assistant.
Your goal is to provide accurate, conversational, and engaging answers to a wide range of questions.
If a question is unclear, ask for clarification.
If you don't know the answer to a question, say so honestly.
If it is helpful, you are encouraged to suggest reputable websites where the user can find more information.

Question: {q.question}
Answer:"""
    
    # Use fallback system for general conversation too
    result = safe_llm_invoke(general_prompt, primary_llm, secondary_llm, tertiary_llm)
    return {"answer": result.content}


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

# --- Health Check Endpoints ---
@app.get("/llm_status")
async def check_llm_status():
    """Check which LLMs are available"""
    status = {}
    test_prompt = "Hello"
    
    # Check each LLM if it exists
    llm_configs = [
        ("Gemini", primary_llm),
        ("OpenAI", secondary_llm), 
        ("Ollama", tertiary_llm)
    ]
    
    for name, llm in llm_configs:
        if llm is None:
            status[name] = "Not configured"
            continue
            
        try:
            llm.invoke(test_prompt)
            status[name] = " Available"
        except Exception as e:
            status[name] = f" Unavailable: {str(e)[:50]}..."
    
    return status

@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "message": "Momentum AI is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)