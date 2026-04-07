from agents.plugins.base import Plugin


class SensorPlugin(Plugin):
    name = "sensor"
    version = "1.0.0"
    description = "Sensor and environment summary plugin"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "env_summary",
                "description": "Query current environment state",
                "parameters": {},
            }
        ]
