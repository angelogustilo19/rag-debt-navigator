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
You are Momentum AI, a helpful and friendly assistant.
Your goal is to provide accurate, conversational, and engaging answers to a wide range of questions.
If a question is unclear, ask for clarification.
If you don't know the answer to a question, say so honestly.
You can also assist with financial calculations and provide comprehensive, easy-to-understand explanations of the results.
"""

def load_system_prompt(path: str = PROMPT_FILE) -> str:
    """Load system prompt from file if available, else use default."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return DEFAULT_SYSTEM_PROMPT.strip()

def create_retriever(embedding_model_name: str = "openai", rebuild: bool = False) -> BaseRetriever:
    """Create an empty retriever."""
    embeddings = get_embedding_model(embedding_model_name)
    # Create an empty vectorstore
    vectorstore = FAISS.from_documents([Document(page_content="")], embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 1})

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
