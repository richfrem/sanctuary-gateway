"""
MCP SSE Server - Hello World Example

This server correctly implements the MCP SSE transport protocol:
1. GET /sse - Establishes SSE stream, sends 'endpoint' event, then listens for responses to push
2. POST /messages - Receives JSON-RPC requests, processes them, pushes response to SSE stream, returns 202
"""
from fastapi import FastAPI, Request, Response
from sse_starlette.sse import EventSourceResponse
import uvicorn
import asyncio
import json
from typing import Dict, Any
import uuid

app = FastAPI()

# Store active SSE connections by session_id
# In production, use Redis or similar for multi-process support
active_sessions: Dict[str, asyncio.Queue] = {}


@app.get("/sse")
async def handle_sse(request: Request):
    """SSE endpoint - establishes bidirectional communication channel."""
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Build absolute URL for the messages endpoint with session_id
    base_url = str(request.base_url).rstrip("/")
    messages_url = f"{base_url}/messages?session_id={session_id}"
    
    # Create response queue for this session
    response_queue: asyncio.Queue = asyncio.Queue()
    active_sessions[session_id] = response_queue
    
    async def event_generator():
        try:
            # First event MUST be 'endpoint' with the POST URL
            yield {
                "event": "endpoint",
                "data": messages_url
            }
            
            # Now wait for responses to push to client
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    # Wait for a response to send (with timeout for keepalive)
                    response_data = await asyncio.wait_for(
                        response_queue.get(), 
                        timeout=30.0
                    )
                    # Send the JSON-RPC response as 'message' event
                    yield {
                        "event": "message",
                        "data": json.dumps(response_data)
                    }
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    continue
                    
        finally:
            # Cleanup session on disconnect
            active_sessions.pop(session_id, None)

    return EventSourceResponse(event_generator())


@app.post("/messages")
async def handle_messages(request: Request):
    """Message endpoint - receives JSON-RPC, pushes response to SSE stream."""
    # Get session_id from query params
    session_id = request.query_params.get("session_id")
    
    if not session_id or session_id not in active_sessions:
        return Response(
            content=json.dumps({"error": "Invalid or missing session_id"}),
            status_code=400,
            media_type="application/json"
        )
    
    body = await request.json()
    method = body.get("method")
    req_id = body.get("id")
    
    # Process the JSON-RPC request
    response = process_jsonrpc(method, body.get("params", {}), req_id)
    
    # Push response to the SSE queue (if there's a response to send)
    if response is not None:
        await active_sessions[session_id].put(response)
    
    # Return 202 Accepted (or 200 with no body) per MCP SSE spec
    return Response(status_code=202)


def process_jsonrpc(method: str, params: dict, req_id: Any) -> dict | None:
    """Process JSON-RPC methods and return response dict."""
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "hello-world",
                    "version": "1.0.0"
                }
            }
        }
    
    if method == "notifications/initialized":
        # Notifications don't get responses
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "say_hello",
                        "description": "Says hello to someone",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name to greet"
                                }
                            }
                        }
                    }
                ]
            }
        }

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        if tool_name == "say_hello":
            name = args.get("name", "World")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Hello, {name}!"
                        }
                    ]
                }
            }
    
    # Method not found
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": "Method not found"
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
