"""MiniMax Chat Client for agent-framework.

This module provides a custom chat client that implements the agent-framework
BaseChatClient interface using MiniMax's Chat Completions API.

This allows agent-framework to work with MiniMax models that only support
the older Chat Completions API, not the newer Responses API.
"""

from __future__ import annotations

import os
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterable,
    Generic,
    TypedDict,
    cast,
)

from agent_framework import (
    BaseChatClient,
    ChatOptions,
    ChatResponse,
    ChatResponseUpdate,
    Content,
    Message,
    TextSpanRegion,
    UsageDetails,
)
from pydantic import BaseModel

if TYPE_CHECKING:
    pass


class MiniMaxChatOptions(ChatOptions[Any], total=False):
    """MiniMax-specific chat options."""

    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stream: bool | None = None


class MiniMaxChatClient(BaseChatClient[MiniMaxChatOptions]):
    """Custom chat client for MiniMax using Chat Completions API.

    This client adapts the agent-framework's BaseChatClient interface
    to MiniMax's Chat Completions API.
    """

    def __init__(
        self,
        *,
        model: str = "MiniMax-M2.7-highspeed",
        api_key: str | None = None,
        base_url: str = "https://api.minimaxi.com/v1",
        **kwargs: Any,
    ) -> None:
        """Initialize MiniMax chat client.

        Args:
            model: MiniMax model name
            api_key: MiniMax API key
            base_url: MiniMax API base URL
        """
        super().__init__(**kwargs)
        self.model = model
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")

    async def _inner_get_response(
        self,
        *,
        messages: list[Message],
        stream: bool,
        options: MiniMaxChatOptions | None = None,
        **kwargs: Any,
    ) -> ChatResponse | AsyncIterable[ChatResponseUpdate]:
        """Get response from MiniMax Chat API.

        Args:
            messages: List of messages
            stream: Whether to stream response
            options: Chat options
        """
        import httpx
        import json

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Convert agent_framework Message to OpenAI format
        openai_messages = []
        for msg in messages:
            if isinstance(msg, str):
                openai_messages.append({"role": "user", "content": msg})
            elif hasattr(msg, "role") and hasattr(msg, "contents"):
                content = ""
                if msg.contents:
                    if isinstance(msg.contents, str):
                        content = msg.contents
                    elif isinstance(msg.contents, list):
                        for c in msg.contents:
                            if isinstance(c, str):
                                content += c
                            elif isinstance(c, dict) and c.get("type") == "text":
                                content += c.get("text", "")
                            elif hasattr(c, "text"):
                                content += c.text
                    else:
                        content = str(msg.contents)
                openai_messages.append({
                    "role": str(msg.role) if hasattr(msg, "role") else "user",
                    "content": content,
                })

        # Build request
        data: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "thinking": {"type": "off"},  # Disable thinking tokens
        }

        if options:
            if options.get("temperature") is not None:
                data["temperature"] = options["temperature"]
            if options.get("max_tokens") is not None:
                data["max_tokens"] = options["max_tokens"]
            if options.get("top_p") is not None:
                data["top_p"] = options["top_p"]

        if stream:
            data["stream"] = True

        async def _stream() -> AsyncIterable[ChatResponseUpdate]:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            line = line[6:]
                            if line.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(line)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if delta.get("content"):
                                    yield ChatResponseUpdate(
                                        role="assistant",
                                        contents=[{"type": "text", "text": delta["content"]}],
                                    )
                            except json.JSONDecodeError:
                                continue

        if stream:
            return _stream()
        else:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                )
                resp.raise_for_status()
                result = resp.json()

                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if isinstance(content, list):
                    text = ""
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            text += c.get("text", "")
                        else:
                            text += str(c)
                    content = text

                # Filter out thinking tokens (MiniMax specific)
                if "<|EOT|>" in content:
                    content = content.split("<|EOT|>")[-1].strip()

                return ChatResponse(
                    messages=[Message(role="assistant", contents=[content])],
                    response_id=result.get("id", "minimax-response"),
                )


def create_minimax_client(
    model: str = "MiniMax-M2.7-highspeed",
    api_key: str | None = None,
    base_url: str = "https://api.minimaxi.com/v1",
) -> MiniMaxChatClient:
    """Create a MiniMax chat client for agent-framework.

    Args:
        model: MiniMax model name
        api_key: MiniMax API key
        base_url: MiniMax API base URL

    Returns:
        Configured MiniMaxChatClient
    """
    return MiniMaxChatClient(
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
