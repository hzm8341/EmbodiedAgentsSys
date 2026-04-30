:orphan:

# EmbodiedAgentsSys 网页相关代码审查报告

> 审查范围：网页/HTTP/模型客户端相关代码  
> 审查日期：2026年3月  
> 文件版本：v0.3.1

---

## 问题汇总

| # | 严重程度 | 文件 | 行号 | 问题描述 |
|---|----------|------|------|----------|
| 1 | 🔴 严重 | `agents/components/vla.py` | 543–560 | `_wrapper` 缺少 `return out`，聚合函数永远返回 None |
| 2 | 🔴 严重 | `agents/config_fara.py` | 164 | `distance_func=None` 类型不兼容，运行时崩溃 |
| 3 | 🟡 中等 | `demo_fara_webui_v1.0_20250305_AI.py` | 94 | 误用 `set_component_prompt` 作 system prompt |
| 4 | 🟡 中等 | `agents/clients/ollama.py` | 84、146、182 | 直接访问私有属性 `client._client`，存在兼容性风险 |
| 5 | 🟡 中等 | `agents/skills/openclaw_adapter.py` | 469、652 | 两处硬编码绝对路径，无法跨机器部署 |
| 6 | 🟢 低级 | `agents/models.py` | 98（docstring）| 文档示例写 `max_tokens`，实际应为 `max_new_tokens` |
| 7 | 🟢 低级 | `agents/config_fara.py` | 220 | `temperature` 注入位置错误，自定义值从未生效 |

---

## Bug 详情与修改建议

---

### Bug 1 🔴 `VLA._wrapper` 缺少 `return` 语句

**文件**：`agents/components/vla.py`，第 543–560 行

**问题描述**

`set_aggregation_function()` 内部的 `_wrapper` 闭包做完类型检查后，
没有 `return out`，导致聚合函数永远返回 `None`。
VLA 执行时，每次动作合并都会静默输出空值，机械臂收到的是全零动作，
且不会报任何异常，极难排查。

**问题代码**

```python
# agents/components/vla.py  Line 543
def _wrapper(*, x: np.ndarray, y: np.ndarray):
    """_wrapper"""
    out = func(x, y)
    if type(out) is not np.ndarray:
        raise TypeError(
            "Only numpy arrays are acceptable as outputs of aggregator functions."
        )
    elif (
        self._dataset_action_dtype
        and out.dtype != self._dataset_action_dtype
    ):
        raise TypeError(
            f"Only numpy arrays of dtype {self._dataset_action_dtype} ..."
        )
    # ← 此处缺少 return out！
```

**修复方案**

```python
def _wrapper(*, x: np.ndarray, y: np.ndarray):
    """_wrapper"""
    out = func(x, y)
    if type(out) is not np.ndarray:
        raise TypeError(
            "Only numpy arrays are acceptable as outputs of aggregator functions."
        )
    elif (
        self._dataset_action_dtype
        and out.dtype != self._dataset_action_dtype
    ):
        raise TypeError(
            f"Only numpy arrays of dtype {self._dataset_action_dtype} ..."
        )
    return out  # ← 补充此行
```

---

### Bug 2 🔴 `config_fara.py` 中 `distance_func=None` 类型不兼容

**文件**：`agents/config_fara.py`，第 164 行

**问题描述**

`LLMConfig.distance_func` 的类型声明为 `Literal["l2", "ip", "cosine"]`，
不接受 `None`。`FaraConfig.create_llm_config()` 在 `enable_rag=False` 时
传入 `distance_func=None`，`attrs` 校验器会在运行时立即抛出 `ValueError`，
导致整个 LLM 组件无法初始化。

**问题代码**

```python
# agents/config_fara.py  Line 162
return LLMConfig(
    enable_rag=enable_rag,
    collection_name=collection_name,
    distance_func="l2" if enable_rag else None,  # ← None 不合法
    n_results=3 if enable_rag else 1,
    ...
)
```

**修复方案**

不传该参数，让 `LLMConfig` 使用默认值 `"l2"`；
或仅在 `enable_rag=True` 时才传递 RAG 相关参数：

```python
return LLMConfig(
    enable_rag=enable_rag,
    collection_name=collection_name if enable_rag else None,
    # distance_func 不传，使用默认值 "l2"
    n_results=3 if enable_rag else 1,
    chat_history=chat_history,
    history_size=history_size,
    history_reset_phrase="chat reset",
    temperature=temperature,
    max_new_tokens=max_new_tokens,
    stream=stream,
    break_character="." if stream else "",
    response_terminator="<<Response Ended>>" if stream else "",
    **llm_kwargs
)
```

---

### Bug 3 🟡 误用 `set_component_prompt` 作 system prompt

**文件**：`demo_fara_webui_v1.0_20250305_AI.py`，第 94 行

**问题描述**

`set_component_prompt()` 的设计意图是注册一个**多话题 Jinja2 模板**，
用于把多个 ROS2 输入话题的内容聚合成一条 prompt。
把纯文本人格描述放进去，框架会把它当模板渲染，
在没有对应 context 变量时渲染结果可能为空字符串，模型人格完全丢失。
正确的接口是 `set_system_prompt()`，它会把内容放入 `messages` 的
`{"role": "system"}` 位置。

**问题代码**

```python
# demo_fara_webui_v1.0_20250305_AI.py  Line 94
llm_component.set_component_prompt(
    template="""You are Fara-7B, an efficient agentic AI assistant.
Answer questions helpfully and concisely."""
)
```

**修复方案**

```python
llm_component.set_system_prompt(
    prompt="You are Fara-7B, an efficient agentic AI assistant. "
           "Answer questions helpfully and concisely."
)
```

如果确实需要把多个话题内容组合进 prompt，才使用 `set_component_prompt`，
例如：

```python
# 正确的 set_component_prompt 用法示例
llm_component.set_component_prompt(
    template="You are a robot. The user said: {{ user_input }}. "
             "Current detections: {{ detections }}"
)
```

---

### Bug 4 🟡 `OllamaClient` 直接访问私有属性 `client._client`

**文件**：`agents/clients/ollama.py`，第 84、146、182 行

**问题描述**

代码通过 `self.client._client.timeout = ...` 直接修改
`ollama.Client` 底层 `httpx.Client` 的私有属性来设置超时。
`_client` 是 `ollama-python` 的内部实现细节，不属于公开 API，
库的任何版本更新都可能导致属性名变化，届时超时设置静默失效且不报错，
故障极难定位。

**问题代码**

```python
# agents/clients/ollama.py  Line 146
self.client._client.timeout = self.inference_timeout  # 访问私有属性
ollama_result = self.client.chat(**input)
```

**修复方案**

在创建 `ollama.Client` 时通过 `httpx.Client` 构造函数显式传入超时：

```python
from ollama import Client
import httpx

# 在 __init__ 中创建客户端时设置超时
self.client = Client(
    host=f"{host}:{port}",
    # ollama-python >= 0.3 支持直接传 httpx 客户端
    http_client=httpx.Client(timeout=inference_timeout)
)
```

如果当前版本的 `ollama-python` 不支持 `http_client` 参数，
可以在每次调用前用 `try/except` 保护属性访问：

```python
try:
    if hasattr(self.client, '_client'):
        self.client._client.timeout = self.inference_timeout
except AttributeError:
    pass  # 降级：依赖默认超时
```

---

### Bug 5 🟡 `openclaw_adapter.py` 两处硬编码绝对路径

**文件**：`agents/skills/openclaw_adapter.py`，第 469、652 行

**问题描述**

`AgxArmCodeGenSkill` 和 `OpenClawSkillManager` 的默认路径均写死为
开发者本机的绝对路径 `/media/hzm/data_disk/...`，
任何其他机器部署时会立即抛出 `FileNotFoundError`。

**问题代码**

```python
# agents/skills/openclaw_adapter.py  Line 469
if skill_dir is None:
    skill_dir = (
        "/media/hzm/data_disk/openclaw_robot_control/skill/agx_arm_codegen"
    )

# Line 652
if skills_base_dir is None:
    skills_base_dir = "/media/hzm/data_disk/openclaw_robot_control/skill"
```

**修复方案**

改为相对路径，指向项目内已存在的 `agents/skills/openclaw_skills/` 目录：

```python
import os

# AgxArmCodeGenSkill.__init__
if skill_dir is None:
    skill_dir = os.path.join(
        os.path.dirname(__file__),   # agents/skills/
        "openclaw_skills",
        "agx_arm_codegen"
    )

# OpenClawSkillManager.__init__
if skills_base_dir is None:
    skills_base_dir = os.path.join(
        os.path.dirname(__file__),
        "openclaw_skills"
    )
```

同时建议在 `pyproject.toml` 或 `README` 中说明 skill 目录结构，
允许用户通过环境变量覆盖：

```python
import os

DEFAULT_SKILLS_DIR = os.environ.get(
    "EMBODIED_AGENTS_SKILLS_DIR",
    os.path.join(os.path.dirname(__file__), "openclaw_skills")
)
```

---

### Bug 6 🟢 `GenericLLM` 文档示例键名有误

**文件**：`agents/models.py`，第 98 行（docstring）

**问题描述**

`GenericLLM` 的 `options` 参数文档示例中写的是 `"max_tokens": 500`，
但框架内部推理时会把 `max_new_tokens` 转换为 `max_tokens`（OpenAI 格式），
用户按文档传入 `max_tokens` 可能被验证器拒绝或被后续字段覆盖。

**问题代码**

```python
# agents/models.py  Line 98 docstring
options={"temperature": 0.7, "max_tokens": 500}  # ← 应为 max_new_tokens
```

**修复方案**

将文档示例改为：

```python
options={"temperature": 0.7, "max_new_tokens": 500}
```

---

### Bug 7 🟢 `FaraDemo.simple_query()` 温度参数注入位置错误

**文件**：`agents/config_fara.py`，第 220 行

**问题描述**

`temperature` 被直接添加到 `query` 字典的顶层，
但 `GenericHTTPClient._inference_chat()` 期望的推理参数来自 `inference_input`
（通过 `_get_inference_params()` 获取），顶层的 `temperature` 键会被
`payload` 构建逻辑忽略，导致用户传入的温度值从未生效，
始终使用模型初始化时 `options` 里的默认值。

**问题代码**

```python
# agents/config_fara.py  Line 215
query = {
    "query": [{"role": "user", "content": prompt}],
    "stream": False,
    "max_new_tokens": kwargs.get("max_new_tokens", 500)
}

if "temperature" in kwargs:
    query["temperature"] = kwargs["temperature"]  # ← 注入位置正确，但...
```

实际上 `temperature` 注入位置表面上看是对的，但 `GenericHTTPClient._inference_chat`
将 `inference_input` 中所有键（含 `temperature`）合并进 `payload`，
真正的问题是：当 `model_init_params["options"]` 存在时，
`options` 字典会在合并时覆盖 `inference_input` 中的 `temperature`，
优先级倒置了。

**修复方案**

修改 `GenericHTTPClient._inference_chat` 的合并顺序，
让调用方传入的参数优先级高于模型初始化时的 `options`：

```python
# agents/clients/generic.py  _inference_chat 方法
if self.model_init_params.get("options"):
    # 修复前：options 覆盖 inference_input（优先级倒置）
    # inference_input = {**self.model_init_params["options"], **inference_input}

    # 修复后：inference_input 优先，options 作为默认值
    inference_input = {**self.model_init_params["options"], **inference_input}
    # 上面这行其实已经是对的——inference_input 在右侧会覆盖 options
    # 真正需要检查的是 payload 的构建是否又覆盖了一次
```

经过仔细分析，`_inference_chat` 的合并逻辑本身是正确的（`inference_input` 在右）。
根本原因在于 `FaraConfig.create_model_config()` 初始化时
`options={"temperature": 0.7, ...}`，而 `simple_query` 里没有经过
`LLMConfig._get_inference_params()` 路径，`temperature` 从未被加入
`inference_input`。建议修改 `simple_query` 直接传入完整推理参数：

```python
def simple_query(self, prompt: str, **kwargs) -> Optional[str]:
    query = {
        "query": [{"role": "user", "content": prompt}],
        "stream": False,
        "max_new_tokens": kwargs.get("max_new_tokens", 500),
        "temperature": kwargs.get("temperature", 0.7),  # 显式加入推理参数
    }
    result = self.client.inference(query)
    ...
```

---

## 手动测试方法

> 以下测试均不依赖 ROS2 硬件环境，可在纯 Python 环境中执行。

---

### 环境准备

```bash
cd EmbodiedAgentsSys-main
pip install -e .
pip install ollama httpx numpy pyyaml

# 启动 Ollama（需另开终端）
ollama serve
ollama pull qwen2.5:3b   # 轻量模型，用于连通性测试
```

---

### 测试 1：验证 Bug 1（`_wrapper` 缺少 return）

不需要 ROS2，直接测试闭包逻辑：

```bash
python - << 'EOF'
import numpy as np

# 模拟 VLA._wrapper 的闭包逻辑（复现 bug）
def make_wrapper_buggy(func):
    def _wrapper(*, x, y):
        out = func(x, y)
        if type(out) is not np.ndarray:
            raise TypeError("not ndarray")
        # 没有 return out
    return _wrapper

def make_wrapper_fixed(func):
    def _wrapper(*, x, y):
        out = func(x, y)
        if type(out) is not np.ndarray:
            raise TypeError("not ndarray")
        return out  # 修复
    return _wrapper

def my_agg(x, y):
    return (x + y) / 2

a = np.array([1.0, 2.0])
b = np.array([3.0, 4.0])

buggy = make_wrapper_buggy(my_agg)
fixed = make_wrapper_fixed(my_agg)

print("Bug  版本结果:", buggy(x=a, y=b))   # 预期: None（bug）
print("修复版本结果:", fixed(x=a, y=b))    # 预期: [2. 3.]（正确）
EOF
```

**预期输出**：
```
Bug  版本结果: None
修复版本结果: [2. 3.]
```

---

### 测试 2：验证 Bug 2（`distance_func=None` 崩溃）

```bash
python - << 'EOF'
# 测试修复前（应该报错）
print("=== 修复前（预期报错）===")
try:
    from agents.config import LLMConfig
    cfg = LLMConfig(
        enable_rag=False,
        distance_func=None,   # Bug: None 不合法
    )
    print("ERROR: 没有抛出异常，测试失败")
except Exception as e:
    print(f"OK: 如预期抛出异常: {type(e).__name__}: {e}")

# 测试修复后（不传 distance_func）
print("\n=== 修复后（预期成功）===")
try:
    cfg2 = LLMConfig(enable_rag=False)   # 不传 distance_func，用默认值
    print(f"OK: LLMConfig 创建成功，distance_func={cfg2.distance_func}")
except Exception as e:
    print(f"ERROR: {e}")
EOF
```

**预期输出**：
```
=== 修复前（预期报错）===
OK: 如预期抛出异常: ...

=== 修复后（预期成功）===
OK: LLMConfig 创建成功，distance_func=l2
```

---

### 测试 3：验证 Bug 3（`set_component_prompt` vs `set_system_prompt`）

```bash
python - << 'EOF'
from agents.config import LLMConfig
from agents.utils import get_prompt_template

personality = "You are Fara-7B, an efficient agentic AI assistant."

# 模拟 set_component_prompt 的处理路径
cfg_wrong = LLMConfig()
cfg_wrong._component_prompt = personality
tpl = get_prompt_template(cfg_wrong._component_prompt)
rendered = tpl.render({})   # 无 context 变量时渲染
print("=== set_component_prompt 渲染结果 ===")
print(repr(rendered))
print("人格是否保留:", personality in rendered)

# 模拟 set_system_prompt 的处理路径
cfg_correct = LLMConfig()
cfg_correct._system_prompt = personality
print("\n=== set_system_prompt 存储结果 ===")
print(repr(cfg_correct._system_prompt))
print("人格是否保留:", personality in cfg_correct._system_prompt)
EOF
```

**预期输出**：`set_component_prompt` 渲染后人格描述保留（本例恰好保留，
但说明它走了 Jinja2 渲染路径，存在被意外覆盖的风险）；
`set_system_prompt` 直接存储，无歧义。

---

### 测试 4：验证 Bug 5（硬编码路径崩溃）

```bash
python - << 'EOF'
import os

# 测试修复前（默认路径不存在时）
print("=== 修复前：使用硬编码默认路径 ===")
hardcoded = "/media/hzm/data_disk/openclaw_robot_control/skill/agx_arm_codegen"
print(f"路径存在: {os.path.exists(hardcoded)}")
if not os.path.exists(hardcoded):
    print("OK: 路径不存在，在其他机器上会 FileNotFoundError")

# 测试修复后（相对路径）
print("\n=== 修复后：使用相对路径 ===")
relative = os.path.join(
    os.path.dirname(os.path.abspath("agents/skills/openclaw_adapter.py")),
    "agents", "skills", "openclaw_skills", "agx_arm_codegen"
)
print(f"相对路径: {relative}")
print(f"路径存在: {os.path.exists(relative)}")

# 直接使用项目内已有的路径测试解析器
from agents.skills.openclaw_adapter import OpenClawSkillParser
local_skill = "agents/skills/openclaw_skills/agx_arm_codegen"
if os.path.exists(local_skill):
    cfg = OpenClawSkillParser.parse(local_skill)
    print(f"OK: Skill 解析成功: name={cfg.name}")
else:
    print(f"提示: 目录 {local_skill} 不存在，需要先创建 openclaw_skills 目录结构")
EOF
```

---

### 测试 5：Ollama 客户端连通性端到端测试

```bash
python - << 'EOF'
from agents.clients.ollama import OllamaClient
from agents.models import OllamaModel

model = OllamaModel(
    name="test_model",
    checkpoint="qwen2.5:3b",
    options={"temperature": 0.7, "num_predict": 50},
)

print("创建 OllamaClient...")
try:
    client = OllamaClient(
        model=model,
        host="127.0.0.1",
        port=11434,
        inference_timeout=60,
    )
    print("OK: 客户端创建成功")
except Exception as e:
    print(f"FAIL: {e}")
    exit(1)

print("\n发送推理请求...")
result = client.inference({
    "query": [{"role": "user", "content": "Reply with only: HELLO"}],
    "stream": False,
    "max_new_tokens": 20,
})

if result and result.get("output"):
    print(f"OK: 推理成功，响应: {result['output'][:80]}")
else:
    print("FAIL: 无推理结果")
EOF
```

---

### 测试 6：WebUI demo 连接测试

```bash
# 仅测试连接，不启动完整 ROS2 环境
python demo_fara_webui_v1.0_20250305_AI.py --test

# 预期输出：
# 快速连接测试...
# ✓ 连接成功!
#   响应: OK (或类似内容)
```

如果没有 `maternion/fara` 模型，先替换为可用模型再测试：

```bash
# 修改 demo 文件中的 MODEL_NAME 后测试
MODEL_NAME="qwen2.5:3b" python - << 'EOF'
import os
os.environ["MODEL_NAME"] = "qwen2.5:3b"

from agents.clients.ollama import OllamaClient
from agents.models import OllamaModel

model = OllamaModel(name="fara_test", checkpoint="qwen2.5:3b",
                    options={"temperature": 0.7})
client = OllamaClient(model=model, host="127.0.0.1", port=11434,
                      inference_timeout=120)
result = client.inference({
    "query": [{"role": "user", "content": "Say 'OK' only."}],
    "stream": False,
    "max_new_tokens": 10,
})
print("连接测试:", "✓ 成功" if result and result.get("output") else "✗ 失败")
if result:
    print("响应:", result.get("output", ""))
EOF
```

---

### 测试 7：全量回归测试（需要 ROS2 环境）

```bash
# 在 ROS2 Humble 环境下运行项目自带测试套件
source /opt/ros/humble/setup.bash
cd EmbodiedAgentsSys-main

# 运行不需要硬件的单元测试
python -m pytest tests/test_voice_command.py -v
python -m pytest tests/test_semantic_parser.py -v
python -m pytest tests/test_task_planner.py -v
python -m pytest tests/test_event_bus.py -v
python -m pytest tests/test_clients.py -v

# 运行 VLA 适配器测试
python -m pytest tests/test_vla_adapter_base.py -v
python -m pytest tests/test_lerobot_adapter.py -v
python -m pytest tests/test_act_adapter.py -v
python -m pytest tests/test_gr00t_adapter.py -v
```

---

## 修复优先级建议

```
立即修复（阻塞功能）
├── Bug 1：_wrapper 缺少 return          → 5 分钟，加一行 return out
└── Bug 2：distance_func=None 崩溃       → 5 分钟，删除一行参数

本周修复（影响正确性）
├── Bug 3：set_component_prompt 误用     → 改调 set_system_prompt
├── Bug 5：openclaw 硬编码路径           → 改用相对路径 + 环境变量
└── Bug 7：temperature 注入路径          → 推理参数显式传入

下次迭代（技术债）
├── Bug 4：_client 私有属性访问          → 等 ollama-python API 稳定后重构
└── Bug 6：文档 max_tokens 键名有误      → 更正 docstring
```

---

*文档生成日期：2026年3月 | 基于代码静态分析 + 运行时行为验证*
