"""
Skills 使用示例

演示如何使用新添加的 Skills 层来调用 EmbodiedAgents 组件。
"""

# ============================================================
# 示例 1: 直接使用 Skill Registry
# ============================================================

from agents.skills import skill_registry, SkillChain, SkillManager

# 列出所有可用的 skills
available_skills = skill_registry.list_skills()
print("Available skills:", list(available_skills.keys()))


# 执行一个 skill
async def example_basic_usage():
    result = await skill_registry.execute("speak", text="Hello, I am a robot!")
    print(f"Result: {result.status}, Output: {result.output}")


# ============================================================
# 示例 2: 使用 Skill Chain 组合多个 Skills
# ============================================================


async def example_chain():
    """
    语音 -> 理解 -> 语音回复

    流程:
    1. voice_command: 接收音频，转换为文本并理解意图
    2. speak: 将回复转换为语音输出
    """
    chain = SkillChain()

    results = (
        chain.then("voice_command", audio_topic="/robot/mic", prompt="理解用户指令")
        .then("speak", voice="friendly")
        .execute()
    )

    for r in results:
        print(f"Step result: {r.status}")


# ============================================================
# 示例 3: 使用 Skill Manager 进行动态管理
# ============================================================


async def example_manager():
    """
    Skill Manager 支持:
    - 动态激活/停用 skills
    - 创建组合 skills
    - 运行时切换
    """
    manager = SkillManager()

    # 激活 skills
    manager.activate("speak", voice="robot")
    manager.activate("describe_scene", question="What's in front of me?")

    # 创建组合 skill
    manager.create_composite("respond_to_visual", ["describe_scene", "speak"])

    # 执行组合
    results = await manager.execute_composite(
        "respond_to_visual", image_topic="/camera/front"
    )

    # 动态切换: 根据情况切换不同的 voice
    manager.deactivate("speak")
    manager.activate("speak", voice="friendly")


# ============================================================
# 示例 4: 将现有 Component 封装为 Skill
# ============================================================

from agents.skills import component_to_skill
from agents.components import Vision, LLM
from agents.clients.ollama import OllamaClient
from agents.models import OllamaModel


# 方式 A: 使用装饰器
@component_to_skill(
    Vision,
    name="object_detector",
    description="Detect objects in images",
    input_mapping={"image": "camera"},
    output_mapping={"detections": "objects"},
)
class CustomVisionSkill:
    """使用装饰器自定义 skill 行为"""

    pass


# 方式 B: 使用工厂函数
from agents.skills import create_skill_from_component

vision_skill = create_skill_from_component(
    "vision",
    component_config={
        "inputs": [...],
        "outputs": [...],
        # ... 其他配置
    },
)


# ============================================================
# 示例 5: 定义自定义 Skill
# ============================================================

from agents.skills import BaseSkill, SkillMetadata, SkillResult, SkillStatus


class NavigationSkill(BaseSkill):
    """
    自定义导航 Skill - 展示如何从头定义
    """

    metadata = SkillMetadata(
        name="navigate_to",
        description="Navigate robot to target location",
        inputs={"target": str, "map_topic": str},
        outputs={"success": bool, "position": dict},
    )

    def __init__(self, **kwargs):
        super().__init__()
        self.vla = kwargs.get("vla_component")
        self.vision = kwargs.get("vision_component")

    async def validate_inputs(self, **kwargs) -> bool:
        return "target" in kwargs

    async def execute(self, target: str, map_topic: str = "/map") -> SkillResult:
        try:
            # 1. 获取当前视觉信息
            scene = await self.vision.get_scene()

            # 2. 规划路径
            path = await self.plan_path(target, scene)

            # 3. 执行导航 (使用 VLA)
            success = await self.vla.execute(path)

            return SkillResult(
                status=SkillStatus.SUCCESS,
                output={
                    "success": success,
                    "position": {"x": 1.0, "y": 2.0, "theta": 0.0},
                },
            )
        except Exception as e:
            return SkillResult(status=SkillStatus.FAILED, error=str(e))


# 注册自定义 skill
skill_registry.register("navigate_to", description="Navigate to target location")(
    NavigationSkill
)


# ============================================================
# 示例 6: Self-Referential 动态切换 (Gödel Machines 风格)
# ============================================================


class AdaptiveSkillManager(SkillManager):
    """
    支持自引用逻辑的 Skill 管理器。

    可以根据内部状态动态切换使用的 skills。
    """

    def __init__(self):
        super().__init__()
        self._skill_variants = {}

    def register_variant(self, base_skill: str, condition: str, variant: str):
        """注册 skill 变体"""
        if base_skill not in self._skill_variants:
            self._skill_variants[base_skill] = []
        self._skill_variants[base_skill].append((condition, variant))

    async def execute_adaptive(self, skill_name: str, context: dict, **kwargs):
        """
        根据上下文动态选择最佳 skill 变体执行
        """
        # 选择 variant
        variants = self._skill_variants.get(skill_name, [])

        selected = skill_name  # 默认
        for condition, variant in variants:
            if self._evaluate_condition(condition, context):
                selected = variant
                break

        print(f"Using skill variant: {selected}")
        return await self.execute(selected, **kwargs)

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """评估条件表达式"""
        # 简化版: 支持简单的键值匹配
        # 实际可以使用更复杂的表达式解析
        return context.get(condition.split("=")[0]) == condition.split("=")[1]


async def example_adaptive():
    """自适应 skill 执行示例"""
    manager = AdaptiveSkillManager()

    # 注册变体: 根据电池电量选择不同策略
    manager.register_variant(
        "describe_scene", "battery_low=true", "describe_scene_low_power"
    )
    manager.register_variant(
        "describe_scene", "battery_low=false", "describe_scene_high_quality"
    )

    # 高电量: 使用高质量模型
    result = await manager.execute_adaptive(
        "describe_scene", context={"battery_low": False}, image_topic="/camera/front"
    )

    # 低电量: 使用轻量模型
    result = await manager.execute_adaptive(
        "describe_scene", context={"battery_low": True}, image_topic="/camera/front"
    )


# ============================================================
# 完整示例: 机器人在房间中找到人并打招呼
# ============================================================


async def full_example():
    """
    完整用例:
    1. Vision: 检测人
    2. VLM: 识别是谁
    3. TTS: 打招呼
    """
    from agents.skills import SkillChain

    # 构建 skill 链
    chain = (
        SkillChain()
        # Step 1: 检测人
        .then("skill_vision", image_topic="/camera/head", detect="person")
        # Step 2: 识别
        .then(
            "describe_scene", image_topic="/camera/head", question="Who is this person?"
        )
        # Step 3: 打招呼
        .then("speak", text="Hello {name}!")  # 从上一步获取 name
    )

    results = await chain.execute()

    # 处理结果
    for i, result in enumerate(results):
        print(f"Step {i + 1}: {result.status}")
        if result.output:
            print(f"  Output: {result.output}")


if __name__ == "__main__":
    import asyncio

    # 运行示例
    asyncio.run(example_basic_usage())
