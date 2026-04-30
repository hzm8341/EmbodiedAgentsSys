:orphan:

# EmbodiedAgentsSys 下一步开发计划

> 版本：v0.3.1 → 生产就绪  
> 文档日期：2026年3月  
> 分析基准：代码仓库 `hzm8341/EmbodiedAgentsSys`

---

## 总体优先级原则

**先跑通单条 pick-and-place 的真实闭环，再横向扩展到多 Skill 场景，再纵向增强智能泛化能力。**

| 阶段 | 周期 | 优先级 | 核心目标 |
|------|------|--------|----------|
| 阶段 1 | 0–4 周 | 🔴 必须 | 补全推理闭环（解除阻塞生产的缺口） |
| 阶段 2 | 1–3 月 | 🟡 重要 | 接入真实硬件传感器 |
| 阶段 3 | 3–6 月 | 🟢 增值 | 增强智能泛化能力 |

---

## 阶段 1：补全推理闭环（0–4 周）

> 三处改动打通主干路径，是整个系统距离"能真正跑起来"最近的缺口。

### 任务 1.1：接通 VLA 真实推理

**问题**：`LeRobotVLAAdapter.act()` 直接返回 `np.zeros(7)`，无任何推理逻辑。

**文件**：`agents/clients/vla_adapters/lerobot.py`

**方案**：复用已有的 gRPC 传输层 `agents/clients/lerobot_transport/services.proto`，改写 `act()` 方法：

```python
def act(self, observation, skill_token, termination=None):
    if self._client is None:
        import grpc
        # 使用绝对导入，避免包结构问题
        from agents.clients.lerobot_transport import services_pb2_grpc
        channel = grpc.insecure_channel(f"{self.host}:{self.port}")
        self._client = services_pb2_grpc.LeRobotServiceStub(channel)
        self._initialized = True

    request = build_inference_request(observation, skill_token)
    response = self._client.Predict(request, timeout=5.0)
    return np.array(response.action[:self._action_dim])
```

> ⚠️ 注意：
> - `build_inference_request` 函数需在 `agents/clients/lerobot_transport/utils.py` 中实现
> - gRPC 调用需添加超时和重试机制，防止推理服务不可用时阻塞控制循环
> - 建议添加连接状态检查和自动重连逻辑

**同步改动**：`ACTVLAAdapter` 和 `GR00TVLAAdapter` 的 `act()` 方法同理，分别对接本地模型推理服务。

**验收标准**：`adapter.act(obs, "grasp(object=cube)")` 能返回非零的 7 维动作向量。

---

### 任务 1.2：实现观察获取闭环

**问题**：`VLASkill._get_observation()` 返回空字典 `{}`，控制循环完全无法感知环境变化。

**文件**：`agents/skills/vla_skill.py`

**方案**：在 `VLASkill` 基类中添加 ROS2 话题订阅，实现最小可用观察集：

```python
class VLASkill(ABC):
    def __init__(self, vla_adapter=None, ros_node=None, **kwargs):
        self.vla = vla_adapter
        self._node = ros_node  # 传入 ROS2 节点实例
        self._latest_joint_state = None
        self._latest_image = None
        self._gripper_force = 0.0
        self._setup_subscribers()

    def _setup_subscribers(self):
        if self._node is None:
            return
        
        # ROS2 消息类型导入（需安装 ros-humble-sensor-msgs）
        from sensor_msgs.msg import JointState, Image
        
        self._node.create_subscription(
            JointState, "/joint_states",
            lambda msg: setattr(self, "_latest_joint_state", msg), 10
        )
        self._node.create_subscription(
            Image, "/camera/color/image_raw",
            lambda msg: setattr(self, "_latest_image", msg), 1
        )

    async def _get_observation(self) -> Dict:
        obs = {}
        if self._latest_joint_state:
            obs["joint_positions"] = list(self._latest_joint_state.position)
            obs["joint_velocities"] = list(self._latest_joint_state.velocity)
        if self._latest_image:
            obs["image"] = self._latest_image
        obs["gripper_force"] = self._gripper_force
        return obs
```

**验收标准**：控制循环中每步 `observation` 包含真实关节位置，不再是空字典。

---

### 任务 1.3：实现各 Skill 的终止条件

**问题**：`GraspSkill.check_termination()` 依赖 `observation.get("grasp_success", False)`，但该字段从未被填充，导致技能只能靠 `max_steps` 超时退出。

**文件**：`agents/skills/manipulation/grasp.py` 及其他 Skill

**方案**：将终止条件与真实传感器数据绑定：

```python
# grasp.py
def check_termination(self, observation: Dict) -> bool:
    # 夹爪力超过接触阈值 + 关节位置稳定 → 抓取成功
    gripper_force = observation.get("gripper_force", 0.0)
    return gripper_force > self._contact_threshold  # 默认 0.5N

# place.py
def check_termination(self, observation: Dict) -> bool:
    # 末端位置到达目标位置误差 < 5mm
    current_pos = np.array(observation.get("end_effector_pos", [0,0,0]))
    return np.linalg.norm(current_pos - self.target_position) < 0.005

# reach.py
def check_termination(self, observation: Dict) -> bool:
    current_pos = np.array(observation.get("end_effector_pos", [0,0,0]))
    return np.linalg.norm(current_pos - self.target_position) < 0.01
```

**验收标准**：执行 `GraspSkill` 时，夹取到物体后能在 `max_steps` 之前正常退出并返回 `SUCCESS`。

---

### 阶段 1 任务依赖关系

```
任务 1.1 (VLA 推理) ──┐
                      ├──► 阶段 1 核心闭环
任务 1.2 (观察获取) ──┤
                      │
任务 1.3 (终止条件) ──┘  ←─ 依赖任务 1.2（需要真实观察数据）
```

> **关键路径**：任务 1.2 必须先于 1.3 完成，因为终止条件依赖真实的传感器观察数据。

---

## 阶段 2：接入真实硬件（1–3 月）

> ⚠️ **硬件依赖**：本阶段需要以下物理设备：
> - 力/力矩传感器（如 ATI Mini45 或类似）
> - RGBD 相机（如 RealSense D435i）
> - 7自由度机械臂（如 Franka Panda 或 Universal Robots）
> 
> 如无硬件，可跳过本阶段，使用仿真环境验证。

### 任务 2.1：力传感器接入

**问题**：`ForceController.read_force_sensor()` 对初始值为全零的 `_current_force` 做滤波，没有真实输入。

**文件**：`skills/force_control/force_control.py`

**方案**：增加 ROS2 话题订阅，接入力/力矩传感器数据：

```python
class ForceController:
    def __init__(self, ..., ros_node=None):
        self._node = ros_node
        self._raw_force = np.zeros(6)
        if self._node:
            from geometry_msgs.msg import WrenchStamped
            self._node.create_subscription(
                WrenchStamped, "/ft_sensor/raw",
                self._force_callback, 10
            )

    def _force_callback(self, msg):
        w = msg.wrench
        self._raw_force = np.array([
            w.force.x, w.force.y, w.force.z,
            w.torque.x, w.torque.y, w.torque.z
        ])
        # 触发滤波更新
        self.read_force_sensor(self._raw_force)
```

**验收标准**：`detect_contact()` 在真实接触时返回 `True`，柔顺控制模式能正确触发。

---

### 任务 2.2：3D 感知接入

**问题**：`skills/vision/perception_3d_skill.py` 骨架存在，但缺少将 RGBD 点云转换为目标物体 3D 坐标的实现。框架已定义 `RGBD` 消息类型，但没有消费端。

**文件**：`skills/vision/perception_3d_skill.py`

**方案**：集成 Open3D，从 RGBD 点云提取目标物体位置：

```python
import open3d as o3d

class Perception3DSkill:
    async def localize_object(self, rgbd_msg, target_label: str) -> np.ndarray:
        """从 RGBD 消息返回目标物体的 3D 坐标 [x, y, z]"""
        # 1. 将 ROS2 RGBD 转换为 Open3D 点云
        rgb = ros_image_to_numpy(rgbd_msg.rgb)
        depth = ros_image_to_numpy(rgbd_msg.depth)
        pcd = create_point_cloud(rgb, depth, self.camera_intrinsics)

        # 2. 调用 2D 检测器定位目标（对接 PerceptionSkill）
        bbox = await self._detect_2d(rgb, target_label)

        # 3. 从 BBox 对应区域的点云取均值作为 3D 位置
        roi_points = extract_roi_points(pcd, bbox, depth)
        return np.mean(roi_points, axis=0)
```

**依赖新增**：`pip install open3d` 并在 `pyproject.toml` 中添加 `open3d>=0.17.0`。

**验收标准**：`TaskPlanner` 中 `localize_3d` 步骤能返回真实物体坐标，误差 < 1cm。

---

### 任务 2.3：关节状态实时反馈标准化

**问题**：`agents/models.py` 定义了完整的 `JointState`、`JointTrajectory` 封装，但 Skills 执行过程中没有统一的关节状态访问机制。

**文件**：`agents/skills/vla_skill.py`（在任务 1.2 基础上扩展）

**方案**：在 `VLASkill` 基类中维护关节状态缓存，并提供标准访问方法：

```python
class VLASkill(ABC):
    def get_joint_positions(self) -> np.ndarray:
        if self._latest_joint_state:
            return np.array(self._latest_joint_state.position)
        return np.zeros(7)  # fallback

    def get_end_effector_pose(self) -> np.ndarray:
        """通过 TF2 计算末端位姿，返回 [x, y, z, roll, pitch, yaw]"""
        # 使用 tf2_ros 从关节状态计算正向运动学
        ...
```

**验收标准**：所有 Skills 通过 `self.get_joint_positions()` 统一获取关节状态，不再各自订阅话题。

---

### 任务 2.4：装配技能力控集成

**问题**：`skills/manipulation/assembly_skill.py` 中装配动作依赖力控，但 `ForceController` 未被调用。

**文件**：`skills/manipulation/assembly_skill.py`

**方案**：在装配执行过程中接入力控柔顺模式：

```python
class AssemblySkill:
    async def execute_insertion(self, target_pose):
        # 1. 切换为力控混合模式
        self.force_controller.set_mode(ForceControlMode.HYBRID)

        # 2. 缓慢下压，监控力反馈
        for step in range(100):
            force = self.force_controller._current_force
            result = await self.force_controller.execute(
                np.array([0, 0, -2.0, 0, 0, 0])  # 2N 向下
            )
            if result["status"] == "contact":
                # 接触到位，停止插入
                break
            await asyncio.sleep(0.02)
```

---

## 阶段 3：增强智能能力（3–6 月）

> ⚠️ **服务依赖**：本阶段需要以下服务运行：
> - **Ollama 服务**：本地 LLM 推理服务（推荐 `qwen2.5:3b` 或 `llama3:8b`）
> - **模型推理延迟**：3B 模型单次推理约 200-500ms，需评估是否满足实时控制要求
> 
> 如无 GPU 硬件，可使用云端 API 或跳过 LLM 相关任务。

### 任务 3.1：语义解析升级

**问题**：`SemanticParser` 和 `VoiceCommand` 使用硬编码中文关键词，遇到自然语言变体（如"帮我把那个圆形零件移过去"）完全失效。

**文件**：`agents/components/semantic_parser.py`

**方案**：接入本地 Ollama 服务（框架已有 `agents/clients/ollama.py`），LLM 做意图分类，规则方案作 fallback：

```python
class SemanticParser:
    def __init__(self, use_llm=True, ollama_model="qwen2.5:3b"):
        self.use_llm = use_llm
        self._ollama = OllamaClient(model=ollama_model) if use_llm else None

    async def parse_async(self, text: str) -> Dict[str, Any]:
        if self.use_llm:
            try:
                prompt = f"""
将以下机器人操作指令解析为JSON格式。
输出格式: {{"intent": "motion|grasp|place|task|gripper", "params": {{...}}}}
指令: {text}
只输出JSON，不要其他内容:"""
                response = await self._ollama.generate(prompt)
                return json.loads(response.strip())
            except Exception:
                pass  # fallback to rules
        # 原有规则解析作为 fallback
        return self.parse(text)
```

**验收标准**：对 50 条未见过的自然语言指令，意图识别准确率 > 85%。

---

### 任务 3.2：TaskPlanner 增加执行记忆

**问题**：`TaskPlanner` 每次规划完全无状态，LLM Prompt 不包含任何历史上下文，相似任务无法从经验中受益。

**文件**：`agents/components/task_planner.py`

**方案**：增加任务历史队列，构建 Prompt 时附上最近的成功/失败案例：

```python
from collections import deque

class TaskPlanner:
    def __init__(self, ..., memory_size=10):
        self._history: deque = deque(maxlen=memory_size)

    def _record_execution(self, task_desc: str, plan: TaskPlan, success: bool):
        self._history.append({
            "task": task_desc,
            "task_type": plan.task_type.value,
            "steps": [s.skill_name for s in plan.steps],
            "success": success,
            "duration": plan.estimated_duration
        })

    def _build_planning_prompt(self, task_description, context) -> str:
        history_str = ""
        if self._history:
            recent = list(self._history)[-3:]  # 最近 3 条
            history_str = "\n近期任务历史:\n" + json.dumps(recent, ensure_ascii=False, indent=2)

        return f"""你是机器人任务规划专家。
{history_str}
当前任务: {task_description}
{context.to_prompt_context()}
...（原有 Prompt 内容）"""
```

**验收标准**：同类任务第二次规划时，步骤质量优于首次（通过人工评分对比）。

---

### 任务 3.3：SkillGenerator 端到端打通

**问题**：`SkillGenerator.export_skill()` 是模拟模式，生成的代码 `execute_body` 只有注释，示教→可运行代码这条链路没有真正跑通。

**文件**：`skills/teaching/skill_generator.py`

**方案**：将关键帧的关节角度序列直接硬编码进生成的 `execute()` 方法中，配合 `JointTrajectory` 发送：

```python
def _generate_execute_body(self, frames: List[Dict]) -> str:
    if not frames:
        return "        pass"

    # 提取关键帧关节角度
    keyframes_data = []
    for f in frames:
        if "joint_positions" in f:
            keyframes_data.append(f["joint_positions"])

    keyframes_str = json.dumps(keyframes_data)
    return f"""
        import numpy as np
        keyframes = {keyframes_str}
        for positions in keyframes:
            msg = build_joint_trajectory(positions, duration=0.5)
            self._joint_pub.publish(msg)
            await asyncio.sleep(0.5)
"""

def export_skill(self, skill_id, filename=None, output_dir="./generated_skills"):
    # 移除 _simulated 模式，真实写入文件
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename or f"{skill.name}.py")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(skill.skill_code)
    # 同时写出测试文件
    test_filepath = os.path.join(output_dir, f"test_{skill.name}.py")
    with open(test_filepath, "w", encoding="utf-8") as f:
        f.write(skill.test_code)
    return {"success": True, "filepath": filepath, "test_filepath": test_filepath}
```

**验收标准**：完成一次示教录制后，生成的 `.py` 文件可直接 `python skill_name.py` 运行并复现动作。

---

### 任务 3.4：多机器人协作基础（可选）

**问题**：当前 `EventBus` 是进程内单例，无法跨 ROS2 节点广播事件，限制了多机器人协作。

**文件**：`agents/events/bus.py`

**方案**：增加基于 ROS2 话题的跨节点事件桥接：

```python
class DistributedEventBus(EventBus):
    """扩展 EventBus，支持跨节点事件广播"""

    def __init__(self, ros_node=None, namespace="/agents/events"):
        super().__init__()
        self._ros_node = ros_node
        self._namespace = namespace
        if ros_node:
            self._setup_ros_bridge()

    def _setup_ros_bridge(self):
        from std_msgs.msg import String
        # 发布本节点事件到 ROS2 话题
        self._publisher = self._ros_node.create_publisher(
            String, f"{self._namespace}/broadcast", 10
        )
        # 订阅其他节点的事件
        self._ros_node.create_subscription(
            String, f"{self._namespace}/broadcast",
            self._on_remote_event, 10
        )

    async def publish(self, event: Event) -> None:
        await super().publish(event)
        # 同时广播到 ROS2 网络
        if hasattr(self, "_publisher"):
            msg = String(data=json.dumps({
                "type": event.type,
                "source": event.source,
                "data": str(event.data)
            }))
            self._publisher.publish(msg)
```

---

## 依赖变更汇总

在 `pyproject.toml` 中需新增以下依赖：

```toml
[project]
dependencies = [
    "sugarcoat>=0.5.0",
    "lerobot>=0.1.0",
    "numpy>=1.24.0",
    "pyyaml>=6.0",
    # 阶段 2 新增
    "open3d>=0.17.0",          # 3D 点云处理
    "grpcio>=1.50.0",          # LeRobot gRPC 通信
    "grpcio-tools>=1.50.0",    # protobuf 代码生成
    # 阶段 3 新增（可选）
    "ollama>=0.1.0",           # 本地 LLM 推理
]
```

---

## 测试建议

每个阶段完成后建议新增以下集成测试：

### 阶段 1 完成后
- `tests/test_vla_real_inference.py`：验证适配器能返回非零动作向量
- `tests/test_skill_observation_loop.py`：验证控制循环能感知环境变化
- `tests/test_grasp_termination.py`：验证夹取成功后正常退出

### 阶段 2 完成后
- `tests/test_force_sensor_integration.py`：真实力传感器数据流验证
- `tests/test_3d_localization.py`：物体定位误差 < 1cm 验证
- `tests/test_pick_and_place_e2e.py`：完整端到端 pick-and-place 流程

### 阶段 3 完成后
- `tests/test_semantic_parser_llm.py`：50 条自然语言指令准确率测试
- `tests/test_skill_generator_runnable.py`：生成代码可直接执行验证
- `tests/test_task_planner_memory.py`：历史上下文对规划质量的影响验证

---

## 里程碑定义

| 里程碑 | 条件 | 目标周期 | 备注 |
|--------|------|----------|------|
| M1: 推理闭环 | pick-and-place 在**仿真环境**中跑通完整一次 | 第 4 周 | 阶段 1 交付物 |
| M2: 真实硬件 | 在**真实机械臂**上完成 pick-and-place，成功率 > 80% | 第 12 周 | 阶段 2 交付物 |
| M3: 语音驱动 | 语音指令 → 任务规划 → 执行，端到端跑通 | 第 16 周 | 需阶段 3 部分支持 |
| M4: 生产就绪 | 连续运行 8 小时，任务成功率 > 95%，支持示教新技能 | 第 24 周 | 完整功能交付 |

---

*文档生成日期：2026年3月 | 基于代码静态分析*
