# 通用具身智能 Agent 系统设计规格

**文档版本**: v1.1
**创建日期**: 2026-03-20
**项目**: EmbodiedAgentsSys
**目标场景**: 仓储物流（移动机器人 + 工业机械臂联合作业）
**主要用户**: 工程师/技术人员（部署阶段）

---

## 1. 目标与约束

### 1.1 核心目标

构建一个通用的具身智能 Agent 系统，使工程师只需通过语音描述场景和任务，系统即可自动生成技术方案，评估能力缺口，触发训练管道，并驱动任意机器人执行任务。

### 1.2 关键约束

- **首要落地场景**：仓储物流，移动底盘 + 机械臂联合作业
- **主要用户**：工程师/技术人员，可接受结构化模板和技术细节
- **训练自动化**：分阶段渐进，短期人工主导，长期基于置信度自动化
- **硬件适配策略**：统一抽象接口 + 插件化适配器，不绑定特定品牌
- **方案输出格式**：人可读 Markdown 报告 + 机器可读 YAML 执行方案（双格式）

---

## 2. 系统架构

### 2.1 分层多 Agent 架构

```
用户语音输入
    ↓
[Layer 0] 用户交互层   — 语音模板引导对话 Agent，场景结构化解析
    ↓
[Layer 1] 规划层       — 技术方案生成器，方案确认与版本管理
    ↓
[Layer 2] 能力评估层   — 能力注册表，缺口检测引擎，训练触发器
    ↓
[Layer 3] 技能编排层   — 技能调度器，移动导航，操作技能库
    ↓
[Layer 4] 硬件适配层   — RobotAdapter 统一接口，插件化适配器
    ↓
[Layer 5] 数据与训练层 — 失败数据采集，自动标注，训练管道
```

### 2.2 现有能力映射

| 层级 | 已有 | 待开发 |
|------|------|--------|
| Layer 0 | STT/TTS (speechtotext, texttospeech) | 语音模板引导 Agent，场景结构化解析器 |
| Layer 1 | TaskPlanner, SemanticMap | 技术方案生成器（MD+YAML），方案版本管理 |
| Layer 2 | — | 能力注册表，缺口检测引擎，训练触发器 |
| Layer 3 | 抓取/放置/装配/力控/感知技能，CollisionChecker | 技能调度器，移动导航技能，移动+臂协调器 |
| Layer 4 | AGX Arm, LeRobot 客户端 | RobotAdapter 抽象接口，UR/ROS2/VDA5050 适配器 |
| Layer 5 | VLA适配层（ACT, GR00T, LeRobot）| 失败数据记录器，自动标注管线，训练任务调度，模型版本管理 |

---

## 3. 用户交互层（Layer 0）

### 3.1 场景描述模板（SceneSpec v1.0）

工程师通过语音或填写触发引导式问答，系统将输入结构化为 SceneSpec：

```yaml
scene:
  environment: "仓库A区，货架高度2m，地面平整，光照充足"
  obstacles: ["叉车通道", "固定货架立柱"]

robot:
  type: "mobile_arm"          # mobile / arm / mobile_arm
  model: "unknown"            # 填 unknown 则触发硬件发现流程
  payload_kg: 5
  reach_mm: 800

task:
  goal: "将货架B3位置的红色箱子搬运至打包区C1"
  priority: "normal"          # urgent / normal / low
  success_criteria: "箱子放置误差 < 5cm，无碰撞"

constraints:
  max_cycle_time_s: 30
  safety_zone: "人机协作区，需减速"
  forbidden_zones: ["叉车通道"]
```

对话 Agent 通过逐字段引导问答填充模板，每个字段提供默认值和示例。工程师不需要记忆模板格式。

### 3.2 两阶段确认流程

```
第一阶段（概要方案确认）
  → 展示任务分解 + 风险评估 + 能力缺口列表
  → 工程师选择：[确认] / [修改场景] / [放弃]
  → 超时（默认 5 分钟无响应）：自动保存方案草稿，会话挂起
  → 无可行方案（全为硬缺口）：输出缺口报告，直接跳转训练触发器，不进入第二阶段

第二阶段（详细执行方案确认）
  → 展示完整 YAML 执行方案 + 各步骤参数（缺口步骤标注 status: gap）
  → 工程师选择：[确认执行] / [调整参数] / [模拟运行]
  → 超时（默认 5 分钟）：自动保存，会话挂起
  → LLM 输出格式错误（非法 YAML）：记录错误，退回第一阶段并提示重新生成
```

---

## 4. 规划层（Layer 1）

### 4.1 技术方案生成器

基于 SceneSpec，调用 LLM（扩展现有 TaskPlanner）生成双格式输出：

**Markdown 报告（人可读）**
- 任务分解步骤与预计耗时
- 所需技能清单及置信度
- 风险评估与建议
- 能力缺口高亮标注

**YAML 执行方案（机器可读）**

`capability_gaps` 字段为**信息性字段**，列出检测到缺口的技能 ID。缺口步骤仍出现在 `steps` 中，但标注 `status: gap`，调度器遇到 `status: gap` 的步骤时暂停执行并上报缺口，不中断整个方案（方便工程师审查完整流程）。

```yaml
plan_id: "2026-03-20-001"
steps:
  - skill: navigation.goto
    status: gap            # 硬缺口：技能不存在，调度器到此暂停
    params: {target: "shelf_B3", avoid: ["forklift_lane"]}
    timeout_s: 15
  - skill: vision.detect
    params: {query: "red box", model: "grounded_sam", threshold: 0.85}
  - skill: manipulation.grasp
    params: {force_feedback: true, max_force_n: 20}
  - skill: navigation.goto
    status: gap
    params: {target: "pack_zone_C1"}
  - skill: manipulation.place
    params: {precision_mm: 50}
capability_gaps:
  - skill_id: "navigation.goto"
    gap_type: "hard"       # hard / adapter / performance
    message: "技能不存在，需开发移动导航模块"
```

### 4.1.1 技能命名空间规范

所有技能 ID 使用两级点分命名，格式为 `<domain>.<action>`：

| 域（domain） | 技能示例 | 对应现有 TaskPlanner 动作 |
|------------|--------|----------------------|
| `navigation` | `navigation.goto`, `navigation.dock` | `go_to`, `navigate` |
| `manipulation` | `manipulation.grasp`, `manipulation.place`, `manipulation.assemble` | `pick`→`grasp`, `place` |
| `vision` | `vision.detect`, `vision.segment`, `vision.localize` | `inspect` |
| `force` | `force.push`, `force.insert` | — |

现有 `TaskPlanner` 的平面动作词汇（`go_to`, `pick`, `place`, `inspect`）在扩展时通过映射表转换为新命名空间；新规划器直接使用点分格式输出。旧格式在 Phase 1 期间保持向下兼容。

### 4.2 方案版本管理

每次方案生成记录版本，支持回退。历史方案以新类型 `plan_record` 存储到 SemanticMap 中（SemanticMap 现有条目为空间对象，`plan_record` 为非空间条目，通过 `entry_type` 字段区分，YAML 持久化机制复用不变）。执行结果（成功/失败/部分完成）回写到对应 `plan_record` 条目。

---

## 5. 能力评估层（Layer 2）

### 5.1 能力注册表（RobotCapabilityRegistry）

每个技能注册时声明元数据（YAML 格式）：

```yaml
skill_id: "manipulation.grasp"
version: "1.2.0"
supported_robots: ["agx_arm", "ur5", "ur10", "*"]
requirements:
  sensors: ["rgb_camera", "depth_camera"]
  dof_min: 6
  payload_max_kg: 5
performance:
  success_rate: 0.91
  avg_time_s: 3.2
  last_evaluated: "2026-03-15"
training_data:
  dataset: "grasp_warehouse_v2"
  model: "act_v1.2"
```

Python 访问接口（所有组件通过此接口查询注册表，不直接读 YAML）：

```python
from dataclasses import dataclass
from enum import Enum

class GapType(Enum):
    HARD = "hard"           # 技能不存在
    ADAPTER = "adapter"     # 技能不支持当前机器人
    PERFORMANCE = "performance"  # 成功率低于阈值

@dataclass
class CapabilityResult:
    available: bool
    gap_type: GapType | None
    message: str
    success_rate: float | None

class RobotCapabilityRegistry:
    def register(self, skill_meta: dict) -> None: ...
    def query(self, skill_id: str, robot_type: str) -> CapabilityResult: ...
    def update_performance(self, skill_id: str, metrics: dict) -> None: ...
    def list_gaps(self, plan_steps: list[dict], robot_type: str) -> list[CapabilityResult]: ...
```

### 5.2 缺口检测引擎（三层检查）

```
任务需要某技能
  → ① 技能是否存在？           → 不存在 → 硬缺口
  → ② 技能是否支持当前机器人？  → 不支持 → 适配缺口
  → ③ 成功率是否 ≥ 0.8？       → 不达标 → 性能缺口
```

| 缺口类型 | 短期响应（Phase 1-2）| 长期响应（Phase 3+）|
|--------|-------------------|------------------|
| 硬缺口 | 生成技能开发任务单 + 数据采集指引 | Agent 自动生成技能脚手架 |
| 适配缺口 | 生成适配器开发模板 | 自动尝试 ROS2 通用桥接 |
| 性能缺口 | 生成微调数据集需求 + 训练脚本 | 自动采集失败案例并触发微调 |

---

## 6. 技能编排层（Layer 3）

### 6.1 技能调度器

支持串行、并行、条件分支三种执行模式，基于 YAML 执行方案驱动，与能力注册表集成做运行时能力检查。

### 6.2 移动导航技能栈（仓储物流核心缺口）

```
地图层
  ├── SLAM 建图（cartographer / slam_toolbox）
  ├── 语义地图扩展（复用 SemanticMap，增加导航节点）
  └── 动态障碍物更新（叉车、人员实时位置）

规划层
  ├── 全局路径规划（ROS2 Nav2）
  ├── 局部避障（DWA / TEB）
  └── 任务点管理（货架坐标数据库）

执行层
  ├── MobileAdapter（实现 RobotAdapter 子集）
  ├── 导航状态机（待命/导航中/到达/失败）
  └── 与机械臂的协调接口
```

### 6.3 移动底盘 + 机械臂协调

```
导航到位 → 视觉精定位对齐（±2cm）→ 底盘锁定
  → 机械臂执行操作 → 操作完成 → 底盘解锁 → 导航下一目标
```

协调器负责仲裁两者控制权，防止机械臂运动时底盘意外移动。

**精定位对齐实现**：到位后使用 GroundedSAM 检测货架基准标记（AprilTag 或货架固定特征点），计算末端偏差后通过 `MobileAdapter.dock()` 二次精对齐，目标精度 ±2cm。AprilTag 为首选方案，无标记时退化为颜色/形状特征。

---

## 7. 硬件适配层（Layer 4）

### 7.1 硬件适配器抽象接口

机械臂和移动底盘职责不同，拆分为两个独立 ABC，通过 `RobotCapabilities.robot_type` 区分。

**ArmAdapter（机械臂）**

```python
class ArmAdapter(ABC):
    @abstractmethod
    async def move_to_pose(self, pose: Pose6D, speed: float) -> bool: ...
    @abstractmethod
    async def move_joints(self, angles: list[float], speed: float) -> bool: ...
    @abstractmethod
    async def set_gripper(self, opening: float, force: float) -> bool: ...
    @abstractmethod
    async def get_state(self) -> RobotState: ...
    @abstractmethod
    async def is_ready(self) -> bool: ...
    @abstractmethod
    async def emergency_stop(self) -> None: ...
    @abstractmethod
    def get_capabilities(self) -> RobotCapabilities: ...
```

**MobileAdapter（移动底盘）**

```python
class MobileAdapter(ABC):
    @abstractmethod
    async def navigate_to(self, target: MapPoint, avoid: list[str]) -> bool: ...
    @abstractmethod
    async def get_pose_on_map(self) -> MapPose: ...
    @abstractmethod
    async def set_velocity(self, linear: float, angular: float) -> None: ...
    @abstractmethod
    async def dock(self, dock_pose: MapPose, precision_mm: float) -> bool: ...
    @abstractmethod
    async def is_ready(self) -> bool: ...
    @abstractmethod
    async def emergency_stop(self) -> None: ...
    @abstractmethod
    def get_capabilities(self) -> RobotCapabilities: ...
```

`mobile_arm` 类型的机器人同时持有一个 `ArmAdapter` 和一个 `MobileAdapter` 实例，由协调器统一管理控制权。

### 7.2 适配器插件机制

每个适配器是独立包，通过 `adapter.yaml` 自动发现和注册，无需修改核心代码。

**内置适配器路线图：**

| 适配器 | 目标硬件 | 计划阶段 |
|--------|---------|---------|
| `agx_arm_adapter`（包装现有客户端）| AGX Arm | Phase 1 |
| `lerobot_adapter`（包装现有客户端）| LeRobot | Phase 1 |
| `ur_adapter` | UR3/5/10/16（URScript + RTDE）| Phase 2 |
| `ros2_bridge` | 通用 ROS2 桥接（覆盖长尾机器人）| Phase 2 |
| `nav2_adapter` | ROS2 Nav2 移动底盘 | Phase 2 |
| `vda5050_adapter` | 仓储 AMR 协议，接入第三方 WMS | Phase 2 |
| `fanuc_adapter` | FANUC 系列 | 未排期（社区贡献）|

---

## 8. 数据与训练层（Layer 5）

### 8.1 失败数据自动采集

任务执行时实时保存三类数据：
1. **传感器快照**：失败前 N 帧（默认 30 帧）的 RGB/Depth/点云
2. **机器人状态**：关节角、末端位姿、力传感器读数
3. **任务上下文**：SceneSpec + 执行 YAML + 失败步骤 + 错误类型

**存储估算（每次失败事件）：**
- RGB 30帧 × 640×480 × 3ch ≈ 28 MB
- Depth 30帧 × 640×480 × 2bytes ≈ 18 MB
- 点云（稀疏）≈ 5 MB / 帧 × 5关键帧 ≈ 25 MB
- 状态日志 + 上下文 < 1 MB
- **合计约 70 MB / 次失败**

**Phase 1 存储策略：** 本地 SSD 预留 500 GB，保留最近 30 天数据，超出则按时间戳 FIFO 淘汰。建议使用 LZ4 压缩 RGB/Depth 帧，可降低约 40%。

### 8.2 三阶段训练管道

**阶段一（Phase 1-2，当前）：** 人工主导
- 自动记录失败数据 → 生成标注任务 → 工程师手动标注 → 输出训练配置 + 脚本 → 工程师执行训练 → 注册新模型

**阶段二（Phase 3，6-12个月）：** 半自动
- 置信度低于阈值 → 自动触发数据采集 → VLM 伪标签 → 云端训练 → 仿真自动验证 → 人工审核指标后上线

**阶段三（Phase 4，12个月+）：** 全自动
- 置信度动态阈值 + 全自动部署 + 跨机器人迁移学习

---

## 9. 分阶段开发路线图

### Phase 1（1-3个月）：核心闭环
**目标：** 端到端流程跑通（语音输入 → 方案生成 → 缺口检测 → 训练需求输出）

| 模块 | 说明 |
|------|------|
| 语音模板 Agent | 引导式问答填充 SceneSpec |
| 技术方案生成器 | LLM 生成 MD + YAML，扩展 TaskPlanner |
| 能力注册表 v1 | 静态 YAML 注册 |
| 缺口检测 v1 | 仅检测硬缺口 |
| 失败数据记录器 | 自动保存 3 类数据到本地 |
| 训练脚本生成器 | 输出数据集需求文档和训练配置 |
| ArmAdapter + AGX/LeRobot 包装器 | 将现有 AGX Arm 和 LeRobot 客户端包装为 ArmAdapter 实现，验证接口设计，无需新硬件 |

### Phase 2（3-6个月）：导航 + 联合作业
**目标：** 真实仓储场景移动底盘 + 机械臂联合作业

| 模块 | 说明 |
|------|------|
| 移动导航技能 | Nav2 集成，语义地图扩展 |
| 移动+臂协调器 | 停车对齐、控制权仲裁 |
| 能力注册表 v2 | 动态注册，运行时性能指标更新 |
| 缺口检测 v2 | 增加适配缺口 + 性能缺口 |
| VDA5050 适配器 | 接入第三方 WMS |
| ROS2 通用桥接 | 覆盖非标机器人 |
| 仿真环境集成 | Gazebo/IsaacSim 方案预验证 |

### Phase 3（6-12个月）：半自动训练闭环
| 模块 | 说明 |
|------|------|
| 自动标注管线 | VLM 对失败帧做伪标签 |
| 训练任务调度 | 本地 GPU / 云端，监控进度 |
| 仿真自动验证 | 新模型先跑 N 次，成功率达标提交人审 |
| 模型版本管理 | A/B 测试，新旧模型对比指标 |
| 置信度动态阈值 | 根据场景风险等级自动调整介入阈值 |

### Phase 4（12个月+）：平台化 + 生态开放
| 模块 | 说明 |
|------|------|
| 技能市场 | 适配器/技能的发布、版本管理、评分 |
| 跨机器人迁移学习 | 机器人 A 的技能迁移到机器人 B |
| 多机器人协作调度 | 多 AMR + 多机械臂任务分配优化 |
| 全自动部署管线 | 置信度足够时绕过人工审核直接上线 |

---

## 10. 错误与缺口分类枚举

调度器、仪表盘和 API 响应中统一使用以下结构化类型，不使用裸字符串：

```python
class GapType(Enum):
    HARD = "hard"               # 技能不存在
    ADAPTER = "adapter"         # 技能不支持当前机器人型号
    PERFORMANCE = "performance" # 成功率低于阈值（默认 0.8）

class ExecutionError(Enum):
    SKILL_NOT_FOUND = "skill_not_found"
    ROBOT_NOT_READY = "robot_not_ready"
    TIMEOUT = "timeout"
    SENSOR_FAILURE = "sensor_failure"
    COLLISION_DETECTED = "collision_detected"
    GRASP_FAILURE = "grasp_failure"
    NAVIGATION_FAILURE = "navigation_failure"
    DOCK_ALIGNMENT_FAILURE = "dock_alignment_failure"
    PLAN_INVALID = "plan_invalid"           # LLM 输出非法 YAML
    CAPABILITY_GAP = "capability_gap"       # 执行到 status:gap 步骤

class PlanStatus(Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"         # 部分步骤成功
    SUSPENDED = "suspended"     # 超时挂起
```

---

## 11. 功能优先级总览

```
必须做（Phase 1-2，最小可用系统）
  ├── 语音模板 Agent
  ├── 技术方案生成器（MD + YAML）
  ├── 能力注册表 + 缺口检测
  ├── 失败数据记录器
  ├── 移动导航技能
  ├── 移动+臂协调器
  └── UR / ROS2 适配器

重要但可延后（Phase 3）
  ├── 自动标注管线
  ├── 训练任务调度
  └── 仿真自动验证

长期愿景（Phase 4）
  ├── 技能市场
  ├── 跨机器人迁移学习
  └── 全自动部署
```
