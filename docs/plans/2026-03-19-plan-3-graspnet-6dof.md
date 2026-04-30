:orphan:

# GraspNet 6DoF Grasp Pose Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `GraspPoseGenerator` 组件，将 RGB-D 图像转换为经过碰撞检测和偏航角过滤的最优 6DoF 抓取姿态，补全当前项目缺失的抓取执行链路。

**Architecture:** `GraspPoseGenerator` 接收 RGB + 深度图 + 对象掩码，输出结构化的 6DoF 抓取姿态列表；包含 GraspNet 推理（可替换 mock）、偏航角约束过滤、与现有 `CollisionChecker` 集成三个阶段。所有坐标以机器人基坐标系表示。

**Tech Stack:** Python 3.10, `numpy`, `open3d`（点云处理）, `graspnetAPI`（可选，可 mock）, 现有 `CollisionChecker`

---

## 文件结构

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `agents/components/grasp_pose_generator.py` | GraspPoseGenerator 主类 |
| Modify | `agents/components/__init__.py` | 导出新组件 |
| Create | `tests/test_grasp_pose_generator.py` | 单元测试 |

---

### Task 1: 定义 GraspPose 数据结构

**Files:**
- Create: `agents/components/grasp_pose_generator.py`
- Test: `tests/test_grasp_pose_generator.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_grasp_pose_generator.py
import numpy as np
import pytest
from agents.components.grasp_pose_generator import GraspPose

def test_grasp_pose_fields():
    pose = GraspPose(
        position={"x": 0.3, "y": 0.1, "z": 0.5},
        rotation_matrix=np.eye(3),
        yaw_deg=-90.0,
        score=0.75,
        collision_free=True,
    )
    assert pose.position["x"] == 0.3
    assert pose.score == 0.75
    assert pose.collision_free is True

def test_grasp_pose_to_dict():
    pose = GraspPose(
        position={"x": 0.1, "y": 0.0, "z": 0.4},
        rotation_matrix=np.eye(3),
        yaw_deg=-90.0,
        score=0.8,
        collision_free=True,
    )
    d = pose.to_dict()
    assert "position" in d
    assert "yaw_deg" in d
    assert d["score"] == 0.8
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_grasp_pose_generator.py -v
```
期望：`FAILED`

- [ ] **Step 3: 实现 GraspPose 数据结构**

```python
# agents/components/grasp_pose_generator.py
"""GraspNet 6DoF 抓取姿态生成器。"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np


@dataclass
class GraspPose:
    """单个 6DoF 抓取姿态，以机器人基坐标系表示。"""
    position: Dict[str, float]       # {"x": ..., "y": ..., "z": ...}
    rotation_matrix: np.ndarray      # 3x3 旋转矩阵
    yaw_deg: float                   # 偏航角（度），相对机器人基坐标系 Z 轴
    score: float                     # GraspNet 质量分数 [0, 1]
    collision_free: bool = True      # 是否通过碰撞检测

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于 ROS 消息或日志）。"""
        return {
            "position": self.position,
            "rotation_matrix": self.rotation_matrix.tolist(),
            "yaw_deg": self.yaw_deg,
            "score": self.score,
            "collision_free": self.collision_free,
        }
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_grasp_pose_generator.py::test_grasp_pose_fields \
       tests/test_grasp_pose_generator.py::test_grasp_pose_to_dict -v
```

- [ ] **Step 5: 提交**

```bash
git add agents/components/grasp_pose_generator.py tests/test_grasp_pose_generator.py
git commit -m "feat: add GraspPose dataclass for 6DoF grasp representation"
```

---

### Task 2: 实现点云生成与偏航角过滤

**Files:**
- Modify: `agents/components/grasp_pose_generator.py`
- Test: `tests/test_grasp_pose_generator.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_grasp_pose_generator.py
from agents.components.grasp_pose_generator import GraspPoseGenerator

def make_test_depth_rgb():
    """创建测试用深度图和 RGB 图。"""
    depth = np.random.uniform(0.3, 1.0, (480, 640)).astype(np.float32)
    rgb = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    mask = np.zeros((480, 640), dtype=np.uint8)
    mask[200:300, 250:350] = 1
    return rgb, depth, mask

def test_depth_to_pointcloud():
    """深度图 → 点云，采样点数在预期范围内。"""
    gen = GraspPoseGenerator(backend="mock")
    rgb, depth, mask = make_test_depth_rgb()
    pcd = gen._depth_to_pointcloud(depth, rgb, mask,
                                   fx=615.0, fy=615.0, cx=320.0, cy=240.0)
    assert pcd.shape[1] == 6        # (N, 6): xyz + rgb
    assert len(pcd) <= 20000

def test_yaw_angle_filter():
    """偏航角过滤：只保留 -120° ~ -60° 范围内的姿态。"""
    gen = GraspPoseGenerator(backend="mock")
    poses = [
        GraspPose({"x": 0, "y": 0, "z": 0.5}, np.eye(3), yaw_deg=-90.0, score=0.9),
        GraspPose({"x": 0, "y": 0, "z": 0.5}, np.eye(3), yaw_deg=0.0, score=0.8),
        GraspPose({"x": 0, "y": 0, "z": 0.5}, np.eye(3), yaw_deg=-110.0, score=0.7),
        GraspPose({"x": 0, "y": 0, "z": 0.5}, np.eye(3), yaw_deg=-170.0, score=0.6),
    ]
    filtered = gen._filter_by_yaw(poses)
    yaws = [p.yaw_deg for p in filtered]
    assert all(-120.0 <= y <= -60.0 for y in yaws)
    assert len(filtered) == 2  # -90 和 -110 在范围内

def test_collision_checker_preserves_extra_fields():
    """验证 CollisionChecker.validate_grasp_points 保留自定义字段（_pose_id 机制的前提）。"""
    from agents.components.collision_checker import CollisionChecker
    cc = CollisionChecker()
    points = [{"position": {"x": 0.1, "y": 0.0, "z": 0.5}, "quality_score": 0.8, "_pose_id": 42}]
    result = cc.validate_grasp_points(points)
    assert result[0]["_pose_id"] == 42  # gp.copy() 必须保留自定义字段

def test_filter_by_collision_marks_flags_and_preserves_identity():
    """碰撞过滤应保留原始对象引用，并正确设置 collision_free 标记。"""
    from agents.components.collision_checker import CollisionChecker
    cc = CollisionChecker(
        workspace_bounds={"x": [-1.0, 1.0], "y": [-1.0, 1.0], "z": [0.0, 1.5]}
    )
    gen = GraspPoseGenerator(backend="mock", collision_checker=cc)
    p_in  = GraspPose({"x": 0.3, "y": 0.0, "z": 0.5}, np.eye(3), yaw_deg=-90.0, score=0.9)
    p_out = GraspPose({"x": 5.0, "y": 0.0, "z": 0.5}, np.eye(3), yaw_deg=-90.0, score=0.8)
    result = gen._filter_by_collision([p_in, p_out])
    assert len(result) == 2  # 保留全部，只打标记
    # 验证对象引用身份：result 中的元素必须是原始对象
    assert p_in in result
    assert p_out in result
    # 验证标记正确
    assert p_in.collision_free is True
    assert p_out.collision_free is False
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_grasp_pose_generator.py -v
```
期望：3 个 `FAILED`（`test_depth_to_pointcloud`、`test_yaw_angle_filter`、`test_filter_by_collision_marks_flags`）

- [ ] **Step 3: 实现点云生成与偏航角过滤**

```python
# 追加到 agents/components/grasp_pose_generator.py
from typing import Literal

YAW_MIN_DEG = -120.0
YAW_MAX_DEG = -60.0
MAX_POINTS = 20000


class GraspPoseGenerator:
    """
    6DoF 抓取姿态生成器。

    流水线：
      RGB-D + 掩码 → 点云 → GraspNet 候选 → 偏航角过滤 → 碰撞检测 → 排序输出

    Args:
        backend: "graspnet" 使用真实模型；"mock" 用于测试
        yaw_min_deg: 偏航角下限（默认 -120°）
        yaw_max_deg: 偏航角上限（默认 -60°）
        collision_checker: 可选 CollisionChecker 实例
    """

    def __init__(
        self,
        backend: Literal["graspnet", "mock"] = "graspnet",
        yaw_min_deg: float = YAW_MIN_DEG,
        yaw_max_deg: float = YAW_MAX_DEG,
        collision_checker=None,
    ):
        self._backend = backend
        self.yaw_min = yaw_min_deg
        self.yaw_max = yaw_max_deg
        self._collision_checker = collision_checker
        self._graspnet = None

        if backend == "graspnet":
            self._load_graspnet()

    def _load_graspnet(self) -> None:
        """懒加载 GraspNet 模型。"""
        try:
            # 实际使用时替换为真实 GraspNet 加载逻辑
            # from graspnetAPI import GraspNet
            pass
        except ImportError:
            self._backend = "mock"

    # ---------- 点云生成 ----------

    def _depth_to_pointcloud(
        self,
        depth: np.ndarray,
        rgb: np.ndarray,
        mask: np.ndarray,
        fx: float, fy: float,
        cx: float, cy: float,
    ) -> np.ndarray:
        """
        将深度图转换为掩码区域的点云（含颜色）。

        Args:
            depth: 深度图 (H, W) float32，单位：米
            rgb: 彩色图 (H, W, 3) uint8
            mask: 对象掩码 (H, W) uint8，非零为目标区域
            fx, fy, cx, cy: 相机内参

        Returns:
            点云数组 (N, 6)，列顺序：x, y, z, r, g, b
        """
        h, w = depth.shape
        ys, xs = np.where(mask > 0)

        if len(xs) == 0:
            return np.zeros((0, 6), dtype=np.float32)

        # 反投影到 3D
        z = depth[ys, xs]
        valid = z > 0
        xs, ys, z = xs[valid], ys[valid], z[valid]

        x3d = (xs - cx) * z / fx
        y3d = (ys - cy) * z / fy

        colors = rgb[ys, xs].astype(np.float32) / 255.0

        points = np.stack([x3d, y3d, z, colors[:, 0], colors[:, 1], colors[:, 2]], axis=1)

        # 随机采样至最大点数
        if len(points) > MAX_POINTS:
            idx = np.random.choice(len(points), MAX_POINTS, replace=False)
            points = points[idx]

        return points.astype(np.float32)

    # ---------- 偏航角过滤 ----------

    def _filter_by_yaw(self, poses: List[GraspPose]) -> List[GraspPose]:
        """过滤偏航角不在可达范围内的抓取姿态。"""
        return [p for p in poses if self.yaw_min <= p.yaw_deg <= self.yaw_max]

    # ---------- 碰撞过滤 ----------

    def _filter_by_collision(self, poses: List[GraspPose]) -> List[GraspPose]:
        """使用 CollisionChecker 标记每个姿态的 collision_free 状态，返回全部姿态。"""
        if not self._collision_checker:
            return poses

        # 用 id(pose) 作为键，确保排序后仍能精确映射回原始 GraspPose 对象
        pose_by_id = {id(p): p for p in poses}
        grasp_points = [
            {"position": p.position, "quality_score": p.score, "_pose_id": id(p)}
            for p in poses
        ]
        # validate_grasp_points 使用 gp.copy()，_pose_id 字段会保留在副本中
        validated = self._collision_checker.validate_grasp_points(grasp_points)

        result = []
        for vp in validated:
            pose = pose_by_id[vp["_pose_id"]]
            pose.collision_free = vp["collision_free"]
            result.append(pose)
        return result

    # ---------- 主接口 ----------

    def generate(
        self,
        rgb: np.ndarray,
        depth: np.ndarray,
        mask: np.ndarray,
        fx: float = 615.0,
        fy: float = 615.0,
        cx: float = 320.0,
        cy: float = 240.0,
    ) -> List[GraspPose]:
        """
        生成过滤后的 6DoF 抓取姿态列表（按质量降序排列）。

        Args:
            rgb: 彩色图 (H, W, 3) uint8
            depth: 深度图 (H, W) float32，单位：米
            mask: 对象掩码 (H, W) uint8
            fx, fy, cx, cy: 相机内参

        Returns:
            GraspPose 列表，collision_free=True 的优先排前面
        """
        pcd = self._depth_to_pointcloud(depth, rgb, mask, fx, fy, cx, cy)

        if len(pcd) == 0:
            return []

        if self._backend == "mock":
            poses = self._mock_grasp(pcd)
        else:
            poses = self._graspnet_infer(pcd)

        # 偏航角过滤
        poses = self._filter_by_yaw(poses)

        # 碰撞过滤
        poses = self._filter_by_collision(poses)

        # 排序：collision_free 优先，再按分数降序
        poses.sort(key=lambda p: (0 if p.collision_free else 1, -p.score))

        return poses

    def _mock_grasp(self, pcd: np.ndarray) -> List[GraspPose]:
        """Mock GraspNet 推理（测试用）。"""
        if len(pcd) == 0:
            return []
        center = pcd[:, :3].mean(axis=0)
        return [
            GraspPose(
                position={"x": float(center[0]), "y": float(center[1]), "z": float(center[2])},
                rotation_matrix=np.eye(3),
                yaw_deg=-90.0,
                score=0.85,
                collision_free=True,
            ),
            GraspPose(
                position={"x": float(center[0] + 0.01), "y": float(center[1]), "z": float(center[2])},
                rotation_matrix=np.eye(3),
                yaw_deg=-75.0,
                score=0.70,
                collision_free=True,
            ),
        ]

    def _graspnet_infer(self, pcd: np.ndarray) -> List[GraspPose]:
        """真实 GraspNet 推理（生产环境）。"""
        # TODO: 接入真实 GraspNet 推理
        # gg = self._graspnet.predict(pcd)
        # return [GraspPose(...) for g in gg]
        return self._mock_grasp(pcd)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_grasp_pose_generator.py -v
```
期望：全部 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add agents/components/grasp_pose_generator.py tests/test_grasp_pose_generator.py
git commit -m "feat: implement GraspPoseGenerator with pointcloud, yaw filter, collision check"
```

---

### Task 3: 集成 CollisionChecker 并写端到端测试

**Files:**
- Test: `tests/test_grasp_pose_generator.py`

- [ ] **Step 1: 写集成测试**

```python
# 追加到 tests/test_grasp_pose_generator.py
from agents.components.collision_checker import CollisionChecker

def test_generate_with_collision_checker():
    """端到端：生成姿态并通过 CollisionChecker 过滤。"""
    cc = CollisionChecker(
        workspace_bounds={"x": [-1.0, 1.0], "y": [-1.0, 1.0], "z": [0.0, 1.5]}
    )
    gen = GraspPoseGenerator(backend="mock", collision_checker=cc)
    rgb, depth, mask = make_test_depth_rgb()
    poses = gen.generate(rgb, depth, mask)
    assert len(poses) >= 1
    # 第一个应为 collision_free
    assert poses[0].collision_free is True

def test_generate_empty_mask_returns_empty():
    """空掩码（无目标区域）应返回空列表。"""
    gen = GraspPoseGenerator(backend="mock")
    rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    depth = np.ones((480, 640), dtype=np.float32) * 0.5
    mask = np.zeros((480, 640), dtype=np.uint8)  # 全空
    poses = gen.generate(rgb, depth, mask)
    assert poses == []

def test_best_pose_has_highest_score():
    """返回的第一个姿态分数应最高（collision_free 相同时）。"""
    gen = GraspPoseGenerator(backend="mock")
    rgb, depth, mask = make_test_depth_rgb()
    poses = gen.generate(rgb, depth, mask)
    if len(poses) >= 2:
        # collision_free 相同时按分数降序
        same_flag = [p for p in poses if p.collision_free == poses[0].collision_free]
        scores = [p.score for p in same_flag]
        assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: 在 Task 2 完成之前运行，确认这些测试尚不存在（FAILED/ERROR）**

```bash
pytest tests/test_grasp_pose_generator.py::test_generate_with_collision_checker \
       tests/test_grasp_pose_generator.py::test_generate_empty_mask_returns_empty \
       tests/test_grasp_pose_generator.py::test_best_pose_has_highest_score -v
```
期望：`ERROR` — test not found（函数尚未写入文件）

> **注意**：Task 2 的实现已覆盖 `collision_checker` 构造参数和 `generate()` 方法。
> Task 3 的测试在追加到文件后，在 Task 2 实现的基础上应直接通过。
> 若 Step 2 输出 `PASSED` 而非 `ERROR`，说明测试已提前添加，继续即可。

- [ ] **Step 3: 追加测试后运行全套验证**

```bash
pytest tests/test_grasp_pose_generator.py tests/test_collision_checker.py -v
```
期望：全部 `PASSED`

- [ ] **Step 4: 导出到 `__init__.py`**

```python
from .grasp_pose_generator import GraspPoseGenerator, GraspPose
```

- [ ] **Step 5: 提交**

```bash
git add agents/components/__init__.py tests/test_grasp_pose_generator.py
git commit -m "feat: integrate GraspPoseGenerator with CollisionChecker, export from components"
```

---

## 验收标准

- [ ] `pytest tests/test_grasp_pose_generator.py -v` 全部通过
- [ ] `gen.generate(rgb, depth, mask)` 空掩码返回 `[]`
- [ ] 偏航角过滤保留 -120° ~ -60° 范围（可通过配置修改）
- [ ] 返回列表：collision_free=True 的姿态排在前面
- [ ] 不影响现有 `test_collision_checker.py`

## 后续接入真实 GraspNet

1. 安装 `graspnetAPI`：`pip install graspnetAPI`
2. 下载 Scale-Balanced-Grasp 权重
3. 替换 `_graspnet_infer()` 中的 TODO 部分
4. 调整相机内参（`fx, fy, cx, cy`）与实际硬件匹配
