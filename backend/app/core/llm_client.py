from __future__ import annotations
import json
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import httpx
from openai import AsyncOpenAI

from app.config import settings


class BaseLLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        ...

    @abstractmethod
    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        ...


class OpenAIClient(BaseLLMClient):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.model = settings.OPENAI_MODEL

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        kwargs = {"model": self.model, "messages": messages, "temperature": 0.3}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = await self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        result = {"content": msg.content or "", "tool_calls": []}
        if msg.tool_calls:
            for tc in msg.tool_calls:
                result["tool_calls"].append({
                    "id": tc.id,
                    "function": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })
        return result

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0.3, stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


class OllamaClient(BaseLLMClient):
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        payload: dict = {"model": self.model, "messages": messages, "stream": False}
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        msg = data.get("message", {})
        result = {"content": msg.get("content", ""), "tool_calls": []}
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            result["tool_calls"].append({
                "id": fn.get("name", ""),
                "function": fn.get("name", ""),
                "arguments": fn.get("arguments", {}),
            })
        return result

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        payload = {"model": self.model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content


def get_llm_client(provider: str | None = None) -> BaseLLMClient:
    p = provider or settings.LLM_PROVIDER
    if p == "ollama":
        return OllamaClient()
    return OpenAIClient()
