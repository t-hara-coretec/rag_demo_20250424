from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.programming.framework import FastAPI
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.queue import Kafka
from diagrams.aws.storage import S3
from diagrams.custom import Custom
from diagrams.generic.compute import Rack
from diagrams.onprem.compute import Server
from diagrams.generic.network import Firewall
from diagrams.generic.storage import Storage
from diagrams.generic.database import SQL
from diagrams.programming.language import Javascript
from diagrams.programming.language import TypeScript

# We can't use Custom icons as they require image files, so let's use alternatives
with Diagram("RAG Demo Application Architecture", show=False, filename="rag_demo_flowchart"):
    
    # Frontend components
    with Cluster("Frontend"):
        html = Javascript("chat_app.html")
        typescript = TypeScript("chat_app.ts")
    
    # Backend components
    with Cluster("Backend"):
        # Main application
        fastapi_app = FastAPI("chat_app.py")
        
        # Database
        sqlite = SQL("SQLite\nMessage Storage")
        
        # RAG Service components
        with Cluster("RAG Components"):
            rag_service = Python("rag_service.py")
            vector_store = Python("vector_store.py")
            pdf_processor = Python("pdf_processor.py")
            web_processor = Python("web_processor.py")
            chroma_db = Storage("ChromaDB\nVector Database")
    
    # Data sources
    with Cluster("Data Sources"):
        pdf_docs = Storage("PDF Documents")
        web_content = Firewall("Web Content")
    
    # AI Model
    llm = Rack("LLM\n(OpenAI or Ollama)")
    
    # Connect components with arrows
    html >> Edge(label="HTTP") >> fastapi_app
    typescript >> html
    
    fastapi_app >> sqlite
    fastapi_app >> rag_service
    fastapi_app >> llm
    
    rag_service >> vector_store
    rag_service >> web_processor
    vector_store >> chroma_db
    vector_store >> pdf_processor
    
    pdf_processor >> pdf_docs
    web_processor >> web_content