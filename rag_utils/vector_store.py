from typing import List, Dict, Any, Optional
import os
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from rag_utils.pdf_processor import process_pdf_documents


class VectorStore:
    def __init__(self, collection_name: str = "pdf_documents", data_dir: str = "./chroma_db"):
        """
        Initialize the vector store with ChromaDB.
        
        Args:
            collection_name: Name of the collection to store documents
            data_dir: Directory to store the ChromaDB persistence data
        """
        # Create directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(path=data_dir)
        
        # Use the OpenAI embedding function (we could replace this with a local model)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # Try to get the collection or create a new one
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"Using existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"Created new collection: {collection_name} with cosine similarity")

    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document dictionaries with 'content' and 'metadata'
        """
        if not documents:
            return
        
        # Get current count to ensure IDs are unique
        try:
            # Use the current timestamp plus a counter to ensure uniqueness
            import time
            timestamp = int(time.time())
            
            # Extract components for ChromaDB with unique IDs
            ids = [f"doc_{timestamp}_{i}" for i in range(len(documents))]
            texts = [doc["content"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            print(f"Added {len(documents)} documents to vector store with IDs starting with doc_{timestamp}_0")
        except Exception as e:
            print(f"Error adding documents: {e}")
            import traceback
            traceback.print_exc()
    
    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the vector store for relevant documents.
        
        Args:
            query_text: The query text to find relevant documents for
            top_k: Number of top results to return
        
        Returns:
            List of document dictionaries with content, metadata, and relevance scores
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # Convert results to a list of document dictionaries
        documents = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                # Calculate a score from distance (1.0 is perfect match, 0.0 is poor match)
                # For cosine similarity, the distance is 1 - cosine_similarity
                # So the score is just 1 - distance, which equals cosine_similarity
                distance = results["distances"][0][i] if "distances" in results and results["distances"] else 1.0
                
                # Convert distance to score (1.0 is perfect match, 0.0 is poor match)
                # For cosine, we can use 1-distance directly since distance = 1-cosine_similarity
                score = max(0.0, min(1.0, distance))
                
                documents.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": score
                })
        
        return documents


def initialize_vector_store(pdf_dir: str, collection_name: str = "pdf_documents", chroma_db_dir: str = "./chroma_db") -> VectorStore:
    """
    Initialize and populate the vector store with documents from the PDF directory.
    
    Args:
        pdf_dir: Directory containing PDF files
        collection_name: Name for the ChromaDB collection
        chroma_db_dir: Directory to store ChromaDB files
    
    Returns:
        Initialized VectorStore instance
    """
    # Initialize vector store
    vector_store = VectorStore(collection_name=collection_name, data_dir=chroma_db_dir)
    
    # Process PDF documents
    documents = process_pdf_documents(pdf_dir)
    
    # Add documents to vector store
    if documents:
        vector_store.add_documents(documents)
        print(f"Initialized vector store with {len(documents)} document chunks from {pdf_dir}")
    else:
        print(f"No documents found in {pdf_dir}")
    
    return vector_store