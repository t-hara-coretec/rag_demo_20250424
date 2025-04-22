# RAG Demo Project - ASCII Flow Chart

```
+---------------------------+
|         User Query        |
+---------------------------+
             |
             v
+---------------------------+
|      Web Interface        |
|  (chat_app.html/ts)       |
+---------------------------+
             |
             v
+---------------------------+
|    FastAPI Application    |
|     (chat_app.py)         |
+---------------------------+
     /        |       \
    /         |        \
   v          v         v
+-------+ +----------+ +----------+
|SQLite | | RAG      | |  LLM     |
|DB     | | Service  | |(OpenAI/  |
|       | |          | | Ollama)  |
+-------+ +----------+ +----------+
              /     \
             /       \
            v         v
    +------------+ +------------+
    |Vector Store| |Web         |
    |            | |Processor   |
    +------------+ +------------+
       /      \
      /        \
     v          v
+--------+  +------------+
|PDF     |  |ChromaDB    |
|Processor|  |Vector DB   |
+--------+  +------------+
     |
     v
+------------+
|PDF Documents|
+------------+
```

## Flow Description

1. User submits a query through the chat interface
2. The web interface sends the query to the FastAPI backend
3. The backend processes the request in several ways:
   - Stores messages in SQLite database
   - If RAG is enabled, processes the query through the RAG service
   - Sends the query (with or without context) to the LLM
4. The RAG service:
   - Uses the vector store to find relevant documents
   - Can process PDFs from the data folder
   - Can fetch and process web content
   - Stores embeddings in ChromaDB
5. The response from the LLM is streamed back to the user