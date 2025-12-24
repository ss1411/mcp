# This mcp client does following:
# 1. Uses httpx.AsyncClient
# 2. Sends a JSON‑RPC 2.0 request
# 3. Streams the HTTP response and concatenates text chunks into one JSON string

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict

import httpx

DEFAULT_MCP_URL = "https://vipfapwm3x.us-east-1.awsapprunner.com/mcp"


class MCPClient:
    """
    Async client for a Streamable HTTP MCP server using JSON-RPC 2.0.
    """

    def __init__(self, base_url: str | None = None, timeout: float = 60.0):
        self.base_url = base_url or os.getenv("MCP_SERVER_URL") or DEFAULT_MCP_URL
        self.timeout = timeout

    async def list_tools(self) -> list[Dict[str, Any]]:
        """
        Retrieve a list of available tools/resources from the MCP server.
        """
        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/list",
            "params": {},
        }

        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Accept": "application/json, text/event-stream"},
        ) as client:
            async with client.stream("POST", self.base_url, json=payload) as response:
                response.raise_for_status()
                chunks: list[str] = []
                async for part in response.aiter_text():
                    if part:
                        chunks.append(part)

        raw_text = "".join(chunks)


        data = json.loads(raw_text)

        if "error" in data:
            raise RuntimeError(
                f"MCP list_tools error (id={data.get('id')}): "
                f"{data['error'].get('code')} {data['error'].get('message')}"
            )

        return data.get("result", [])

    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on a JSON-RPC 2.0 MCP server over Streamable HTTP
        and return the final JSON-RPC result object.

        This assumes the response body is a single JSON-RPC 2.0 message
        streamed as chunks of text.
        """
        request_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        # Try a few Accept header values in case the server performs strict
        # content-negotiation and returns 406 Not Acceptable for some values.
        accept_options = [
            "application/json, text/event-stream",
            "text/event-stream",
            "application/json",
        ]

        raw_text = None
        last_exc: Exception | None = None

        for accept in accept_options:
            async with httpx.AsyncClient(timeout=self.timeout, headers={"Accept": accept}) as client:
                try:
                    # Use streaming so we don't block on the full response at once.
                    async with client.stream("POST", self.base_url, json=payload) as response:
                        response.raise_for_status()
                        chunks: list[str] = []
                        async for part in response.aiter_text():
                            if part:
                                chunks.append(part)

                    raw_text = "".join(chunks)
                    last_exc = None
                    break
                except httpx.HTTPStatusError as e:
                    # If the server returns 406, try the next Accept header.
                    if e.response is not None and e.response.status_code == 406:
                        last_exc = e
                        continue
                    raise

        if raw_text is None:
            # If we couldn't get a successful response, raise the last error.
            if last_exc:
                raise last_exc
            raise RuntimeError("Failed to call tool: no response received")

        raw_text = "".join(chunks)

        # For a simple demo, I am assuming the final concatenated text is valid JSON.
        # If the server sends multiple JSON-RPC messages in one stream, I'llneed to parse line-delimited JSON
        import json
        data = json.loads(raw_text)

        if "error" in data:
            raise RuntimeError(
                f"MCP tool error (id={data.get('id')}): "
                f"{data['error'].get('code')} {data['error'].get('message')}"
            )

        return data.get("result", {})

if __name__ == "__main__":
    mcp = MCPClient()
    import asyncio
    tools = asyncio.run(mcp.list_tools())
    print("Available tools:", tools)