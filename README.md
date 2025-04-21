# Chat App with RAG Support

This is a simple chat application with Retrieval-Augmented Generation (RAG) capabilities. The application can retrieve information from PDF documents to enhance the responses provided by the AI model.

## Features

- Interactive chat interface
- RAG functionality with PDF document support
- Toggle for enabling/disabling RAG
- Support for different AI models (using pydantic-ai)

## Setup

1. Install the required packages:

```bash
pip install -r rag_requirements.txt
```

2. Place your PDF documents in the `datas` folder.

3. Run the application:

```bash
python chat_app.py
```

4. Access the application at `http://localhost:8000`

## RAG Implementation

The RAG implementation has three main components:

1. **PDF Processing** - Extracts text from PDFs and splits it into chunks.
2. **Vector Store** - Creates and maintains a vector database for document retrieval using ChromaDB.
3. **RAG Service** - Integrates the vector store with the chat functionality.

When RAG is enabled, the user's query is used to retrieve relevant document chunks which are then provided to the AI model along with the original query, allowing the model to generate more informed responses.

## Customization

- To change the model, update the `agent` initialization in `chat_app.py`
- To configure RAG, adjust parameters in the `rag_utils/rag_service.py` file

## File Structure

- `chat_app.py` - Main application file
- `chat_app.html` - Frontend HTML template
- `chat_app.ts` - Frontend TypeScript code
- `rag_utils/` - RAG implementation modules
  - `pdf_processor.py` - PDF text extraction and chunking
  - `vector_store.py` - ChromaDB vector database implementation
  - `rag_service.py` - RAG service integration with chat
- `datas/` - Directory containing PDF documents
- `chroma_db/` - Directory for storing the vector database