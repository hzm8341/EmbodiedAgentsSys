:orphan:

# Airship Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 AIRSHIP 机器人软件栈的所有功能模块（感知、抓取、导航、规划器、物体地图、语音交互）封装为 EmbodiedAgentsSys 的 Skill 组件，实现硬件抽象和混合 ROS/Python 模式。

**Architecture:** 采用 Adapter 模式封装各模块，上层通过统一 Skill 接口调用，下层通过硬件抽象层适配不同平台。保留 ROS2 客户端支持，同时提供纯 Python 实现。

**Tech Stack:** Python 3.10+, ROS2 Humble, GroundingDINO, SAM, GraspNet, Navigation2, Ollama

---

## 阶段 1: 架构设计（基础设施）

### Task 1: 创建 Airship Skill 基础架构

**Files:**
- Create: `skills/airship/__init__.py`
- Create: `skills/airship/base.py` - 基础适配器类
- Create: `skills/airship/config.py` - 配置管理
- Create: `skills/airship/hardware_abstraction.py` - 硬件抽象层

**Step 1: 创建目录结构**

```bash
mkdir -p skills/airship
```

**Step 2: 创建基础适配器类**

```python
# skills/airship/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class AirshipModuleBase(ABC):
    """AIRSHIP 模块基类"""
    
    config: BaseModel
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化模块"""
        pass
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """执行模块功能"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭模块"""
        pass

class HardwareBackend(ABC):
    """硬件后端抽象"""
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        pass
```

**Step 3: 创建硬件抽象层**

```python
# skills/airship/hardware_abstraction.py
from enum import Enum
from typing import Optional

class HardwareType(Enum):
    ROS2 = "ros2"
    PYTHON = "python"
    HYBRID = "hybrid"

class HardwareFactory:
    @staticmethod
    def create_backend(hw_type: HardwareType, config: dict):
        if hw_type == HardwareType.ROS2:
            from .backends.ros2_backend import ROS2Backend
            return ROS2Backend(config)
        elif hw_type == HardwareType.PYTHON:
            from .backends.python_backend import PythonBackend
            return PythonBackend(config)
        # ... etc
```

**Step 4: 创建配置类**

```python
# skills/airship/config.py
from pydantic import BaseModel
from typing import Optional, List

class AirshipConfig(BaseModel):
    hardware_type: str = "hybrid"
    use_ros: bool = True
    # 感知配置
    perception_model_path: Optional[str] = None
    groundingdino_model: str = "groundingdino_swint_ogc"
    sam_model: str = "sam_vit_h"
    # 抓取配置
    graspnet_model_path: Optional[str] = None
    # 导航配置
    nav_map_path: Optional[str] = None
    # LLM 配置
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1:70b"
    llm_url: str = "http://localhost:11434"
    # 语音配置
    whisper_model: str = "base"
    tts_provider: str = "edge"
```

**Step 5: 提交**

```bash
git add skills/airship/
git commit -m "feat(airship): create base architecture for airship skill integration"
```

---

### Task 2: 创建统一的 Airship Skill 接口

**Files:**
- Create: `skills/airship/skill.py` - 主 Skill 类
- Create: `skills/airship/backends/__init__.py`

**Step 1: 创建主 Skill 类**

```python
# skills/airship/skill.py
from typing import Any, Dict
from datetime import datetime

class AirshipSkill:
    """AIRSHIP 统一 Skill 接口"""
    
    name = "airship"
    description = "AIRSHIP 机器人集成 - 感知、抓取、导航、规划、语音"
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._perception = None
        self._grasp = None
        self._navigation = None
        self._planner = None
        self._object_map = None
        self._voice = None
    
    async def initialize(self) -> bool:
        """初始化所有子模块"""
        # 延迟导入和初始化各模块
        from .perception import AirshipPerception
        from .grasp import AirshipGrasp
        from .navigation import AirshipNavigation
        from .planner import AirshipPlanner
        from .object_map import AirshipObjectMap
        from .voice import AirshipVoice
        
        self._perception = AirshipPerception(self.config)
        self._grasp = AirshipGrasp(self.config)
        self._navigation = AirshipNavigation(self.config)
        self._planner = AirshipPlanner(self.config)
        self._object_map = AirshipObjectMap(self.config)
        self._voice = AirshipVoice(self.config)
        
        return True
    
    async def execute(self, command: str, **kwargs) -> Dict[str, Any]:
        """执行自然语言命令"""
        # 解析命令并路由到对应模块
        pass
    
    @property
    def perception(self):
        return self._perception
    
    @property
    def grasp(self):
        return self._grasp
    
    # ... 其他属性
```

**Step 2: 创建 backends 目录**

```bash
mkdir -p skills/airship/backends
touch skills/airship/backends/__init__.py
```

**Step 3: 提交**

```bash
git add skills/airship/
git commit -m "feat(airship): create unified airship skill interface"
```

---

## 阶段 2: 感知模块 (Perception)

### Task 3: 实现 Airship Perception Skill

**Files:**
- Create: `skills/airship/perception.py`
- Create: `skills/airship/backends/perception_backend.py`
- Test: `tests/test_airship_perception.py`

**Step 1: 编写测试**

```python
# tests/test_airship_perception.py
import pytest
from skills.airship.perception import AirshipPerception
from skills.airship.config import AirshipConfig

@pytest.fixture
def perception_config():
    return AirshipConfig(
        groundingdino_model="groundingdino_swint_ogc",
        sam_model="sam_vit_h",
    )

@pytest.mark.asyncio
async def test_perception_init(perception_config):
    perception = AirshipPerception(perception_config)
    result = await perception.initialize()
    assert result == True

@pytest.mark.asyncio
async def test_detect_objects(perception_config):
    perception = AirshipPerception(perception_config)
    await perception.initialize()
    # 模拟图像输入
    dummy_image = None  # 需要真实图像或 mock
    result = await perception.detect("cup", dummy_image)
    assert "masks" in result or "boxes" in result
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/test_airship_perception.py -v
# Expected: FAIL - 模块未实现
```

**Step 3: 实现感知模块**

```python
# skills/airship/perception.py
from typing import Any, Dict, List, Optional
import numpy as np

class AirshipPerception:
    """AIRSHIP 感知模块 - 目标检测与分割"""
    
    def __init__(self, config):
        self.config = config
        self._groundingdino = None
        self._sam = None
    
    async def initialize(self) -> bool:
        """初始化 GroundingDINO + SAM"""
        try:
            from .backends.perception_backend import GroundingDINOSAMBackend
            self._backend = GroundingDINOSAMBackend(self.config)
            return await self._backend.load_models()
        except ImportError as e:
            print(f"Warning: Perception backend not available: {e}")
            return False
    
    async def detect(
        self, 
        object_name: str, 
        image: np.ndarray,
        threshold: float = 0.3
    ) -> Dict[str, Any]:
        """检测目标"""
        if not self._backend:
            raise RuntimeError("Perception not initialized")
        
        # 使用 GroundingDINO 获取边界框
        boxes = await self._backend.detect_box(image, object_name)
        
        # 使用 SAM 生成掩码
        masks = await self._backend.segment(image, boxes)
        
        return {
            "boxes": boxes,
            "masks": masks,
            "object_name": object_name
        }
    
    async def segment(
        self,
        image: np.ndarray,
        points: Optional[List] = None,
        box: Optional[List] = None
    ) -> np.ndarray:
        """分割"""
        return await self._backend.segment(image, points=points, box=box)
```

**Step 4: 实现后端**

```python
# skills/airship/backends/perception_backend.py
import torch
from typing import Any, Dict, List, Optional
import numpy as np

class GroundingDINOSAMBackend:
    """GroundingDINO + SAM 后端"""
    
    def __init__(self, config):
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.groundingdino = None
        self.sam = None
    
    async def load_models(self) -> bool:
        """加载模型"""
        # GroundingDINO
        from groundingdino.models import build_model
        self.groundingdino = build_model(
            torch.load(self.config.groundingdino_model, map_location=self.device)
        )
        
        # SAM
        from segment_anything import sam_model_registry
        self.sam = sam_model_registry["vit_h"](
            checkpoint=self.config.sam_model
        ).to(self.device)
        
        return True
    
    async def detect_box(self, image, text_prompt):
        """检测边界框"""
        # 实现 GroundingDINO 推理
        pass
    
    async def segment(self, image, boxes=None, points=None):
        """SAM 分割"""
        # 实现 SAM 推理
        pass
```

**Step 5: 运行测试验证通过**

```bash
pytest tests/test_airship_perception.py -v
# Expected: PASS (或 SKIP 如果没有模型权重)
```

**Step 6: 提交**

```bash
git add skills/airship/perception.py skills/airship/backends/perception_backend.py tests/test_airship_perception.py
git commit -m "feat(airship): add perception module with GroundingDINO + SAM"
```

---

## 阶段 3: 抓取模块 (Grasp)

### Task 4: 实现 Airship Grasp Skill

**Files:**
- Create: `skills/airship/grasp.py`
- Create: `skills/airship/backends/grasp_backend.py`
- Test: `tests/test_airship_grasp.py`

**Step 1: 编写测试**

```python
# tests/test_airship_grasp.py
import pytest
from skills.airship.grasp import AirshipGrasp
from skills.airship.config import AirshipConfig
import numpy as np

@pytest.fixture
def grasp_config():
    return AirshipConfig()

@pytest.mark.asyncio
async def test_grasp_init(grasp_config):
    grasp = AirshipGrasp(grasp_config)
    result = await grasp.initialize()
    assert result == True

@pytest.mark.asyncio
async def test_compute_grasp(grasp_config):
    grasp = AirshipGrasp(grasp_config)
    await grasp.initialize()
    
    # 模拟 RGBD 图像
    rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    depth = np.zeros((480, 640), dtype=np.float32)
    mask = np.zeros((480, 640), dtype=bool)
    
    result = await grasp.compute_grasp(rgb, depth, mask, "cup")
    assert "pose" in result or "grasps" in result
```

**Step 2: 运行测试**

```bash
pytest tests/test_airship_grasp.py -v
# Expected: FAIL
```

**Step 3: 实现抓取模块**

```python
# skills/airship/grasp.py
from typing import Any, Dict, List
import numpy as np

class AirshipGrasp:
    """AIRSHIP 抓取模块 - GraspNet + 机械臂控制"""
    
    def __init__(self, config):
        self.config = config
        self._backend = None
        self._arm_controller = None
    
    async def initialize(self) -> bool:
        from .backends.grasp_backend import GraspNetBackend
        self._backend = GraspNetBackend(self.config)
        return await self._backend.load_models()
    
    async def compute_grasp(
        self,
        rgb: np.ndarray,
        depth: np.ndarray,
        mask: np.ndarray,
        object_name: str
    ) -> Dict[str, Any]:
        """计算抓取姿态"""
        # 1. 使用 GraspNet 生成候选抓取
        candidates = await self._backend.predict(rgb, depth, mask)
        
        # 2. 过滤目标物体的抓取
        filtered = self._filter_grasps(candidates, object_name)
        
        # 3. 选择最优抓取
        best = self._select_best_grasp(filtered)
        
        return {
            "pose": best["pose"],
            "score": best["score"],
            "approach_angle": best.get("approach_angle", 0)
        }
    
    async def execute_grasp(self, pose: Dict[str, Any]) -> bool:
        """执行抓取"""
        # 移动机械臂到抓取姿态
        # 闭合夹爪
        # 抬起
        pass
    
    def _filter_grasps(self, candidates, object_name):
        # 根据物体名称过滤
        pass
    
    def _select_best_grasp(self, candidates):
        # 选择得分最高的抓取
        pass
```

**Step 4: 实现后端**

```python
# skills/airship/backends/grasp_backend.py
import torch
import numpy as np
from typing import Any, List, Dict

class GraspNetBackend:
    """GraspNet 后端"""
    
    def __init__(self, config):
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
    
    async def load_models(self) -> bool:
        """加载 GraspNet 模型"""
        # 加载 Scale-Balanced-Grasp 模型
        # 或者 graspnetAPI
        pass
    
    async def predict(
        self,
        rgb: np.ndarray,
        depth: np.ndarray,
        mask: np.ndarray
    ) -> List[Dict[str, Any]]:
        """预测抓取"""
        # 预处理
        # 推理
        # 后处理
        pass
```

**Step 5: 测试并提交**

```bash
pytest tests/test_airship_grasp.py -v
git add skills/airship/grasp.py skills/airship/backends/grasp_backend.py tests/test_airship_grasp.py
git commit -m "feat(airship): add grasp module with GraspNet"
```

---

## 阶段 4: 导航模块 (Navigation)

### Task 5: 实现 Airship Navigation Skill

**Files:**
- Create: `skills/airship/navigation.py`
- Create: `skills/airship/backends/nav_backend.py`
- Test: `tests/test_airship_navigation.py`

**Step 1-5: 类似前面的模式**

导航模块需要实现：
- 定位 (Localization)
- 路径规划 (Path Planning)
- 底盘控制 (Base Control)

```python
# skills/airship/navigation.py
class AirshipNavigation:
    """AIRSHIP 导航模块"""
    
    async def initialize(self) -> bool:
        from .backends.nav_backend import NavBackend
        self._backend = NavBackend(self.config)
        return await self._backend.start()
    
    async def navigate_to(
        self,
        x: float,
        y: float,
        theta: float = 0.0
    ) -> bool:
        """导航到目标位置"""
        return await self._backend.navigate(x, y, theta)
    
    async def get_pose(self) -> Dict[str, float]:
        """获取当前位置"""
        return await self._backend.get_pose()
```

**提交**

```bash
git add skills/airship/navigation.py skills/airship/backends/nav_backend.py tests/test_airship_navigation.py
git commit -m "feat(airship): add navigation module"
```

---

## 阶段 5: 规划器模块 (Planner)

### Task 6: 实现 Airship Planner Skill

**Files:**
- Create: `skills/airship/planner.py`
- Test: `tests/test_airship_planner.py`

**Step 1: 编写测试**

```python
# tests/test_airship_planner.py
@pytest.mark.asyncio
async def test_planner_init():
    from skills.airship.planner import AirshipPlanner
    planner = AirshipPlanner(config)
    await planner.initialize()
    assert planner.llm is not None

@pytest.mark.asyncio
async def test_plan_task():
    planner = AirshipPlanner(config)
    await planner.initialize()
    
    result = await planner.plan("Bring me a cup from the table")
    assert "steps" in result or "actions" in result
```

**Step 2: 实现规划器**

```python
# skills/airship/planner.py
from typing import Any, Dict, List
import json

class AirshipPlanner:
    """AIRSHIP LLM 任务规划器"""
    
    SYSTEM_PROMPT = """You are a robot task planner. 
Given a human instruction, break it down into atomic robot actions.
Available actions: navigation, grasp, place, detect, speak.
Output format: JSON array of actions."""

    def __init__(self, config):
        self.config = config
        self.llm = None
        self.history = []
    
    async def initialize(self) -> bool:
        """初始化 LLM"""
        from agents.clients.ollama import OllamaClient
        self.llm = OllamaClient(
            model=self.config.llm_model,
            base_url=self.config.llm_url
        )
        return True
    
    async def plan(self, instruction: str) -> Dict[str, Any]:
        """将指令分解为动作序列"""
        prompt = f"{self.SYSTEM_PROMPT}\n\nInstruction: {instruction}"
        
        response = await self.llm.chat(prompt)
        
        # 解析 JSON 响应
        try:
            actions = json.loads(response)
        except:
            # 如果不是 JSON，尝试提取
            actions = self._parse_response(response)
        
        return {
            "instruction": instruction,
            "actions": actions,
            "llm_response": response
        }
    
    def _parse_response(self, response: str) -> List[Dict]:
        # 解析非 JSON 格式的响应
        pass
```

**Step 3: 测试并提交**

```bash
pytest tests/test_airship_planner.py -v
git add skills/airship/planner.py tests/test_airship_planner.py
git commit -m "feat(airship): add LLM task planner"
```

---

## 阶段 6: 物体地图模块 (Object Map)

### Task 7: 实现 Airship Object Map Skill

**Files:**
- Create: `skills/airship/object_map.py`
- Test: `tests/test_airship_object_map.py`

**功能:**
- 维护语义地图（物体名称 -> 位置映射）
- 保存/加载导航目标
- 物体定位

```python
# skills/airship/object_map.py
class AirshipObjectMap:
    """AIRSHIP 语义地图模块"""
    
    def __init__(self, config):
        self.objects = {}  # name -> position
        self.nav_goals = {}
    
    async def add_object(self, name: str, position: Dict[str, float]) -> None:
        """添加物体位置"""
        self.objects[name] = position
    
    async def find_object(self, name: str) -> Optional[Dict[str, float]]:
        """查找物体位置"""
        return self.objects.get(name)
    
    async def save_nav_goal(self, name: str, x: float, y: float, theta: float) -> None:
        """保存导航目标"""
        self.nav_goals[name] = {"x": x, "y": y, "theta": theta}
    
    async def get_nav_goal(self, name: str) -> Optional[Dict[str, float]]:
        """获取导航目标"""
        return self.nav_goals.get(name)
```

**提交**

```bash
git add skills/airship/object_map.py tests/test_airship_object_map.py
git commit -m "feat(airship): add object map module"
```

---

## 阶段 7: 语音交互模块 (Voice)

### Task 8: 实现 Airship Voice Skill

**Files:**
- Create: `skills/airship/voice.py`
- Test: `tests/test_airship_voice.py`

**功能:**
- 语音识别 (STT)
- 语音合成 (TTS)
- 语音对话

```python
# skills/airship/voice.py
class AirshipVoice:
    """AIRSHIP 语音交互模块"""
    
    def __init__(self, config):
        self.config = config
        self.stt = None
        self.tts = None
    
    async def initialize(self) -> bool:
        from .backends.stt_backend import WhisperSTT
        from .backends.tts_backend import EdgeTTS
        self.stt = WhisperSTT(self.config)
        self.tts = EdgeTTS(self.config)
        return True
    
    async def listen(self) -> str:
        """语音识别"""
        audio = await self._capture_audio()
        return await self.stt.transcribe(audio)
    
    async def speak(self, text: str) -> None:
        """语音合成"""
        audio = await self.tts.synthesize(text)
        await self._play_audio(audio)
```

**提交**

```bash
git add skills/airship/voice.py tests/test_airship_voice.py
git commit -m "feat(airship): add voice interaction module"
```

---

## 阶段 8: 集成测试

### Task 9: 端到端集成测试

**Files:**
- Create: `tests/test_airship_integration.py`

**Step 1: 编写集成测试**

```python
# tests/test_airship_integration.py
@pytest.mark.asyncio
async def test_full_task_execution():
    """测试完整任务：理解指令 -> 规划 -> 执行"""
    from skills.airship import AirshipSkill
    from skills.airship.config import AirshipConfig
    
    config = AirshipConfig(
        hardware_type="python",  # 使用模拟后端
        use_ros=False
    )
    
    skill = AirshipSkill(config)
    await skill.initialize()
    
    # 测试：去桌子那里拿杯子
    result = await skill.execute("Go to the table and bring me the cup")
    
    assert result["status"] in ["success", "completed", "partial"]
    # 验证执行了正确的动作序列
```

**Step 2: 运行集成测试**

```bash
pytest tests/test_airship_integration.py -v
```

**Step 3: 提交**

```bash
git add tests/test_airship_integration.py
git commit -m "test(airship): add integration tests"
```

---

## 阶段 9: 文档与示例

### Task 10: 编写使用文档

**Files:**
- Create: `docs/airship_skill_usage.md`

**内容:**
- 安装依赖
- 配置说明
- 使用示例
- API 文档

**提交**

```bash
git add docs/airship_skill_usage.md
git commit -m "docs(airship): add usage documentation"
```

---

## 执行顺序建议

1. **Task 1-2**: 基础架构（必须先完成）
2. **Task 3**: 感知模块
3. **Task 4**: 抓取模块
4. **Task 5**: 导航模块
5. **Task 6**: 规划器模块（关键依赖其他模块）
6. **Task 7**: 物体地图
7. **Task 8**: 语音模块
8. **Task 9**: 集成测试
9. **Task 10**: 文档

---

## 关键依赖

```yaml
# requirements-airship.txt
torch>=2.0.0
torchvision
transformers
groundingdino
segment-anything
graspnetAPI
pymycobot
numpy
opencv-python
open3d
pydantic
```

---

**Plan complete and saved to `docs/plans/2026-03-06-airship-integration.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
