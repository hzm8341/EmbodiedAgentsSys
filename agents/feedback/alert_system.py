"""Alert system for critical safety events."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Single alert event."""
    event_id: str
    level: AlertLevel
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False


class AlertSystem:
    """System for raising and tracking alerts."""

    def __init__(self):
        self.alerts: List[Alert] = []

    def raise_alert(
        self,
        event_id: str,
        level: AlertLevel,
        message: str
    ) -> None:
        """Raise an alert."""
        alert = Alert(event_id=event_id, level=level, message=message)
        self.alerts.append(alert)

    def acknowledge_alert(self, alert_index: int) -> None:
        """Mark alert as acknowledged."""
        if 0 <= alert_index < len(self.alerts):
            self.alerts[alert_index].acknowledged = True

    def get_unacknowledged_alerts(self) -> List[Alert]:
        """Get all unacknowledged alerts."""
        return [a for a in self.alerts if not a.acknowledged]
