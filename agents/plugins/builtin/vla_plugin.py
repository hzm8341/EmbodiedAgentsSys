from agents.plugins.base import Plugin


class VLAPlugin(Plugin):
    name = "vla"
    version = "1.0.0"
    description = "VLA policy execution plugin"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "start_policy",
                "description": "Start a VLA policy skill by ID",
                "parameters": {"skill_id": "str"},
            },
            {
                "name": "change_policy",
                "description": "Switch to a different VLA policy",
                "parameters": {"skill_id": "str"},
            },
        ]
