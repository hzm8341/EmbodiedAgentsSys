"""
agents - EmbodiedAgentsSys 核心包

纯 Python 实现的 4 层机器人代理架构，无 ROS2 依赖。

架构层级：
  ├─ Perception Layer: RobotObservation
  ├─ Cognition Layer: Planning, Reasoning, Learning
  ├─ Execution Layer: Tools framework
  └─ Feedback Layer: FeedbackLoop

快速开始：
  from agents import SimpleAgent
  agent = SimpleAgent.from_preset("default")
  result = await agent.run_task("pick up object")
"""

__version__ = "1.0.0"

# Core types and components
from agents.core.types import (
    RobotObservation,
    SkillResult,
    AgentConfig,
)
from agents.core.agent_loop import RobotAgentLoop

# Configuration management
from agents.config.manager import ConfigManager
from agents.config.schemas import AgentConfigSchema

# Cognition layers
from agents.cognition.planning import (
    PlanningLayerBase,
    DefaultPlanningLayer,
    PlanningLayer,  # Backward compatibility
)
from agents.cognition.reasoning import (
    ReasoningLayerBase,
    DefaultReasoningLayer,
    ReasoningLayer,  # Backward compatibility
)
from agents.cognition.learning import (
    LearningLayerBase,
    DefaultLearningLayer,
    LearningLayer,  # Backward compatibility
)
from agents.cognition.engine import CognitionEngine

# Feedback system
from agents.feedback.logger import FeedbackLogger
from agents.feedback.analyzer import FeedbackAnalyzer
from agents.feedback.loop import FeedbackLoop

# Execution tools
from agents.execution.tools.base import ToolBase
from agents.execution.tools.registry import ToolRegistry
from agents.execution.tools.strategy import StrategySelector
from agents.execution.tools.gripper_tool import GripperTool
from agents.execution.tools.move_tool import MoveTool
from agents.execution.tools.vision_tool import VisionTool

# Extensions framework
from agents.extensions.plugin import PluginBase
from agents.extensions.registry import PluginRegistry
from agents.extensions.loader import PluginLoader
from agents.extensions.preprocessor_plugin import PreprocessorPlugin
from agents.extensions.postprocessor_plugin import PostprocessorPlugin
from agents.extensions.visualization_plugin import VisualizationPlugin

# Simplified interface
from agents.simple_agent import SimpleAgent

__all__ = [
    # Core
    "RobotObservation",
    "SkillResult",
    "AgentConfig",
    "RobotAgentLoop",

    # Configuration
    "ConfigManager",
    "AgentConfigSchema",

    # Cognition
    "PlanningLayerBase",
    "DefaultPlanningLayer",
    "PlanningLayer",
    "ReasoningLayerBase",
    "DefaultReasoningLayer",
    "ReasoningLayer",
    "LearningLayerBase",
    "DefaultLearningLayer",
    "LearningLayer",
    "CognitionEngine",

    # Feedback
    "FeedbackLogger",
    "FeedbackAnalyzer",
    "FeedbackLoop",

    # Execution
    "ToolBase",
    "ToolRegistry",
    "StrategySelector",
    "GripperTool",
    "MoveTool",
    "VisionTool",

    # Extensions
    "PluginBase",
    "PluginRegistry",
    "PluginLoader",
    "PreprocessorPlugin",
    "PostprocessorPlugin",
    "VisualizationPlugin",

    # Simple interface
    "SimpleAgent",
]
