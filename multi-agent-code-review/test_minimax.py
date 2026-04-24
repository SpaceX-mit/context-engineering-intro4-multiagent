"""Test MiniMax client with agent-framework."""
import asyncio
import os

from agent_framework import Agent, Message, BaseChatClient, ChatResponse, ChatResponseUpdate, ChatOptions
from typing import Any, AsyncIterable


class MiniMaxChatClient(BaseChatClient[ChatOptions]):
    """Chat Completions API client for MiniMax."""

    OTEL_PROVIDER_NAME = "minimax"

    def __init__(
        self,
        *,
        model: str = "MiniMax-M2.7-highspeed",
        api_key: str | None = None,
        base_url: str = "https://api.minimaxi.com/v1",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.model = model
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")

    async def _inner_get_response(
        self,
        *,
        messages: list[Message],
        stream: bool,
        options: ChatOptions | None = None,
        **kwargs: Any,
    ):
        import httpx
        import json

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        openai_messages = []
        for msg in messages:
            if isinstance(msg, str):
                openai_messages.append({"role": "user", "content": msg})
            else:
                content = ""
                if hasattr(msg, "contents"):
                    if isinstance(msg.contents, str):
                        content = msg.contents
                    elif isinstance(msg.contents, list):
                        for c in msg.contents:
                            if isinstance(c, str):
                                content += c
                            elif isinstance(c, dict) and c.get("type") == "text":
                                content += c.get("text", "")

                role = "user"
                if hasattr(msg, "role"):
                    role = str(msg.role)

                openai_messages.append({"role": role, "content": content})

        data = {"model": self.model, "messages": openai_messages}

        if options:
            if options.get("temperature") is not None:
                data["temperature"] = options["temperature"]
            if options.get("max_tokens") is not None:
                data["max_tokens"] = options["max_tokens"]

        if stream:
            async def _stream():
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST", f"{self.base_url}/chat/completions",
                        headers=headers, json=data
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
                                        contents=[{"type": "text", "text": delta["content"]}]
                                    )
                            except json.JSONDecodeError:
                                continue
            return _stream()
        else:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers, json=data
                )
                resp.raise_for_status()
                result = resp.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if isinstance(content, list):
                    text = "".join(
                        c.get("text", "") if isinstance(c, dict) else str(c)
                        for c in content
                    )
                    content = text
                return ChatResponse(
                    messages=[Message(role="assistant", contents=[content])],
                    response_id=result.get("id", "minimax-response"),
                )


async def main():
    client = MiniMaxChatClient(
        model="MiniMax-M2.7-highspeed",
        api_key="sk-cp-vkEj751v_1aMyUXzNAkeaXw90HnTQ8GbQubW85hBWHxHrR1PaRX-S_DVVWzDCpaVLhbJHxjzTBH7lv2pXmoWhyI5pyM9wevrFr3ggQBOfi73PaTfydZUpa0",
        base_url="https://api.minimaxi.com/v1",
    )

    agent = Agent(
        client=client,
        name="Test",
        instructions="Say hello in one word."
    )

    result = await agent.run("Say hello")
    print("Result:", result.text)


if __name__ == "__main__":
    asyncio.run(main())
