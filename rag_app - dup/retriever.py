import os
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.schema import Document, BaseRetriever
from langchain.base_language import BaseLanguageModel
from rag_app.utils import get_embedding_model, chunk_csv_data  # Keep your existing helper if needed

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'TOTALSL.csv')
FAISS_INDEX_PATH = os.path.join(BASE_DIR, 'faiss_index')
PROMPT_FILE = os.path.join(BASE_DIR, 'prompts', 'system_prompt.txt')  # optional external prompt file

# --- System Prompt ---
DEFAULT_SYSTEM_PROMPT = """
You are a specialized financial assistant focused on loans, debt, and financial calculations. 
Your role is to provide clear, accurate, and self-contained information.
When asked a question, analyze the user's query and the retrieved context to provide a comprehensive and easy-to-understand answer.
If a user's query is ambiguous or incomplete, ask clarifying questions to get the necessary details before attempting to answer.
If the context does not contain the necessary information to answer the question, or if the question is outside the scope of finance, 
state that you cannot provide an answer and explain what information is missing or that you are limited to financial topics.
Do not make up information or provide financial advice. Do not suggest external tools or websites. 
Your goal is to be a reliable and informative resource for users within the domain of finance.
"""

def load_system_prompt(path: str = PROMPT_FILE) -> str:
    """Load system prompt from file if available, else use default."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return DEFAULT_SYSTEM_PROMPT.strip()

def create_retriever(embedding_model_name: str = "openai", rebuild: bool = False) -> BaseRetriever:
    """Create or load FAISS retriever."""
    embeddings = get_embedding_model(embedding_model_name)

    if not rebuild and os.path.exists(FAISS_INDEX_PATH):
        vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        # Use the more efficient chunking function from utils
        documents = chunk_csv_data(DATA_FILE)
        vectorstore = FAISS.from_documents(documents, embeddings)
        vectorstore.save_local(FAISS_INDEX_PATH)

    return vectorstore.as_retriever()

def get_qa_chain(llm: BaseLanguageModel, retriever: BaseRetriever):
    """Create RetrievalQA chain with a structured prompt."""
    system_prompt = load_system_prompt()
    prompt_template = system_prompt + "\n\nContext: {context}\n\nQuestion: {question}\n\nAnswer:"
    
    PROMPT = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )

    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT}
    )
