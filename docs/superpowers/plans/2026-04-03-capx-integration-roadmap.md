:orphan:

# CaP-X 整合实施计划

**制定日期**: 2026-04-03
**计划周期**: 12 周（3 个月）
**目标**: 将 CaP-X 的关键设计模式和能力集成到 EmbodiedAgentsSys 中

---

## 整体策略

采用**分阶段、渐进式集成**的策略：

```
第一阶段（1-2 周）— 工程基础
    ↓ (基础稳定后)
第二阶段（2-4 周）— 代理核心升级
    ↓ (核心稳定后)
第三阶段（4-8 周）— 智能反馈集成
    ↓ (可选，高价值)
第四阶段（8-12 周）— 在线学习和优化
```

**原则**：
- 每个阶段完成后验证稳定性，再进入下一阶段
- 优先处理基础设施，再处理核心功能
- 保持现有功能可用，新功能并行开发

---

## 第一阶段：工程基础（1-2 周）

### 目标
建立现代化的工程基础，为后续升级铺垫。

### 1.1 迁移到 tyro CLI（3-5 天）

**现状**：使用 dataclass 手写参数解析

**目标**：使用 tyro 从 dataclass 自动生成 CLI

**实施步骤**：

1. **安装 tyro**
   ```bash
   pip install tyro
   ```

2. **创建 CLI 入口点** (`agents/cli.py`)
   ```python
   from dataclasses import dataclass
   from tyro import cli

   @dataclass
   class HarnessArgs:
       """Harness 配置。"""
       mode: str = "hardware_mock"
       robot_type: str = "arm"
       auto_attach: bool = False
       task_timeout: int = 60

   @dataclass
   class LLMArgs:
       """LLM 配置。"""
       provider: str = "openai"
       model: str = "gpt-4"
       temperature: float = 1.0
       max_tokens: int = 2048

   @dataclass
   class Args:
       """总参数。"""
       harness: HarnessArgs
       llm: LLMArgs
       task_description: str
       log_dir: str = "logs"

   def main():
       args = cli(Args, default=Args(...))
       # 启动代理循环
       ...

   if __name__ == "__main__":
       main()
   ```

3. **更新启动脚本**
   ```bash
   # 之前：python agents/agent_loop.py --config config.yaml
   # 之后：python agents/cli.py --harness.mode hardware_mock --llm.model gpt-4
   ```

4. **验证**
   ```bash
   python agents/cli.py --help  # 应该显示结构化的帮助信息
   ```

**验证清单**：
- [ ] `--help` 显示嵌套配置结构
- [ ] 可以通过命令行覆盖所有主要参数
- [ ] 现有的脚本可以无缝迁移

**预期时间**: 3-5 天

---

### 1.2 实现工厂注册模式（3-5 天）

**现状**：硬件客户端和技能需要在代码中硬编码

**目标**：实现工厂模式，支持动态注册和发现

**实施步骤**：

1. **创建工厂模块** (`agents/factories.py`)
   ```python
   from typing import Callable, Any, Dict
   from abc import ABC, abstractmethod

   # 硬件工厂
   _HARDWARE_FACTORIES: Dict[str, Callable] = {}

   def register_hardware(name: str, factory: Callable) -> None:
       """注册硬件工厂。"""
       _HARDWARE_FACTORIES[name] = factory

   def get_hardware(name: str, **kwargs) -> Any:
       """获取硬件实例。"""
       if name not in _HARDWARE_FACTORIES:
           raise KeyError(f"Hardware '{name}' not registered")
       return _HARDWARE_FACTORIES[name](**kwargs)

   def list_hardware() -> list[str]:
       """列出所有可用硬件。"""
       return list(_HARDWARE_FACTORIES.keys())

   # 技能工厂
   _SKILL_FACTORIES: Dict[str, Callable] = {}

   def register_skill(name: str, factory: Callable) -> None:
       """注册技能工厂。"""
       _SKILL_FACTORIES[name] = factory

   def get_skill(name: str, **kwargs) -> Any:
       """获取技能实例。"""
       if name not in _SKILL_FACTORIES:
           raise KeyError(f"Skill '{name}' not registered")
       return _SKILL_FACTORIES[name](**kwargs)

   def list_skills() -> list[str]:
       """列出所有可用技能。"""
       return list(_SKILL_FACTORIES.keys())
   ```

2. **注册现有的硬件**（`agents/clients/registry.py`）
   ```python
   from agents.factories import register_hardware
   from agents.clients.lerobot_transport import LeRobotClient
   from agents.clients.vla_adapters.base import VLAAdapter

   # 注册硬件
   register_hardware("franka_real", lambda config: LeRobotClient(config))
   register_hardware("franka_sim", lambda config: SimulatorClient(config))
   register_hardware("vla_adapter", lambda config: VLAAdapter(config))

   # 在模块导入时自动注册
   # from agents.clients.registry import *
   ```

3. **注册现有技能**（`agents/skills/registry.py`）
   ```python
   from agents.factories import register_skill
   from agents.skills.manipulation.grasp import GraspSkill
   from agents.skills.manipulation.move import MoveSkill
   # ... 其他技能

   register_skill("grasp", GraspSkill)
   register_skill("move", MoveSkill)
   register_skill("place", PlaceSkill)
   register_skill("reach", ReachSkill)
   register_skill("inspect", InspectSkill)
   ```

4. **在代理循环中使用**
   ```python
   # 之前
   from agents.clients.lerobot_transport import LeRobotClient
   hardware = LeRobotClient(config)

   # 之后
   from agents.factories import get_hardware
   hardware = get_hardware("franka_real", config=config)

   # 或者从命令行动态选择
   # python agents/cli.py --hardware-type franka_real
   ```

5. **验证**
   ```python
   from agents.factories import list_hardware, list_skills
   print(list_hardware())  # ['franka_real', 'franka_sim', 'vla_adapter']
   print(list_skills())    # ['grasp', 'move', 'place', 'reach', 'inspect']
   ```

**验证清单**：
- [ ] 所有硬件可以通过工厂注册/获取
- [ ] 所有技能可以通过工厂注册/获取
- [ ] 新增硬件/技能可以动态注册，无需修改主代码
- [ ] `list_hardware()` / `list_skills()` 返回完整列表

**预期时间**: 3-5 天

---

### 1.3 改进日志和人工制品保存（2-3 天）

**现状**：日志分散，追踪信息不完整

**目标**：系统化的人工制品保存（代码、输出、状态、图像）

**实施步骤**：

1. **创建人工制品管理器** (`agents/artifacts.py`)
   ```python
   from pathlib import Path
   from dataclasses import dataclass
   import json
   from datetime import datetime
   import io

   @dataclass
   class ExecutionArtifacts:
       """单次执行的所有人工制品。"""
       trial_id: str
       artifacts_dir: Path

       def __post_init__(self):
           self.artifacts_dir.mkdir(parents=True, exist_ok=True)

       def save_code(self, code: str):
           """保存生成的代码。"""
           with open(self.artifacts_dir / "code.py", "w") as f:
               f.write(code)

       def save_output(self, stdout: str, stderr: str):
           """保存执行输出。"""
           with open(self.artifacts_dir / "stdout.txt", "w") as f:
               f.write(stdout)
           with open(self.artifacts_dir / "stderr.txt", "w") as f:
               f.write(stderr)

       def save_state(self, state: dict):
           """保存环境状态。"""
           with open(self.artifacts_dir / "state.json", "w") as f:
               json.dump(state, f, indent=2)

       def save_image(self, image, frame_id: int = 0):
           """保存环境图像。"""
           from PIL import Image as PILImage
           img = PILImage.fromarray(image)
           img.save(self.artifacts_dir / f"frame_{frame_id:04d}.png")

       def save_metadata(self, metadata: dict):
           """保存元数据。"""
           metadata["timestamp"] = datetime.now().isoformat()
           with open(self.artifacts_dir / "metadata.json", "w") as f:
               json.dump(metadata, f, indent=2)

   class ArtifactManager:
       """管理多个执行的人工制品。"""

       def __init__(self, base_dir: str = "logs"):
           self.base_dir = Path(base_dir)
           self.base_dir.mkdir(exist_ok=True)

       def create_trial(self, trial_id: str) -> ExecutionArtifacts:
           """创建新的试验人工制品。"""
           trial_dir = self.base_dir / f"trial_{trial_id}"
           return ExecutionArtifacts(trial_id, trial_dir)

       def list_trials(self):
           """列出所有试验。"""
           return [d.name for d in self.base_dir.glob("trial_*")]
   ```

2. **集成 Tee 流输出捕获** (`agents/utils/tee.py`)
   ```python
   import io
   import sys

   class Tee(io.TextIOBase):
       """同时输出到多个流。"""

       def __init__(self, *streams):
           self.streams = streams

       def write(self, s):
           for stream in self.streams:
               stream.write(s)
               stream.flush()

       def flush(self):
           for stream in self.streams:
               stream.flush()
   ```

3. **在代理循环中使用**
   ```python
   from agents.artifacts import ArtifactManager
   from agents.utils.tee import Tee

   # 初始化
   artifact_mgr = ArtifactManager("logs")
   artifacts = artifact_mgr.create_trial(f"trial_{datetime.now().isoformat()}")

   # 捕获输出
   stdout_buffer = io.StringIO()
   sys.stdout = Tee(sys.stdout, stdout_buffer)
   sys.stderr = Tee(sys.stderr, stdout_buffer)

   try:
       # ... 执行代理循环
       result = await agent_loop.run()

       # 保存人工制品
       artifacts.save_code(generated_code)
       artifacts.save_output(stdout_buffer.getvalue(), "")
       artifacts.save_state(result.environment_state)
       artifacts.save_metadata({
           "success": result.success,
           "steps": result.steps,
           "task": task.description
       })
   finally:
       sys.stdout = sys.__stdout__
       sys.stderr = sys.__stderr__
   ```

**验证清单**：
- [ ] 每次执行生成 `logs/trial_*/` 目录
- [ ] 目录中包含 code.py、stdout.txt、state.json、metadata.json
- [ ] 可以列出所有试验：`artifact_mgr.list_trials()`
- [ ] 图像可以正确保存和查看

**预期时间**: 2-3 天

---

## 第二阶段：代理核心升级（2-4 周）

### 目标
升级代理的决策能力，从固定技能调用到灵活的代码生成和执行。

### 2.1 将技能转为 API 函数库（5-7 天）

**现状**：技能是预定义的类（GraspSkill、MoveSkill 等）

**目标**：将技能表示为可暴露给代码生成的 API 函数

**实施步骤**：

1. **创建 API 基类** (`agents/apis/base.py`)
   ```python
   from abc import ABC, abstractmethod
   from typing import Callable, Dict, Any
   import inspect

   class ApiBase(ABC):
       """API 基类，模仿 CaP-X 的 ApiBase。"""

       def __init__(self, env: Any = None):
           self._env = env

       @abstractmethod
       def functions(self) -> Dict[str, Callable]:
           """返回暴露给代码生成器的函数字典。"""
           pass

       def combined_doc(self) -> str:
           """自动生成文档。"""
           doc = ""
           for func_name, func in self.functions().items():
               doc += f"\n## {func_name}\n"
               doc += (func.__doc__ or "No documentation") + "\n"
           return doc

       def set_env(self, env: Any):
           """设置环境引用。"""
           self._env = env
   ```

2. **将 GraspSkill 转为 GraspAPI**（`agents/apis/manipulation.py`）
   ```python
   import numpy as np
   from agents.apis.base import ApiBase

   class GraspAPI(ApiBase):
       """抓取规划 API。"""

       def functions(self):
           return {
               "plan_grasp": self.plan_grasp,
               "execute_grasp": self.execute_grasp,
           }

       def plan_grasp(self, depth: np.ndarray, intrinsics: np.ndarray) -> list:
           """
           规划平行夹爪抓取。

           Args:
               depth: (H, W) float32 深度图，单位为米
               intrinsics: (3, 3) float32 相机内参

           Returns:
               list of dict: [{pose: (4,4), width: float, score: float}]
           """
           # 使用原有的 GraspSkill 的逻辑
           grasp_skill = GraspSkill(self._env)
           return grasp_skill.plan(depth, intrinsics)

       def execute_grasp(self, grasp_pose: np.ndarray) -> dict:
           """
           执行单个抓取。

           Args:
               grasp_pose: (4, 4) 抓取位姿

           Returns:
               dict: {success: bool, info: str}
           """
           grasp_skill = GraspSkill(self._env)
           return grasp_skill.execute(grasp_pose)

   class MoveAPI(ApiBase):
       """运动规划 API。"""

       def functions(self):
           return {
               "move_to_pose": self.move_to_pose,
               "move_to_position": self.move_to_position,
           }

       def move_to_pose(self, target_pose: np.ndarray) -> dict:
           """
           移动到目标位姿。

           Args:
               target_pose: (4, 4) 目标位姿

           Returns:
               dict: {success: bool, steps: int}
           """
           move_skill = MoveSkill(self._env)
           return move_skill.move_to_pose(target_pose)

       def move_to_position(self, target_pos: np.ndarray) -> dict:
           """
           移动到目标位置（保持当前朝向）。

           Args:
               target_pos: (3,) 目标位置 [x, y, z]

           Returns:
               dict: {success: bool, steps: int}
           """
           move_skill = MoveSkill(self._env)
           return move_skill.move_to_position(target_pos)

   # ... 类似地将其他技能转为 API
   ```

3. **创建 API 注册表** (`agents/apis/registry.py`)
   ```python
   from agents.apis.manipulation import GraspAPI, MoveAPI, PlaceAPI, ReachAPI
   from agents.factories import register_skill

   # 注册 API（同时保持向后兼容）
   _API_REGISTRY = {}

   def register_api(name: str, api_class):
       """注册 API。"""
       _API_REGISTRY[name] = api_class

   def get_api(name: str, env=None):
       """获取 API 实例。"""
       if name not in _API_REGISTRY:
           raise KeyError(f"API '{name}' not registered")
       return _API_REGISTRY[name](env=env)

   def list_apis():
       """列出所有 API。"""
       return list(_API_REGISTRY.keys())

   # 注册所有 API
   register_api("grasp", GraspAPI)
   register_api("move", MoveAPI)
   register_api("place", PlaceAPI)
   register_api("reach", ReachAPI)
   register_api("inspect", InspectAPI)
   ```

4. **验证**
   ```python
   from agents.apis.registry import list_apis, get_api

   print(list_apis())  # ['grasp', 'move', 'place', 'reach', 'inspect']

   api = get_api("grasp", env=environment)
   print(api.combined_doc())  # 显示所有函数的文档
   ```

**验证清单**：
- [ ] 所有现有技能可以通过 API 调用
- [ ] `combined_doc()` 生成完整的 API 文档
- [ ] 可以列出所有 API
- [ ] 现有的代理循环仍然可以工作（向后兼容）

**预期时间**: 5-7 天

---

### 2.2 实现改进的提示词工程（3-5 天）

**现状**：提示词固定，不包含动态上下文

**目标**：构建结构化的上下文，包含当前观察、可用 API、历史信息等

**实施步骤**：

1. **创建上下文构建器** (`agents/prompting/context_builder.py`)
   ```python
   from dataclasses import dataclass
   from typing import Dict, List, Any
   import json

   @dataclass
   class AgentContext:
       """代理决策的上下文。"""
       observation: Dict[str, Any]        # 当前观察
       available_apis: List[str]           # 可用的 API
       available_skills: List[str]         # 可用的技能
       task_description: str               # 任务描述
       task_constraints: List[str]         # 任务约束
       history: List[Dict]                 # 历史决策和结果
       feedback: str = ""                  # 来自 VDM 的反馈（可选）

   class ContextBuilder:
       """构建代理决策的上下文。"""

       def __init__(self, env, api_registry, skill_registry):
           self.env = env
           self.api_registry = api_registry
           self.skill_registry = skill_registry

       def build(self, task, history=None) -> AgentContext:
           """构建完整的上下文。"""

           # 1. 获取当前观察
           observation = {
               "image": self.env.get_observation()["image"],
               "state": self.env.get_observation()["state"],
               "gripper_state": self.env.get_gripper_state(),
           }

           # 2. 列出可用 API 和技能
           available_apis = self.api_registry.list_apis()
           available_skills = self.skill_registry.list_skills()

           # 3. 构建上下文
           context = AgentContext(
               observation=observation,
               available_apis=available_apis,
               available_skills=available_skills,
               task_description=task.description,
               task_constraints=task.constraints or [],
               history=history or [],
           )

           return context

   def context_to_prompt(context: AgentContext, api_docs: str) -> str:
       """将上下文转为提示词。"""

       prompt = f"""You are a robot task executor.

## Current Task
{context.task_description}

## Constraints
{chr(10).join(f"- {c}" for c in context.task_constraints)}

## Current Observation
Image shape: {context.observation['image'].shape}
Robot state: {json.dumps(context.observation['state'], indent=2, default=str)}
Gripper: {context.observation['gripper_state']}

## Available APIs
{context.available_apis}

## API Documentation
{api_docs}

## History
{json.dumps(context.history, indent=2, default=str) if context.history else "No history yet"}

## Your Task
Generate Python code to accomplish the task.
You have access to:
- `env`: Robot environment with methods like `get_observation()`, `step(action)`, etc.
- `APIS`: Dictionary of available APIs, e.g., `APIS['grasp'].plan_grasp(...)`
- `INPUTS`: Input dictionary
- `RESULT`: Store your final result here

Example code structure:
```python
# Get current depth
depth = env.get_observation()["depth"]
intrinsics = env.get_camera_intrinsics()

# Plan grasp using API
grasps = APIS["grasp"].plan_grasp(depth, intrinsics)

# Execute grasp
result = APIS["grasp"].execute_grasp(grasps[0])

# Store result
RESULT = {{"success": result["success"], "info": result["info"]}}
```

Now generate the code:
"""
       return prompt
   ```

2. **集成到代理循环**
   ```python
   # 在 RobotAgentLoop 中
   from agents.prompting.context_builder import ContextBuilder, context_to_prompt

   class ImprovedRobotAgentLoop:
       def __init__(self, ...):
           ...
           self.context_builder = ContextBuilder(
               self.env,
               self.api_registry,
               self.skill_registry
           )

       async def decide_next_action(self, task):
           """改进的决策逻辑。"""

           # 1. 构建上下文
           context = self.context_builder.build(task, history=self.history)

           # 2. 获取 API 文档
           api_docs = "\n".join([
               self.api_registry.get_api(api).combined_doc()
               for api in context.available_apis
           ])

           # 3. 生成提示词
           prompt = context_to_prompt(context, api_docs)

           # 4. 调用 LLM
           code = await self.llm_provider.generate(prompt)

           # 5. 返回代码
           return code
   ```

**验证清单**：
- [ ] 上下文包含当前观察、可用 API、历史信息
- [ ] 生成的提示词结构清晰、信息完整
- [ ] API 文档自动生成，无需手工维护

**预期时间**: 3-5 天

---

### 2.3 实现代码执行器（SimpleExecutor）（3-5 天）

**现状**：技能执行通过 skill.execute() 的方法调用

**目标**：支持生成的 Python 代码的安全执行

**实施步骤**：

1. **创建代码执行器** (`agents/executor/code_executor.py`)
   ```python
   import sys
   import traceback
   from io import StringIO
   from typing import Dict, Any

   class SimpleCodeExecutor:
       """简化的代码执行器，模仿 CaP-X 的 SimpleExecutor。"""

       def __init__(self, env: Any, apis: Dict[str, Any]):
           self.env = env
           self.apis = apis

       def run(self, code: str, inputs: Dict[str, Any] = None) -> Dict[str, Any]:
           """
           执行代码。

           全局命名空间包含：
           - env: 环境对象
           - APIS: API 字典
           - INPUTS: 输入参数
           - RESULT: 结果存储

           Returns:
               {ok: bool, result: Any, error: str, traceback: str, stdout: str}
           """

           # 创建受控的全局命名空间
           globals_dict = {
               "__name__": "__main__",
               "env": self.env,
               "APIS": self.apis,
               "INPUTS": inputs or {},
               "RESULT": None,
           }

           # 捕获输出
           stdout_buffer = StringIO()
           original_stdout = sys.stdout
           sys.stdout = stdout_buffer

           try:
               # 执行代码
               exec(code, globals_dict)

               return {
                   "ok": True,
                   "result": globals_dict.get("RESULT"),
                   "error": None,
                   "traceback": None,
                   "stdout": stdout_buffer.getvalue(),
               }

           except Exception as e:
               return {
                   "ok": False,
                   "result": None,
                   "error": str(e),
                   "traceback": traceback.format_exc(),
                   "stdout": stdout_buffer.getvalue(),
               }

           finally:
               sys.stdout = original_stdout

   class CodeExecutionResult:
       """代码执行的结果。"""

       def __init__(self, exec_result: Dict[str, Any]):
           self.ok = exec_result["ok"]
           self.result = exec_result["result"]
           self.error = exec_result["error"]
           self.traceback = exec_result["traceback"]
           self.stdout = exec_result["stdout"]

       @property
       def success(self) -> bool:
           """是否执行成功。"""
           return self.ok

       def __repr__(self):
           if self.ok:
               return f"CodeExecutionResult(ok=True, result={self.result})"
           else:
               return f"CodeExecutionResult(ok=False, error={self.error})"
   ```

2. **集成到代理循环**
   ```python
   from agents.executor.code_executor import SimpleCodeExecutor

   class ImprovedRobotAgentLoop:
       def __init__(self, ...):
           ...
           self.executor = SimpleCodeExecutor(self.env, self.api_registry)

       async def execute_generated_code(self, code: str) -> CodeExecutionResult:
           """执行生成的代码。"""

           result = self.executor.run(
               code,
               inputs={
                   "task_description": self.current_task.description,
                   "history": self.history,
               }
           )

           return CodeExecutionResult(result)

       async def run(self):
           """改进的代理循环。"""
           while not self.task_completed:
               # 1. 决策：生成代码
               code = await self.decide_next_action(self.current_task)

               # 2. 执行：运行代码
               exec_result = await self.execute_generated_code(code)

               # 3. 反馈：记录结果
               if exec_result.success:
                   self.update_memory(code, exec_result.result)
               else:
                   self.failure_log.record(code, exec_result.error)

               # 4. 检查是否完成
               if exec_result.result and exec_result.result.get("success"):
                   self.task_completed = True
   ```

3. **安全考虑**
   - 代码执行在隔离的全局命名空间中
   - 只能访问 env、APIS、INPUTS、RESULT
   - 任何异常都被捕获并返回
   - 可以添加超时控制（如需要）

**验证清单**：
- [ ] 简单代码可以成功执行
- [ ] 异常被正确捕获和报告
- [ ] 输出被正确捕获
- [ ] 结果存储在 RESULT 变量中

**预期时间**: 3-5 天

---

### 2.4 测试和验证第二阶段（2-3 天）

**目标**：确保代理可以生成并执行代码，完成简单任务

**验证步骤**：

1. **单元测试**
   - `test_code_executor.py`: 测试代码执行
   - `test_context_builder.py`: 测试上下文构建
   - `test_api_registry.py`: 测试 API 注册和发现

2. **集成测试**
   - 生成一个简单任务的代码
   - 执行该代码
   - 验证结果

3. **回归测试**
   - 确保现有的技能调用路径仍然工作
   - 确保 MessageBus 事件仍然被处理

**预期时间**: 2-3 天

---

## 第三阶段：智能反馈集成（4-8 周）

### 目标
集成多轮反馈和改进机制，使代理能够自我纠正。

### 3.1 实现 VDM 视觉差分模型（2-3 周）

**现状**：失败时只记录日志，不提供具体的改进反馈

**目标**：使用视觉差分分析执行前后的差异，指导代码改进

**实施步骤**：

1. **创建 VDM 模块** (`agents/vdm/visual_difference_model.py`)
   ```python
   from dataclasses import dataclass
   from typing import Optional
   import numpy as np

   @dataclass
   class VisualDifferenceAnalysis:
       """视觉差分分析结果。"""
       before_image: np.ndarray       # 执行前的图像
       after_image: np.ndarray        # 执行后的图像
       difference_map: np.ndarray     # 差异热力图
       analysis_text: str             # LLM 生成的分析文本
       suggested_fix: str             # 建议的修复

   class VisualDifferenceModel:
       """基于 LLM 的视觉差分模型。"""

       def __init__(self, llm_provider):
           self.llm_provider = llm_provider

       async def analyze(
           self,
           before_image: np.ndarray,
           after_image: np.ndarray,
           intended_goal: str,
       ) -> VisualDifferenceAnalysis:
           """
           分析执行前后的视觉差异。

           使用 Claude Vision 或 GPT-4V 进行分析。
           """

           # 计算差异（简单版：直接差异）
           difference = np.abs(before_image.astype(float) - after_image.astype(float))
           difference_normalized = (difference / difference.max() * 255).astype(np.uint8)

           # 调用 LLM 进行智能分析
           analysis_prompt = f"""
           Analyze the before and after images of a robot manipulation task.

           Intended goal: {intended_goal}

           Before image: [image]
           After image: [image]

           Please analyze:
           1. What changed in the scene?
           2. Did the action move towards the goal?
           3. If not, what went wrong?
           4. How should the code be modified?

           Provide a concise analysis and suggested fix.
           """

           analysis_text = await self.llm_provider.analyze_images(
               analysis_prompt,
               [before_image, after_image]
           )

           return VisualDifferenceAnalysis(
               before_image=before_image,
               after_image=after_image,
               difference_map=difference_normalized,
               analysis_text=analysis_text,
               suggested_fix=analysis_text.split("Suggested fix:")[-1] if "Suggested fix:" in analysis_text else ""
           )
   ```

2. **集成到代理循环**
   ```python
   from agents.vdm.visual_difference_model import VisualDifferenceModel

   class ImprovedRobotAgentLoop:
       def __init__(self, ...):
           ...
           self.vdm = VisualDifferenceModel(self.llm_provider)

       async def run_with_feedback(self):
           """支持多轮反馈的代理循环。"""

           max_iterations = 5
           for iteration in range(max_iterations):
               # 1. 生成代码
               code = await self.decide_next_action(self.current_task)

               # 2. 执行代码
               before_obs = self.env.get_observation()
               exec_result = await self.execute_generated_code(code)
               after_obs = self.env.get_observation()

               # 3. 检查成功
               if exec_result.success and exec_result.result.get("success"):
                   return True

               # 4. 如果失败，使用 VDM 分析
               vdm_analysis = await self.vdm.analyze(
                   before_image=before_obs["image"],
                   after_image=after_obs["image"],
                   intended_goal=self.current_task.description
               )

               # 5. 使用 VDM 反馈改进代码
               improved_code = await self.improve_code(
                   original_code=code,
                   vdm_feedback=vdm_analysis.analysis_text,
                   vdm_suggestion=vdm_analysis.suggested_fix
               )

               code = improved_code

           return False

       async def improve_code(self, original_code, vdm_feedback, vdm_suggestion) -> str:
           """基于 VDM 反馈改进代码。"""

           improvement_prompt = f"""
           The previous code did not achieve the goal.

           Original code:
           {original_code}

           Visual feedback:
           {vdm_feedback}

           Suggested fix:
           {vdm_suggestion}

           Please modify the code to fix the issue.
           """

           improved_code = await self.llm_provider.generate(improvement_prompt)
           return improved_code
   ```

3. **验证**
   - [ ] VDM 能够分析执行前后的差异
   - [ ] LLM 能够生成改进建议
   - [ ] 改进的代码可以重新执行
   - [ ] 多轮改进逐步逼近目标

**预期时间**: 2-3 周

---

### 3.2 实现自动技能库学习（2-3 周）

**现状**：成功的代码被丢弃，下次遇到相似任务时需要重新生成

**目标**：保存成功的代码作为可重用的技能，建立在线学习环路

**实施步骤**：

1. **创建成功记录** (`agents/learning/success_record.py`)
   ```python
   from dataclasses import dataclass
   from datetime import datetime
   import json

   @dataclass
   class SuccessRecord:
       """成功执行的记录。"""
       task_name: str
       code: str
       result: dict
       metrics: dict              # 成功率、步数等
       timestamp: str
       environment_config: dict   # 环境配置（用于验证）

   class SuccessLibrary:
       """成功代码的库。"""

       def __init__(self, library_dir: str = "skill_library"):
           self.library_dir = library_dir
           self._load_library()

       def _load_library(self):
           """从磁盘加载库。"""
           self.skills = {}
           # ...

       def save(self, record: SuccessRecord):
           """保存成功的代码。"""
           # 存储为 task_name.py 和元数据 task_name.json
           ...

       def retrieve_similar(self, task_description: str, top_k=3) -> list:
           """检索相似的成功代码。"""
           # 使用语义相似度搜索
           ...
   ```

2. **集成学习环路**
   ```python
   from agents.learning.success_record import SuccessRecord, SuccessLibrary

   class LearningRobotAgentLoop:
       def __init__(self, ...):
           ...
           self.success_library = SuccessLibrary()

       async def run_with_learning(self):
           """支持在线学习的代理循环。"""

           success = False
           max_iterations = 5

           for iteration in range(max_iterations):
               # 1. 检索相似的历史成功
               similar_codes = self.success_library.retrieve_similar(
                   self.current_task.description
               )

               # 2. 生成代码（可以参考历史代码）
               code = await self.decide_with_history(
                   self.current_task,
                   similar_codes=similar_codes
               )

               # 3. 执行
               exec_result = await self.execute_generated_code(code)

               if exec_result.success:
                   # 4. 保存成功的代码
                   record = SuccessRecord(
                       task_name=self.current_task.name,
                       code=code,
                       result=exec_result.result,
                       metrics={"success": True},
                       timestamp=datetime.now().isoformat(),
                       environment_config=self.env.config.dict()
                   )
                   self.success_library.save(record)
                   success = True
                   break

               # 5. 如果失败，使用 VDM 反馈改进
               vdm_analysis = await self.vdm.analyze(...)
               code = await self.improve_code(code, vdm_analysis.analysis_text)

           return success
   ```

3. **验证**
   - [ ] 成功的代码被保存到库
   - [ ] 可以检索相似的历史代码
   - [ ] 历史代码可以作为改进的参考

**预期时间**: 2-3 周

---

## 第四阶段：在线优化和可选增强（8-12 周）

### 目标
添加可选的高级功能，提升代理的自适应和学习能力。

### 4.1 实现并行代码生成（1-2 周）

**目标**：同时生成多个代码候选，选择最有希望的

```python
async def generate_candidates(self, task, num_candidates=3) -> list:
    """生成多个代码候选。"""
    candidates = await asyncio.gather(
        self.decide_next_action(task, temperature=1.0),
        self.decide_next_action(task, temperature=0.7),
        self.decide_next_action(task, temperature=0.5),
    )
    return candidates

async def run_with_ensemble(self):
    """支持并行推理的代理循环。"""

    # 生成多个候选
    candidates = await self.generate_candidates(self.current_task)

    # 并行执行
    results = await asyncio.gather(
        *[self.execute_generated_code(code) for code in candidates]
    )

    # 选择最佳结果
    best_idx = max(range(len(results)), key=lambda i: results[i].confidence)
    return results[best_idx]
```

---

### 4.2 实现 OmegaConf 配置系统（1-2 周）

**目标**：将配置系统从 dataclass 迁移到 OmegaConf，支持更灵活的配置

```python
# config.yaml
environment:
  type: franka_real
  ip: 192.168.1.100

llm:
  provider: openai
  model: gpt-4
  temperature: 1.0

harness:
  mode: hardware_mock
  robot_type: arm
  timeout: 60

# Python 代码
from omegaconf import OmegaConf
config = OmegaConf.load("config.yaml")
config = OmegaConf.merge(config, OmegaConf.from_cli(sys.argv[1:]))
env = get_hardware(config.environment.type, config=config.environment)
```

---

### 4.3 实现强化学习后训练（可选，2-4 周）

**目标**：使用环境奖励对 LLM 进行微调

```python
class RL_Trainer:
    """使用 RL 对代码生成 LLM 进行微调。"""

    async def train(self, tasks, num_episodes=100):
        """GRPO 风格的训练。"""

        for episode in range(num_episodes):
            task = random.choice(tasks)

            # 1. 生成多个候选
            candidates = await self.agent.generate_candidates(task, num_candidates=4)

            # 2. 执行并获取奖励
            rewards = []
            for code in candidates:
                result = await self.agent.execute_generated_code(code)
                reward = 1.0 if result.success else 0.0
                rewards.append(reward)

            # 3. GRPO 更新
            self.update_model(candidates, rewards)
```

---

## 时间估算总结

| 阶段 | 任务 | 时间 | 总计 |
|------|------|------|------|
| **第一阶段** | tyro CLI | 3-5 天 | |
| | 工厂注册 | 3-5 天 | |
| | 人工制品管理 | 2-3 天 | **1-2 周** |
| **第二阶段** | 技能→API | 5-7 天 | |
| | 提示词工程 | 3-5 天 | |
| | 代码执行器 | 3-5 天 | |
| | 测试验证 | 2-3 天 | **2-4 周** |
| **第三阶段** | VDM 集成 | 2-3 周 | |
| | 技能学习 | 2-3 周 | **4-8 周** |
| **第四阶段** | 并行生成 | 1-2 周 | |
| | OmegaConf | 1-2 周 | |
| | RL 训练（可选） | 2-4 周 | **4-8 周** |
| **总计** | | | **12 周** |

---

## 关键验证点

### 第一阶段结束时
- [ ] 所有硬件和技能可以通过工厂注册和发现
- [ ] CLI 支持命令行参数覆盖
- [ ] 每次执行生成完整的人工制品记录

### 第二阶段结束时
- [ ] 代理可以生成 Python 代码完成简单任务
- [ ] 生成的代码可以成功执行和获取结果
- [ ] 当前的基于技能的路径仍然可以工作

### 第三阶段结束时
- [ ] VDM 可以分析执行前后的差异
- [ ] 代理可以进行多轮改进
- [ ] 成功的代码被自动保存和重用

### 第四阶段结束时
- [ ] 可选功能（并行、RL）已验证
- [ ] 整个系统可以端到端运行
- [ ] 新的代码生成路径超越或匹配之前的技能调用路径

---

## 风险和缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM 生成不可靠的代码 | 任务失败 | VDM 反馈 + 多轮改进 |
| 代码执行超时 | 卡死 | 添加超时控制 + 重试机制 |
| 技能学习库污染 | 坏代码被重用 | 质量检查 + 人工审核 |
| 性能下降 | 更慢的执行 | 保持向后兼容，可以回退 |

---

## 开发顺序建议

1. **第一周**：工程基础（tyro + 工厂模式）
   - 快速赢得动力
   - 建立现代化的开发环境

2. **第2-3周**：代理核心（提示词 + 代码执行器）
   - 核心功能正常工作
   - 验证代码生成的可行性

3. **第4-5周**：技能学习（成功库 + 语义搜索）
   - 建立在线学习的基础
   - 跨会话知识积累

4. **第6-9周**：VDM 反馈（多轮改进）
   - 提升任务成功率
   - 体验代码生成的力量

5. **第10-12周**：可选增强和优化
   - 根据实际情况选择（并行、RL、OmegaConf）
   - 微调和性能优化

---

## 资源和文档参考

- **CaP-X 架构分析**: `2026-04-03-capx-architecture-analysis.md`
- **CaP-X 补充遗漏**: `2026-04-03-capx-architecture-gaps.md`
- **CaP-X 功能对标**: `2026-04-03-capx-functional-mapping.md`

---

**准备好开始？让我们从第一阶段开始！**
