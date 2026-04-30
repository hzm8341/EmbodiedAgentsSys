:orphan:

# VLA+ 手动测试手册

**版本**: v1.0
**日期**: 2026-03-13
**适用**: EmbodiedAgentsSys VLA+ 场景理解与抓取 Pipeline

---

## 环境准备

### 1. 确认测试命令

由于项目依赖 ROS2，所有测试必须使用以下命令格式：

```bash
PYTHONPATH=/media/hzm/data_disk/EmbodiedAgentsSys python -m pytest tests/<test_file>.py -v
```

### 2. 运行全部自动化测试（验证基线）

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys

PYTHONPATH=. python -m pytest \
  tests/test_vla_plus_config.py \
  tests/test_data_structures.py \
  tests/test_sam3_segmenter.py \
  tests/test_qwen3l_processor.py \
  tests/test_collision_checker.py \
  tests/test_vla_plus.py \
  -v
```

**预期结果**: `25 passed`

---

## 模块手动测试

### 测试 1：配置系统

```python
# 在项目根目录运行：
# PYTHONPATH=. python

from agents.config_vla_plus import VLAPlusConfig, SceneUnderstandingConfig

# 默认配置
config = VLAPlusConfig()
print(config.sam3_model_path)        # models/sam3/sam3_vit_h.pth
print(config.confidence_threshold)   # 0.7
print(config.enable_collision_check) # True

# 自定义配置
config_cpu = VLAPlusConfig(device="cpu", confidence_threshold=0.5)
print(config_cpu.device)             # cpu

# 场景理解配置
scene_cfg = SceneUnderstandingConfig()
print(scene_cfg.object_categories)   # ['水果', '蔬菜', ...]
print(scene_cfg.temperature)         # 0.1
```

**预期**: 所有 print 输出与注释一致，无报错。

---

### 测试 2：数据结构

```python
import numpy as np
from agents.components.data_structures import ObjectInfo, GraspPoint, GraspCommand, SceneAnalysisResult

# 创建 ObjectInfo
mask = np.zeros((100, 100), dtype=bool)
mask[20:50, 20:50] = True

obj = ObjectInfo(
    name="香蕉",
    category="水果",
    bbox=[0.1, 0.2, 0.5, 0.6],
    mask=mask,
    confidence=0.92,
    attributes={"颜色": "黄色", "形状": "弯曲"}
)
print(obj.name)           # 香蕉
print(obj.to_dict())      # 字典格式输出

# 创建 GraspPoint
gp = GraspPoint(
    position={"x": 0.15, "y": 0.25, "z": 0.30},
    orientation={"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
    quality_score=0.88,
    approach_direction=[0.0, 0.0, -1.0],
    gripper_width=0.05,
    collision_free=True
)
print(gp.quality_score)   # 0.88
print(gp.to_dict())

# 创建 SceneAnalysisResult
result = SceneAnalysisResult(
    detected_objects=[obj],
    segmentation_masks=[mask],
    grasp_candidates=[gp],
    scene_description="桌面上有一根香蕉",
    timestamp=1234567890.0
)
print(result.scene_description)      # 桌面上有一根香蕉
print(len(result.detected_objects))  # 1
```

**预期**: 所有对象正常创建，`to_dict()` 返回字典，无报错。

---

### 测试 3：SAM3 分割器

```python
import numpy as np
import asyncio
from agents.components.sam3_segmenter import SAM3Segmenter, SegmentationResult

# 初始化（使用 cpu，不需要真实模型）
segmenter = SAM3Segmenter(
    model_path="models/sam3/sam3_vit_h.pth",
    device="cpu",
    confidence_threshold=0.5,
    min_object_size=100
)

# 创建测试图像
test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

# 运行分割
async def test_segment():
    result = await segmenter.segment(test_image)
    print(type(result))           # <class 'agents.components.sam3_segmenter.SegmentationResult'>
    print(result.image_size)      # (480, 640)
    print(len(result.masks))      # 分割出的物体数量（mock 模式下通常 1-3 个）
    print(result.scores)          # 置信度列表
    return result

result = asyncio.run(test_segment())
```

**预期**: 返回 `SegmentationResult`，`image_size=(480, 640)`，masks/scores/bboxes 列表非空。

---

### 测试 4：过滤功能验证

```python
from agents.components.sam3_segmenter import SAM3Segmenter
import numpy as np

segmenter = SAM3Segmenter(model_path="test", device="cpu", confidence_threshold=0.7, min_object_size=100)

masks = [np.ones((10, 10)), np.ones((10, 10)), np.ones((10, 10))]
scores = [0.9, 0.4, 0.8]   # 0.4 应被过滤
bboxes = [[0,0,10,10], [0,0,10,10], [0,0,10,10]]

valid = segmenter._filter_results(masks, scores, bboxes)
print(valid)   # [0, 2]  — 索引 1 (score=0.4) 被过滤
```

**预期**: `valid = [0, 2]`，索引 1 被过滤掉。

---

### 测试 5：Qwen3L 处理器

```python
import numpy as np
import asyncio
from agents.components.qwen3l_processor import Qwen3LProcessor

processor = Qwen3LProcessor(
    model_path="models/qwen3l/qwen3l-7b-instruct",
    device="cpu",
    temperature=0.1,
    max_tokens=500
)

# 测试 prompt 构建
seg_result = {
    "masks": [np.zeros((100, 100))],
    "scores": [0.9],
    "bboxes": [[10, 20, 100, 150]]
}
prompt = processor._build_prompt("抓取香蕉", seg_result)
print("抓取香蕉" in prompt)   # True
print("1" in prompt)          # True（1个物体）

# 测试 JSON 解析
response = '{"scene_description": "桌上有香蕉", "objects": [{"name": "香蕉", "category": "水果", "confidence": 0.95, "attributes": {}}], "target_object": "香蕉"}'
parsed = processor._parse_response(response)
print(parsed["scene_description"])        # 桌上有香蕉
print(parsed["objects"][0]["name"])       # 香蕉

# 测试 understand 方法
test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

async def test_understand():
    result = await processor.understand(test_image, seg_result, "抓取香蕉")
    print("objects" in result)            # True
    print("scene_description" in result)  # True
    print(result)
    return result

asyncio.run(test_understand())
```

**预期**: prompt 包含指令文本，JSON 解析正确，`understand()` 返回含 `objects` 和 `scene_description` 的字典。

---

### 测试 6：碰撞检测器

```python
from agents.components.collision_checker import CollisionChecker

checker = CollisionChecker(
    collision_margin=0.02,
    workspace_bounds={"x": [-0.5, 0.5], "y": [-0.5, 0.5], "z": [0.0, 0.8]}
)

# 测试工作空间边界检查
print(checker._check_workspace_bounds({"x": 0.1, "y": 0.1, "z": 0.3}))   # True（在范围内）
print(checker._check_workspace_bounds({"x": 1.0, "y": 0.0, "z": 0.3}))   # False（x 超出范围）
print(checker._check_workspace_bounds({"x": 0.0, "y": 0.0, "z": 0.9}))   # False（z 超出范围）

# 测试抓取点验证
grasp_points = [
    {
        "position": {"x": 0.1, "y": 0.1, "z": 0.3},
        "quality_score": 0.9,
        "approach_direction": [0, 0, -1],
        "gripper_width": 0.05,
        "collision_free": True
    },
    {
        "position": {"x": 2.0, "y": 2.0, "z": 2.0},  # 超出工作空间
        "quality_score": 0.8,
        "approach_direction": [0, 0, -1],
        "gripper_width": 0.05,
        "collision_free": True
    }
]

validated = checker.validate_grasp_points(grasp_points)
for p in validated:
    print(f"位置: {p['position']}, collision_free: {p['collision_free']}")
# 第一个点: collision_free=True
# 第二个点: collision_free=False
```

**预期**: 工作空间内的点 `collision_free=True`，超出范围的点 `collision_free=False`，结果按 collision_free 优先排序。

---

### 测试 7：VLAPlus 主组件（完整 Pipeline）

```python
import numpy as np
import asyncio
from agents.components.vla_plus import VLAPlus, VLAPlusConfig

# 初始化
config = VLAPlusConfig(device="cpu", confidence_threshold=0.5)
vla = VLAPlus(config=config)

# 验证组件未初始化（懒加载）
print(vla._segmenter is None)         # True
print(vla._processor is None)         # True
print(vla._collision_checker is None) # True

# 手动初始化组件
vla._setup_components()
print(vla._segmenter is not None)         # True
print(vla._processor is not None)         # True
print(vla._collision_checker is not None) # True

# 运行完整 pipeline
test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

async def test_pipeline():
    result = await vla.analyze_scene(test_image, "抓取桌上的香蕉")
    print("=== Pipeline 结果 ===")
    print(f"场景描述: {result['scene_description']}")
    print(f"检测物体数: {len(result['objects'])}")
    print(f"目标物体: {result['target_object']}")
    print(f"抓取候选数: {len(result['grasp_candidates'])}")
    for i, gp in enumerate(result['grasp_candidates']):
        print(f"  抓取点 {i+1}: 位置={gp['position']}, 质量={gp['quality_score']:.2f}, 无碰撞={gp['collision_free']}")
    return result

result = asyncio.run(test_pipeline())
```

**预期**: 返回包含 `scene_description`、`objects`、`target_object`、`grasp_candidates` 的字典，抓取候选点有 `collision_free` 标记。

---

## 快速一键测试脚本

将以下内容保存为 `scripts/test_vla_plus_manual.py` 并运行：

```bash
PYTHONPATH=/media/hzm/data_disk/EmbodiedAgentsSys python scripts/test_vla_plus_manual.py
```

```python
#!/usr/bin/env python3
"""VLA+ 手动集成测试脚本"""
import numpy as np
import asyncio
import sys

def check(name, condition, detail=""):
    status = "✅" if condition else "❌"
    print(f"{status} {name}" + (f": {detail}" if detail else ""))
    return condition

async def main():
    print("=== VLA+ 手动集成测试 ===\n")
    passed = 0
    total = 0

    # 1. 配置
    from agents.config_vla_plus import VLAPlusConfig, SceneUnderstandingConfig
    cfg = VLAPlusConfig()
    total += 3
    passed += check("VLAPlusConfig 默认值", cfg.confidence_threshold == 0.7)
    passed += check("VLAPlusConfig collision_check", cfg.enable_collision_check is True)
    scene_cfg = SceneUnderstandingConfig()
    passed += check("SceneUnderstandingConfig 类别", "水果" in scene_cfg.object_categories)

    # 2. 数据结构
    from agents.components.data_structures import ObjectInfo, GraspPoint
    mask = np.zeros((50, 50), dtype=bool)
    obj = ObjectInfo(name="苹果", category="水果", bbox=[0,0,1,1], mask=mask, confidence=0.9, attributes={})
    total += 2
    passed += check("ObjectInfo 创建", obj.name == "苹果")
    passed += check("ObjectInfo to_dict", "name" in obj.to_dict())

    # 3. SAM3 分割
    from agents.components.sam3_segmenter import SAM3Segmenter
    seg = SAM3Segmenter(model_path="test", device="cpu")
    img = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    result = await seg.segment(img)
    total += 2
    passed += check("SAM3 segment 返回结果", result is not None)
    passed += check("SAM3 image_size 正确", result.image_size == (240, 320))

    # 4. Qwen3L 处理器
    from agents.components.qwen3l_processor import Qwen3LProcessor
    proc = Qwen3LProcessor(model_path="test", device="cpu")
    seg_dict = {"masks": [mask], "scores": [0.9], "bboxes": [[0,0,50,50]]}
    understand_result = await proc.understand(img, seg_dict, "抓取苹果")
    total += 2
    passed += check("Qwen3L understand 返回字典", isinstance(understand_result, dict))
    passed += check("Qwen3L 包含 objects", "objects" in understand_result)

    # 5. 碰撞检测
    from agents.components.collision_checker import CollisionChecker
    checker = CollisionChecker()
    total += 2
    passed += check("工作空间内点有效", checker._check_workspace_bounds({"x": 0.1, "y": 0.1, "z": 0.3}))
    passed += check("工作空间外点无效", not checker._check_workspace_bounds({"x": 5.0, "y": 0.0, "z": 0.3}))

    # 6. VLAPlus 完整 pipeline
    from agents.components.vla_plus import VLAPlus, VLAPlusConfig
    vla = VLAPlus(config=VLAPlusConfig(device="cpu"))
    pipeline_result = await vla.analyze_scene(img, "抓取苹果")
    total += 3
    passed += check("Pipeline 返回 scene_description", "scene_description" in pipeline_result)
    passed += check("Pipeline 返回 objects", "objects" in pipeline_result)
    passed += check("Pipeline 返回 grasp_candidates", "grasp_candidates" in pipeline_result)

    print(f"\n=== 结果: {passed}/{total} 通过 ===")
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
```

---

## 常见问题

### Q: 运行时出现 `ros_sugar` 错误
**A**: 使用 `PYTHONPATH=.` 前缀运行，不要直接 `python`：
```bash
PYTHONPATH=/media/hzm/data_disk/EmbodiedAgentsSys python your_script.py
```

### Q: `isinstance(vla.config, VLAPlusConfig)` 返回 False
**A**: 从 `vla_plus` 模块导入 `VLAPlusConfig`，而不是从 `agents.config_vla_plus`：
```python
from agents.components.vla_plus import VLAPlus, VLAPlusConfig  # ✅
# 不要用：from agents.config_vla_plus import VLAPlusConfig     # ❌
```

### Q: pytest 出现 `INTERNALERROR`
**A**: 使用 `--rootdir` 参数避开根目录的旧测试文件：
```bash
PYTHONPATH=. python -m pytest tests/test_vla_plus.py --rootdir=tests -v
```

### Q: 如何替换 mock 模型为真实模型
**A**: 修改以下文件中的 `_load_model()` 方法：
- `agents/components/sam3_segmenter.py` — 替换 `_MockSAM3Model()` 为真实 SAM3 加载
- `agents/components/qwen3l_processor.py` — 替换 `_MockQwen3LModel()` 为 transformers 加载
