"""MockLLM factory for test use."""
from agents.llm.provider import LLMProvider, LLMResponse


class _MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, responses: list[str]):
        """Initialize mock LLM provider.

        Args:
            responses: List of response strings to cycle through.
        """
        self._responses = list(responses)
        self._index = 0
        self.call_history: list = []

    async def chat(
        self,
        messages,
        tools=None,
        model=None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort=None,
        tool_choice=None,
        **kwargs
    ) -> LLMResponse:
        """Generate chat response.

        Args:
            messages: List of message dicts with role and content.
            tools: Optional list of available tools.
            model: Optional model name override.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
            reasoning_effort: Optional reasoning effort level.
            tool_choice: Optional tool choice specification.
            **kwargs: Additional provider-specific kwargs.

        Returns:
            LLMResponse with content from configured responses.
        """
        self.call_history.append(messages)
        if self._responses:
            content = self._responses[self._index % len(self._responses)]
            self._index += 1
        else:
            content = "mock response"
        return LLMResponse(content=content, tool_calls=[])

    def get_model_name(self) -> str:
        """Get the model name.

        Returns:
            Mock model name.
        """
        return "mock-model"

    def get_default_model(self) -> str:
        """Get the default model name.

        Returns:
            Default mock model name.
        """
        return "mock-model"


def make_mock_llm(responses: list[str] | None = None) -> _MockLLMProvider:
    """Factory function to create a mock LLM provider.

    Args:
        responses: List of response strings to cycle through.
                  Defaults to ["mock response"] if None.

    Returns:
        Mock LLM provider instance.
    """
    return _MockLLMProvider(responses=responses or ["mock response"])
