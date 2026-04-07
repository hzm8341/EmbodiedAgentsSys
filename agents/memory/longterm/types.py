# agents/memory/longterm/types.py
"""Memory type taxonomy for EmbodiedAgentsSys long-term memory."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import yaml


class MemoryType(str, Enum):
    ROBOT_CONFIG = "robot_config"
    FEEDBACK = "feedback"
    MISSION = "mission"
    REFERENCE = "reference"


@dataclass
class MemoryHeader:
    filename: str
    file_path: str
    mtime_ms: float
    description: Optional[str]
    type: Optional[MemoryType]
    name: Optional[str]


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(content[3:end]) or {}
    except yaml.YAMLError:
        return {}
