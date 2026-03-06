# EmbodiedAgents 技术报告

## 1. 项目概述

**EmbodiedAgents** 是一个用于部署 **Physical AI（物理AI）** 的生产级框架，由 [Automatika Robotics](https://automatikarobotics.com/) 与 [Inria](https://inria.fr/) 合作开发。该框架使开发者能够创建交互式的物理智能体，这些智能体不仅能够对话，还能够理解、移动、操作并适应其所在的环境。

### 1.1 核心特性

| 特性 | 描述 |
|------|------|
| **生产就绪** | 提供稳健的编排层，使Physical AI的部署变得简单、可扩展且可靠 |
| **自引用逻辑** | 创建具有自我意识的智能体，能够根据内部或外部事件启动、停止或重新配置组件 |
| **时空记忆** | 利用具身原语如分层时空记忆和语义路由，构建任意复杂的信息流图 |
| **纯Python，原生ROS2** | 使用标准Python定义复杂的异步图，无需接触XML启动文件，完全兼容ROS2生态系统 |
| **动态Web UI** | 基于FastHTML自动生成完全动态的Web UI，提供即时控制和可视化 |

### 1.2 项目信息

- **版本**: 0.3.1
- **许可证**: MIT
- **Python版本**: 3.8+
- **ROS2版本**: Humble+
- **依赖**: Sugarcoat (automatika-ros-sugar) >= 0.5.0

---

## 2. 项目架构

### 2.1 目录结构

```
ros-agents/
├── agents/                    # 核心代码
│   ├── __init__.py           # 包初始化，含Sugarcoat版本检查
│   ├── config.py              # 配置类定义
│   ├── models.py              # 模型定义
│   ├── ros.py                 # ROS类型和Topic抽象
│   ├── callbacks.py            # ROS回调处理
│   ├── publisher.py            # 发布者
│   ├── ui_elements.py          # UI元素
│   ├── vectordbs.py            # 向量数据库
│   ├── components/            # 组件实现
│   │   ├── component_base.py   # 组件基类
│   │   ├── model_component.py  # 模型组件基类
│   │   ├── llm.py              # LLM组件
│   │   ├── mllm.py             # 多模态LLM组件
│   │   ├── vla.py              # VLA组件
│   │   ├── vision.py           # 视觉组件
│   │   ├── speechtotext.py     # 语音转文本组件
│   │   ├── texttospeech.py     # 文本转语音组件
│   │   ├── semantic_router.py  # 语义路由组件
│   │   ├── map_encoding.py     # 地图编码组件
│   │   └── imagestovideo.py   # 图像转视频组件
│   ├── clients/               # 模型客户端
│   │   ├── model_base.py       # 客户端基类
│   │   ├── db_base.py          # 数据库客户端基类
│   │   ├── generic.py          # 通用HTTP客户端
│   │   ├── ollama.py           # Ollama客户端
│   │   ├── roboml.py           # RoboML客户端
│   │   ├── lerobot.py          # LeRobot客户端
│   │   └── chroma.py           # ChromaDB客户端
│   └── utils/                  # 工具函数
│       ├── utils.py            # 通用工具
│       ├── vision.py           # 视觉工具
│       ├── voice.py            # 语音工具
│       ├── actions.py          # 动作工具
│       └── pluralize.py        # 复数工具
├── msg/                        # ROS消息定义
│   ├── Video.msg
│   ├── Trackings.msg
│   ├── Detections2D.msg
│   ├── Bbox2D.msg
│   ├── Point2D.msg
│   └── ...
├── examples/                   # 示例代码
│   ├── complete_agent.py
│   ├── tool_calling.py
│   ├── semantic_router.py
│   └── ...
├── docs/                       # 文档
│   ├── quickstart.md
│   ├── installation.md
│   ├── basics/
│   └── examples/
├── tests/                      # 测试
│   └── test_clients.py
├── pyproject.toml             # 项目配置
├── package.xml                # ROS包配置
└── CMakeLists.txt             # CMake配置
```

### 2.2 架构分层

```
┌─────────────────────────────────────────┐
│           应用层 (Examples)              │
├─────────────────────────────────────────┤
│           组件层 (Components)           │
│  LLM | VLM | VLA | Vision | STT | TTS  │
├─────────────────────────────────────────┤
│           客户端层 (Clients)             │
│  Ollama | RoboML | LeRobot | Generic   │
├─────────────────────────────────────────┤
│           模型层 (Models)               │
│  LLM | MLLM | VLA | TTS | STT | Vision │
├─────────────────────────────────────────┤
│         ROS2/Sugarcoat 层               │
├─────────────────────────────────────────┤
│           ROS2 底层                      │
└─────────────────────────────────────────┘
```

---

## 3. 核心组件详解

### 3.1 组件系统

EmbodiedAgents中的每个组件本质上是对ROS2生命周期节点的语法抽象。组件构成智能体图的基本执行单元。

#### 组件基类 (Component)

```python
class Component(BaseComponent):
    def __init__(
        self,
        inputs: Optional[Sequence[Union[Topic, FixedInput]]] = None,
        outputs: Optional[Sequence[Topic]] = None,
        config: Optional[BaseComponentConfig] = None,
        trigger: Union[Topic, List[Topic], float, Event, NoneType] = 1.0,
        component_name: str = "agents_component",
        **kwargs,
    ):
```

**关键特性**:
- **输入/输出**: 通过Topic定义，支持固定输入(FixedInput)
- **触发机制**: 支持事件触发 Topic、定时触发(频率)、Event触发
- **类型验证**: 运行时验证输入/输出类型

#### 运行类型

| 类型 | 描述 |
|------|------|
| `TIMED` | 定时执行，基于指定频率 |
| `EVENT` | 事件驱动，基于Topic或Event触发 |
| `ACTION_SERVER` | Action服务模式 |
| `SERVER` | 服务器模式 |

### 3.2 内置组件

| 组件 | 文件 | 功能 |
|------|------|------|
| **LLM** | llm.py | 大语言模型处理，支持RAG、工具调用 |
| **VLM/MLLM** | mllm.py | 多模态LLM，处理文本+图像 |
| **VLA** | vla.py | 视觉语言动作模型，用于操作和控制 |
| **SpeechToText** | speechtotext.py | 语音识别，支持VAD和唤醒词 |
| **TextToSpeech** | texttospeech.py | 语音合成 |
| **Vision** | vision.py | 目标检测与跟踪 |
| **SemanticRouter** | semantic_router.py | 语义路由，基于向量匹配 |
| **MapEncoding** | map_encoding.py | 时空记忆，语义地图 |
| **VideoMessageMaker** | imagestovideo.py | 视频消息生成 |

---

## 4. 模型客户端系统

### 4.1 客户端架构

```
ModelClient (ABC)
├── GenericHTTPClient      # OpenAI兼容API
├── OllamaClient           # Ollama
├── RoboMLHTTPClient       # RoboML HTTP
├── RoboMLWSClient         # RoboML WebSocket
├── RoboMLRESPClient       # RoboML RESP
├── LeRobotClient          # LeRobot VLA
└── ChromaClient           # ChromaDB
```

### 4.2 支持的模型

#### 语言模型 (LLM)

| 模型类 | 说明 |
|--------|------|
| `GenericLLM` | OpenAI兼容API |
| `OllamaModel` | Ollama |
| `TransformersLLM` | HuggingFace Transformers |
| `RoboBrain2` | BAAI RoboBrain 2.0 |

#### 多模态模型 (MLLM)

| 模型类 | 说明 |
|--------|------|
| `GenericMLLM` | OpenAI兼容多模态 |
| `TransformersMLLM` | HuggingFace多模态 |
| `VLMConfig` = `MLLMConfig` | VLM配置 |

#### 视觉模型

| 模型类 | 说明 |
|--------|------|
| `VisionModel` | mmdet目标检测 |
| `RoboBrain2` | 视觉推理 |

#### 语音模型

| 模型类 | 说明 |
|--------|------|
| `Whisper` | 语音识别 (OpenAI) |
| `GenericSTT` | 通用语音识别 |
| `SpeechT5` | 语音合成 (Microsoft) |
| `Bark` | 语音合成 (SunoAI) |
| `MeloTTS` | 语音合成 (MyShell) |
| `GenericTTS` | 通用语音合成 |

#### VLA模型

| 模型类 | 说明 |
|--------|------|
| `LeRobotPolicy` | HuggingFace LeRobot |

---

## 5. 配置系统

### 5.1 配置类层次

```
BaseComponentConfig
├── ModelComponentConfig
│   ├── LLMConfig
│   │   └── MLLMConfig (VLMConfig)
│   └── VLAConfig
├── VisionConfig
├── SpeechToTextConfig
├── TextToSpeechConfig
├── MapConfig
├── SemanticRouterConfig
└── VideoMessageMakerConfig
```

### 5.2 关键配置参数

#### LLMConfig

```python
@define(kw_only=True)
class LLMConfig(ModelComponentConfig):
    enable_rag: bool = False                    # 启用RAG
    collection_name: Optional[str] = None       # 向量数据库集合名
    distance_func: Literal["l2", "ip", "cosine"] = "l2"
    n_results: int = 1                         # RAG返回数量
    chat_history: bool = False                  # 聊天历史
    temperature: float = 0.8
    max_new_tokens: int = 500
    stream: bool = False                        # 流式输出
```

#### VLAConfig

```python
@define(kw_only=True)
class VLAConfig(ModelComponentConfig):
    joint_names_map: Dict[str, str]           # 关节名称映射
    camera_inputs_map: Mapping[str, Union[Topic, Dict]]  # 相机输入
    state_input_type: Literal["positions", "velocities", "accelerations", "efforts"]
    action_output_type: Literal["positions", "velocities", "accelerations", "efforts"]
    observation_sending_rate: float = 10.0     # 观察频率
    action_sending_rate: float = 10.0          # 动作频率
    input_timeout: float = 30.0                # 输入超时
    robot_urdf_file: Optional[str] = None      # URDF文件
```

---

## 6. ROS集成

### 6.1 自定义消息类型

| 类型 | ROS消息 | 功能 |
|------|---------|------|
| `StreamingString` | `automatika_embodied_agents/msg/StreamingString` | 流式字符串 |
| `Video` | `automatika_embodied_agents/msg/Video` | 视频消息 |
| `Detections2D` | `automatika_embodied_agents/msg/Detections2D` | 2D检测 |
| `Detections2DMultiSource` | 多源2D检测 | |
| `Trackings` | `automatika_embodied_agents/msg/Trackings` | 目标跟踪 |
| `PointsOfInterest` | `automatika_embodied_agents/msg/PointsOfInterest` | 兴趣点 |
| `RGBD` | `realsense2_camera_msgs/msg/RGBD` | RGBD图像 |

### 6.2 Topic抽象

```python
@define(kw_only=True)
class Topic(BaseTopic):
    """ROS2 Topic的惯用包装器"""
    name: str
    msg_type: Union[type[SupportedType], str]
    qos_profile: Optional[QoSConfig] = None
```

### 6.3 特殊Topic类型

| 类型 | 描述 |
|------|------|
| `FixedInput` | 固定输入，不创建订阅者，始终返回相同数据 |
| `MapLayer` | 地图层，支持时空变化 |
| `Route` | 语义路由目标 |

---

## 7. 代码质量分析

### 7.1 编码规范

- **类型注解**: 广泛使用Python类型注解
- **配置管理**: 使用`attrs`库进行声明式配置
- **文档**: 详细的docstring，包含参数说明和示例
- **代码检查**: 使用`ruff`、`interrogate`

### 7.2 项目配置

```toml
[tool.ruff]
line-length = 88
preview = true
select = ["B","C","E","F","W","B9"]
max-complexity = 11

[tool.interrogate]
ignore-init-method = true
ignore-module = true
```

### 7.3 设计模式

| 模式 | 应用 |
|------|------|
| **抽象基类 (ABC)** | ModelClient, Component |
| **工厂模式** | 组件/客户端创建 |
| **策略模式** | 不同模型客户端 |
| **装饰器** | @define (attrs) |
| **观察者模式** | 事件触发机制 |

---

## 8. 使用示例

### 8.1 简单VLM Agent

```python
from agents.clients.ollama import OllamaClient
from agents.components import VLM
from agents.models import OllamaModel
from agents.ros import Topic, Launcher

# 定义输入输出Topic
text0 = Topic(name="text0", msg_type="String")
image0 = Topic(name="image_raw", msg_type="Image")
text1 = Topic(name="text1", msg_type="String")

# 定义模型客户端
qwen_vl = OllamaModel(name="qwen_vl", checkpoint="qwen2.5vl:latest")
qwen_client = OllamaClient(qwen_vl)

# 定义VLM组件
vlm = VLM(
    inputs=[text0, image0],
    outputs=[text1],
    model_client=qwen_client,
    trigger=text0,
    component_name="vqa"
)

# 设置提示模板
vlm.set_topic_prompt(text0, template="""You are an amazing robot.
    Answer: {{ text0 }}""")

# 启动Agent
launcher = Launcher()
launcher.add_pkg(components=[vlm])
launcher.bringup()
```

### 8.2 带RAG的LLM

```python
from agents.config import LLMConfig
from agents.components import LLM

config = LLMConfig(
    enable_rag=True,
    collection_name="my_knowledge",
    distance_func="cosine",
    n_results=3,
    chat_history=True,
    temperature=0.7
)
```

---

## 9. 依赖关系

### 9.1 核心依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| `attrs` | >= 23.2.0 | 配置管理 |
| `numpy` | - | 数值计算 |
| `opencv-python-headless` | - | 图像处理 |
| `jinja2` | - | 模板引擎 |
| `httpx` | - | HTTP客户端 |
| `msgpack` | - | 消息序列化 |
| `ros_sugar` (Sugarcoat) | >= 0.5.0 | ROS2抽象层 |

### 9.2 可选依赖

| 依赖 | 用途 |
|------|------|
| `ollama` | Ollama客户端 |
| `grpcio` | LeRobot客户端 |
| `torch` | LeRobot策略 |
| `chromadb` | 向量数据库 |
| `redis[hiredis]` | RoboML RESP客户端 |

---

## 10. 总结

**EmbodiedAgents** 是一个设计精良的ROS2物理AI框架，具有以下优点：

1. **模块化设计**: 清晰的组件层次和客户端架构
2. **灵活性**: 支持多种模型部署平台
3. **生产就绪**: 完整的事件驱动和生命周期管理
4. **易用性**: Pythonic API设计，降低使用门槛
5. **可扩展性**: 易于添加新的组件和客户端

该框架特别适合需要将大语言模型、多模态模型和VLA模型集成到ROS2机器人系统的开发者。
