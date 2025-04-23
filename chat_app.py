from __future__ import annotations as _annotations

import asyncio
import json
import sqlite3
import os
from collections.abc import AsyncIterator
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Annotated, Any, Callable, Literal, TypeVar, Optional
from urllib.parse import urlparse

import fastapi
import logfire
from fastapi import Depends, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from typing_extensions import LiteralString, ParamSpec, TypedDict

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.agent import InstrumentationSettings
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Import RAG utils
from rag_utils.rag_service import RagService

logfire.configure(token="pylf_v1_us_yRsWtVfb9mWG189CpHS62bvhSp2lVwm8vZpsHCP4Cdv2",
                 send_to_logfire="if-token-present")

llama_model = OpenAIModel(
    model_name="7shi/ezo-gemma-2-jpn:2b-instruct-q8_0",
    provider=OpenAIProvider(
        base_url="http://localhost:11434/v1",
        api_key="ollama"
    )
)
openai_model = "openai:gpt-4.1"
#openai_model = "openai:o4-mini"

agent = Agent(
    openai_model, 
    #llama_model,
    system_prompt=(
      #"Be concise, simple, and sincere in your answers. Use additional info only if relevant.",
      "あなたは優秀なアシスタントです。ユーザーの質問に誠意をもって答えて下さい。聞かれたこと以外は答えないように気をつけてくださいね。",
    ),
    retries=2,
    instrument=True)
Agent.instrument_all()
logfire.instrument_httpx(capture_all=True) 

THIS_DIR = Path(__file__).parent

# Initialize RAG service with PDF documents in the datas folder
PDF_DIR = os.path.join(THIS_DIR, "datas")
CHROMA_DB_DIR = os.path.join(THIS_DIR, "chroma_db")
rag_service = RagService(pdf_dir=PDF_DIR, chroma_db_dir=CHROMA_DB_DIR)


@asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
    async with Database.connect() as db:
        yield {"db": db}


app = fastapi.FastAPI(lifespan=lifespan)
#logfire.instrument_fastapi(app)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse((THIS_DIR / "chat_app.html"), media_type="text/html")


@app.get("/chat_app.ts")
async def main_ts() -> FileResponse:
    """Get the raw typescript code, it's compiled in the browser, forgive me."""
    return FileResponse((THIS_DIR / "chat_app.ts"), media_type="text/plain")


async def get_db(request: Request) -> Database:
    return request.state.db


@app.get("/chat/")
async def get_chat(database: Database = Depends(get_db)) -> Response:
    msgs = await database.get_messages()
    safe_msgs = []
    for m in msgs:
        try:
            safe_msgs.append(json.dumps(to_chat_message(m)).encode("utf-8"))
        except Exception:
            # Skip any message that cannot be parsed/displayed as chat
            continue
    return Response(
        b"\n".join(safe_msgs),
        media_type="text/plain",
    )


class ChatMessage(TypedDict):
    """Format of messages sent to the browser."""
    role: Literal["user", "model"]
    timestamp: str
    content: str


def to_chat_message(m: ModelMessage) -> ChatMessage:
    first_part = m.parts[0]
    if isinstance(m, ModelRequest):
        if isinstance(first_part, UserPromptPart):
            assert isinstance(first_part.content, str)
            return {
                "role": "user",
                "timestamp": first_part.timestamp.isoformat(),
                "content": first_part.content,
            }
    elif isinstance(m, ModelResponse):
        if isinstance(first_part, TextPart):
            return {
                "role": "model",
                "timestamp": m.timestamp.isoformat(),
                "content": first_part.content,
            }
    print("=== DEBUG: Unexpected message in to_chat_message ===")
    print("Type:", type(m))
    print("Value:", repr(m))
    print("Parts:", getattr(m, "parts", None))
    raise UnexpectedModelBehavior(f"Unexpected message type for chat app: {m}")


@app.post("/chat/")
async def post_chat(
    prompt: Annotated[str, fastapi.Form()], 
    use_rag: Annotated[str, fastapi.Form()] = "true",
    database: Database = Depends(get_db)
) -> StreamingResponse:
    async def stream_messages():
        """Streams new line delimited JSON "Message"s to the client."""
        # Store the original prompt
        original_prompt = prompt
        
        # Convert use_rag to bool ("true"/"false" string to Python bool)
        use_rag_bool = use_rag.lower() == "true"
        
        # Augment with RAG context if enabled
        augmented_prompt = original_prompt
        if use_rag_bool:
            augmented_prompt = rag_service.answer_with_rag(original_prompt)
        
        # 1. Add the original user request to the chat DB first, if your framework allows it:
        from pydantic_ai.messages import ModelRequest, UserPromptPart
        import json as _jsonlib_mod_for_typing

        user_msg = ModelRequest(parts=[UserPromptPart(content=original_prompt, timestamp=datetime.now(tz=timezone.utc))])
        # Store only the user's true prompt in DB immediately
        # Option A: Prepend/appends to current history (simulate message add)
        messages = await database.get_messages()
        messages.append(user_msg)
        # Prepare for streaming to client
        yield (
            json.dumps(
                {
                    "role": "user",
                    "timestamp": user_msg.parts[0].timestamp.isoformat(),
                    "content": original_prompt,
                }
            ).encode("utf-8")
            + b"\n"
        )
        # 2. Use the augmented prompt with the agent, but only for inference—history stays clean
        async with agent.run_stream(augmented_prompt, message_history=messages) as result:
            async for text in result.stream(debounce_by=0.01):
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp())
                yield json.dumps(to_chat_message(m)).encode("utf-8") + b"\n"

        await database.add_messages(result.new_messages_json())
    return StreamingResponse(stream_messages(), media_type="text/plain")


@app.get("/rag_status/")
async def get_rag_status() -> Response:
    """Get information about the RAG service status and loaded documents"""
    try:
        doc_count = len(rag_service.vector_store.collection.get()['documents']) if rag_service.vector_store.collection.count() > 0 else 0
        return Response(
            json.dumps({
                "status": "active",
                "pdf_dir": PDF_DIR,
                "document_chunks": doc_count,
            }),
            media_type="application/json",
        )
    except Exception as e:
        return Response(
            json.dumps({
                "status": "error",
                "error": str(e),
            }),
            media_type="application/json",
            status_code=500,
        )


@app.post("/add_url/")
async def add_url(url: Annotated[str, fastapi.Form()]) -> Response:
    """Add content from a URL to the RAG knowledge base"""
    try:
        print(f"Received URL: '{url}'")
        
        # Validate URL format
        if not url or not url.strip():
            print("URL is empty or contains only whitespace")
            return Response(
                json.dumps({
                    "status": "error",
                    "message": "URL cannot be empty"
                }),
                media_type="application/json",
                status_code=400
            )
            
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            print(f"Invalid URL format: {url}")
            return Response(
                json.dumps({
                    "status": "error",
                    "message": "Invalid URL format. URL must start with http:// or https://"
                }),
                media_type="application/json",
                status_code=400
            )
        
        # Add URL to knowledge base
        success = rag_service.add_web_url(url)
        
        if success:
            print(f"Successfully added URL: {url}")
            return Response(
                json.dumps({
                    "status": "success",
                    "message": f"Successfully added content from {url} to knowledge base"
                }),
                media_type="application/json"
            )
        else:
            print(f"Failed to add URL: {url}")
            return Response(
                json.dumps({
                    "status": "error",
                    "message": f"Failed to add content from {url}"
                }),
                media_type="application/json",
                status_code=500
            )
    except Exception as e:
        print(f"Error processing URL: {e}")
        return Response(
            json.dumps({
                "status": "error",
                "message": f"Error processing URL: {str(e)}"
            }),
            media_type="application/json",
            status_code=500
        )


@app.post("/clear_url_cache/")
async def clear_url_cache() -> Response:
    """Clear the web content cache"""
    try:
        success = rag_service.web_processor.clear_cache()
        return Response(
            json.dumps({
                "status": "success",
                "message": "Successfully cleared web content cache"
            }),
            media_type="application/json"
        )
    except Exception as e:
        print(f"Error clearing URL cache: {e}")
        return Response(
            json.dumps({
                "status": "error",
                "message": f"Error clearing cache: {str(e)}"
            }),
            media_type="application/json",
            status_code=500
        )


@app.get("/get_urls/")
async def get_urls() -> Response:
    """Get the list of URLs added to the knowledge base"""
    try:
        # Get all documents from vector store with 'web' type
        web_docs = []
        collection_count = rag_service.vector_store.collection.count()
        print(f"Collection contains {collection_count} total documents")
        
        if collection_count > 0:
            results = rag_service.vector_store.collection.get()
            print(f"Retrieved {len(results.get('metadatas', []))} documents from collection")
            
            for i, metadata in enumerate(results.get('metadatas', [])):
                # Log the metadata for debugging
                print(f"Document {i} metadata: {metadata}")
                
                if metadata.get('type') == 'web' and 'source' in metadata and 'title' in metadata:
                    # Check if this URL is already in our list
                    url = metadata['source']
                    if not any(doc['url'] == url for doc in web_docs):
                        web_docs.append({
                            'url': url,
                            'title': metadata['title'],
                            'domain': metadata.get('domain', urlparse(url).netloc)
                        })
        
        print(f"Found {len(web_docs)} unique web URLs")
        return Response(
            json.dumps({
                "status": "success",
                "urls": web_docs
            }),
            media_type="application/json"
        )
    except Exception as e:
        print(f"Error getting URLs: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            json.dumps({
                "status": "error",
                "message": f"Error retrieving URLs: {str(e)}"
            }),
            media_type="application/json",
            status_code=500
        )


@app.post("/chat/clear")
async def clear_chat(database: Database = Depends(get_db)) -> Response:
    """Clear all chat history from the database."""
    await database.clear_messages()
    return Response(status_code=200)
    

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class Database:

    con: sqlite3.Connection
    _loop: asyncio.AbstractEventLoop
    _executor: ThreadPoolExecutor
    
    @classmethod
    @asynccontextmanager
    async def connect(
        cls, file: Path = THIS_DIR / ".chat_app_messages.sqlite"
    ) -> AsyncIterator[Database]:
        with logfire.span("connect to DB"):
            loop = asyncio.get_event_loop()
            executor = ThreadPoolExecutor(max_workers=1)
            con = await loop.run_in_executor(executor, cls._connect, file)
            slf = cls(con, loop, executor)
        try:
            yield slf
        finally:
            await slf._asyncify(con.close)

    @staticmethod
    def _connect(file: Path) -> sqlite3.Connection:
        con = sqlite3.connect(str(file))
        con = logfire.instrument_sqlite3(con)
        cur = con.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS messages (id INT PRIMARY KEY, message_list TEXT);"
        )
        con.commit()
        return con
        
    async def add_messages(self, messages: bytes):
        await self._asyncify(
            self._execute,
            "INSERT INTO messages (message_list) VALUES (?);",
            messages,
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def get_messages(self) -> list[ModelMessage]:
        c = await self._asyncify(
            self._execute, "SELECT message_list FROM messages order by id"
        )
        rows = await self._asyncify(c.fetchall)
        messages: list[ModelMessage] = []
        for row in rows:
            messages.extend(ModelMessagesTypeAdapter.validate_json(row[0]))
        return messages

    async def clear_messages(self) -> None:
        """Delete all messages from the database."""
        await self._asyncify(
            self._execute, "DELETE FROM messages;", commit=True
        )

    def _execute(
        self, sql: LiteralString,
        *args: Any,
        commit: bool = False,
        ) -> sqlite3.Cursor:
        cur = self.con.cursor()
        cur.execute(sql, args)
        if commit:
            self.con.commit()
        return cur

    async def _asyncify(
        self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> R:
        return await self._loop.run_in_executor(
            self._executor,
            partial(func, **kwargs),
            *args,
        )
    

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "chat_app:app", 
        host="0.0.0.0",
        port=8000,
        reload=True, 
        reload_dirs=[str(THIS_DIR)]
    )









