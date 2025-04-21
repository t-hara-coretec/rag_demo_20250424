import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import os
import json
from pathlib import Path
import hashlib
from langchain_text_splitters import RecursiveCharacterTextSplitter


class WebContentProcessor:
    def __init__(self, cache_dir: str = "./web_cache"):
        """
        Initialize the web content processor with caching capability.
        
        Args:
            cache_dir: Directory to store cached web content
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def extract_content_from_url(self, url: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Extract content from a web URL with optional caching.
        
        Args:
            url: The URL to extract content from
            use_cache: Whether to use cached content if available
            
        Returns:
            Dictionary with extracted content and metadata
        """
        # Create a hash of the URL for cache filename
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"{url_hash}.json")
        
        # Return cached content if available and requested
        if use_cache and os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading cache for {url}: {e}")
        
        # Otherwise, fetch and process the content
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = soup.title.string if soup.title else url
            
            # Remove script and style elements
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.extract()
            
            # Get text content
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up text (remove excessive whitespace)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Create result dictionary
            result = {
                "content": text,
                "metadata": {
                    "source": url,
                    "title": title,
                    "domain": urlparse(url).netloc,
                    "type": "web"
                }
            }
            
            # Cache the result
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False)
            except Exception as e:
                print(f"Error caching content for {url}: {e}")
            
            return result
            
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            return {
                "content": f"Error fetching content from {url}: {str(e)}",
                "metadata": {
                    "source": url,
                    "error": str(e),
                    "type": "web"
                }
            }
    
    def process_url_to_chunks(self, url: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Process a URL and split the content into chunks for vector storage.
        
        Args:
            url: The URL to process
            chunk_size: Size of each text chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of document dictionaries with content and metadata
        """
        # Extract content
        result = self.extract_content_from_url(url)
        
        # Check if we got an error
        if "error" in result["metadata"]:
            # Return single document with error message
            return [result]
        
        # Split content into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        
        chunks = text_splitter.split_text(result["content"])
        
        # Create document chunks
        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                "content": chunk,
                "metadata": {
                    **result["metadata"],
                    "chunk": i
                }
            }
            documents.append(doc)
        
        return documents