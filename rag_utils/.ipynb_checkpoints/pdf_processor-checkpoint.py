import os
from typing import List, Dict, Any
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text() + "\n"
    return text


def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """Split text into chunks for processing."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    chunks = text_splitter.split_text(text)
    return chunks


def process_pdf_documents(pdf_dir: str) -> List[Dict[str, Any]]:
    """Process all PDF documents in a directory."""
    documents = []
    for filename in os.listdir(pdf_dir):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(pdf_dir, filename)
            try:
                # Extract text from PDF
                text = extract_text_from_pdf(pdf_path)
                
                # Split text into chunks
                chunks = split_text(text)
                
                # Create document entries for each chunk
                for i, chunk in enumerate(chunks):
                    doc = {
                        "content": chunk,
                        "metadata": {
                            "source": filename,
                            "chunk": i,
                            "path": pdf_path
                        }
                    }
                    documents.append(doc)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    return documents