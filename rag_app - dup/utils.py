import os
from dotenv import load_dotenv
import pandas as pd
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.docstore.document import Document

load_dotenv()

def get_embedding_model(model_name: str = "openai"):
    model_name = model_name.lower()
    api_keys = {
        "openai": ("OPENAI_API_KEY", lambda key: OpenAIEmbeddings(openai_api_key=key)),
        "gemini": ("GEMINI_API_KEY", lambda key: GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=key))
    }
    if model_name not in api_keys:
        raise ValueError("Unsupported embedding model. Choose 'openai' or 'gemini'.")
    env_var, model_constructor = api_keys[model_name]
    api_key = os.getenv(env_var)
    if not api_key:
        raise EnvironmentError(f"{env_var} not found in environment variables.")
    return model_constructor(api_key)

def chunk_csv_data(file_path: str) -> list[Document]:
    try:
        df = pd.read_csv(file_path, usecols=["observation_date", "TOTALSL"])
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    except ValueError as e:
        raise ValueError(f"Missing required columns in CSV: {e}")
    return [
        Document(
            page_content=f"observation_date: {row.observation_date}, Total Student Loan Debt: {row.TOTALSL} Trillion USD",
            metadata={"source": file_path, "row": idx}
        )
        for idx, row in df.iterrows()
    ]