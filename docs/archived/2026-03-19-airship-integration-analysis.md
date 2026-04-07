# Airship 代码库功能评估与借鉴分析

**日期**：2026-03-19
**目标**：评估 `/media/hzm/data_disk/airship` 中可借鉴到 EmbodiedAgentsSys 的功能

---

## 一、Airship 项目概览

**AIRSHIP** 是一个基于 ROS2 的开源具身 AI 机器人软件栈，支持轮式底盘 + 机械臂的复合机器人形态。

### 目录结构

```
/media/hzm/data_disk/airship/
├── airship_chat/              # 语音接口与指令处理
├── airship_grasp/             # 机械臂抓取控制与规划
├── airship_interface/         # ROS2 服务/消息定义
├── airship_localization/      # SLAM 与建图（Cartographer）
├── airship_navigation/        # 路径规划与底盘控制
├── airship_object/            # 语义对象建图
├── airship_perception/        # 视觉目标检测与分割
├── airship_planner/           # 基于 LLM 的任务规划
├── airship_description/       # URDF 机器人描述
├── airship_sim/               # Isaac Sim 仿真环境
├── docs/                      # 文档与安装指南
└── scripts/                   # 安装与测试脚本
```

### 技术栈

- **核心框架**：ROS2 Humble + Python 3.10 + PyTorch 2.3.0
- **AI 模型**：GPT-4 / LLAMA 3.1 70B、GroundingDINO、SAM、GraspNet、Whisper、PocketSphinx
- **硬件**：Nvidia Jetson Orin AGX、Intel RealSense D435、RoboSense Helios 32 LiDAR
- **导航**：NAV2 + Cartographer SLAM
- **机械臂**：Elephant Robotics mycobot 630

### 端到端任务执行流程

```
用户语音 → 唤醒词检测 → Whisper ASR → LLM 任务规划
→ [导航 | 感知 | 抓取] 并行执行 → 错误恢复重规划
```

---

## 二、EmbodiedAgentsSys 当前能力

| 模块 | 现有功能 |
|------|---------|
| VLA 客户端 | ACT、LeRobot、GR00T 模型接入 |
| 推理后端 | Ollama、RoboML 客户端 |
| 感知 | SAM3 分割、Qwen VLM 场景描述 |
| 安全 | CollisionChecker 碰撞检测 |
| 记忆 | Chroma 向量数据库集成 |
| 交互 | Web 仪表盘（摄像头、场景描述、对话） |
| 语音 | SpeechToText 基础组件 |

---

## 三、可借鉴功能详细分析

### P0 - 最高优先级

#### 1. 带历史上下文的错误恢复规划器

**来源**：`airship_planner/airship_planner/task_planner.py` + `llm_planner_node.py`

**核心机制**：
- 任务失败后，将失败历史（在哪里找不到什么对象）附加到 prompt 中
- LLM 基于历史重新生成执行计划
- 支持 GPT-4o 和 LLAMA 3.1（通过 Ollama）双后端

**借鉴价值**：当前项目缺少 retry-with-feedback 机制，加入后可显著提升任务完成率。

**参考 Prompt 模式**：
```python
# 历史上下文格式
history = "Previously tried: flower not found at desk, cup found at table"
prompt = f"Task: {instruction}\nHistory: {history}\nReplan:"
```

---

#### 2. GroundingDINO + SAM 两阶段感知流水线

**来源**：`airship_perception/lib/grounded_sam_api.py` + `seg_service_node.py`

**核心机制**：
- **第一阶段**：GroundingDINO open-vocabulary 检测 → 边界框 + 置信度
- **第二阶段**：SAM 精确分割 → 像素级掩码
- **NMS 后处理**：非极大值抑制去重
- **任务感知过滤**：
  - 抓取模式：返回置信度最高的单个掩码
  - 建图模式：返回所有对象掩码 + 标签

**借鉴价值**：当前 `sam3_segmenter.py` 缺少 open-vocabulary 检测能力，无法处理任意对象名称。

**关键阈值参数**：
```yaml
box_threshold: 0.35      # GroundingDINO 边界框置信度
text_threshold: 0.25     # 文本匹配置信度
nms_threshold: 0.8       # NMS 去重阈值
```

---

### P1 - 高优先级

#### 3. GraspNet 6DoF 抓取姿态合成

**来源**：`airship_grasp/lib/utility_graspnet.py`

**核心机制**：
- 深度图 + RGB → 20K 采样点云（计算效率）
- GraspNet 推理 → 300 视角 × 12 角度 × 4 深度 候选
- **偏航角约束过滤**：限制为 -120° ~ -60°（可达构型）
- **碰撞检测**：过滤与机器人本体/场景障碍物碰撞的姿态
- Scale-Balanced-Grasp 后端（提升小物体抓取成功率）

**借鉴价值**：当前项目有 `collision_checker.py` 但缺少完整的 6DoF 抓取姿态生成链路。

**坐标系变换链**：
```
相机坐标系 → 夹爪坐标系 → 机器人基坐标系 → 世界坐标系
```

---

#### 4. 语义地图 YAML 持久化

**来源**：`airship_object/airship_object/object_map_node.py`

**核心机制**：
- 多线程 3D 对象检测 + 聚类
- 同步深度/RGB/里程计流（ApproximateTimeSynchronizer）
- 基于关键帧的 3D 对象地图构建
- 服务接口：`/airship_object/save_object_nav_goal` → 保存到 YAML

**YAML 格式**：
```yaml
locations:
  desk: [1.2, 0.5, 0.0]      # [x, y, theta]
  table: [3.1, -0.8, 1.57]
objects:
  flower: {location: desk, pos_3d: [1.2, 0.5, 0.85]}
```

**借鉴价值**：LLM 规划时可直接引用地点名称而非坐标，提升规划可解释性。

---

### P2 - 中优先级

#### 5. 唤醒词 + Whisper 语音流水线

**来源**：`airship_chat/airship_chat/chatbot_node.py`

**核心机制**：
- PocketSphinx 持续监听唤醒词（"AIRSHIP"）
- PyAudio 录音 + 自动静音检测（>1秒静音 = 停止）
- OpenAI Whisper ASR 语音转文字
- 音频播放反馈管理

**借鉴价值**：当前 `speechtotext.py` 缺少唤醒词检测，每次都需要手动触发。

---

#### 6. 多传感器流同步模式

**来源**：`airship_object/airship_object/object_map_node.py`

**核心机制**：
```python
from message_filters import ApproximateTimeSynchronizer, Subscriber
sync = ApproximateTimeSynchronizer(
    [depth_sub, rgb_sub, odom_sub],
    queue_size=10,
    slop=0.1  # 100ms 时间容差
)
sync.registerCallback(self.synchronized_callback)
```

**借鉴价值**：多摄像头或深度+RGB 联合处理场景的标准同步方案。

---

#### 7. 精细化导航状态码

**来源**：`airship_navigation/airship_navigation/navigation_service_node.py`

**5 级状态码**：
```python
SUCCESS = 0          # 精确到达目标
CLOSEST_POINT = 1    # 到达最近可达点
PATH_FAIL = 2        # 路径规划失败
TIMEOUT = 3          # 超时
GENERIC_FAIL = 4     # 其他失败
```

**借鉴价值**：比 bool 粗粒度状态更利于上层任务规划器做决策。

---

## 四、优先级汇总

| 优先级 | 功能 | 工作量 | 收益 |
|--------|------|--------|------|
| P0 | 带历史上下文的错误恢复规划器 | 中 | 显著提升任务完成率 |
| P0 | GroundingDINO + SAM 两阶段感知 | 中 | 支持任意对象名称检测 |
| P1 | GraspNet 6DoF 抓取姿态合成 | 高 | 补全抓取执行链路 |
| P1 | 语义地图 YAML 持久化 | 低 | LLM 规划空间锚定 |
| P2 | 唤醒词 + Whisper 流水线 | 低 | 提升自然交互体验 |
| P2 | 多传感器流同步模式 | 低 | 标准化多模态数据处理 |
| P2 | 精细化导航状态码 | 低 | 改善错误处理粒度 |

---

## 五、建议集成路径

```
阶段 1：感知增强
  └─ 集成 GroundingDINO → 升级 sam3_segmenter 为两阶段流水线

阶段 2：规划增强
  └─ 为 semantic_parser + llm 组件添加错误恢复机制
  └─ 实现语义地图 YAML 持久化

阶段 3：执行增强
  └─ 集成 GraspNet 抓取姿态生成
  └─ 完善导航状态码

阶段 4：交互增强
  └─ 升级 speechtotext 添加唤醒词检测
```

---

**参考代码路径**：`/media/hzm/data_disk/airship/`
**关联计划文档**：[2026-03-06-airship-integration.md](2026-03-06-airship-integration.md)
