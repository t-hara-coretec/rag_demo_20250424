import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import os
import json
from pathlib import Path
import hashlib
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chardet


class WebContentProcessor:
    def __init__(self, cache_dir: str = "./web_cache"):
        """
        Initialize the web content processor with caching capability.
        
        Args:
            cache_dir: Directory to store cached web content
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def clear_cache(self):
        """
        Clear all cached web content.
        """
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                if file.endswith('.json'):
                    try:
                        os.remove(os.path.join(self.cache_dir, file))
                    except Exception as e:
                        print(f"Error removing cache file {file}: {e}")
            print(f"Cleared web cache directory: {self.cache_dir}")
        return True
    
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
                    cached_content = json.load(f)
                    print(f"Using cached content for {url}")
                    return cached_content
            except Exception as e:
                print(f"Error reading cache for {url}: {e}")
                # If there's an error reading the cache, delete the cache file
                try:
                    os.remove(cache_path)
                    print(f"Removed corrupt cache file for {url}")
                except:
                    pass
        
        # Otherwise, fetch and process the content
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': '*'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Try to detect encoding from the content
            # First check content-type header
            content_type = response.headers.get('content-type', '').lower()
            encoding = None
            
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[-1].split(';')[0].strip()
                print(f"Detected encoding from headers: {encoding}")
            
            # If no encoding in headers, use chardet to detect from content
            if not encoding:
                detected = chardet.detect(response.content)
                encoding = detected['encoding']
                confidence = detected['confidence']
                print(f"Detected encoding with chardet: {encoding} (confidence: {confidence:.2f})")
            
            # Default to utf-8 if no encoding detected
            if not encoding:
                encoding = 'utf-8'
                print(f"Using default encoding: {encoding}")
            
            # Parse HTML with explicit encoding
            content = response.content.decode(encoding, errors='replace')
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract and clean title
            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
                # Ensure title is properly encoded
                title = title.encode().decode('utf-8', errors='replace')
            else:
                title = url
            
            # Remove script and style elements
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.extract()
            
            # Get text content with better handling of line breaks and whitespace
            text_parts = []
            for element in soup.find_all(text=True):
                parent = element.parent.name.lower() if element.parent else ''
                if parent in ['script', 'style', 'meta', 'noscript', 'header', 'footer', 'nav']:
                    continue
                    
                text = element.strip()
                if text:
                    # Add appropriate spacing based on parent element
                    if parent in ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']:
                        text_parts.append(text + '\n')
                    else:
                        text_parts.append(text + ' ')
            
            # Join all parts and normalize whitespace
            raw_text = ''.join(text_parts)
            
            # Normalize whitespace (multiple spaces/newlines to single)
            import re
            text = re.sub(r'\s+', ' ', raw_text).strip()
            text = re.sub(r'\n\s*\n', '\n\n', text)  # Keep paragraph breaks
            
            # Verify text encoding is consistent
            text = text.encode().decode('utf-8', errors='replace')
            
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
            
            # Cache the result with proper encoding handling
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                    print(f"Cached content for {url}")
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