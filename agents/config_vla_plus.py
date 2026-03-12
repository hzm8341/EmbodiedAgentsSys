from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class VLAPlusConfig:
    """VLA+ component configuration"""

    # Model paths
    sam3_model_path: str = "models/sam3/sam3_vit_h.pth"
    qwen3l_model_path: str = "models/qwen3l/qwen3l-7b-instruct"
    device: str = "cuda"

    # Visual processing
    confidence_threshold: float = 0.7
    min_object_size: int = 100
    max_objects: int = 10

    # Grasp planning
    enable_collision_check: bool = True
    collision_margin: float = 0.05
    max_grasp_candidates: int = 5
    grasp_force_limit: float = 20.0

    # Performance
    batch_size: int = 1
    use_half_precision: bool = True
    cache_size: int = 10

    # Debug
    enable_visualization: bool = False
    save_debug_images: bool = False
    debug_image_dir: str = "debug_images"


@dataclass
class SceneUnderstandingConfig:
    """Scene understanding configuration"""

    # Object categories
    object_categories: List[str] = field(default_factory=lambda: [
        "水果", "蔬菜", "工具", "容器", "电子设备",
        "日常用品", "办公用品", "厨房用品"
    ])

    # Attribute detection
    enable_attribute_detection: bool = True
    attribute_categories: List[str] = field(default_factory=lambda: [
        "颜色", "形状", "大小", "材质", "纹理"
    ])

    # Language model
    temperature: float = 0.1
    max_tokens: int = 500
    top_p: float = 0.9
    repetition_penalty: float = 1.1

    # Prompt template
    scene_description_template: str = """
    请描述这个场景中有哪些物体。
    图像中已经分割出{num_objects}个物体。
    用户指令是："{instruction}"

    请按照以下格式输出：
    1. 场景描述：一句话描述场景内容
    2. 物体列表：每个物体包括名称、类别、置信度
    3. 目标物体：用户指令中提到的目标物体
    """
