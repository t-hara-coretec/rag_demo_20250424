# RAG Demo Project - Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant Frontend as Web Interface<br>(chat_app.html/ts)
    participant Backend as FastAPI Backend<br>(chat_app.py)
    participant DB as SQLite<br>Database
    participant RAG as RAG Service<br>(rag_service.py)
    participant Vector as Vector Store<br>(vector_store.py)
    participant ChromaDB as ChromaDB<br>Vector Database
    participant PDFProc as PDF Processor<br>(pdf_processor.py)
    participant WebProc as Web Processor<br>(web_processor.py)
    participant LLM as Language Model<br>(OpenAI/Ollama)
    
    %% Initial document loading (happens at startup)
    Note over PDFProc,ChromaDB: PDF documents processed at startup
    PDFProc->>ChromaDB: Load document embeddings
    
    %% Query flow
    User->>Frontend: 1. Enter query
    Frontend->>Backend: 2. Send HTTP request
    Backend->>DB: 3. Log user message
    
    alt RAG enabled
        Backend->>RAG: 4a. Process query with RAG
        RAG->>Vector: 5. Search for relevant documents
        Vector->>ChromaDB: 6. Query vector database
        ChromaDB-->>Vector: 7. Return similar documents
        Vector-->>RAG: 8. Return relevant context
        RAG-->>Backend: 9. Return augmented query
    else RAG disabled
        Note over Backend: 4b. Use original query
    end
    
    %% Web URL handling (optional flow)
    opt URL detected in query
        RAG->>WebProc: Add URL to knowledge base
        WebProc->>External: Fetch web content
        WebProc->>ChromaDB: Store as embeddings
    end
    
    Backend->>LLM: 10. Send query to model
    LLM-->>Backend: 11. Stream response
    Backend->>DB: 12. Log model response
    Backend-->>Frontend: 13. Stream response to user
    Frontend-->>User: 14. Display response
```

## Sequence Flow Description

### Initialization
- When the application starts, PDF documents in the `datas/` folder are processed and stored in the ChromaDB vector database

### User Query Processing
1. User enters a query in the chat interface
2. The frontend sends an HTTP request to the FastAPI backend
3. The backend logs the user message in the SQLite database

### RAG Processing (if enabled)
4a. If RAG is enabled, the backend sends the query to the RAG service
5. The RAG service forwards the query to the Vector Store
6. The Vector Store queries the ChromaDB vector database
7. ChromaDB returns semantically similar documents
8. The Vector Store returns the relevant documents to the RAG service
9. The RAG service augments the original query with the retrieved context

### Web URL Processing (optional)
- If a URL is detected in the query, the RAG service extracts it
- The Web Processor fetches the content from the URL
- The content is processed and stored in the ChromaDB vector database

### Response Generation
10. The backend sends the query (augmented or original) to the Language Model
11. The LLM generates a response and streams it back
12. The backend logs the model response in the SQLite database
13. The response is streamed to the frontend
14. The frontend displays the response to the user