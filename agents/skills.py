"""
Skills Layer for EmbodiedAgents

将现有的 Components 封装为可复用的 Skills，
提供统一的调用接口。

示例用法:
    from agents.skills import Skill, skill_registry

    # 注册 skill
    @skill_registry.register("voice_command")
    class VoiceCommandSkill:
        def __init__(self):
            self.stt = SpeechToText(...)
            self.llm = LLM(...)

        async def execute(self, audio_topic: str, prompt: str) -> str:
            # 执行逻辑
            pass

    # 调用 skill
    result = await skill_registry.execute("voice_command", audio_topic="/audio", prompt="...")
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class SkillStatus(Enum):
    """Skill execution status."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class SkillResult:
    """Skill execution result."""

    status: SkillStatus
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillMetadata:
    """Skill metadata for registration."""

    name: str
    description: str
    inputs: Dict[str, type]  # input_name -> type
    outputs: Dict[str, type]  # output_name -> type
    tags: list[str] = field(default_factory=list)


class BaseSkill(ABC):
    """Base class for all Skills."""

    metadata: SkillMetadata

    def __init__(self, **kwargs):
        self._status = SkillStatus.IDLE
        self._components = {}

    @abstractmethod
    async def execute(self, **kwargs) -> SkillResult:
        """Execute the skill with given inputs."""
        pass

    @abstractmethod
    async def validate_inputs(self, **kwargs) -> bool:
        """Validate input parameters."""
        pass

    async def cleanup(self):
        """Cleanup resources."""
        pass

    @property
    def status(self) -> SkillStatus:
        return self._status


class SkillRegistry:
    """
    Central registry for all Skills.

    提供 Skills 的注册、发现和调用功能。
    """

    _instance = None
    _skills: Dict[str, type[BaseSkill]] = {}
    _instances: Dict[str, BaseSkill] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(
        self, name: str, description: str = "", tags: list[str] = None
    ) -> Callable:
        """
        Decorator to register a skill.

        Usage:
            @skill_registry.register("voice_command", description="Handle voice commands")
            class VoiceCommandSkill(BaseSkill):
                ...
        """

        def decorator(skill_class: type[BaseSkill]):
            self._skills[name] = skill_class

            # 添加 metadata
            if hasattr(skill_class, "metadata"):
                skill_class.metadata.name = name
                skill_class.metadata.description = description
                skill_class.metadata.tags = tags or []

            return skill_class

        return decorator

    def get(self, name: str, **init_kwargs) -> BaseSkill:
        """
        Get or create a skill instance.

        Args:
            name: Skill name
            **init_kwargs: Arguments to initialize the skill

        Returns:
            Skill instance
        """
        if name not in self._skills:
            raise ValueError(
                f"Skill '{name}' not found. Available: {list(self._skills.keys())}"
            )

        # Return cached instance if exists and no new kwargs
        if name in self._instances and not init_kwargs:
            return self._instances[name]

        # Create new instance
        skill_class = self._skills[name]
        instance = skill_class(**init_kwargs)

        if not init_kwargs:
            self._instances[name] = instance

        return instance

    async def execute(self, name: str, **kwargs) -> SkillResult:
        """
        Execute a skill by name.

        Args:
            name: Skill name
            **kwargs: Input parameters

        Returns:
            SkillResult
        """
        skill = self.get(name)

        # Validate inputs
        if not await skill.validate_inputs(**kwargs):
            return SkillResult(
                status=SkillStatus.FAILED, error="Input validation failed"
            )

        # Execute
        try:
            skill._status = SkillStatus.RUNNING
            result = await skill.execute(**kwargs)
            result.status = SkillStatus.SUCCESS
            return result
        except Exception as e:
            skill._status = SkillStatus.FAILED
            return SkillResult(status=SkillStatus.FAILED, error=str(e))

    def list_skills(self) -> Dict[str, Dict[str, Any]]:
        """List all registered skills with metadata."""
        return {
            name: {
                "description": getattr(cls.metadata, "description", ""),
                "tags": getattr(cls.metadata, "tags", []),
                "inputs": getattr(cls.metadata, "inputs", {}),
                "outputs": getattr(cls.metadata, "outputs", {}),
            }
            for name, cls in self._skills.items()
        }

    def unregister(self, name: str):
        """Unregister a skill."""
        if name in self._skills:
            del self._skills[name]
        if name in self._instances:
            del self._instances[name]


# Global registry instance
skill_registry = SkillRegistry()


# ============================================================
# Convenience: Wrap existing Components as Skills
# ============================================================


def component_to_skill(
    component_class,
    name: str,
    description: str = "",
    input_mapping: Dict[str, str] = None,
    output_mapping: Dict[str, str] = None,
):
    """
    Wrapper to convert existing Component to Skill.

    Args:
        component_class: Component class (e.g., LLM, Vision)
        name: Skill name
        description: Description
        input_mapping: Maps skill input -> component input
        output_mapping: Maps component output -> skill output

    Example:
        vision_skill = component_to_skill(
            Vision,
            "detect_objects",
            "Detect objects in image",
            input_mapping={"image": "camera_topic"},
            output_mapping={"detections": "objects"}
        )
    """

    @skill_registry.register(name, description)
    class WrappedSkill(BaseSkill):
        metadata = SkillMetadata(
            name=name,
            description=description,
            inputs=input_mapping or {},
            outputs=output_mapping or {},
        )

        def __init__(self, **kwargs):
            super().__init__()
            self.component = component_class(**kwargs)

        async def execute(self, **kwargs) -> SkillResult:
            # Map inputs to component
            mapped_inputs = {}
            if input_mapping:
                for skill_input, comp_input in input_mapping.items():
                    mapped_inputs[comp_input] = kwargs.get(skill_input)

            # Execute component
            result = await self.component.step(**mapped_inputs)

            # Map outputs
            if output_mapping:
                mapped_outputs = {}
                for comp_output, skill_output in output_mapping.items():
                    mapped_outputs[skill_output] = result.get(comp_output)
                result = mapped_outputs

            return SkillResult(status=SkillStatus.SUCCESS, output=result)

        async def validate_inputs(self, **kwargs) -> bool:
            return all(k in kwargs for k in (input_mapping or {}).keys())

    return WrappedSkill


# ============================================================
# Example: Built-in Skills
# ============================================================


@skill_registry.register(
    "voice_command",
    description="Listen for voice commands and process with LLM",
    tags=["audio", "speech", "llm"],
)
class VoiceCommandSkill(BaseSkill):
    """语音命令技能 - 封装 STT + LLM"""

    metadata = SkillMetadata(
        name="voice_command",
        description="Listen and understand voice commands",
        inputs={"audio_topic": str, "prompt": str},
        outputs={"text": str, "action": str},
    )

    def __init__(self, stt_component=None, llm_component=None, **kwargs):
        super().__init__()
        # 可以注入现有 components 或创建新的
        self.stt = stt_component
        self.llm = llm_component
        self._config = kwargs

    async def execute(self, audio_topic: str, prompt: str) -> SkillResult:
        # 1. 接收音频
        # 2. STT 转换为文本
        # 3. LLM 处理意图
        # 4. 返回结果

        try:
            # 模拟执行
            text = await self.stt.process(audio_topic)
            response = await self.llm.prompt(prompt, context={"transcript": text})

            return SkillResult(
                status=SkillStatus.SUCCESS, output={"text": text, "action": response}
            )
        except Exception as e:
            return SkillResult(status=SkillStatus.FAILED, error=str(e))

    async def validate_inputs(self, **kwargs) -> bool:
        return "audio_topic" in kwargs and "prompt" in kwargs


@skill_registry.register(
    "describe_scene", description="Describe what the robot sees", tags=["vision", "vlm"]
)
class DescribeSceneSkill(BaseSkill):
    """场景描述技能 - 封装 VLM"""

    metadata = SkillMetadata(
        name="describe_scene",
        description="Generate scene description from camera",
        inputs={"image_topic": str, "question": str},
        outputs={"description": str},
    )

    def __init__(self, vlm_component=None, **kwargs):
        super().__init__()
        self.vlm = vlm_component

    async def execute(
        self, image_topic: str, question: str = "Describe this scene"
    ) -> SkillResult:
        try:
            description = await self.vlm.analyze(image_topic, question)
            return SkillResult(
                status=SkillStatus.SUCCESS, output={"description": description}
            )
        except Exception as e:
            return SkillResult(status=SkillStatus.FAILED, error=str(e))

    async def validate_inputs(self, **kwargs) -> bool:
        return "image_topic" in kwargs


@skill_registry.register(
    "speak", description="Convert text to speech", tags=["audio", "tts"]
)
class SpeakSkill(BaseSkill):
    """语音合成技能 - 封装 TextToSpeech"""

    metadata = SkillMetadata(
        name="speak",
        description="Convert text to speech",
        inputs={"text": str, "voice": str},
        outputs={"audio_topic": str},
    )

    def __init__(self, tts_component=None, **kwargs):
        super().__init__()
        self.tts = tts_component

    async def execute(self, text: str, voice: str = "default") -> SkillResult:
        try:
            await self.tts.say(text)
            return SkillResult(
                status=SkillStatus.SUCCESS,
                output={"audio_topic": "/tts/output", "text": text},
            )
        except Exception as e:
            return SkillResult(status=SkillStatus.FAILED, error=str(e))

    async def validate_inputs(self, **kwargs) -> bool:
        return "text" in kwargs


# ============================================================
# High-level API: Skill Composer
# ============================================================


class SkillChain:
    """
    Chain multiple skills together.

    示例:
        chain = SkillChain()
        chain.then("voice_command", audio_topic="/mic", prompt="What do I see?")
              .then("speak", voice="friendly")
              .execute()
    """

    def __init__(self):
        self._steps = []

    def then(self, skill_name: str, **kwargs) -> "SkillChain":
        self._steps.append((skill_name, kwargs))
        return self

    async def execute(self) -> list[SkillResult]:
        results = []
        context = {}  # 传递上下文给下一步

        for skill_name, kwargs in self._steps:
            # 合并上下文到参数
            merged_kwargs = {**kwargs, **context}
            result = await skill_registry.execute(skill_name, **merged_kwargs)
            results.append(result)

            # 将输出添加到上下文
            if result.status == SkillStatus.SUCCESS and result.output:
                context.update(result.output)
            else:
                # 如果某步失败，停止链
                break

        return results


class SkillManager:
    """
    高级 Skill 管理器 - 支持动态组合和切换。

    功能:
    - 动态加载/卸载 skills
    - Skill 组合 (composite skills)
    - 运行时 skill 切换 (self-referential)
    """

    def __init__(self):
        self._registry = skill_registry
        self._active_skills: Dict[str, BaseSkill] = {}
        self._composites: Dict[str, list[str]] = {}

    def activate(self, name: str, **kwargs):
        """激活一个 skill"""
        skill = self._registry.get(name, **kwargs)
        self._active_skills[name] = skill
        return skill

    def deactivate(self, name: str):
        """停用一个 skill"""
        if name in self._active_skills:
            asyncio.create_task(self._active_skills[name].cleanup())
            del self._active_skills[name]

    def create_composite(self, name: str, skill_names: list[str]):
        """创建组合 skill"""
        self._composites[name] = skill_names

    async def execute_composite(self, name: str, **kwargs) -> list[SkillResult]:
        """执行组合 skill"""
        if name not in self._composites:
            raise ValueError(f"Composite '{name}' not found")

        results = []
        for skill_name in self._composites[name]:
            result = await self._registry.execute(skill_name, **kwargs)
            results.append(result)
            # 更新 kwargs 以传递上下文
            if result.output:
                kwargs.update(result.output)

        return results

    def get_active_skills(self) -> list[str]:
        """获取当前活跃的 skills"""
        return list(self._active_skills.keys())


# ============================================================
# Integration with existing Components
# ============================================================


def create_skill_from_component(
    component_name: str, component_config: dict = None
) -> BaseSkill:
    """
    从现有 Component 创建 Skill 的工厂函数。

    Args:
        component_name: Component 名称 (llm, vlm, vision, etc.)
        component_config: Component 配置

    Returns:
        BaseSkill instance
    """
    from agents.components import LLM, VLM, Vision, SpeechToText, TextToSpeech, VLA

    COMPONENT_MAP = {
        "llm": LLM,
        "vlm": VLM,
        "vision": Vision,
        "stt": SpeechToText,
        "tts": TextToSpeech,
        "vla": VLA,
    }

    if component_name not in COMPONENT_MAP:
        raise ValueError(f"Unknown component: {component_name}")

    component_class = COMPONENT_MAP[component_name]

    @skill_registry.register(f"skill_{component_name}")
    class ComponentSkill(BaseSkill):
        metadata = SkillMetadata(
            name=f"skill_{component_name}",
            description=f"Skill wrapper for {component_name}",
            inputs={},
            outputs={},
        )

        def __init__(self, **kwargs):
            super().__init__()
            self.component = component_class(**(component_config or {}))

        async def execute(self, **kwargs) -> SkillResult:
            result = await self.component.step(**kwargs)
            return SkillResult(status=SkillStatus.SUCCESS, output=result)

        async def validate_inputs(self, **kwargs) -> bool:
            return True

    return ComponentSkill
