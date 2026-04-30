:orphan:

# 通用具身智能 Agent 系统开发计划

**文档版本**: v1.1  
**创建日期**: 2026-03-09  
**项目**: EmbodiedAgentsSys 扩展计划  
**目标**: 变成通用的具身智能 Agent 系统，支持人形机器人、工业机械臂、移动机器人

---

## 1. 项目愿景与目标

### 1.1 愿景

构建一个**生产级通用具身智能 Agent 框架**，能够：

- 支持多种机器人形态（人形、机械臂、移动机器人）
- 覆盖从感知到执行的完整数据流
- 提供预训练模型、微调、训练的全流程支持
- 适配科研与工业双重场景

### 1.2 核心目标

| 目标 | 描述 | 优先级 |
|------|------|--------|
| G1 | 支持 3+ 种机器人平台 | P0 |
| G2 | 集成主流 VLA 模型（LeRobot, ACT, GR00T） | P0 |
| G3 | 实现完整的运动控制 pipeline | P0 |
| G4 | 支持 VLA 预训练、微调、训练 | P1 |
| G5 | 多模态感知（视觉、语音、力觉） | P1 |
| G6 | 任务规划与执行系统 | P1 |
| G7 | 云-边-端分布式部署 | P2 |
| G8 | 多机器人协作 | P2 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              云端服务器 (Cloud)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        VLA 训练与推理服务                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────┐ │  │
│  │  │ LeRobot 训练 │  │ ACT 训练     │  │ GR00T 训练   │  │ 自定义  │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        任务规划服务 (LLM)                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│  │  │ 规则规划器    │  │ LLM 规划器   │  │ 技能编排器    │              │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        视觉推理服务                                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│  │  │ 目标检测      │  │ 语义分割     │  │ 3D 重建      │              │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                              │ REST / gRPC / WebSocket                    │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                         边缘服务器 (Edge PC)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        核心中间件                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│  │  │ 通信网关      │  │ 状态管理     │  │ 数据缓存      │              │  │
│  │  │ (REST/gRPC)  │  │ (Redis)      │  │ (Redis)       │              │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        运动规划层                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│  │  │ 运动学求解    │  │ 轨迹规划      │  │ 避障规划      │              │  │
│  │  │ (IK/FK)      │  │ (MoveIt)     │  │ (OMPL)        │              │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        技能执行层                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│  │  │ GraspSkill   │  │ PlaceSkill   │  │ MoveSkill    │              │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│  │  │ ReachSkill   │  │ ForceSkill   │  │ NavSkill     │              │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                              │ ROS2 Humble                                │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                           机器人本体 (Robot)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        传感器层                                      │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────┐ │  │
│  │  │ 深度相机      │  │ IMU          │  │ 力矩传感器    │  │ 激光   │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        控制层                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│  │  │ 关节控制器    │  │ 末端控制器    │  │ 移动控制器    │              │  │
│  │  │ (Position)   │  │ (Velocity)   │  │ (Differential)│             │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        执行层                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│  │  │ 机械臂执行器  │  │ 夹爪执行器    │  │ 轮毂电机      │              │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 架构分层说明

| 层级 | 位置 | 功能 | 关键技术 |
|------|------|------|----------|
| **应用层** | 云端 | 用户交互、任务下发 | Web UI, API |
| **服务层** | 云端 | VLA 训练/推理、任务规划 | PyTorch, LLM, VLM |
| **中间件层** | 边缘 | 通信、数据处理、缓存 | Redis, gRPC |
| **规划层** | 边缘 | 运动学、轨迹规划 | MoveIt, OMPL |
| **技能层** | 边缘 | 原子技能执行 | Python, ROS2 |
| **控制层** | 机器人 | 电机控制、传感器采集 | ROS2 Control |
| **硬件层** | 机器人 | 执行器、传感器 | 硬件接口 |

---

## 3. 模块详细设计

### 3.1 云端服务模块

#### 3.1.1 VLA 训练服务

**功能**: 支持 VLA 模型的预训练、微调、推理

**技术栈**:

- 训练框架: PyTorch 2.0+, Lightning
- 分布式: PyTorch DDP, DeepSpeed
- 模型库: HuggingFace Transformers, Diffusers
- 实验管理: MLflow, Weights & Biases

**模块划分**:

```
vla_training/
├── core/
│   ├── trainer.py          # 训练器基类
│   ├── dataset.py         # 数据集加载
│   └── config.py          # 配置管理
├── algorithms/
│   ├── lerobot/           # LeRobot 算法实现
│   ├── act/               # ACT 算法实现
│   └── gr00t/             # GR00T 算法实现
├── inference/
│   ├── server.py          # 推理服务 (gRPC)
│   └── client.py          # 边缘调用客户端
└── utils/
    ├── checkpoint.py       # 检查点管理
    └── visualization.py   # 可视化工具
```

**API 接口**:

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/vla/train` | POST | 启动训练任务 |
| `/api/vla/train/status` | GET | 获取训练状态 |
| `/api/vla/inference` | POST | VLA 推理调用 |
| `/api/vla/checkpoint` | GET | 下载模型权重 |

#### 3.1.2 任务规划服务

**功能**: 自然语言任务分解、动作序列生成

**技术栈**:

- LLM: Ollama (本地), OpenAI API (云端)
- Prompt Engineering: LangChain
- 技能库: 本地技能索引 (ChromaDB)

**模块划分**:

```
task_planning/
├── planner/
│   ├── base.py            # 规划器基类
│   ├── rule_planner.py    # 规则规划器
│   └── llm_planner.py     # LLM 规划器
├── skills/
│   ├── registry.py        # 技能注册
│   └── indexer.py        # 技能索引
└── executor/
    └── executor.py        # 执行器
```

### 3.2 边缘服务器模块

#### 3.2.1 运动控制模块

**功能**: 逆运动学、轨迹规划、速度控制

**技术栈**:

- 运动库: PyBullet, OMPL, MoveIt
- 数学库: NumPy, SciPy, Pinocchio (人形)
- 实时控制: ROS2 Control

**支持的机器人配置**:

```yaml
# robots/panda.yaml
robot:
  type: "manipulator"
  name: "panda"
  manufacturer: "Franka Emika"
  
  dof: 7
  payload: 3.0  # kg
  reach: 0.855  # m
  
  joint_limits:
    position: [-2.8973, 2.8973]  # rad
    velocity: 2.175  # rad/s
    torque: 87.0  # Nm
    
  links:
    - name: "panda_link0"
    - name: "panda_link1"
    # ...
    
  gripper:
    type: "parallel"
    max_width: 0.08  # m
    max_force: 140  # N
```

```yaml
# robots/h1.yaml
robot:
  type: "humanoid"
  name: "h1"
  manufacturer: "Unitree"
  
  dof: 19  # 全身上限
  height: 1.7  # m
  weight: 70  # kg
  
  joints:
    leg:
      - "left_hip_yaw"
      - "left_hip_roll"
      # ...
    arm:
      - "left_shoulder_pitch"
      # ...
```

```yaml
# robots/ugv.yaml
robot:
  type: "mobile"
  name: "diff_bot"
  
  dimensions:
    length: 0.6
    width: 0.4
    height: 0.3
    
  wheels:
    type: "differential"
    radius: 0.1
    
  sensors:
    lidar:
      type: "rplidar"
      range: 12  # m
```

#### 3.2.2 技能系统

**技能基类**:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class SkillStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class SkillResult:
    status: SkillStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BaseSkill(ABC):
    """技能基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
        
    @abstractmethod
    async def execute(self, observation: Dict) -> SkillResult:
        """执行技能"""
        pass
    
    @abstractmethod
    def check_preconditions(self, observation: Dict) -> bool:
        """检查前置条件"""
        pass
    
    @abstractmethod
    def check_postconditions(self, observation: Dict) -> bool:
        """检查后置条件"""
        pass
```

**内置技能库**:

| 技能 | 适用机器人 | 功能 |
|------|-----------|------|
| GraspSkill | 机械臂 | 抓取物体 |
| PlaceSkill | 机械臂 | 放置物体 |
| ReachSkill | 机械臂 | 移动到目标位置 |
| MoveSkill | 机械臂 | 关节/末端运动 |
| InspectSkill | 机械臂 | 检查/识别物体 |
| ForceSkill | 机械臂 | 力控操作 |
| WalkSkill | 人形 | 行走 |
| BalanceSkill | 人形 | 平衡控制 |
| NavSkill | 移动机器人 | 导航 |
| AvoidSkill | 移动机器人 | 避障 |

### 3.3 数据流设计

#### 3.3.1 任务执行流程

```
用户输入: "把桌子上的杯子拿给我"
     │
     ▼
┌─────────────┐
│  语音/文本   │ ──► ASR / 语义解析
└─────────────┘
     │
     ▼
┌─────────────┐
│  任务规划    │ ──► LLM 分解: ["reach(cup)", "grasp(cup)", "move(user)", "release(cup)"]
└─────────────┘
     │
     ▼
┌─────────────┐
│  技能链执行  │
│  ┌────────┐ │
│  │ Reach  │─┼──► IK 求解 ──► 轨迹规划 ──► 关节控制
│  └────────┘ │
│  ┌────────┐ │
│  │ Grasp  │─┼──► 抓取策略 ──► 夹爪控制 ──► 力反馈
│  └────────┘ │
│  ┌────────┐ │
│  │ Move   │─┼──► 路径规划 ──► 移动控制
│  └────────┘ │
│  ┌────────┐ │
│  │Release │─┼──► 释放策略 ──► 夹爪打开
│  └────────┘ │
└─────────────┘
     │
     ▼
┌─────────────┐
│  执行结果反馈 │
└─────────────┘
```

#### 3.3.2 VLA 推理流程

```
观察数据 (Observation):
{
  "image": [H, W, 3],        # RGB 图像
  "depth": [H, W],           # 深度图 (可选)
  "joint_positions": [7],    # 关节角度
  "joint_velocities": [7],   # 关节速度
  "force_torque": [6],       # 末端力矩 (可选)
  "task_description": "grasp the cup"
}
     │
     ▼
┌─────────────┐
│  特征编码    │ ──► Vision Encoder ──► 视觉特征
│              │ ──► State Encoder  ──► 状态特征
└─────────────┘
     │
     ▼
┌─────────────┐
│  VLA 模型   │ ──► Action = π(visual_features, state_features, task)
└─────────────┘
     │
     ▼
┌─────────────┐
│  动作输出    │
│  {          │
│    "actions": [7],         # 目标关节位置/速度
│    "gripper": 1.0,         # 夹爪开合 (0-1)
│    "horizon": 8            # 动作时域长度
│  }          │
└─────────────┘
     │
     ▼
┌─────────────┐
│  控制器执行  │ ──► PID/阻抗控制 ──► 电机指令
└─────────────┘
```

### 3.4 通信协议设计

#### 3.4.1 云-边通信

```protobuf
// vla_inference.proto
service VLAInference {
  rpc Infer(VLARequest) returns (VLAResponse);
  rpc StreamInfer(VLARequest) returns (stream VLAResponse);
}

message VLARequest {
  string robot_id = 1;
  string model_name = 2;
  Observation observation = 3;
  InferenceConfig config = 4;
}

message Observation {
  bytes image = 1;
  repeated float joint_positions = 2;
  repeated float joint_velocities = 3;
  repeated float force_torque = 4;
  string task_description = 5;
}

message VLAResponse {
  repeated float actions = 1;
  float gripper = 2;
  int32 horizon = 3;
  float confidence = 4;
}
```

#### 3.4.2 边-端通信 (ROS2)

```yaml
# 话题定义
topics:
  # 传感器
  camera:
    type: "sensor_msgs/Image"
    topic: "/robot/camera/rgb"
  depth:
    type: "sensor_msgs/Image"
    topic: "/robot/camera/depth"
  joint_states:
    type: "sensor_msgs/JointState"
    topic: "/robot/joint_states"
  ft_sensor:
    type: "geometry_msgs/WrenchStamped"
    topic: "/robot/ft_sensor"
  
  # 控制
  joint_commands:
    type: "sensor_msgs/JointState"
    topic: "/robot/joint_commands"
  gripper_command:
    type: "std_msgs/Float64"
    topic: "/robot/gripper_command"
```

---

## 4. 开发阶段规划

### 4.1 阶段划分

| 阶段 | 时间 | 目标 | 交付物 |
|------|------|------|--------|
| **Phase 1: 基础架构** | 1-2 月 | 框架搭建、核心模块实现 | 代码骨架、基础技能 |
| **Phase 2: 机器人适配** | 2-3 月 | 支持 3 种机器人平台 | Panda/H1/UGV 配置 |
| **Phase 3: VLA 集成** | 2-3 月 | VLA 推理/训练 pipeline | 推理服务、训练脚本 |
| **Phase 4: 高级功能** | 2-3 月 | 任务规划、多模态感知 | 规划器、感知模块 |
| **Phase 5: 优化与部署** | 1-2 月 | 性能优化、生产部署 | 部署配置、文档 |

**总周期**: 8-12 个月

### 4.2 Phase 1 详细计划 (基础架构)

**目标**: 搭建开发框架，实现核心模块

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W1 | 项目结构搭建、CI/CD 配置 | GitHub Actions, 代码模板 |
| W2 | ROS2 环境配置、通信基础 | 消息定义、话题接口 |
| W3 | 运动学求解器 (IK/FK) | IK 求解库 |
| W4 | 技能基类、SkillRegistry | 技能框架 |
| W5 | 基础运动技能 (Move, Reach) | MoveSkill, ReachSkill |
| W6 | 抓取/放置技能 | GraspSkill, PlaceSkill |
| W7 | 感知基础 (相机接入) | 相机驱动、图像话题 |
| W8 | **Phase 1 验收** | 演示系统 |

### 4.3 Phase 2 详细计划 (机器人适配)

**目标**: 支持 3 种机器人平台

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W9-10 | 机械臂适配 (Panda) | Panda 配置文件、运动配置 |
| W11-12 | 人形机器人适配 (H1) | H1 配置文件、步态规划 |
| W13-14 | 移动机器人适配 (UGV) | UGV 配置文件、导航配置 |
| W15 | 机器人配置系统重构 | 统一配置管理 |
| W16 | **Phase 2 验收** | 3 种机器人演示 |

### 4.4 Phase 3 详细计划 (VLA 集成)

**目标**: VLA 推理与训练 pipeline

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W17-18 | VLA 推理服务搭建 | gRPC 服务 |
| W19-20 | LeRobot 适配器 | LeRobotVLAAdapter |
| W21-22 | ACT/GR00T 适配器 | ACTVLAAdapter, GR00TAdapter |
| W23-24 | 数据采集 pipeline | 演示录制工具 |
| W25-26 | VLA 训练脚本 | 训练代码、配置 |
| W27-28 | 微调 pipeline | LoRA/全参数微调 |
| W29-30 | **Phase 3 验收** | VLA 演示 |

### 4.5 Phase 4 详细计划 (高级功能)

**目标**: 任务规划、多模态感知

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W31-32 | LLM 任务规划器 | LLMPlanner |
| W33-34 | 规则任务规划器 | RulePlanner |
| W35-36 | 语音交互 (ASR/TTS) | 语音组件 |
| W37-38 | 3D 感知 (Perception) | 3D 重建、物体检测 |
| W39-40 | 力控技能 | ForceSkill |
| W41-42 | 示教与技能学习 | TeachingRecorder |
| W43-44 | **Phase 4 验收** | 完整演示 |

### 4.6 Phase 5 详细计划 (优化与部署)

**目标**: 性能优化、生产部署

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W45-46 | 性能优化 (延迟、吞吐量) | 优化报告 |
| W47-48 | 部署配置 (Docker/K8s) | Docker 镜像 |
| W49 | 监控与日志 | 监控系统 |
| W50 | 文档完善 | API 文档、用户手册 |
| W51-52 | **最终验收** | 发布 v1.0 |

---

## 5. 技术选型汇总

### 5.1 核心技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **框架** | ROS2 | Humble | 机器人中间件 |
| **框架** | Python | 3.10+ | 开发语言 |
| **深度学习** | PyTorch | 2.0+ | 神经网络训练 |
| **控制** | MoveIt | 2.x | 运动规划 |
| **控制** | ROS2 Control | - | 实时控制 |
| **LLM** | Ollama | latest | 本地 LLM |
| **LLM** | LangChain | 0.3+ | 提示词工程 |
| **向量库** | ChromaDB | 0.4+ | 技能索引 |
| **缓存** | Redis | 7.x | 状态缓存 |
| **部署** | Docker | 24+ | 容器化 |

### 5.2 硬件兼容性

| 机器人类型 | 品牌/型号 | 通信接口 | 控制频率 |
|-----------|----------|---------|---------|
| 机械臂 | Franka Panda | Ethernet (ROS2) | 1kHz |
| 机械臂 | UR5/UR5e | Ethernet (ROS2) | 125Hz |
| 人形 | Unitree H1 | Ethernet (ROS2) | 100Hz |
| 人形 | Tesla Optimus | TBD | TBD |
| 移动 | Clearpath Jackal | ROS2 | 50Hz |
| 移动 | TurtleBot4 | WiFi (ROS2) | 30Hz |

---

## 6. 测试策略

### 6.1 测试分层

```
┌─────────────────────────────────────────┐
│           E2E 测试 (系统测试)            │
│   完整任务: "抓取杯子放到指定位置"        │
├─────────────────────────────────────────┤
│           集成测试                       │
│   技能链、规划器、VLA 推理                │
├─────────────────────────────────────────┤
│           单元测试                       │
│   IK 求解、运动控制、感知算法             │
└─────────────────────────────────────────┘
```

### 6.2 测试覆盖目标

| 指标 | 目标 |
|------|------|
| 单元测试覆盖率 | > 70% |
| 集成测试用例 | > 50 |
| E2E 演示用例 | > 10 |
| 性能基准测试 | > 20 |

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| VLA 训练资源需求高 | Phase 3 延迟 | 使用云 GPU、降低目标 |
| 多机器人同步难 | Phase 4 延迟 | 先单机再扩展 |
| 实时性不足 | 系统不可用 | 边缘优化、分级控制 |
| 硬件兼容性 | 无法部署 | 多平台测试、抽象接口 |

---

## 8. 技术细节补充

### 8.1 核心数据结构

```python
# observation.py - 观察数据结构
from dataclasses import dataclass, field
from typing import Optional, List
import numpy as np

@dataclass
class Observation:
    """机器人观察数据"""
    # 视觉
    rgb_image: Optional[np.ndarray] = None      # [H, W, 3]
    depth_image: Optional[np.ndarray] = None   # [H, W]
    
    # 关节状态
    joint_positions: Optional[np.ndarray] = None  # [dof]
    joint_velocities: Optional[np.ndarray] = None  # [dof]
    joint_efforts: Optional[np.ndarray] = None    # [dof]
    
    # 末端执行器
    end_effector_pose: Optional[np.ndarray] = None  # [7] xyz + quat
    end_effector_velocity: Optional[np.ndarray] = None  # [6]
    
    # 力觉
    ft_sensor: Optional[np.ndarray] = None  # [6] force + torque
    
    # 环境
    task_description: str = ""
    timestamp: float = 0.0
    
@dataclass
class Action:
    """机器人动作指令"""
    # 关节控制
    joint_positions: Optional[np.ndarray] = None  # [dof]
    joint_velocities: Optional[np.ndarray] = None  # [dof]
    joint_efforts: Optional[np.ndarray] = None    # [dof]
    
    # 末端控制
    end_effector_pose: Optional[np.ndarray] = None  # [7] xyz + quat
    
    # 夹爪
    gripper_position: float = 0.0  # 0=close, 1=open
    gripper_force: float = 0.0
    
    # 元数据
    horizon: int = 1  # 动作时域长度
    confidence: float = 1.0
    
@dataclass
class RobotConfig:
    """机器人配置"""
    name: str
    type: str  # "manipulator", "humanoid", "mobile"
    dof: int
    urdf_path: str
    srdf_path: str
    
    # 运动学参数
    base_frame: str = "base_link"
    ee_frame: str = "tool0"
    
    # 限制
    joint_limits: dict = field(default_factory=dict)
    velocity_limits: dict = field(default_factory=dict)
    acceleration_limits: dict = field(default_factory=dict)
    
    # 控制器配置
    controllers: dict = field(default_factory=dict)
```

### 8.2 gRPC 服务接口

```python
# robot_service.proto - 机器人控制服务
syntax = "proto3";

package embodied_agents;

service RobotControl {
    // 运动控制
    rpc MoveToPose(MoveToPoseRequest) returns (MoveToPoseResponse);
    rpc MoveToJoint(MoveToJointRequest) returns (MoveToJointResponse);
    rpc ExecuteTrajectory(ExecuteTrajectoryRequest) returns (stream ExecuteTrajectoryResponse);
    
    // 夹爪控制
    rpc SetGripper(SetGripperRequest) returns (SetGripperResponse);
    
    // 状态查询
    rpc GetState(GetStateRequest) returns (GetStateResponse);
    rpc StreamState(StreamStateRequest) returns (stream StateUpdate);
    
    // 技能执行
    rpc ExecuteSkill(SkillRequest) returns (SkillResponse);
    rpc StreamSkill(SkillRequest) returns (stream SkillFeedback);
}

message MoveToPoseRequest {
    string robot_id = 1;
    Pose target_pose = 2;
    MotionProfile profile = 3;
}

message MoveToJointRequest {
    string robot_id = 1;
    repeated float target_joints = 2;
    MotionProfile profile = 3;
}

message MotionProfile {
    float max_velocity = 1;
    float max_acceleration = 2;
    float max_jerk = 3;
}

message Pose {
    Position position = 1;
    Quaternion orientation = 2;
}

message Position {
    float x = 1;
    float y = 2;
    float z = 3;
}

message Quaternion {
    float x = 1;
    float y = 2;
    float z = 3;
    float w = 4;
}
```

### 8.3 REST API 接口

```yaml
# openapi.yaml - REST API 定义
openapi: 3.0.0
info:
  title: Embodied Agents API
  version: 1.0.0

paths:
  /api/v1/robots:
    get:
      summary: 获取机器人列表
      responses:
        200:
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Robot'
    
    post:
      summary: 注册新机器人
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RobotConfig'
      responses:
        201:
          description: 机器人注册成功

  /api/v1/robots/{robot_id}/execute:
    post:
      summary: 执行任务
      parameters:
        - name: robot_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                task:
                  type: string
                  example: "把杯子放到桌子上"
                mode:
                  type: string
                  enum: [sync, async]
      responses:
        200:
          description: 执行结果

  /api/v1/skills:
    get:
      summary: 获取可用技能列表
      responses:
        200:
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Skill'

  /api/v1/vla/inference:
    post:
      summary: VLA 模型推理
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/VLARequest'
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VLAResponse'
```

---

## 9. 机器人配置模板

### 9.1 机械臂配置 (Franka Panda)

```yaml
# config/robots/panda.yaml
name: "panda"
type: "manipulator"
manufacturer: "Franka Emika"

# 运动学
dof: 7
base_frame: "panda_link0"
ee_frame: "panda_tool"

# 物理参数
payload: 3.0  # kg
reach: 0.855  # m

# 关节限制
joint_limits:
  panda_joint1: [-2.8973, 2.8973]
  panda_joint2: [-1.7628, 1.7628]
  panda_joint3: [-2.8973, 2.8973]
  panda_joint4: [-3.0718, -0.0698]
  panda_joint5: [-2.8973, 2.8973]
  panda_joint6: [-0.0175, 3.7525]
  panda_joint7: [-2.8973, 2.8973]

velocity_limits: [2.175, 2.175, 2.175, 2.175, 2.61, 2.61, 2.61]

# 夹爪配置
gripper:
  type: "parallel"
  name: "panda_hand"
  dof: 2
  max_width: 0.08  # m
  max_force: 140.0  # N

# 控制器
controllers:
  position_controller:
    type: "position"
    interface: "position"
  velocity_controller:
    type: "velocity"
    interface: "velocity"
  effort_controller:
    type: "effort"
    interface: "effort"

# 传感器
sensors:
  ft_sensor:
    type: "ATI_Net_FT"
    topic: "/robot/ft_sensor"
    frame: "panda_tool"
  camera:
    type: "RealSense_D435i"
    topic: "/camera/color/image_raw"
```

### 9.2 人形机器人配置 (Unitree H1)

```yaml
# config/robots/h1.yaml
name: "h1"
type: "humanoid"
manufacturer: "Unitree"

# 运动学
dof: 19
height: 1.7  # m
weight: 70  # kg

# 关节配置
joints:
 torso:
    - name: "torso_yaw"
      id: 0
      axis: [0, 0, 1]
      limits: [-0.52, 0.52]  # rad
      
  leg_left:
    - name: "left_hip_yaw"
      id: 1
      limits: [-0.52, 0.52]
    - name: "left_hip_roll"
      id: 2
      limits: [-0.26, 0.26]
    - name: "left_hip_pitch"
      id: 3
      limits: [-2.96, 2.96]
    - name: "left_knee"
      id: 4
      limits: [0, 2.79]
    - name: "left_ankle_pitch"
      id: 5
      limits: [-0.52, 0.52]
    - name: "left_ankle_roll"
      id: 6
      limits: [-0.26, 0.26]
      
  leg_right: [类似左腿...]
  
  arm_left:
    - name: "left_shoulder_pitch"
      id: 7
      limits: [-2.96, 2.96]
    - name: "left_shoulder_roll"
      id: 8
      limits: [-0.26, 1.57]
    - name: "left_elbow"
      id: 9
      limits: [-2.79, 0]
      
  arm_right: [类似左臂...]

# 控制器
controllers:
  walking_controller:
    type: "walking_pattern"
    gait: "trot"
    step_height: 0.05
    step_length: 0.15
    step_period: 0.5
    
  balance_controller:
    type: "mpc"
    horizon: 10
    frequency: 100
    
  whole_body_controller:
    type: "qpoases"
    weight:
      position: 1.0
      orientation: 10.0
      velocity: 0.1
```

### 9.3 移动机器人配置 (UGV)

```yaml
# config/robots/ugv_diff.yaml
name: "diff_bot"
type: "mobile"
manufacturer: "Custom"

# 物理参数
dimensions:
  length: 0.6
  width: 0.4
  height: 0.3
  
mass: 20.0  # kg

# 轮子配置
wheels:
  type: "differential"
  radius: 0.1  # m
  track_width: 0.35  # m
  max_linear_velocity: 1.0  # m/s
  max_angular_velocity: 2.0  # rad/s

# 驱动配置
motors:
  left:
    model: "MYD-JGB37-520"
    encoder_resolution: 990
    gear_ratio: 30
    
  right:
    model: "MYD-JGB37-520"
    encoder_resolution: 990
    gear_ratio: 30

# 传感器配置
sensors:
  lidar:
    type: "rplidar_a1"
    topic: "/scan"
    range_min: 0.15
    range_max: 12.0
    angle_min: -3.14
    angle_max: 3.14
    
  camera:
    type: "Logitech_C270"
    topic: "/camera/image"
    resolution: [640, 480]
    
  imu:
    type: "MPU6050"
    topic: "/imu/data"
    frame_id: "imu_link"

# 导航配置
navigation:
  local_planner: "dwa"
  global_planner: "astar"
  recovery_behavior: true
  
  costmap:
    global:
      width: 20.0
      height: 20.0
      resolution: 0.05
    local:
      width: 10.0
      height: 10.0
      resolution: 0.025
```

---

## 10. 代码框架示例

### 10.1 运动学求解器

```python
# kinematics/solver.py
import numpy as np
from typing import Tuple, Optional

class InverseKinematicsSolver:
    """逆运动学求解器基类"""
    
    def __init__(self, robot_config: dict):
        self.config = robot_config
        self.dof = robot_config['dof']
        self.urdf_path = robot_config['urdf_path']
        
    def solve(
        self, 
        target_pose: np.ndarray,
        seed: Optional[np.ndarray] = None,
        max_iterations: int = 100,
        tolerance: float = 1e-4
    ) -> Tuple[bool, np.ndarray]:
        """
        求解逆运动学
        
        Args:
            target_pose: 目标末端位姿 [x, y, z, qx, qy, qz, qw]
            seed: 初始关节角度
            max_iterations: 最大迭代次数
            tolerance: 收敛容差
            
        Returns:
            (success, joint_positions)
        """
        raise NotImplementedError
    
    def forward(
        self, 
        joint_positions: np.ndarray
    ) -> np.ndarray:
        """
        正运动学求解
        
        Args:
            joint_positions: 关节角度
            
        Returns:
            末端位姿 [x, y, z, qx, qy, qz, qw]
        """
        raise NotImplementedError


class PyBulletIKSolver(InverseKinematicsSolver):
    """基于 PyBullet 的 IK 求解器"""
    
    def __init__(self, robot_config: dict):
        super().__init__(robot_config)
        import pybullet as p
        import pybullet_data
        
        self.client = p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        
        # 加载机器人
        self.robot_id = p.loadURDF(
            self.urdf_path,
            flags=p.URDF_USE_SELF_COLLISION
        )
        
    def solve(self, target_pose: np.ndarray, **kwargs) -> Tuple[bool, np.ndarray]:
        joint_positions = p.calculateInverseKinematics(
            self.robot_id,
            self.ee_link_id,
            target_pose[:3],
            target_pose[3:7],
            max_iterations=kwargs.get('max_iterations', 100)
        )
        return True, np.array(joint_positions)
```

### 10.2 技能执行器

```python
# skills/executor.py
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ExecutionContext:
    """技能执行上下文"""
    robot_id: str
    observation: Dict[str, Any]
    parameters: Dict[str, Any]
    execution_id: str
    
class SkillExecutor:
    """技能执行器"""
    
    def __init__(self, robot_config: dict):
        self.config = robot_config
        self.skill_registry: Dict[str, BaseSkill] = {}
        self.execution_history: List[ExecutionContext] = []
        
    def register_skill(self, skill: BaseSkill):
        """注册技能"""
        self.skill_registry[skill.name] = skill
        
    async def execute_skill_chain(
        self,
        skill_names: List[str],
        context: ExecutionContext,
        stop_on_failure: bool = True
    ) -> List[SkillResult]:
        """执行技能链"""
        results = []
        
        for skill_name in skill_names:
            if skill_name not in self.skill_registry:
                results.append(SkillResult(
                    status=SkillStatus.FAILED,
                    error=f"Skill {skill_name} not found"
                ))
                if stop_on_failure:
                    break
                continue
                
            skill = self.skill_registry[skill_name]
            
            # 检查前置条件
            if not skill.check_preconditions(context.observation):
                results.append(SkillResult(
                    status=SkillStatus.FAILED,
                    error=f"Preconditions not met for {skill_name}"
                ))
                if stop_on_failure:
                    break
                continue
                
            # 执行技能
            result = await skill.execute(context.observation)
            results.append(result)
            
            # 更新观察
            context.observation.update(result.output or {})
            
            # 失败处理
            if result.status == SkillStatus.FAILED and stop_on_failure:
                break
                
        return results
        
    def get_execution_status(self, execution_id: str) -> Optional[ExecutionContext]:
        """获取执行状态"""
        for ctx in self.execution_history:
            if ctx.execution_id == execution_id:
                return ctx
        return None
```

### 10.3 VLA 适配器

```python
# vla/adapter.py
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import torch

class VLAAdapter(ABC):
    """VLA 适配器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
    @abstractmethod
    def load_model(self, checkpoint_path: str):
        """加载模型"""
        pass
        
    @abstractmethod
    def preprocess_observation(self, observation: Dict) -> Dict[str, torch.Tensor]:
        """预处理观察数据"""
        pass
        
    @abstractmethod
    def predict(self, processed_obs: Dict[str, torch.Tensor]) -> np.ndarray:
        """预测动作"""
        pass
        
    def act(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """执行一步推理"""
        # 预处理
        processed = self.preprocess_observation(observation)
        
        # 移动到设备
        processed = {k: v.to(self.device) for k, v in processed.items()}
        
        # 预测
        with torch.no_grad():
            actions = self.predict(processed)
            
        return {
            "actions": actions,
            "horizon": self.config.get("action_horizon", 1)
        }


class LeRobotVLAAdapter(VLAAdapter):
    """LeRobot VLA 适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.action_dim = config.get("action_dim", 7)
        self.obs_horizon = config.get("obs_horizon", 2)
        
    def load_model(self, checkpoint_path: str):
        from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
        # 加载模型权重
        self.model = torch.load(checkpoint_path)
        self.model.to(self.device)
        self.model.eval()
        
    def preprocess_observation(self, observation: Dict) -> Dict[str, torch.Tensor]:
        """将观察数据转换为模型输入"""
        import torchvision.transforms as T
        
        # 图像处理
        image = observation.get("rgb_image")
        if image is not None:
            transform = T.Compose([
                T.ToTensor(),
                T.Resize((224, 224)),
                T.Normalize(mean=[0.485, 0.456, 0.406], 
                          std=[0.229, 0.224, 0.225])
            ])
            image = transform(image).unsqueeze(0)  # [1, 3, 224, 224]
            
        # 状态处理
        state = observation.get("joint_positions", np.zeros(self.action_dim))
        state = torch.FloatTensor(state).unsqueeze(0)  # [1, dof]
        
        # 任务描述编码
        task = observation.get("task_description", "")
        # 这里应该使用文本编码器
        task_embed = torch.zeros(1, 512)  # TODO: 实现文本编码
        
        return {
            "image": image.to(self.device),
            "state": state.to(self.device),
            "task": task_embed.to(self.device)
        }
        
    def predict(self, processed_obs: Dict[str, torch.Tensor]) -> np.ndarray:
        """执行推理"""
        with torch.no_grad():
            output = self.model(**processed_obs)
            
        # 提取动作
        actions = output["action"].cpu().numpy()[0]
        
        # 添加夹爪维度（如果需要）
        if len(actions) < self.action_dim:
            gripper = processed_obs.get("gripper", torch.zeros(1, 1))
            actions = np.concatenate([actions, gripper.cpu().numpy()[0]])
            
        return actions
```

---

## 11. 详细里程碑与验收标准

### Phase 1: 基础架构

| 里程碑 | 时间 | 验收标准 |
|--------|------|----------|
| M1.1 项目初始化 | W1 | - Git 仓库建立<br>- CI/CD 流水线配置完成<br>- 代码模板可用 |
| M1.2 通信基础 | W2 | - ROS2 话题通信正常<br>- 消息定义完成<br>- 单元测试 > 20% |
| M1.3 运动学 | W3 | - IK/FK 求解器实现<br>- 支持 Panda 机械臂<br>- 单元测试 > 30% |
| M1.4 技能框架 | W4 | - Skill 基类实现<br>- SkillRegistry 完成<br>- 单元测试 > 40% |
| M1.5 运动技能 | W5-6 | - MoveSkill 可用<br>- ReachSkill 可用<br>- 集成测试 > 5 个 |
| M1.6 抓取技能 | W6 | - GraspSkill 可用<br>- PlaceSkill 可用 |
| M1.7 感知接入 | W7 | - 相机驱动正常<br>- 图像话题发布 |
| M1.8 Phase 1 演示 | W8 | - 完整演示: "移动到目标 → 抓取 → 移动到目标 → 放置"<br>- 单元测试 > 50%<br>- 集成测试 > 10 个 |

### Phase 2: 机器人适配

| 里程碑 | 时间 | 验收标准 |
|--------|------|----------|
| M2.1 Panda 适配 | W9-10 | - URDF/SRDF 配置完成<br>- 运动参数校准<br>- 控制器调优 |
| M2.2 H1 适配 | W11-12 | - URDF 配置完成<br>- 步态规划器实现<br>- 平衡控制可用 |
| M2.3 UGV 适配 | W13-14 | - 机器人模型配置完成<br>- 导航栈集成<br>- 避障功能可用 |
| M2.4 配置重构 | W15 | - 统一配置格式<br>- 配置加载器完成 |
| M2.5 Phase 2 演示 | W16 | - Panda 演示: 抓取任务<br>- H1 演示: 行走任务<br>- UGV 演示: 导航任务 |

### Phase 3: VLA 集成

| 里程碑 | 时间 | 验收标准 |
|--------|------|----------|
| M3.1 推理服务 | W17-18 | - gRPC 服务正常运行<br>- 延迟 < 100ms |
| M3.2 LeRobot | W19-20 | - LeRobot 适配器完成<br>- 推理测试通过 |
| M3.3 ACT/GR00T | W21-22 | - ACT 适配器完成<br>- GR00T 适配器完成 |
| M3.4 数据采集 | W23-24 | - 演示录制工具完成<br>- 数据集格式定义 |
| M3.5 训练脚本 | W25-26 | - 训练脚本可用<br>- 单机训练验证 |
| M3.6 微调 | W27-28 | - LoRA 微调完成<br>- 全参数微调验证 |
| M3.7 Phase 3 演示 | W29-30 | - VLA 推理演示<br>- 微调模型演示 |

### Phase 4: 高级功能

| 里程碑 | 时间 | 验收标准 |
|--------|------|----------|
| M4.1 LLM 规划 | W31-32 | - LLM 规划器可用<br>- Ollama 集成完成 |
| M4.2 规则规划 | W33-34 | - 规则规划器可用<br>- 技能链生成正常 |
| M4.3 语音 | W35-36 | - ASR 组件完成<br>- TTS 组件完成 |
| M4.4 3D 感知 | W37-38 | - 3D 重建可用<br>- 物体检测集成 |
| M4.5 力控 | W39-40 | - ForceSkill 可用<br>- 阻抗控制实现 |
| M4.6 示教 | W41-42 | - 示教录制完成<br>- 技能生成验证 |
| M4.7 Phase 4 演示 | W43-44 | - 完整任务演示: "语音指令 → 规划 → 执行" |

### Phase 5: 优化与部署

| 里程碑 | 时间 | 验收标准 |
|--------|------|----------|
| M5.1 性能优化 | W45-46 | - 延迟优化报告<br>- 吞吐量提升 2x |
| M5.2 部署 | W47-48 | - Docker 镜像完成<br>- K8s 配置可用 |
| M5.3 监控 | W49 | - 日志系统完成<br>- 监控面板可用 |
| M5.4 文档 | W50 | - API 文档完整<br>- 用户手册完成 |
| M5.5 最终发布 | W51-52 | - v1.0 发布<br>- 演示视频<br>- 发布公告 |

---

## 12. 下一步行动

1. **确认本设计文档** → 用户批准后进入开发
2. **创建 Git 分支** → `feature/universal-embodied-agent`
3. **环境搭建** → Docker 开发环境配置
4. **Phase 1 启动** → 项目结构初始化

---

**文档状态**: ⏳ 待用户审批  
**审批人**: [待定]
