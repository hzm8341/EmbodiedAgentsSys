:orphan:

# 末端位置逆运动学控制设计

## 1. 概述

**功能**: 在 URDF 界面新增对话输入框，用户输入末端目标位置（如 `机器人左臂移动到 X=10 Y=0 Z=20`），系统通过数值逆运动学（Jacobian 伪逆）计算关节角度，驱动 MuJoCo 仿真中的机器人模型实时运动。

**技术路径**: 数值 IK（Jacobian 伪逆） + MuJoCo 仿真 + Vuer 3D 可视化

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         前端 (React)                                 │
│  ┌──────────────────┐   ┌─────────────────┐   ┌──────────────────┐  │
│  │   URDFViewer     │   │  IKChatPanel    │   │  JointControl    │  │
│  │  (3D可视化)       │   │  (对话输入)       │   │  (关节滑块)       │  │
│  └────────┬─────────┘   └────────┬────────┘   └────────┬─────────┘  │
└───────────┼───────────────────────┼───────────────────────┼─────────────┘
            │                       │                       │
            ▼                       ▼                       ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         后端 (FastAPI)                                  │
│  ┌──────────────────┐   ┌─────────────────┐   ┌──────────────────────┐  │
│  │  /api/state/{id} │   │  /api/ik/solve  │   │  /api/joint_state    │  │
│  │  (获取机器人状态)  │   │  (IK求解)        │   │  (更新关节角度)       │  │
│  └──────────────────┘   └─────────────────┘   └──────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
            │                       │                       │
            ▼                       ▼                       ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      仿真层 (MuJoCo + Vuer)                            │
│  ┌──────────────────┐   ┌─────────────────┐   ┌──────────────────┐  │
│  │  SimulationService│   │   IK Solver     │   │   Vuer Server    │  │
│  │  (物理仿真)        │   │ (Jacobian IK)    │   │  (3D渲染)         │  │
│  └──────────────────┘   └─────────────────┘   └──────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 3. 数据流

1. 用户在 `IKChatPanel` 输入: `左臂移动到 X=10 Y=0 Z=20`
2. 前端 POST `/api/ik/solve` 携带 `{ robot_id, target_link, position: {x,y,z} }`
3. 后端 IK Solver:
   - 从 URDF 构建运动学链 (root → ... → left_hand_joint7)
   - 构建 Jacobian 矩阵
   - 迭代求解: `Δq = α * J^T * (target_pos - current_pos)`
   - 返回关节角度列表
4. 后端更新 `/api/state/{robot_id}` 推送关节角度
5. Vuer Server 订阅状态变化，更新 URDF joint positions
6. 3D 场景中的机器人模型实时移动到目标位置

---

## 4. 组件设计

### 4.1 前端: IKChatPanel.tsx

**路径**: `web-dashboard/src/components/IKChatPanel.tsx`

**Props**:
```typescript
interface IKChatPanelProps {
  robotId: string;
  vuerPort: number;
}
```

**State**:
```typescript
interface IKState {
  inputText: string;
  messages: Array<{role: 'user' | 'system'; content: string}>;
  isLoading: boolean;
  lastResult: IKResult | null;
  error: string | null;
}
```

**API 调用**:
```typescript
POST /api/ik/solve
Request: { robot_id: string, target_link: string, position: {x: number, y: number, z: number} }
Response: { status: 'success' | 'error', joints: Array<{name: string, position: number}>, message: string }
```

**UI 布局**:
```
┌─────────────────────────────────────┐
│ IK Control                    [?]  │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ [对话历史区域]                    │ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ 输入: 左臂移动到 X=10 Y=0 Z=20  │ │
│ └─────────────────────────────────┘ │
│                        [发送] [清除] │
└─────────────────────────────────────┘
```

**输入解析规则**:
- 支持自然语言: `左臂移动到 X=10 Y=0 Z=20`
- 支持关键字: `left_arm`, `right_arm`, `l_hand`, `r_hand`
- 位置单位: 米 (m)

### 4.2 后端: IK Solver

**路径**: `simulation/mujoco/ik_solver.py`

**核心类**:
```python
class IKChain:
    """从URDF构建的运动学链"""

    def __init__(self, urdf_path: str, end_effector_link: str):
        ...

    def get_jacobian(self, q: np.ndarray) -> np.ndarray:
        """计算当前关节角度下的 Jacobian 矩阵"""
        ...

    def get_end_effector_position(self, q: np.ndarray) -> np.ndarray:
        """获取末端当前位置"""
        ...

    def solve(self, target_pos: np.ndarray, q_init: np.ndarray,
              max_iterations: int = 100, tolerance: float = 1e-4,
              alpha: float = 0.5) -> np.ndarray:
        """数值IK求解: Δq = α * J^T * Δx"""
        ...

    def solve_with_joint_limits(self, target_pos: np.ndarray, q_init: np.ndarray,
                                joint_limits: dict, ...) -> np.ndarray:
        """带关节限幅的IK求解"""
        ...
```

**求解算法**:
```
while iteration < max_iterations and error > tolerance:
    J = compute_jacobian(q)                    # 3×n Jacobian
    x_current = get_end_effector_position(q)  # 当前末端位置
    delta_x = target - x_current              # 位置误差
    delta_q = alpha * J.T @ delta_x            # 伪逆迭代
    q = q + delta_q                            # 更新关节角度
    error = np.linalg.norm(delta_x)            # 更新误差
```

### 4.3 后端: IK API

**路径**: `backend/api/ik.py`

**Endpoints**:
```
POST /api/ik/solve
  Body: {
    robot_id: str,           # 机器人ID，如 "unitree_g1"
    target_link: str,       # 末端link名，如 "left_hand_joint7"
    position: {x, y, z},     # 目标位置（米）
    arm: "left" | "right"    # 可选，简写解析
  }
  Response: {
    status: "success",
    joints: [{name: str, position: float}],
    target_position: {x, y, z},
    current_position: {x, y, z},
    iterations: int
  }
```

### 4.4 机器人配置

**路径**: `simulation/mujoco/config.py`

**新增配置**:
```python
# 双臂人形机器人 (Wheeled Humanoid)
WHEELED_HUMANOID_CONFIG = {
    "robot_id": "wheeled_humanoid",
    "urdf_path": "assets/wheeled_humanoid/robot.urdf",
    "end_effectors": {
        "left_arm": "left_hand_joint7",
        "right_arm": "right_hand_joint7",
    },
    "joint_groups": {
        "left_arm": ["l_shoulder_joint1", "l_shoulder_joint2", "l_shoulder_joint3",
                      "l_elbow_joint1", "l_elbow_joint2", "l_wrist_joint1"],
        "right_arm": ["r_shoulder_joint1", "r_shoulder_joint2", "r_shoulder_joint3",
                       "r_elbow_joint1", "r_elbow_joint2", "r_wrist_joint1"],
    },
    "default_start_position": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
}
```

---

## 5. 输入解析规则

| 用户输入 | 解析结果 |
|---------|---------|
| `左臂移动到 X=10 Y=0 Z=20` | `{ arm: "left", target_link: "left_hand_joint7", position: {x:10, y:0, z:20} }` |
| `right_arm to x=0.5 y=0.2 z=0.8` | `{ arm: "right", target_link: "right_hand_joint7", position: {x:0.5, y:0.2, z:0.8} }` |
| `移动左手到 10, 0, 20` | `{ arm: "left", target_link: "left_hand_joint7", position: {x:10, y:0, z:20} }` |

---

## 6. 错误处理

| 错误场景 | HTTP状态码 | 错误信息 |
|---------|-----------|---------|
| 机器人不存在 | 404 | `Robot not found: {robot_id}` |
| 末端link不存在 | 400 | `End effector link not found: {link_name}` |
| 目标位置超出工作空间 | 400 | `Target position out of workspace` |
| IK求解失败（达到最大迭代） | 500 | `IK solver failed to converge` |
| URDF解析失败 | 500 | `Failed to parse URDF: {error}` |

---

## 7. 集成点

| 组件 | 文件路径 | 修改内容 |
|-----|---------|---------|
| URDFViewer | `web-dashboard/src/components/URDFViewer.tsx` | 集成 IKChatPanel 作为侧边栏 Tab |
| JointControl | `web-dashboard/src/components/JointControl.tsx` | 保持独立，通过 state API 同步 |
| State API | `backend/api/state.py` | 新增 IK 结果推送端点 |
| Chat API | `backend/api/chat.py` | 复用工具执行框架 |
| SimulationService | `backend/services/simulation.py` | 集成 IK Solver |

---

## 8. 文件清单

| 文件 | 操作 | 说明 |
|-----|------|-----|
| `simulation/mujoco/ik_solver.py` | **新建** | IK 求解器核心 |
| `simulation/mujoco/config.py` | **修改** | 新增机器人配置 |
| `backend/api/ik.py` | **新建** | IK HTTP API |
| `backend/services/simulation.py` | **修改** | 集成 IK Solver |
| `web-dashboard/src/components/IKChatPanel.tsx` | **新建** | 前端对话界面 |
| `web-dashboard/src/components/URDFViewer.tsx` | **修改** | 集成 IKChatPanel |

---

## 9. 验证计划

1. **单元测试**: IK Solver 对已知姿态的逆解验证
2. **集成测试**: 完整数据流（输入 → IK → 状态更新 → 3D渲染）
3. **手动验证**: 在 URDF Viewer 中输入目标位置，观察机器人末端是否正确移动

---

## 10. 风险与备选

| 风险 | 缓解方案 |
|-----|---------|
| Jacobian 奇异位形 | 添加奇异值分解 (SVD) 处理 |
| 关节限幅导致求解失败 | 使用 Null Space 投影保留次要目标 |
| 多解问题 | 使用多起点随机化或关节空间平滑 |
