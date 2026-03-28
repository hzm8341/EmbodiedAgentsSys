"""LLM provider abstraction layer.

Providers:
  - LiteLLMProvider: multi-provider via LiteLLM (Anthropic, OpenAI, Gemini, etc.)
  - OllamaProvider: direct Ollama integration via httpx (no litellm required)

Usage:
    from agents.llm import LiteLLMProvider, OllamaProvider

    provider = OllamaProvider(default_model="qwen2.5:7b")
    response = await provider.chat_with_retry(messages)
"""

from agents.llm.provider import GenerationSettings, LLMProvider, LLMResponse, ToolCallRequest
from agents.llm.ollama_provider import OllamaProvider

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ToolCallRequest",
    "GenerationSettings",
    "OllamaProvider",
]

try:
    from agents.llm.litellm_provider import LiteLLMProvider
    __all__.append("LiteLLMProvider")
except ImportError:
    pass  # litellm is optional
