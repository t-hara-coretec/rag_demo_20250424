# RAG Demo Project Flow Chart

```mermaid
flowchart TD
    %% Main components
    User[User] --> |1. Sends query| Frontend
    Frontend[Web Interface\nchat_app.html/ts] --> |2. HTTP Request| Backend
    Backend[FastAPI Application\nchat_app.py] --> |3a. Query with/without RAG| LLM[Language Model\nOpenAI/Ollama]
    Backend --> |3b. Store messages| DB[(SQLite Database)]
    LLM --> |4. Generate response| Backend
    Backend --> |5. Stream response| Frontend
    
    %% RAG components
    subgraph RAG["RAG Service (rag_service.py)"]
        RagQuery[RAG Query Processing] --> |If RAG enabled| VectorStore
        VectorStore[Vector Store\nvector_store.py] --> |Similarity search| ChromaDB[(ChromaDB\nVector Database)]
        VectorStore --> |PDF processing| PDFProcessor[PDF Processor\npdf_processor.py]
        VectorStore --> |Web content| WebProcessor[Web Processor\nweb_processor.py]
    end
    
    %% Data sources
    PDFProcessor --> PDFs[(PDF Documents\nin datas/ folder)]
    WebProcessor --> |Fetch & cache| WebContent[Web Content]
    
    %% RAG flow
    Backend --> |If RAG enabled| RagQuery
    RagQuery --> |Return relevant context| Backend
    
    %% Legend
    classDef blue fill:#2374ab,stroke:#2374ab,color:white
    classDef green fill:#1aa555,stroke:#1aa555,color:white
    classDef orange fill:#ff7700,stroke:#ff7700,color:white
    classDef purple fill:#673ab7,stroke:#673ab7,color:white
    classDef red fill:#cc3311,stroke:#cc3311,color:white
    
    class Frontend,User blue
    class Backend orange
    class RAG,PDFProcessor,WebProcessor,VectorStore,RagQuery green
    class DB,ChromaDB,PDFs,WebContent purple
    class LLM red
```

## Component Descriptions

### Frontend Components
- **chat_app.html**: HTML template for the chat interface
- **chat_app.ts**: TypeScript code for frontend functionality

### Backend Components
- **chat_app.py**: FastAPI application that handles HTTP requests and connects to the RAG service and LLM
- **SQLite Database**: Stores chat message history

### RAG Components
- **rag_service.py**: Main RAG service that coordinates retrieval and augmentation
- **vector_store.py**: Manages the vector database interactions using ChromaDB
- **pdf_processor.py**: Processes PDF documents into text chunks for the vector store
- **web_processor.py**: Fetches and processes web content for the vector store

### Data Sources
- **PDF Documents**: PDF files stored in the `datas/` folder
- **Web Content**: External web pages that can be added to the knowledge base

### LLM
- Configurable language model (OpenAI or local model like Ollama)

## Process Flow

1. User sends a query through the web interface
2. The query is sent to the backend via HTTP
3. If RAG is enabled:
   - The query is processed by the RAG service
   - Relevant documents are retrieved from the vector store
   - The query is augmented with the retrieved context
4. The augmented query (or original if RAG disabled) is sent to the LLM
5. The LLM generates a response
6. The response is streamed back to the frontend
7. Messages are stored in the SQLite database for history