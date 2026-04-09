"""Driver registry for managing hardware drivers."""

from typing import Optional

from embodiedagentsys.hal.base_driver import BaseDriver


class DriverRegistry:
    """Registry for managing available hardware drivers."""

    def __init__(self):
        self._drivers: dict[str, type[BaseDriver]] = {}

    def register(self, name: str, driver_class: type[BaseDriver]) -> None:
        """Register a driver class."""
        self._drivers[name] = driver_class

    def get(self, name: str) -> Optional[type[BaseDriver]]:
        """Get registered driver class."""
        return self._drivers.get(name)

    def create(self, name: str, **kwargs) -> Optional[BaseDriver]:
        """Create driver instance by name."""
        driver_class = self.get(name)
        if driver_class:
            return driver_class(**kwargs)
        return None

    def list_drivers(self) -> list[str]:
        """List all registered driver names."""
        return list(self._drivers.keys())
