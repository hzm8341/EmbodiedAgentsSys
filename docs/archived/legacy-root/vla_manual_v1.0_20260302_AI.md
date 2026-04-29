# VLA组件使用手册

## 概述

Vision-Language-Action（VLA）组件是EmbodiedAgents框架中用于部署视觉-语言-动作模型的核心组件。该组件将视觉观察和自然语言指令作为输入，经过VLA模型推理后输出直接的机器人关节命令，实现端到端的机器人控制。

VLA组件与HuggingFace的LeRobot生态系统深度集成，支持多种先进的VLA策略架构，包括SmolVLA、ACT、Pi0、Pi0.5和Diffusion策略。通过ROS2 Action Server接口，用户可以以自然语言任务描述的方式触发机器人动作执行。

## 核心特性

VLA组件提供以下核心功能特性：

**多模态输入处理**：组件支持同时接收关节状态（位置、速度、加速度、力矩）和多路相机图像输入，能够将机器人本体感知与视觉观察进行融合处理。

**动作分块机制**：针对实时控制场景，VLA组件实现了动作分块（Action Chunking）功能。每次模型推理可以产生多个连续的动作帧，组件通过异步队列机制管理这些动作，确保动作执行的时序一致性。

**安全限幅保护**：组件内置关节限位保护机制，支持通过URDF文件自动解析关节运动范围，也可手动配置关节限位参数。在动作发送至机器人前，系统会自动裁剪超出安全范围的动作值。

**灵活的任务终止**：提供三种任务终止模式——基于时间步数的自动终止、基于键盘输入的主动终止、以及基于外部事件的触发终止，适应不同的任务执行场景。

**实时反馈监控**：在动作执行过程中，组件会持续发布反馈信息，包括当前执行的时间步数和任务完成状态，便于上位系统进行监控和决策。

## 系统架构

VLA组件采用客户端-服务器架构设计。组件本身作为ROS2节点运行，负责传感器数据采集和动作命令发布；模型推理则由独立的LeRobot Policy Server负责处理。这种设计将计算密集型任务与ROS2实时控制环分离，提高了系统的整体性能和稳定性。

组件接收到传感器数据后，首先进行数据预处理和格式转换，然后通过gRPC协议将观察数据发送至LeRobot Policy Server。服务器完成模型推理后返回动作序列，组件接收这些动作并经过安全检查后发布到机器人控制主题。整个数据流采用异步机制，观察发送和动作接收由独立的定时器管理，确保控制环的实时性。

## 安装依赖

在使用VLA组件之前，需要安装以下依赖项：

```bash
# 安装gRPC和协议缓冲区
pip install grpcio protobuf

# 安装PyTorch（推荐使用CPU版本以降低资源消耗）
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 安装LeRobot（用于模型服务）
pip install lerobot
```

启动LeRobot Policy Server的命令格式如下：

```bash
python -m lerobot.async_inference.policy_server --host=<服务器地址> --port=<端口号>
```

## 配置参数详解

VLAConfig类提供了丰富的配置选项，用于定制VLA组件的行为。以下是各配置参数的详细说明：

### 必需参数

**joint_names_map**：字典类型，指定模型期望的关节名称与机器人实际URDF关节名称之间的映射关系。字典的键（key）为模型训练时使用的关节名称，值（value）为机器人URDF中定义的关节名称。

```python
joint_names_map={
    "shoulder_pan.pos": "Rotation",
    "shoulder_lift.pos": "Pitch",
    "elbow_flex.pos": "Elbow",
    "wrist_flex.pos": "Wrist_Pitch",
    "wrist_roll.pos": "Wrist_Roll",
    "gripper.pos": "Jaw",
}
```

**camera_inputs_map**：字典类型，指定模型期望的相机名称与ROS图像主题之间的映射关系。字典的键（key）为模型训练时使用的相机名称，值（value）为ROS Topic对象或包含主题名称的字典。

```python
camera_inputs_map={
    "front": camera1,
    "wrist": camera2,
}
```

### 可选参数

**state_input_type**：字符串类型，指定从关节状态输入中提取的数据类型。可选值为"positions"（位置）、"velocities"（速度）、"accelerations"（加速度）、"efforts"（力矩）。默认值为"positions"。

**action_output_type**：字符串类型，指定发布到机器人控制器的动作数据类型。可选值与state_input_type相同。默认值为"positions"。

**observation_sending_rate**：浮点数类型，观察数据发送给模型的频率，单位为Hz。默认值为10.0 Hz。

**action_sending_rate**：浮点数类型，动作命令发布到机器人的频率，单位为Hz。默认值为10.0 Hz。

**input_timeout**：浮点数类型，等待所有必要输入（关节和图像）可用的超时时间，单位为秒。默认值为30.0秒。

**robot_urdf_file**：字符串类型，机器人URDF文件的路径。强烈建议提供此参数，以便组件读取关节限位并进行安全限幅。

**joint_limits**：字典类型，当未提供URDF文件时的手动关节限位配置。格式应与解析后的URDF限位一致。

## LeRobotPolicy模型定义

LeRobotPolicy类用于定义要使用的VLA策略模型。以下是主要配置选项：

### 必需参数

**checkpoint**：字符串类型，模型检查点的名称或路径，可以是HuggingFace Hub上的模型标识符，也可以是本地模型路径。

**policy_type**：字符串类型，指定策略架构类型。可选值包括：

- "smolvla"：SmolVLA通用VLA模型
- "act"：Action Chunking Transformer（动作分块Transformer）
- "diffusion"：扩散策略模型
- "pi0"：Physical Intelligence的Pi0模型
- "pi05"：Physical Intelligence的Pi0.5模型

### 可选参数

**actions_per_chunk**：整数类型，每次推理产生的动作数量。该参数仅适用于实现了实时分块（Real Time Chunking）的策略类型，如Pi0和SmolVLA。ACT策略可能有固定的分块大小。默认值为50。

**policy_device**：字符串类型，模型在服务器上运行的设备。可选值为"cuda"（GPU）或"cpu"。默认值为"cuda"。

**dataset_info_file**：字符串类型，数据集元数据文件（info.json）的URL或本地路径。该文件定义了模型的输入特征和动作结构。如果未提供，VLA组件将尝试根据组件配置自动生成。

```python
policy = LeRobotPolicy(
    name="my_policy",
    policy_type="act",
    checkpoint="<your-ACT-checkpoint>",
    dataset_info_file="https://example.com/dataset/info.json",
    actions_per_chunk=100,
)
```

## 基本使用示例

以下是一个完整的基本使用示例，展示了如何配置和使用VLA组件：

```python
from agents.components import VLA
from agents.config import VLAConfig
from agents.clients import LeRobotClient
from agents.models import LeRobotPolicy
from agents.ros import Topic, Launcher

# 定义ROS主题
state = Topic(name="/robot/joint_states", msg_type="JointState")
camera1 = Topic(name="/camera/front/image_raw", msg_type="Image")
camera2 = Topic(name="/camera/wrist/image_raw", msg_type="Image")
joints_action = Topic(name="/robot/joint_command", msg_type="JointState")

# 定义策略模型
policy = LeRobotPolicy(
    name="my_policy",
    policy_type="smolvla",
    checkpoint="lerobot/smolvla_base",
    dataset_info_file="https://huggingface.co/datasets/lerobot/lerobot_info/resolve/main/aloha_sim_insertion_human/info.json",
)

# 创建LeRobot客户端
client = LeRobotClient(model=policy)

# 配置关节和相机映射
joints_map = {
    "joint_0": "shoulder_pan",
    "joint_1": "shoulder_lift",
    "joint_2": "elbow_flex",
    "joint_3": "wrist_flex",
    "joint_4": "wrist_roll",
    "joint_5": "gripper",
}

camera_map = {"top": camera1, "wrist": camera2}

# 创建VLA配置
config = VLAConfig(
    observation_sending_rate=10.0,
    action_sending_rate=10.0,
    joint_names_map=joints_map,
    camera_inputs_map=camera_map,
    robot_urdf_file="/path/to/robot.urdf"
)

# 创建VLA组件
vla = VLA(
    inputs=[state, camera1, camera2],
    outputs=[joints_action],
    model_client=client,
    config=config,
    component_name="vla_controller"
)

# 设置终止触发条件
vla.set_termination_trigger("timesteps", max_timesteps=100)

# 启动组件
launcher = Launcher()
launcher.add_pkg(components=[vla])
launcher.bringup()
```

## ACT模型接入指南

Action Chunking Transformer（ACT）是一种高效的机器人控制策略，能够在单次推理中生成多个时间步的动作序列。VLA组件对ACT提供了原生支持。

### 接入步骤

首先，在LeRobotPolicy中指定policy_type为"act"：

```python
from agents.models import LeRobotPolicy

# 定义ACT策略
policy = LeRobotPolicy(
    name="act_policy",
    policy_type="act",
    checkpoint="<your-ACT-checkpoint>",
    dataset_info_file="<path-to-dataset-info>",
    actions_per_chunk=100,  # ACT会输出100个动作
)
```

然后，按照标准流程创建VLA组件：

```python
from agents.components import VLA
from agents.config import VLAConfig
from agents.clients import LeRobotClient

# 创建客户端
client = LeRobotClient(model=policy)

# 配置映射关系
config = VLAConfig(
    joint_names_map={
        "joint_0": "robot_shoulder_pan",
        "joint_1": "robot_shoulder_lift",
        "joint_2": "robot_elbow",
        "joint_3": "robot_wrist_flex",
        "joint_4": "robot_wrist_roll",
    },
    camera_inputs_map={"front": camera1},
    observation_sending_rate=10.0,
    action_sending_rate=10.0,
    robot_urdf_file="/path/to/robot.urdf"
)

# 创建VLA组件
vla = VLA(
    inputs=[state, camera1],
    outputs=[joints_action],
    model_client=client,
    config=config,
    component_name="act_controller"
)

# 设置终止条件
vla.set_termination_trigger("timesteps", max_timesteps=200)
```

### 发送任务命令

使用ROS2 action命令发送任务：

```bash
ros2 action send_goal /act_controller/vision_language_action automatika_embodied_agents/action/VisionLanguageAction "{task: 'pick up the object'}"
```

### ACT调优建议

针对ACT策略，以下是一些调优建议：

**actions_per_chunk参数**：ACT模型通常有固定的动作分块大小，但可以通过调整此参数来平衡推理延迟和动作平滑度。较大的值会产生更多动作但增加单次推理时间。

**observation_sending_rate**：建议设置为与机器人实际控制频率匹配。对于ACT，10-30Hz是常见的配置范围。

**action_sending_rate**：此参数决定了动作发布到机器人的频率。如果actions_per_chunk较大，可以适当降低此频率。

## Pi0.5模型接入指南

π0.5（Pi0.5）是由Physical Intelligence开发的下一代视觉-语言-动作模型，具有强大的开放世界泛化能力。与其他VLA模型相比，Pi0.5采用了独特的双层专家架构，能够在全新环境中无需微调直接部署。

### Pi0.5技术特点

**双层专家架构**：Pi0.5模型内部包含两个专业化的处理路径。高层路径使用视觉语言模型（VLM）进行推理，理解场景和任务目标；低层路径是一个专用的动作专家（Action Expert），负责生成具体的机器人动作。这种设计类似于人类的"思考后行动"模式。

**动作分块输出**：Pi0.5每次推理会输出一个50步（约1秒）的动作块，实现了连续平滑的动作执行。通过实时分块（Real-Time Chunking，RTC）技术，可以进一步优化动作执行的流畅性和响应速度。

**零样本泛化**：由于采用异构数据协同训练策略，Pi0.5能够在未经训练的新环境中直接工作，具有出色的零样本泛化能力。

### 安装依赖

使用Pi0.5需要安装额外的Physical Intelligence依赖：

```bash
pip install -e ".[pi]"
```

这个命令会安装Pi0系列模型所需的额外依赖包。

### 启动Pi0.5 Policy Server

启动支持Pi0.5的LeRobot Policy Server：

```bash
python -m lerobot.async_inference.policy_server \\
    --host=<服务器地址> \\
    --port=<端口号> \\
    --policy.type=pi05 \\
    --policy.pretrained_name_or_path=lerobot/pi05_base \\
    --policy.actions_per_chunk=50 \\
    --policy_device=cuda
```

### 接入步骤

在EmbodiedAgents中使用Pi0.5的步骤如下：

```python
from agents.models import LeRobotPolicy

# 定义Pi0.5策略
policy = LeRobotPolicy(
    name="pi05_policy",
    policy_type="pi05",
    checkpoint="lerobot/pi05_base",  # 使用官方预训练模型
    dataset_info_file="<path-to-dataset-info>",
    actions_per_chunk=50,  # Pi0.5默认输出50步动作
)
```

创建VLA组件：

```python
from agents.components import VLA
from agents.config import VLAConfig
from agents.clients import LeRobotClient

# 创建客户端
client = LeRobotClient(model=policy)

# Pi0.5配置示例
config = VLAConfig(
    joint_names_map={
        "joint_0": "robot_shoulder_pan",
        "joint_1": "robot_shoulder_lift",
        "joint_2": "robot_elbow",
        "joint_3": "robot_wrist_flex",
        "joint_4": "robot_wrist_roll",
        "joint_5": "gripper",
    },
    camera_inputs_map={"main": camera1},
    # Pi0.5推荐设置
    observation_sending_rate=10.0,  # 观察频率
    action_sending_rate=50.0,       # 动作发送频率（与chunk大小匹配）
    robot_urdf_file="/path/to/robot.urdf"
)

# 创建VLA组件
vla = VLA(
    inputs=[state, camera1],
    outputs=[joints_action],
    model_client=client,
    config=config,
    component_name="pi05_controller"
)

# 设置终止条件（Pi0.5单次推理产生50步动作）
vla.set_termination_trigger("timesteps", max_timesteps=100)
```

### 发送任务命令

使用ROS2 action命令发送自然语言任务：

```bash
ros2 action send_goal /pi05_controller/vision_language_action automatika_embodied_agents/action/VisionLanguageAction "{task: 'pick up the cup and place it on the table'}"
```

Pi0.5的优势在于，即使任务描述比较抽象（如"整理桌面"），模型也能理解并执行相应的动作序列。

### Pi0.5调优建议

**actions_per_chunk参数**：Pi0.5默认输出50步动作，对应约1秒的执行时间。可以根据需要调整：
- 较短的chunk（如25步）：更快的响应速度，但可能影响动作平滑度
- 较长的chunk（如100步）：更平滑的动作，但响应延迟增加

**实时分块（RTC）配置**：对于需要更平滑过渡的场景，可以启用RTC。RTC通过混合相邻动作块来确保动作执行的平滑过渡，特别适合需要精细控制的场景。

**频率设置建议**：

| 应用场景 | observation_sending_rate | action_sending_rate | actions_per_chunk |
|---------|------------------------|-------------------|------------------|
| 精细操作 | 20-30 Hz | 50-100 Hz | 25-50 |
| 一般任务 | 10 Hz | 50 Hz | 50 |
| 慢速演示 | 5 Hz | 25 Hz | 100 |

### 与其他模型的对比

| 特性 | SmolVLA | ACT | Pi0 | Pi0.5 |
|------|---------|-----|-----|--------|
| 参数量 | 较小 | 中等 | 较大 | 较大 |
| 动作分块 | 50步 | 可配置 | 50步 | 50步 |
| 零样本泛化 | 有限 | 有限 | 较好 | 优秀 |
| 双层架构 | 否 | 否 | 否 | 是 |
| 推荐场景 | 快速原型 | 特定任务 | 复杂任务 | 开放环境 |

### 常见问题处理

**动作不连续**：如果观察到机器人动作有跳跃，尝试启用动作聚合函数：

```python
import numpy as np

def smooth_aggregation(existing_action, new_action, alpha=0.7):
    """指数移动平均聚合"""
    return alpha * existing_action + (1 - alpha) * new_action

vla.set_aggregation_function(smooth_aggregation)
```

**推理超时**：如果遇到推理超时错误，确认GPU内存充足、减少相机输入数量或降低图像分辨率。

**模型加载失败**：如果Pi0.5模型无法加载，确认已安装`pip install -e ".[pi]"`依赖、检查模型名称是否正确（如`lerobot/pi05_base`）以及确认dataset_info_file格式正确。

## 高级功能

### 自定义动作聚合函数

VLA组件支持自定义动作聚合函数，用于合并来自模型的不同时间步的动作：

```python
import numpy as np

def custom_aggregation(existing_action, new_action):
    """简单的线性插值聚合"""
    return (existing_action + new_action) / 2.0

vla.set_aggregation_function(custom_aggregation)
```

聚合函数必须接受两个numpy数组作为输入，并返回一个numpy数组。

### 事件驱动的任务终止

除了基于时间步的终止方式，VLA组件还支持基于外部事件的终止：

```python
from agents.ros import Event

# 创建停止事件
stop_event = Event(name="task_completed")

# 配置为事件驱动模式
vla.set_termination_trigger(
    mode="event",
    stop_event=stop_event,
    max_timesteps=500
)

# 当其他组件发布该事件时，任务终止
```

### 键盘终止模式

在调试过程中，可以使用键盘手动终止任务：

```python
vla.set_termination_trigger(
    mode="keyboard",
    stop_key="q",  # 按q键终止
    max_timesteps=1000
)
```

### 动态模型客户端切换

VLA组件支持在运行时动态切换模型客户端，实现自适应控制：

```python
# 备用策略
backup_policy = LeRobotPolicy(
    name="backup_policy",
    policy_type="smolvla",
    checkpoint="lerobot/smolvla_base"
)
backup_client = LeRobotClient(model=backup_policy)

# 注册备用客户端
vla.additional_model_clients = {"backup": backup_client}

# 基于条件切换
if condition:
    vla.change_model_client("backup")
```

## 故障排除

### 连接问题

如果无法连接到LeRobot Policy Server，请检查以下几点：

确认LeRobot服务是否正在运行，尝试使用telnet或nc测试连接：

```bash
nc -zv <host> <port>
```

检查防火墙设置，确保gRPC端口未被阻止。

验证模型检查点路径是否正确，错误的路径会导致初始化失败。

### 映射错误

如果遇到关节名称映射错误：

确保joint_names_map中的所有键都存在于模型的数据集定义中。

验证机器人URDF中的关节名称拼写是否正确。

使用更详细的日志级别进行调试：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 动作限幅问题

如果机器人动作被频繁限幅：

检查URDF文件中的关节限位值是否正确。

考虑增加safety margin：

```python
# 在获取动作后添加自定义安全检查
def custom_safety_check(action):
    # 自定义安全逻辑
    return action
```

### 性能问题

如果推理延迟过高：

降低observation_sending_rate和action_sending_rate。

减少相机数量或降低图像分辨率。

使用GPU版本的PyTorch以加速推理。

考虑使用更轻量的模型如SmolVLA。

## 最佳实践

**安全第一**：始终提供URDF文件以启用关节限位保护。在首次运行新机器人配置时，先在仿真环境中测试。

**日志记录**：启用详细日志以便调试。使用组件的get_logger()方法：

```python
vla.get_logger().set_level(logging.DEBUG)
```

**监控反馈**：订阅VLA组件的反馈主题以监控任务执行状态：

```bash
ros2 topic echo /vla_controller/feedback
```

**资源管理**：确保LeRobot服务器有足够的计算资源。使用CPU推理时，延迟可能较高。

**模型选择**：根据任务复杂度选择合适的策略。简单任务可使用SmolVLA，复杂任务可考虑Pi0或ACT。

## 扩展阅读

更多示例和高级用法请参考以下资源：

- [VLA与事件集成示例](../../examples/planning_control/vla_with_event.md)
- [LeRobot官方文档](https://huggingface.co/docs/lerobot)
- [EmbodiedAgents官方文档](https://automatika-robotics.github.io/embodied-agents/)
