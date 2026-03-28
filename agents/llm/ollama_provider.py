"""Ollama LLM provider — calls Ollama's /api/chat endpoint directly via httpx.

This provider does NOT require litellm. It is a lightweight fallback for
local Ollama deployments used throughout EmbodiedAgentsSys.
"""

import json
import logging
import secrets
import string
from typing import Any

import httpx

from agents.llm.provider import LLMProvider, LLMResponse, ToolCallRequest

logger = logging.getLogger(__name__)

_ALNUM = string.ascii_letters + string.digits


def _short_tool_id() -> str:
    return "".join(secrets.choice(_ALNUM) for _ in range(9))


class OllamaProvider(LLMProvider):
    """LLM provider backed by a local Ollama server.

    Uses Ollama's native /api/chat HTTP endpoint (OpenAI-compatible format).
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11434,
        default_model: str = "qwen2.5:7b",
        timeout: float = 120.0,
    ):
        super().__init__(api_key=None, api_base=f"http://{host}:{port}")
        self.default_model = default_model
        self._base_url = f"http://{host}:{port}"
        self._timeout = timeout

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Send a chat request to Ollama's /api/chat endpoint."""
        resolved_model = model or self.default_model

        # Ollama uses OpenAI-compatible /v1/chat/completions or its own /api/chat.
        # We use /api/chat (native) which supports tool calls since Ollama 0.2.
        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": self._sanitize_empty_content(messages),
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if tools:
            payload["tools"] = tools

        url = f"{self._base_url}/api/chat"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            return LLMResponse(
                content=f"Error calling Ollama: HTTP {e.response.status_code} — {e.response.text}",
                finish_reason="error",
            )
        except Exception as e:
            return LLMResponse(content=f"Error calling Ollama: {e}", finish_reason="error")

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        """Parse Ollama /api/chat response."""
        message = data.get("message", {})
        content: str | None = message.get("content") or None
        done_reason = data.get("done_reason", "stop")

        tool_calls: list[ToolCallRequest] = []
        for tc in message.get("tool_calls") or []:
            func = tc.get("function", {})
            arguments = func.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}

            tool_calls.append(ToolCallRequest(
                id=_short_tool_id(),
                name=func.get("name", ""),
                arguments=arguments,
            ))

        finish_reason = "tool_calls" if tool_calls else (done_reason or "stop")

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )

    def get_default_model(self) -> str:
        """Get the default Ollama model."""
        return self.default_model
