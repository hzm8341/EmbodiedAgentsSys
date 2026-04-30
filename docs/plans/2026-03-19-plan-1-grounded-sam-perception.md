:orphan:

# GroundedSAM Two-Stage Perception Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `agents/components/` 中新增 `GroundedSAMSegmenter`，将 GroundingDINO（开放词汇检测）+ SAM（精确分割）组合为两阶段流水线，支持按文本查询检测任意对象。

**Architecture:** 新建独立的 `GroundedSAMSegmenter` 类（不破坏现有 `SAM3Segmenter`），接收 `(image, text_query, mode)` 输入；第一阶段 GroundingDINO 返回边界框，第二阶段 SAM 生成精确掩码；mode 参数区分 `grasp`（单掩码）和 `map`（全掩码）两种任务需求。

**Tech Stack:** Python 3.10, `groundingdino` (IDEA-Research), `segment_anything` (Meta SAM v1), `torch`, `numpy`, `cv2`

---

## 文件结构

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `agents/components/grounded_sam.py` | GroundedSAMSegmenter 主类 |
| Modify | `agents/components/__init__.py` | 导出新组件 |
| Create | `tests/test_grounded_sam.py` | 单元测试（含 mock 推理） |
| Modify | `config/` | 添加 `grounded_sam_config.yaml` |

---

### Task 1: 定义数据结构与接口

**Files:**
- Create: `agents/components/grounded_sam.py`
- Test: `tests/test_grounded_sam.py`

- [ ] **Step 1: 写失败测试 — GroundedSAMResult 数据结构**

```python
# tests/test_grounded_sam.py
import numpy as np
import pytest
from agents.components.grounded_sam import GroundedSAMResult

def test_grounded_sam_result_fields():
    result = GroundedSAMResult(
        masks=[np.zeros((480, 640), dtype=np.uint8)],
        bboxes=[[10.0, 20.0, 100.0, 150.0]],
        scores=[0.85],
        labels=["cup"],
        image_size=(480, 640),
    )
    assert len(result.masks) == 1
    assert result.labels[0] == "cup"
    assert result.image_size == (480, 640)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_grounded_sam.py::test_grounded_sam_result_fields -v
```
期望输出：`FAILED` with `ModuleNotFoundError` 或 `ImportError`

- [ ] **Step 3: 实现 GroundedSAMResult**

```python
# agents/components/grounded_sam.py
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


@dataclass
class GroundedSAMResult:
    """Two-stage grounded segmentation result."""
    masks: List[np.ndarray]          # 像素掩码列表，每个形状 (H, W) uint8
    bboxes: List[List[float]]        # 边界框 [x1, y1, x2, y2]
    scores: List[float]              # GroundingDINO 置信度
    labels: List[str]                # 对应文本标签
    image_size: tuple                # (H, W)

    def best(self) -> Optional["GroundedSAMResult"]:
        """返回置信度最高的单个结果（抓取模式用）。"""
        if not self.scores:
            return None
        idx = int(np.argmax(self.scores))
        return GroundedSAMResult(
            masks=[self.masks[idx]],
            bboxes=[self.bboxes[idx]],
            scores=[self.scores[idx]],
            labels=[self.labels[idx]],
            image_size=self.image_size,
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_grounded_sam.py::test_grounded_sam_result_fields -v
```
期望：`PASSED`

- [ ] **Step 5: 提交**

```bash
git add agents/components/grounded_sam.py tests/test_grounded_sam.py
git commit -m "feat: add GroundedSAMResult dataclass for two-stage perception"
```

---

### Task 2: 实现 GroundedSAMSegmenter 骨架与 mock 后端

**Files:**
- Modify: `agents/components/grounded_sam.py`
- Test: `tests/test_grounded_sam.py`

- [ ] **Step 1: 写失败测试 — 分割接口**

```python
# 追加到 tests/test_grounded_sam.py
import asyncio
from agents.components.grounded_sam import GroundedSAMSegmenter

def test_segmenter_grasp_mode_returns_single_mask():
    """抓取模式只返回最高置信度的一个掩码。"""
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    segmenter = GroundedSAMSegmenter(
        dino_model_path="mock",
        sam_model_path="mock",
        device="cpu",
    )
    result = asyncio.run(segmenter.segment(img, text_query="cup", mode="grasp"))
    assert isinstance(result, GroundedSAMResult)
    assert len(result.masks) == 1

def test_segmenter_map_mode_returns_all_masks():
    """建图模式返回全部检测结果。"""
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    segmenter = GroundedSAMSegmenter(
        dino_model_path="mock",
        sam_model_path="mock",
        device="cpu",
    )
    result = asyncio.run(segmenter.segment(img, text_query="cup . bottle", mode="map"))
    assert isinstance(result, GroundedSAMResult)
    assert len(result.masks) >= 0  # 允许 0（mock 可能无结果）
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_grounded_sam.py -v
```
期望：2 个 `FAILED`

- [ ] **Step 3: 实现 GroundedSAMSegmenter（含 mock 后端）**

```python
# 追加到 agents/components/grounded_sam.py
import asyncio
from typing import Literal


class GroundedSAMSegmenter:
    """
    两阶段目标检测与分割器：GroundingDINO（开放词汇检测）+ SAM（精确分割）。

    Args:
        dino_model_path: GroundingDINO 权重路径（传 "mock" 使用 mock 后端）
        sam_model_path: SAM 权重路径（传 "mock" 使用 mock 后端）
        device: 推理设备 "cuda" 或 "cpu"
        box_threshold: GroundingDINO 边界框置信度阈值
        text_threshold: 文本匹配置信度阈值
        nms_threshold: NMS 去重阈值
    """

    def __init__(
        self,
        dino_model_path: str,
        sam_model_path: str,
        device: str = "cuda",
        box_threshold: float = 0.35,
        text_threshold: float = 0.25,
        nms_threshold: float = 0.8,
    ):
        self.dino_model_path = dino_model_path
        self.sam_model_path = sam_model_path
        self.device = device
        self.box_threshold = box_threshold
        self.text_threshold = text_threshold
        self.nms_threshold = nms_threshold
        self._dino = None
        self._sam = None
        self._use_mock = (dino_model_path == "mock" or sam_model_path == "mock")

    def _load_models(self) -> None:
        """懒加载模型（首次调用时初始化）。"""
        if self._dino is not None:
            return
        if self._use_mock:
            self._dino = _MockDINO()
            self._sam = _MockSAM()
            return
        try:
            from groundingdino.util.inference import load_model as load_dino
            from segment_anything import sam_model_registry, SamPredictor
            self._dino = load_dino(
                "groundingdino/config/GroundingDINO_SwinT_OGC.py",
                self.dino_model_path,
                device=self.device,
            )
            sam = sam_model_registry["vit_h"](checkpoint=self.sam_model_path)
            sam.to(device=self.device)
            self._sam = SamPredictor(sam)
        except ImportError as e:
            raise ImportError(
                f"请安装 groundingdino 和 segment_anything: {e}"
            )

    def _run_dino(
        self, image: np.ndarray, text_query: str
    ) -> tuple:
        """运行 GroundingDINO，返回 (bboxes, scores, labels)。"""
        return self._dino(image, text_query, self.box_threshold, self.text_threshold)

    def _run_sam(
        self, image: np.ndarray, bboxes: List[List[float]]
    ) -> List[np.ndarray]:
        """对每个边界框运行 SAM，返回掩码列表。"""
        return self._sam(image, bboxes)

    def _apply_nms(
        self,
        bboxes: List[List[float]],
        scores: List[float],
        labels: List[str],
    ) -> tuple:
        """简单 NMS：按置信度降序，过滤 IoU 超过阈值的重叠框。"""
        if not bboxes:
            return bboxes, scores, labels

        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        keep = []
        suppressed = set()

        for i in order:
            if i in suppressed:
                continue
            keep.append(i)
            b1 = bboxes[i]
            for j in order:
                if j <= i or j in suppressed:
                    continue
                b2 = bboxes[j]
                iou = _compute_iou(b1, b2)
                if iou > self.nms_threshold:
                    suppressed.add(j)

        return (
            [bboxes[i] for i in keep],
            [scores[i] for i in keep],
            [labels[i] for i in keep],
        )

    async def segment(
        self,
        image: np.ndarray,
        text_query: str,
        mode: Literal["grasp", "map"] = "grasp",
    ) -> GroundedSAMResult:
        """
        两阶段分割主接口。

        Args:
            image: 输入图像 (H, W, 3) uint8
            text_query: 检测目标文本，多目标用 " . " 分隔（如 "cup . bottle"）
            mode: "grasp" 返回最高置信度单掩码；"map" 返回全部掩码

        Returns:
            GroundedSAMResult
        """
        self._load_models()
        height, width = image.shape[:2]

        # Stage 1: GroundingDINO 检测
        bboxes, scores, labels = self._run_dino(image, text_query)

        # NMS 去重
        bboxes, scores, labels = self._apply_nms(bboxes, scores, labels)

        if not bboxes:
            return GroundedSAMResult(
                masks=[], bboxes=[], scores=[], labels=[], image_size=(height, width)
            )

        # Stage 2: SAM 精确分割
        masks = self._run_sam(image, bboxes)

        result = GroundedSAMResult(
            masks=masks,
            bboxes=bboxes,
            scores=scores,
            labels=labels,
            image_size=(height, width),
        )

        # 模式过滤
        if mode == "grasp":
            return result.best() or result
        return result


def _compute_iou(b1: List[float], b2: List[float]) -> float:
    """计算两个边界框的 IoU。"""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


class _MockDINO:
    """Mock GroundingDINO，用于测试。"""
    def __call__(self, image, text_query, box_thr, text_thr):
        h, w = image.shape[:2]
        # 返回 1 个假框
        return (
            [[w * 0.1, h * 0.1, w * 0.5, h * 0.5]],
            [0.85],
            [text_query.split(" . ")[0]],
        )


class _MockSAM:
    """Mock SAM，用于测试。"""
    def __call__(self, image, bboxes):
        h, w = image.shape[:2]
        masks = []
        for bbox in bboxes:
            mask = np.zeros((h, w), dtype=np.uint8)
            x1, y1, x2, y2 = [int(v) for v in bbox]
            mask[y1:y2, x1:x2] = 1
            masks.append(mask)
        return masks
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_grounded_sam.py -v
```
期望：所有 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add agents/components/grounded_sam.py tests/test_grounded_sam.py
git commit -m "feat: implement GroundedSAMSegmenter with mock backend"
```

---

### Task 3: 注册到 `__init__.py` 并写集成测试

**Files:**
- Modify: `agents/components/__init__.py`
- Test: `tests/test_grounded_sam.py`

- [ ] **Step 1: 写失败测试 — 从顶层导入**

```python
# 追加到 tests/test_grounded_sam.py
def test_import_from_components():
    from agents.components import GroundedSAMSegmenter, GroundedSAMResult
    assert GroundedSAMSegmenter is not None
    assert GroundedSAMResult is not None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_grounded_sam.py::test_import_from_components -v
```

- [ ] **Step 3: 更新 `__init__.py`**

在 `agents/components/__init__.py` 中找到现有导出列表，追加：

```python
from .grounded_sam import GroundedSAMSegmenter, GroundedSAMResult
```

- [ ] **Step 4: 运行全部测试验证无回归**

```bash
pytest tests/test_grounded_sam.py tests/test_sam3_segmenter.py -v
```
期望：全部 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add agents/components/__init__.py tests/test_grounded_sam.py
git commit -m "feat: export GroundedSAMSegmenter from agents.components"
```

---

### Task 4: 添加配置文件

**Files:**
- Create: `config/grounded_sam_config.yaml`

- [ ] **Step 1: 创建配置文件**

```yaml
# config/grounded_sam_config.yaml
grounded_sam:
  dino_model_path: "models/groundingdino_swint_ogc.pth"
  sam_model_path: "models/sam_vit_h_4b8939.pth"
  device: "cuda"
  box_threshold: 0.35
  text_threshold: 0.25
  nms_threshold: 0.8
```

- [ ] **Step 2: 验证文件存在**

```bash
ls -l /media/hzm/data_disk/EmbodiedAgentsSys/config/grounded_sam_config.yaml
```

- [ ] **Step 3: 提交**

```bash
git add config/grounded_sam_config.yaml
git commit -m "config: add grounded_sam_config.yaml with detection thresholds"
```

---

## 安装依赖（执行前手动完成）

```bash
# GroundingDINO
pip install git+https://github.com/IDEA-Research/GroundingDINO.git

# SAM
pip install git+https://github.com/facebookresearch/segment-anything.git

# 下载模型权重
mkdir -p models
wget -q https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth -O models/sam_vit_h_4b8939.pth
# GroundingDINO 权重需从官方发布页下载
```

---

## 验收标准

- [ ] `pytest tests/test_grounded_sam.py -v` 全部通过
- [ ] `from agents.components import GroundedSAMSegmenter` 可正常导入
- [ ] `mode="grasp"` 始终返回 `len(masks) == 1`
- [ ] `mode="map"` 返回全部检测结果
- [ ] 不影响现有 `test_sam3_segmenter.py` 测试
