import os
import pandas as pd
from langchain.docstore.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def get_embedding_model(model_name: str = "openai"):
    """
    Returns the embedding model instance based on the provider.

    Args:
        model_name (str): The name of the embedding model provider ('openai' or 'gemini').

    Returns:
        An instance of the embedding model.
    """
    if model_name == "gemini":
        return GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=os.environ.get("GEMINI_API_KEY"))
    elif model_name == "openai":
        # Note: Ensure OPENAI_API_KEY is set in your environment variables
        return OpenAIEmbeddings()
    else:
        raise ValueError(f"Unsupported embedding model: {model_name}")

def chunk_csv_data(file_path: str, chunk_size: int = 12) -> list[Document]:
    """
    Chunks a CSV file into documents containing a specified number of rows.
    This helps keep related data (e.g., a full year's worth of monthly data) together.

    Args:
        file_path (str): The path to the CSV file.
        chunk_size (int): The number of rows to include in each chunk.

    Returns:
        list[Document]: A list of Document objects, where each document
                        contains a formatted string of the chunked data.
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return []

    documents = []
    # Create chunks by iterating through the DataFrame in steps of chunk_size
    for i in range(0, len(df), chunk_size):
        chunk_df = df.iloc[i:i + chunk_size]
        # Convert the chunk DataFrame to a string, including the headers for context
        content = f"Financial data from a CSV:\n{chunk_df.to_string(index=False)}"
        doc = Document(
            page_content=content,
            metadata={"source": file_path, "chunk_start_row": i}
        )
        documents.append(doc)

    return documents
