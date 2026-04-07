from agents.plugins.base import Plugin


class LLMPlugin(Plugin):
    name = "llm"
    version = "1.0.0"
    description = "LLM inference plugin"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "llm_query",
                "description": "Send a query to the LLM provider",
                "parameters": {"prompt": "str"},
            }
        ]
