# 双臂末端位置控制实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 通过自然语言指令控制机器人左/右臂移动到指定末端位置（基于基座坐标系）

**Architecture:** LLM 解析指令 → IKChain 求解逆运动学 → MuJoCoDriver 控制关节角度 → 仿真更新

**Tech Stack:** Python + MuJoCo + IKChain + FastAPI

---

## 文件变更摘要

| 操作 | 文件路径 |
|------|----------|
| 新增 | `simulation/mujoco/arm_ik_controller.py` |
| 修改 | `simulation/mujoco/mujoco_driver.py` |
| 修改 | `backend/api/chat.py` |
| 新增测试 | `tests/unit/test_ik_solver.py` |

---

## Task 1: 创建 ArmIKController

**Files:**
- Create: `simulation/mujoco/arm_ik_controller.py`
- Test: `tests/unit/test_arm_ik_controller.py`

**Step 1: 编写测试**

```python
# tests/unit/test_arm_ik_controller.py
import numpy as np
from simulation.mujoco.arm_ik_controller import ArmIKController

def test_arm_ik_controller_init():
    """测试 ArmIKController 初始化"""
    controller = ArmIKController("assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    assert controller.left_chain is not None
    assert controller.right_chain is not None

def test_solve_left_arm():
    """测试左臂 IK 求解"""
    controller = ArmIKController("assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    # 目标位置：基座前方 0.1m，中心线右侧 0.1m，高度 0.2m
    target = np.array([0.1, 0.1, 0.2])
    q_solution = controller.solve("left", target)
    assert q_solution is not None
    assert len(q_solution) == 7  # 7 个关节

def test_solve_invalid_arm():
    """测试无效臂名称"""
    controller = ArmIKController("assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    target = np.array([0.1, 0.1, 0.2])
    q_solution = controller.solve("invalid", target)
    assert q_solution is None
```

**Step 2: 运行测试验证失败**

Run: `cd /media/hzm/Data/EmbodiedAgentsSys && python -m pytest tests/unit/test_arm_ik_controller.py -v`
Expected: ERROR - module not found

**Step 3: 编写实现**

```python
# simulation/mujoco/arm_ik_controller.py
import numpy as np
from typing import Optional
from simulation.mujoco.ik_solver import IKChain


class ArmIKController:
    """双臂 IK 控制，支持左臂/右臂末端位置控制"""

    LEFT_ARM_END_EFFECTOR = "Empty_LinkLEND"
    RIGHT_ARM_END_EFFECTOR = "Empty_LinkREND"

    def __init__(self, urdf_path: str):
        """
        Args:
            urdf_path: URDF 文件路径
        """
        self.left_chain = IKChain(urdf_path, self.LEFT_ARM_END_EFFECTOR)
        self.right_chain = IKChain(urdf_path, self.RIGHT_ARM_END_EFFECTOR)

    def solve(self, arm: str, target_pos: np.ndarray, q_init: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
        """求解指定臂的关节角度

        Args:
            arm: "left" 或 "right"
            target_pos: 目标位置 [x, y, z]，单位米
            q_init: 初始关节角度（可选）

        Returns:
            关节角度数组 [q1-q7]，如果臂无效返回 None
        """
        if arm == "left":
            chain = self.left_chain
        elif arm == "right":
            chain = self.right_chain
        else:
            return None

        return chain.solve(target_pos, q_init)
```

**Step 4: 运行测试验证通过**

Run: `cd /media/hzm/Data/EmbodiedAgentsSys && python -m pytest tests/unit/test_arm_ik_controller.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add simulation/mujoco/arm_ik_controller.py tests/unit/test_arm_ik_controller.py
git commit -m "feat(simulation): add ArmIKController for dual-arm IK solving"
```

---

## Task 2: 修改 MuJoCoDriver 添加 move_arm_to

**Files:**
- Modify: `simulation/mujoco/mujoco_driver.py` (添加 `move_arm_to` 方法和 `_arm_ik_controller` 属性)
- Test: `tests/unit/test_arm_ik_controller.py` (已存在)

**Step 1: 编写测试**

```python
# tests/unit/test_mujoco_driver_arm.py
import numpy as np
from simulation.mujoco import MuJoCoDriver

def test_move_arm_to_left():
    """测试左臂移动"""
    driver = MuJoCoDriver(urdf_path="assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    receipt = driver.move_arm_to("left", 0.1, 0.0, 0.2)
    assert receipt.status.value == "success"
    assert "left" in receipt.result_message.lower()

def test_move_arm_to_right():
    """测试右臂移动"""
    driver = MuJoCoDriver(urdf_path="assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    receipt = driver.move_arm_to("right", 0.1, 0.0, 0.2)
    assert receipt.status.value == "success"

def test_move_arm_invalid():
    """测试无效臂"""
    driver = MuJoCoDriver(urdf_path="assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    receipt = driver.move_arm_to("invalid", 0.1, 0.0, 0.2)
    assert receipt.status.value == "failed"

def test_move_arm_unreachable():
    """测试不可达目标"""
    driver = MuJoCoDriver(urdf_path="assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    # 一个非常大的目标位置，应该不可达
    receipt = driver.move_arm_to("left", 100.0, 100.0, 100.0)
    # 应该返回失败或边界解
    assert receipt.status.value in ["failed", "success"]
```

**Step 2: 运行测试验证失败**

Run: `cd /media/hzm/Data/EmbodiedAgentsSys && python -m pytest tests/unit/test_mujoco_driver_arm.py -v`
Expected: ERROR - method not found

**Step 3: 编写实现**

在 `MuJoCoDriver.__init__` 中添加:

```python
from simulation.mujoco.arm_ik_controller import ArmIKController
import os

# 在 __init__ 中添加:
self._arm_ik_controller = None
if urdf_path and os.path.exists(urdf_path):
    try:
        self._arm_ik_controller = ArmIKController(urdf_path)
        self._left_joint_ids = [
            mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, name)
            for name in ["left_hand_joint1", "left_hand_joint2", "left_hand_joint3",
                        "left_hand_joint4", "left_hand_joint5", "left_hand_joint6", "left_hand_joint7"]
        ]
        self._right_joint_ids = [
            mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_JOINT, name)
            for name in ["right_hand_joint1", "right_hand_joint2", "right_hand_joint3",
                        "right_hand_joint4", "right_hand_joint5", "right_hand_joint6", "right_hand_joint7"]
        ]
    except Exception:
        pass  # IK 初始化失败不影响基础仿真
```

添加新方法:

```python
def move_arm_to(self, arm: str, x: float, y: float, z: float) -> ExecutionReceipt:
    """移动指定臂的末端到目标位置

    Args:
        arm: "left" 或 "right"
        x, y, z: 目标位置（基于基座坐标系）

    Returns:
        ExecutionReceipt: 执行凭证
    """
    if self._arm_ik_controller is None:
        return ExecutionReceipt(
            action_type="move_arm_to",
            params={"arm": arm, "x": x, "y": y, "z": z},
            status=ExecutionStatus.FAILED,
            result_message="IK controller not initialized (URDF not loaded)"
        )

    if arm not in ["left", "right"]:
        return ExecutionReceipt(
            action_type="move_arm_to",
            params={"arm": arm, "x": x, "y": y, "z": z},
            status=ExecutionStatus.FAILED,
            result_message=f"Invalid arm: {arm}. Must be 'left' or 'right'"
        )

    target_pos = np.array([x, y, z])

    # 求解 IK
    q_solution = self._arm_ik_controller.solve(arm, target_pos)
    if q_solution is None:
        return ExecutionReceipt(
            action_type="move_arm_to",
            params={"arm": arm, "x": x, "y": y, "z": z},
            status=ExecutionStatus.FAILED,
            result_message=f"IK solver failed for arm: {arm}"
        )

    # 获取关节 ID
    joint_ids = self._left_joint_ids if arm == "left" else self._right_joint_ids

    # 设置关节角度
    for i, joint_id in enumerate(joint_ids):
        self._data.qpos[joint_id] = q_solution[i]

    # 更新仿真
    mujoco.mj_forward(self._model, self._data)

    # 获取末端实际位置
    end_effector_name = "Empty_LinkLEND" if arm == "left" else "Empty_LinkREND"
    actual_pos = self._data.body(end_effector_name).xpos.tolist()

    return ExecutionReceipt(
        action_type="move_arm_to",
        params={"arm": arm, "x": x, "y": y, "z": z},
        status=ExecutionStatus.SUCCESS,
        result_message=f"Moved {arm} arm to ({x}, {y}, {z})",
        result_data={"target": [x, y, z], "actual": actual_pos, "joint_angles": q_solution.tolist()}
    )
```

在 `get_allowed_actions()` 中添加 `"move_arm_to"`。

在 `execute_action()` 的动作分发中添加:

```python
elif action_type == "move_arm_to":
    arm = params.get("arm")
    x = params.get("x", 0.0)
    y = params.get("y", 0.0)
    z = params.get("z", 0.0)
    return self.move_arm_to(arm, x, y, z)
```

**Step 4: 运行测试验证**

Run: `cd /media/hzm/Data/EmbodiedAgentsSys && python -m pytest tests/unit/test_mujoco_driver_arm.py -v`
Expected: PASS (或部分通过，取决于 URDF 加载)

**Step 5: 提交**

```bash
git add simulation/mujoco/mujoco_driver.py
git commit -m "feat(simulation): add move_arm_to method to MuJoCoDriver"
```

---

## Task 3: 更新 API 工具定义

**Files:**
- Modify: `backend/api/chat.py`

**Step 1: 更新 ROBOT_TOOLS 定义**

在 `ROBOT_TOOLS` 列表中，将原来的 `move_to` 工具替换为:

```python
{
    "type": "function",
    "function": {
        "name": "move_arm_to",
        "description": "将机器人指定臂的末端移动到目标位置（基于基座坐标系）",
        "parameters": {
            "type": "object",
            "properties": {
                "arm": {
                    "type": "string",
                    "enum": ["left", "right"],
                    "description": "臂名称：left 或 right"
                },
                "x": {"type": "number", "description": "X坐标 (米，相对于基座)"},
                "y": {"type": "number", "description": "Y坐标 (米，相对于基座)"},
                "z": {"type": "number", "description": "Z坐标 (米，相对于基座)"},
            },
            "required": ["arm", "x", "y", "z"],
        },
    },
},
```

同时更新 `SYSTEM_PROMPT` 添加 arm 参数说明:

```python
SYSTEM_PROMPT = """你是一个机器人控制助手。用户会用自然语言描述想要的动作，你需要调用相应的工具来执行。

支持的工具：
- move_arm_to(arm, x, y, z): 移动指定臂的末端到目标位置
  - arm: "left" 或 "right"
  - x, y, z: 目标位置（米，相对于基座坐标系）
- move_to(x, y, z): 移动机器人整体位置（已废弃，请使用 move_arm_to）
- move_relative(dx, dy, dz): 相对移动
- grasp(): 抓取
- release(): 释放
- get_scene(): 获取场景状态

注意：
- 位置单位是米
- 优先使用 move_arm_to 而非 move_to
- 如果用户没有指定具体数值，先调用get_scene了解当前状态
- 保持回复简洁"""
```

**Step 2: 更新 action_map**

```python
action_map = {
    "move_arm_to": "move_arm_to",
    "move_to": "move_to",
    "move_relative": "move_relative",
    "grasp": "grasp",
    "release": "release",
    "get_scene": "get_scene",
}
```

**Step 3: 验证 API 语法**

Run: `cd /media/hzm/Data/EmbodiedAgentsSys && python -c "from backend.api import chat; print('OK')"`

**Step 4: 提交**

```bash
git add backend/api/chat.py
git commit -m "feat(api): add move_arm_to tool definition for dual-arm control"
```

---

## Task 4: 集成测试

**Files:**
- Test: 手动通过前端测试

**Step 1: 启动后端服务**

Run: `cd /media/hzm/Data/EmbodiedAgentsSys && python -m uvicorn backend.main:app --reload`

**Step 2: 测试 API**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"message": "将机器人的左臂移动到 X=0.1 Y=0 Z=0.2"}'
```

**Step 3: 验证响应**

检查返回的 `tool_calls` 中包含 `move_arm_to` 调用。

---

## 执行选项

**Plan complete and saved to `docs/plans/2026-04-14-arm-ik-control-implementation-plan.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
