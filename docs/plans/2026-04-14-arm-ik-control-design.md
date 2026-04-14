# 双臂末端位置控制设计

## 概述

通过自然语言指令控制机器人左臂或右臂移动到指定位置（基于基座坐标系）。

**用户指令示例**："将机器人的左臂移动到 X=10 Y=0 Z=20"

**技术实现**：LLM 解析指令 → IK 求解 → MuJoCo 仿真

---

## 架构

```
用户输入: "左臂移动到 X=10 Y=0 Z=20"
        ↓
前端 ChatPanel → Backend /api/chat
        ↓
DeepSeek LLM 解析指令
        ↓
工具调用: move_arm_to(arm="left", x=10, y=0, z=20)
        ↓
IKChain.solve(target_pos) → joint angles [q1-q7]
        ↓
MuJoCoDriver 设置 data.qpos → 仿真更新
        ↓
返回执行结果给前端
```

---

## 核心组件

### 1. ArmIKController（新增）

**文件**: `simulation/mujoco/arm_ik_controller.py`

```python
class ArmIKController:
    """双臂 IK 控制，支持左臂/右臂末端位置控制"""

    def __init__(self, urdf_path: str):
        self.left_chain = IKChain(urdf_path, "Empty_LinkLEND")  # 左臂末端
        self.right_chain = IKChain(urdf_path, "Empty_LinkREND")  # 右臂末端

    def solve(self, arm: str, target_pos: np.ndarray, q_init=None) -> np.ndarray:
        """求解指定臂的关节角度"""
        chain = self.left_chain if arm == "left" else self.right_chain
        return chain.solve(target_pos, q_init)
```

**末端执行器 Link**:
- 左臂: `Empty_LinkLEND`（`left_hand_joint9` 的 child link）
- 右臂: `Empty_LinkREND`（`right_hand_joint9` 的 child link）

### 2. MuJoCoDriver 修改

**新增方法**:
- `move_arm_to(arm, x, y, z)` - 移动指定臂到目标位置
- `_get_joint_ids_for_arm(arm)` - 获取指定臂的关节 ID 列表

**关节映射**:
- 左臂关节: `left_hand_joint1` ~ `left_hand_joint7`（7个revolute joint）
- 右臂关节: `right_hand_joint1` ~ `right_hand_joint7`（7个revolute joint）

**IK 执行流程**:
1. 调用 `ArmIKController.solve(arm, [x, y, z])`
2. 获取关节角度数组 [q1-q7]
3. 根据关节 ID 映射设置 `data.qpos`
4. 调用 `mujoco.mj_forward()` 更新仿真

### 3. API 工具定义

**文件**: `backend/api/chat.py`

```python
ROBOT_TOOLS = [
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
                    "x": {"type": "number", "description": "X坐标 (米)"},
                    "y": {"type": "number", "description": "Y坐标 (米)"},
                    "z": {"type": "number", "description": "Z坐标 (米)"},
                },
                "required": ["arm", "x", "y", "z"],
            },
        },
    },
    # 保留原有工具...
]
```

---

## 数据流

1. 前端发送消息 "左臂移动到 X=10 Y=0 Z=20"
2. LLM 解析为 `move_arm_to(arm="left", x=10, y=0, z=20)`
3. Backend 调用 `simulation_service.execute_action("move_arm_to", {"arm": "left", "x": 10, "y": 0, "z": 20})`
4. `MuJoCoDriver.move_arm_to()` 执行:
   - 调用 `ArmIKController.solve("left", [10, 0, 20])` → 获得 [q1-q7]
   - 设置 `self._data.qpos[joint_ids] = joint_angles`
   - 调用 `mujoco.mj_forward()` 更新
5. 返回 ExecutionReceipt（成功/失败）

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| IK 无解（目标不可达） | 返回 FAILED: "目标位置不可达" |
| 关节限位违反 | IK solver 内 clamp，返回边界解 |
| 臂名称无效 | 返回 FAILED: "Invalid arm: xxx" |
| 位置超出基座范围 | 检查 xyz 范围，超出则拒绝 |
| URDF 文件不存在 | 启动时检查，缺失则报错 |

---

## 文件变更

| 操作 | 文件路径 |
|------|----------|
| 新增 | `simulation/mujoco/arm_ik_controller.py` |
| 修改 | `simulation/mujoco/mujoco_driver.py` |
| 修改 | `backend/api/chat.py` |
| 修改 | `backend/services/simulation.py` |

---

## 验证方法

1. 单元测试：单独测试 `ArmIKController.solve()`
2. 集成测试：发送 `move_arm_to(arm="left", x=0.1, y=0, z=0.2)` 验证末端移动
3. 手动测试：通过前端 ChatPanel 输入指令验证完整流程
