:orphan:

# Voice Wake Word Config & Navigation Status Codes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) 为 `SpeechToTextConfig` 添加唤醒词配置示例文档，因为该功能已在代码中实现但缺乏使用说明；(2) 新增 `NavigationStatus` 枚举，提供精细化导航状态码供上层规划器决策。

**Architecture:** `SpeechToText` 已支持 `enable_wakeword=True`，只需补充配置示例和测试；`NavigationStatus` 是纯枚举类，新增到 `agents/components/` 并供 `TaskPlanner` 使用。两个改动均为轻量级。

**Tech Stack:** Python 3.10, `pytest`, 现有 `SpeechToText` 组件

---

## 文件结构

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `agents/components/navigation_status.py` | NavigationStatus 枚举 |
| Modify | `agents/components/__init__.py` | 导出 NavigationStatus |
| Create | `tests/test_navigation_status.py` | 枚举测试 |
| Create | `docs/tutorials/wake_word_configuration.md` | 唤醒词配置教程 |

---

### Task 1: 实现 NavigationStatus 枚举

**Files:**
- Create: `agents/components/navigation_status.py`
- Test: `tests/test_navigation_status.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_navigation_status.py
import pytest
from agents.components.navigation_status import NavigationStatus

def test_all_status_codes_defined():
    assert NavigationStatus.SUCCESS.value == 0
    assert NavigationStatus.CLOSEST_POINT.value == 1
    assert NavigationStatus.PATH_FAIL.value == 2
    assert NavigationStatus.TIMEOUT.value == 3
    assert NavigationStatus.GENERIC_FAIL.value == 4

def test_status_from_int():
    status = NavigationStatus(2)
    assert status == NavigationStatus.PATH_FAIL

def test_is_success():
    assert NavigationStatus.SUCCESS.is_success() is True
    assert NavigationStatus.CLOSEST_POINT.is_success() is True  # 到达最近点也算部分成功
    assert NavigationStatus.PATH_FAIL.is_success() is False
    assert NavigationStatus.TIMEOUT.is_success() is False

def test_requires_replan():
    """PATH_FAIL 和 TIMEOUT 需要重新规划。"""
    assert NavigationStatus.PATH_FAIL.requires_replan() is True
    assert NavigationStatus.TIMEOUT.requires_replan() is True
    assert NavigationStatus.SUCCESS.requires_replan() is False
    assert NavigationStatus.CLOSEST_POINT.requires_replan() is False

def test_description():
    assert "成功" in NavigationStatus.SUCCESS.description()
    assert "路径" in NavigationStatus.PATH_FAIL.description()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_navigation_status.py -v
```
期望：`FAILED`

- [ ] **Step 3: 实现 NavigationStatus**

```python
# agents/components/navigation_status.py
"""导航状态码枚举 — 供任务规划器做精细决策。"""

from enum import IntEnum


class NavigationStatus(IntEnum):
    """
    5 级导航结果状态码（参考 Airship navigation_service_node.py）。

    使用示例::

        status = NavigationStatus.SUCCESS
        if status.is_success():
            proceed_to_grasp()
        elif status.requires_replan():
            task_planner.record_failure(...)
    """
    SUCCESS = 0         # 精确到达目标位姿
    CLOSEST_POINT = 1   # 到达最近可达点（目标不可达但已尽力）
    PATH_FAIL = 2       # 全局路径规划失败
    TIMEOUT = 3         # 导航超时
    GENERIC_FAIL = 4    # 其他失败

    def is_success(self) -> bool:
        """SUCCESS 和 CLOSEST_POINT 均视为可继续执行的结果。"""
        return self in (NavigationStatus.SUCCESS, NavigationStatus.CLOSEST_POINT)

    def requires_replan(self) -> bool:
        """是否需要上层任务规划器介入重新规划。"""
        return self in (NavigationStatus.PATH_FAIL, NavigationStatus.TIMEOUT)

    def description(self) -> str:
        """返回人类可读的中文描述。"""
        descriptions = {
            NavigationStatus.SUCCESS: "导航成功，精确到达目标",
            NavigationStatus.CLOSEST_POINT: "到达最近可达点，目标附近障碍物阻挡",
            NavigationStatus.PATH_FAIL: "路径规划失败，无法找到可行路径",
            NavigationStatus.TIMEOUT: "导航超时，未在规定时间内到达目标",
            NavigationStatus.GENERIC_FAIL: "导航失败（未知原因）",
        }
        return descriptions[self]
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_navigation_status.py -v
```
期望：全部 `PASSED`

- [ ] **Step 5: 导出并提交**

在 `agents/components/__init__.py` 追加：
```python
from .navigation_status import NavigationStatus
```

```bash
git add agents/components/navigation_status.py \
        agents/components/__init__.py \
        tests/test_navigation_status.py
git commit -m "feat: add NavigationStatus enum with 5-level status codes for task replanning"
```

---

### Task 2: TaskPlanner 集成 NavigationStatus

**Files:**
- Modify: `agents/components/task_planner.py`（添加处理方法）
- Test: `tests/test_task_planner_component.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_task_planner_component.py
from agents.components.navigation_status import NavigationStatus

def test_planner_handles_nav_status_path_fail(planner):
    """PATH_FAIL 应触发记录失败。"""
    planner.handle_navigation_result(
        NavigationStatus.PATH_FAIL,
        target="table",
        location="table",
    )
    history = planner.get_failure_history()
    assert len(history) == 1
    assert "table" in history[0]

def test_planner_handles_nav_status_success(planner):
    """SUCCESS 不应记录失败。"""
    planner.handle_navigation_result(
        NavigationStatus.SUCCESS,
        target="desk",
        location="desk",
    )
    assert planner.get_failure_history() == []

def test_planner_handles_nav_status_closest_point(planner):
    """CLOSEST_POINT 不记录失败（视为成功）。"""
    planner.handle_navigation_result(
        NavigationStatus.CLOSEST_POINT,
        target="shelf",
        location="shelf",
    )
    assert planner.get_failure_history() == []
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_task_planner_component.py::test_planner_handles_nav_status_path_fail -v
```

- [ ] **Step 3: 在 TaskPlanner 中添加 `handle_navigation_result`**

在 `agents/components/task_planner.py` 的 `TaskPlanner` 类中追加：

```python
def handle_navigation_result(
    self,
    status: "NavigationStatus",
    target: str,
    location: str,
) -> None:
    """
    根据导航状态码决定是否记录失败。

    Args:
        status: NavigationStatus 枚举值
        target: 导航目标名称
        location: 目标地点名称
    """
    if status.requires_replan():
        self.record_failure(
            target=target,
            location=location,
            reason=status.description(),
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_task_planner_component.py -v
```
期望：全部 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add agents/components/task_planner.py tests/test_task_planner_component.py
git commit -m "feat: TaskPlanner.handle_navigation_result integrates NavigationStatus"
```

---

### Task 3: 补充唤醒词配置教程文档

**Files:**
- Create: `docs/tutorials/wake_word_configuration.md`

> 注意：`SpeechToText` 已内置唤醒词支持（`enable_wakeword=True`），此 Task 仅补充缺失的使用文档。

- [ ] **Step 1: 确认现有 `SpeechToTextConfig` 唤醒词字段**

```bash
grep -n "wakeword\|enable_wakeword" \
  /media/hzm/data_disk/EmbodiedAgentsSys/agents/components/speechtotext.py \
  /media/hzm/data_disk/EmbodiedAgentsSys/agents/config.py 2>/dev/null | head -20
```

- [ ] **Step 2: 创建配置教程**

```markdown
# 唤醒词配置指南

## 功能说明

`SpeechToText` 组件支持唤醒词检测，启用后机器人只在听到指定唤醒词后才开始录制指令。

## 启用唤醒词

```python
from agents.components import SpeechToText
from agents.config import SpeechToTextConfig
from agents.ros import Topic

config = SpeechToTextConfig(
    enable_vad=True,          # 必须同时开启 VAD
    enable_wakeword=True,     # 开启唤醒词检测
    wakeword_threshold=0.5,   # 唤醒词置信度阈值（越高越严格）
)

audio_topic = Topic(name="audio", msg_type="Audio")
text_topic  = Topic(name="text",  msg_type="String")

stt = SpeechToText(
    inputs=[audio_topic],
    outputs=[text_topic],
    model_client=whisper_client,
    config=config,
    trigger=audio_topic,
    component_name="stt_with_wakeword",
)
```

## 工作流程

```
麦克风输入
  └─ VAD 检测到语音开始
       └─ 唤醒词分类器持续检测
            ├─ 未检测到唤醒词 → 丢弃音频
            └─ 检测到唤醒词 → 开始缓冲后续音频
                 └─ VAD 检测到语音结束 → 送入 Whisper ASR → 发布文本
```

## 默认唤醒词模型

系统默认使用 "Hey Jarvis" 唤醒词模型（`hey_jarvis`）。
如需自定义唤醒词，替换 `wakeword_model_path` 指向自训练的 ONNX 模型。

## 与 Airship 的对比

| 特性 | EmbodiedAgentsSys | Airship |
|------|------------------|---------|
| ASR 后端 | Whisper（via RoboML） | OpenAI Whisper |
| 唤醒词引擎 | 自定义 ONNX | PocketSphinx |
| VAD | Silero VAD | PyAudio 静音检测 |
| 触发方式 | enable_wakeword=True | 硬编码 "AIRSHIP" |

## 注意事项

- `enable_wakeword=True` 时必须同时设置 `enable_vad=True`
- 需要 `pyaudio` 已安装：`pip install pyaudio`
- 唤醒词模型文件需提前下载（见 `agents/utils/voice.py` 中 `load_model`）
```

- [ ] **Step 3: 保存文件**

保存到 `docs/tutorials/wake_word_configuration.md`

- [ ] **Step 4: 提交**

```bash
git add docs/tutorials/wake_word_configuration.md
git commit -m "docs: add wake word configuration tutorial for SpeechToText component"
```

---

## 验收标准

- [ ] `pytest tests/test_navigation_status.py -v` 全部通过
- [ ] `NavigationStatus.PATH_FAIL.requires_replan()` 返回 `True`
- [ ] `TaskPlanner.handle_navigation_result(SUCCESS, ...)` 不记录失败
- [ ] `TaskPlanner.handle_navigation_result(PATH_FAIL, ...)` 自动记录失败
- [ ] 唤醒词教程文档存在于 `docs/tutorials/`
