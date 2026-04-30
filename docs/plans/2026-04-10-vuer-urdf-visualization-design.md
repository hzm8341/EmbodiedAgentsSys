:orphan:

# Vuer + FastAPI URDF 可视化系统设计

**日期**: 2026-04-10
**状态**: 已批准

## 1. 目标

将 OpenWBT 的 Vuer 3D 可视化功能迁移到 EmbodiedAgentsSys 项目，实现：
- 网页端实时显示机器人 URDF 模型
- 支持 eyoubot (欧友机器人) 的加载和渲染
- 通过 FastAPI 中转获取仿真状态数据
- 完整的模型树交互功能

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Browser                               │
│  ┌──────────────┐    ┌────────────────────────────────────────┐ │
│  │  Web Dashboard │    │         Vuer 3D Viewer                │ │
│  │  (Vue + TS)   │    │  (URDF Model + Robot Visualization) │ │
│  │  Port: 5173  │    │  Port: 8012 (WebSocket)              │ │
│  └──────────────┘    └────────────────────────────────────────┘ │
└────────────────────────────┬───────────────────────────────────┘
                              │ WebSocket + REST
┌─────────────────────────────┴───────────────────────────────────┐
│                      FastAPI Backend                             │
│                   Port: 8000                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ URDF Loader  │  │ State API     │  │ WebSocket Manager   │  │
│  │ /api/urdf/*  │  │ /api/state/*  │  │ /ws/{robot_id}      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                    Simulation Process                            │
│                  (Mujoco / Robot Control)                        │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 组件设计

### 3.1 Vuer Server (`vuer_server/`)

**职责**：
- 独立进程，端口 8012
- 加载 URDF 文件及 STL mesh
- WebSocket 通信，接收关节状态并更新 3D 模型

**核心模块**：
- `television.py` - Vuer 核心类（从 OpenWBT 迁移）
- `tv_wrapper.py` - URDF 封装（从 OpenWBT 迁移）
- `constants.py` - 坐标系转换常量

**依赖**：
- vuer
- numpy
- pyzmq（共享内存通信）

### 3.2 FastAPI Backend (`backend/`)

**API 端点**：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/urdf/load` | POST | 加载 URDF 文件路径 |
| `/api/urdf/{robot_id}` | GET | 获取机器人模型树结构 |
| `/api/urdf/list` | GET | 列出可用机器人模型 |
| `/api/state/{robot_id}` | GET | 获取当前关节状态 |
| `/ws/{robot_id}` | WebSocket | 实时推送仿真状态 |

**数据模型**：
```python
class JointState(BaseModel):
    joint_name: str
    position: float
    velocity: Optional[float] = None

class RobotState(BaseModel):
    robot_id: str
    joints: List[JointState]
    timestamp: float

class URDFModel(BaseModel):
    robot_id: str
    name: str
    links: List[LinkInfo]
    joints: List[JointInfo]
```

### 3.3 Web Dashboard (`web-dashboard/`)

**功能模块**：
- **左侧面板**：机器人模型树（可折叠、勾选显示/隐藏）
- **右侧区域**：Vuer 3D 视图（iframe 嵌入）
- **底部控制栏**：重置、网格开关、视角切换

**交互功能**：
- 显示/隐藏 link
- 切换视角（轨道、俯视、正交/透视）
- 网格地面开关
- 爆炸图（分离视图）

## 4. 数据流

1. **URDF 加载流程**：
   - 前端请求 `/api/urdf/list` 获取可用模型
   - 选择模型后请求 `/api/urdf/{robot_id}` 获取结构
   - Vuer Server 加载对应 URDF 和 mesh 文件

2. **实时状态流程**：
   - 仿真进程通过共享内存或 ZMQ 推送状态
   - FastAPI WebSocket `/ws/{robot_id}` 转发状态
   - Vuer Server 接收状态并更新 3D 模型姿态

## 5. 迁移的 OpenWBT 文件

从 OpenWBT 迁移以下文件：
- `deploy/teleop/open_television/television.py`
- `deploy/teleop/open_television/tv_wrapper.py`
- `deploy/teleop/open_television/constants.py`
- `deploy/assets/eyoubot/eu_ca_describtion_lbs6.urdf`
- `deploy/assets/eyoubot/meshes/*`

## 6. 目录结构

```
EmbodiedAgentsSys/
├── vuer_server/
│   ├── __init__.py
│   ├── television.py        # 从 OpenWBT 迁移
│   ├── tv_wrapper.py        # 从 OpenWBT 迁移
│   ├── constants.py          # 从 OpenWBT 迁移
│   ├── urdf_loader.py        # 新增：URDF 解析
│   └── requirements.txt
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── urdf.py           # URDF API 路由
│   │   └── state.py          # 状态 API 路由
│   ├── services/
│   │   ├── __init__.py
│   │   └── websocket_manager.py
│   └── main.py
├── web-dashboard/
│   └── src/
│       ├── components/
│       │   ├── URDFViewer.vue
│       │   └── ModelTree.vue
│       └── ...
├── assets/
│   └── eyoubot/              # 从 OpenWBT 迁移
│       ├── eu_ca_describtion_lbs6.urdf
│       └── meshes/
└── docs/
    └── plans/
        └── 2026-04-10-vuer-urdf-visualization-design.md
```

## 7. 实现顺序

1. **Phase 1**: 迁移 Vuer Server 基础功能
   - 迁移 television.py, tv_wrapper.py, constants.py
   - 创建 urdf_loader.py
   - 测试 Vuer 基本渲染

2. **Phase 2**: FastAPI 后端
   - 实现 URDF API 端点
   - 实现 WebSocket 管理器
   - 连接 Vuer Server 和 FastAPI

3. **Phase 3**: Web Dashboard 集成
   - 集成 Vuer viewer iframe
   - 实现模型树组件
   - 实现控制栏

## 8. 验收标准

- [ ] Vuer Server 可独立启动，端口 8012
- [ ] 可加载 eyoubot URDF 并渲染 3D 模型
- [ ] FastAPI 提供完整的 REST API
- [ ] WebSocket 可实时推送机器人状态
- [ ] Web Dashboard 可显示模型树和 3D 视图
- [ ] 支持显示/隐藏 link、切换视角等交互
