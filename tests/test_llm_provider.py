"""Tests for agents/llm — LLMProvider ABC, registry, and OllamaProvider.

These tests are pure unit tests (no real Ollama server needed).
"""

import asyncio
import json
import pytest

from agents.llm.provider import (
    GenerationSettings,
    LLMProvider,
    LLMResponse,
    ToolCallRequest,
)
from agents.llm.registry import find_by_model, find_by_name, find_gateway
from agents.llm.ollama_provider import OllamaProvider


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

class _DummyProvider(LLMProvider):
    """Minimal concrete provider for testing the ABC."""

    def __init__(self, response: LLMResponse | None = None):
        super().__init__()
        self._response = response or LLMResponse(content="ok")
        self.call_count = 0

    async def chat(self, messages, tools=None, model=None, max_tokens=4096,
                   temperature=0.7, reasoning_effort=None, tool_choice=None) -> LLMResponse:
        self.call_count += 1
        return self._response

    def get_default_model(self) -> str:
        return "dummy-model"


class _FailingProvider(LLMProvider):
    """Provider that always returns transient errors then succeeds."""

    def __init__(self, fail_times: int = 1, success_response: LLMResponse | None = None):
        super().__init__()
        self._fail_times = fail_times
        self._success = success_response or LLMResponse(content="recovered")
        self.call_count = 0

    async def chat(self, messages, tools=None, model=None, max_tokens=4096,
                   temperature=0.7, reasoning_effort=None, tool_choice=None) -> LLMResponse:
        self.call_count += 1
        if self.call_count <= self._fail_times:
            return LLMResponse(content="Error calling LLM: 429 rate limit exceeded", finish_reason="error")
        return self._success

    def get_default_model(self) -> str:
        return "failing-model"


# ---------------------------------------------------------------------------
# ToolCallRequest
# ---------------------------------------------------------------------------

def test_tool_call_request_to_openai_format():
    tc = ToolCallRequest(id="abc123xyz", name="move_arm", arguments={"x": 1.0, "y": 2.0})
    payload = tc.to_openai_tool_call()
    assert payload["id"] == "abc123xyz"
    assert payload["type"] == "function"
    assert payload["function"]["name"] == "move_arm"
    args = json.loads(payload["function"]["arguments"])
    assert args == {"x": 1.0, "y": 2.0}


def test_tool_call_request_with_provider_fields():
    tc = ToolCallRequest(
        id="xyz",
        name="grasp",
        arguments={},
        provider_specific_fields={"extra": 1},
        function_provider_specific_fields={"fn_extra": 2},
    )
    payload = tc.to_openai_tool_call()
    assert payload["provider_specific_fields"] == {"extra": 1}
    assert payload["function"]["provider_specific_fields"] == {"fn_extra": 2}


# ---------------------------------------------------------------------------
# LLMResponse
# ---------------------------------------------------------------------------

def test_llm_response_has_tool_calls_false():
    resp = LLMResponse(content="hello")
    assert not resp.has_tool_calls


def test_llm_response_has_tool_calls_true():
    tc = ToolCallRequest(id="x", name="fn", arguments={})
    resp = LLMResponse(content=None, tool_calls=[tc])
    assert resp.has_tool_calls


# ---------------------------------------------------------------------------
# GenerationSettings
# ---------------------------------------------------------------------------

def test_generation_settings_defaults():
    gs = GenerationSettings()
    assert gs.temperature == 0.7
    assert gs.max_tokens == 4096
    assert gs.reasoning_effort is None


def test_generation_settings_custom():
    gs = GenerationSettings(temperature=0.0, max_tokens=1024, reasoning_effort="high")
    assert gs.temperature == 0.0
    assert gs.max_tokens == 1024
    assert gs.reasoning_effort == "high"


# ---------------------------------------------------------------------------
# LLMProvider._sanitize_empty_content
# ---------------------------------------------------------------------------

def test_sanitize_empty_string_content():
    msgs = [{"role": "user", "content": ""}]
    result = LLMProvider._sanitize_empty_content(msgs)
    assert result[0]["content"] == "(empty)"


def test_sanitize_empty_assistant_with_tool_calls():
    msgs = [{"role": "assistant", "content": "", "tool_calls": [{"id": "x"}]}]
    result = LLMProvider._sanitize_empty_content(msgs)
    assert result[0]["content"] is None


def test_sanitize_filters_empty_text_blocks():
    msgs = [
        {"role": "user", "content": [
            {"type": "text", "text": ""},
            {"type": "text", "text": "hello"},
        ]}
    ]
    result = LLMProvider._sanitize_empty_content(msgs)
    assert result[0]["content"] == [{"type": "text", "text": "hello"}]


def test_sanitize_dict_content_becomes_list():
    msgs = [{"role": "user", "content": {"type": "text", "text": "hi"}}]
    result = LLMProvider._sanitize_empty_content(msgs)
    assert result[0]["content"] == [{"type": "text", "text": "hi"}]


# ---------------------------------------------------------------------------
# LLMProvider._strip_image_content
# ---------------------------------------------------------------------------

def test_strip_image_content_removes_image_blocks():
    msgs = [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        {"type": "text", "text": "describe it"},
    ]}]
    result = LLMProvider._strip_image_content(msgs)
    assert result is not None
    assert result[0]["content"][0] == {"type": "text", "text": "[image omitted]"}
    assert result[0]["content"][1]["text"] == "describe it"


def test_strip_image_content_returns_none_when_no_images():
    msgs = [{"role": "user", "content": "no images here"}]
    assert LLMProvider._strip_image_content(msgs) is None


# ---------------------------------------------------------------------------
# LLMProvider.chat_with_retry — sentinel defaults
# ---------------------------------------------------------------------------

def test_chat_with_retry_uses_generation_defaults():
    provider = _DummyProvider()
    provider.generation = GenerationSettings(temperature=0.1, max_tokens=512)

    async def run():
        return await provider.chat_with_retry([{"role": "user", "content": "hi"}])

    resp = asyncio.run(run())
    assert resp.content == "ok"
    assert provider.call_count == 1


def test_chat_with_retry_retries_on_transient_error():
    provider = _FailingProvider(fail_times=1)

    async def run():
        return await provider.chat_with_retry([{"role": "user", "content": "hi"}])

    resp = asyncio.run(run())
    assert resp.content == "recovered"
    assert provider.call_count == 2


def test_chat_with_retry_stops_on_non_transient_error():
    class _NonTransientProvider(LLMProvider):
        def __init__(self):
            super().__init__()
            self.call_count = 0

        async def chat(self, messages, **kwargs) -> LLMResponse:
            self.call_count += 1
            return LLMResponse(content="Error calling LLM: invalid model name", finish_reason="error")

        def get_default_model(self):
            return "x"

    provider = _NonTransientProvider()

    async def run():
        return await provider.chat_with_retry([{"role": "user", "content": "hi"}])

    resp = asyncio.run(run())
    assert resp.finish_reason == "error"
    assert provider.call_count == 1  # no retry for non-transient


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_find_by_model_anthropic():
    spec = find_by_model("claude-opus-4-6")
    assert spec is not None
    assert spec.name == "anthropic"
    assert spec.supports_prompt_caching


def test_find_by_model_with_prefix():
    spec = find_by_model("anthropic/claude-sonnet-4-6")
    assert spec is not None
    assert spec.name == "anthropic"


def test_find_by_model_qwen():
    spec = find_by_model("qwen2.5:7b")
    assert spec is not None
    assert spec.name == "dashscope"


def test_find_by_model_unknown():
    assert find_by_model("unknown-xyz-model") is None


def test_find_by_name_ollama():
    spec = find_by_name("ollama")
    assert spec is not None
    assert spec.is_local
    assert spec.litellm_prefix == "ollama_chat"


def test_find_gateway_by_key_prefix():
    spec = find_gateway(api_key="sk-or-abc123")
    assert spec is not None
    assert spec.name == "openrouter"


def test_find_gateway_by_base_keyword():
    spec = find_gateway(api_base="https://aihubmix.com/v1")
    assert spec is not None
    assert spec.name == "aihubmix"


def test_find_gateway_by_provider_name():
    spec = find_gateway(provider_name="ollama")
    assert spec is not None
    assert spec.name == "ollama"


def test_find_gateway_none_for_standard_provider():
    # Anthropic is not a gateway
    spec = find_gateway(provider_name="anthropic")
    assert spec is None


# ---------------------------------------------------------------------------
# OllamaProvider._parse_response
# ---------------------------------------------------------------------------

def test_ollama_parse_text_response():
    provider = OllamaProvider()
    data = {
        "message": {"role": "assistant", "content": "hello world"},
        "done": True,
        "done_reason": "stop",
    }
    resp = provider._parse_response(data)
    assert resp.content == "hello world"
    assert not resp.has_tool_calls
    assert resp.finish_reason == "stop"


def test_ollama_parse_tool_call_response():
    provider = OllamaProvider()
    data = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "move_arm",
                    "arguments": {"x": 0.5, "y": 0.3},
                }
            }],
        },
        "done": True,
        "done_reason": "stop",
    }
    resp = provider._parse_response(data)
    assert resp.has_tool_calls
    assert resp.tool_calls[0].name == "move_arm"
    assert resp.tool_calls[0].arguments == {"x": 0.5, "y": 0.3}
    assert resp.finish_reason == "tool_calls"


def test_ollama_parse_tool_call_with_string_args():
    provider = OllamaProvider()
    data = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "grasp_object",
                    "arguments": '{"object_id": "cup_01"}',
                }
            }],
        },
        "done": True,
    }
    resp = provider._parse_response(data)
    assert resp.tool_calls[0].arguments == {"object_id": "cup_01"}


def test_ollama_provider_default_model():
    provider = OllamaProvider(default_model="llama3:8b")
    assert provider.get_default_model() == "llama3:8b"
