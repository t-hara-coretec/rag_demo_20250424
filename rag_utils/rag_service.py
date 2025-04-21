from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from urllib.parse import urlparse
import re
from rag_utils.vector_store import VectorStore, initialize_vector_store
from rag_utils.web_processor import WebContentProcessor

class RagService:
    def __init__(self, pdf_dir: str, collection_name: str = "documents", chroma_db_dir: str = "./chroma_db", web_cache_dir: str = "./web_cache"):
        """
        Initialize the RAG service with a vector store.
        
        Args:
            pdf_dir: Directory containing PDF files
            collection_name: Name of the ChromaDB collection
            chroma_db_dir: Directory to store the vector database
            web_cache_dir: Directory to cache web content
        """
        self.vector_store = initialize_vector_store(
            pdf_dir=pdf_dir,
            collection_name=collection_name,
            chroma_db_dir=chroma_db_dir
        )
        self.web_processor = WebContentProcessor(cache_dir=web_cache_dir)
    
    def retrieve_context(self, query: str, max_documents: int = 5, retrieve_score_thresh: float = 0.5) -> str:
        """
        Retrieve relevant context for the given query.
        
        Args:
            query: The user's query to find relevant information for
            max_documents: Maximum number of documents to include in the context
            retrieve_score_thresh: Minimum similarity score threshold for retrieved documents (0.0 to 1.0)
        
        Returns:
            String containing concatenated relevant document content
        """
        documents = self.vector_store.query(query, top_k=max_documents)
        
        # Filter documents by score threshold
        if documents and retrieve_score_thresh > 0.0:
            filtered_documents = [doc for doc in documents if doc.get('score', 0) >= retrieve_score_thresh]
            print(f"Filtered documents from {len(documents)} to {len(filtered_documents)} using score threshold {retrieve_score_thresh}")
            
            # Print scores for debugging
            for i, doc in enumerate(documents):
                score = doc.get('score', 0)
                print(f"Document {i+1} score: {score:.4f} {'(kept)' if score >= retrieve_score_thresh else '(filtered)'}")
                
            documents = filtered_documents
        
        if not documents:
            return ""
        
        # Format the retrieved context
        context_str = "\n\n---\n\nRelevant information from documents:\n\n"
        
        for i, doc in enumerate(documents):
            source = doc["metadata"].get("source", "Unknown source")
            doc_type = doc["metadata"].get("type", "document")
            title = doc["metadata"].get("title", source)
            score = doc.get("score", 0)
            
            if doc_type == "web":
                context_str += f"[Document {i+1} from web: {title} ({source}), score = {score}]\n{doc['content']}\n\n"
            else:
                context_str += f"[Document {i+1} from {source}, score = {score}]\n{doc['content']}\n\n"
        
        return context_str
    
    def answer_with_rag(self, query: str, system_prompt: Optional[str] = None, retrieve_score_thresh: float = 0.5) -> str:
        """
        Answer a query using the RAG approach.
        
        Args:
            query: The user's query
            system_prompt: Optional system prompt to guide the AI response
            retrieve_score_thresh: Minimum similarity score threshold for retrieved documents (0.0 to 1.0)
        
        Returns:
            String response from the language model with retrieved context
        """
        # Check if the query contains a URL, and if so, extract and add it to the knowledge base
        self._process_urls_in_query(query)
        
        # Retrieve relevant context
        context = self.retrieve_context(query, retrieve_score_thresh=retrieve_score_thresh)
        
        # Augment the user query with context
        augmented_query = ""
        if len(context) > 0:
            augmented_query = f"""
            以下参照情報をもとにユーザーの質問に答えてください。
            ********************************************
            {context}
            ********************************************
            """
        augmented_query += f"""
        以下がユーザーの質問です。
        ////////////////////////////////////////////
        {query}
        ////////////////////////////////////////////
        """

        print(augmented_query)
        
        return augmented_query
    
    def _process_urls_in_query(self, query: str) -> None:
        """
        Process URLs found in the query and add them to the knowledge base.
        
        Args:
            query: The user's query that might contain URLs
        """
        # Simple URL regex pattern
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[\w/\-?=%.#&]*'
        
        # Find all URLs in the query
        urls = re.findall(url_pattern, query)
        
        for url in urls:
            self.add_web_url(url)
            
    def add_web_url(self, url: str) -> bool:
        """
        Process a web URL and add its content to the vector store.
        
        Args:
            url: The URL to process and add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Processing URL: {url}")
            
            # Process URL to get chunks
            chunks = self.web_processor.process_url_to_chunks(url)
            
            # Add documents to vector store if chunks were generated
            if chunks:
                print(f"Generated {len(chunks)} chunks from URL: {url}")
                
                # Log chunk info for debugging
                for i, chunk in enumerate(chunks[:2]):  # Log first 2 chunks
                    print(f"Chunk {i} metadata: {chunk['metadata']}")
                    print(f"Chunk {i} content snippet: {chunk['content'][:100]}...")
                
                # Add to vector store
                self.vector_store.add_documents(chunks)
                
                # Verify chunks were added
                doc_count = self.vector_store.collection.count()
                print(f"Vector store now contains {doc_count} documents")
                
                return True
            else:
                print(f"No chunks generated from URL: {url}")
                return False
        except Exception as e:
            import traceback
            print(f"Error adding URL {url}: {e}")
            traceback.print_exc()
            return False