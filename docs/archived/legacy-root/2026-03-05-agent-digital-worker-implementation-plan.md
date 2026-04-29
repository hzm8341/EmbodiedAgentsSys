# Agent数字员工实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 基于EmbodiedAgentsSys框架，实现Agent数字员工的语音示教、上料/预组装、柔性装配三大场景功能

**Architecture:** 采用层级式Agent架构 - 用户层→任务理解层→任务规划层→技能执行层→学习进化层。基于EmbodiedAgentsSys的组件化设计，新增任务规划组件、机械臂控制Skill、力控模块。

**Tech Stack:** 
- 基础框架: EmbodiedAgentsSys (ROS2 + Python)
- 语音: SpeechToText + ASR服务
- 理解: LLM (GPT-4/Claude/Qwen)
- 视觉: Vision组件 + 3DGS重建
- 机械臂: pyAgxArm / ABB EGM / Fanuc J519
- 学习: LoRA微调

---

## 阶段一：语音示教功能开发

### Task 1: 语音输入通道搭建

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/components/voice_command.py`
- Modify: `/media/hzm/data_disk/EmbodiedAgentsSys/examples/complete_agent.py` (参考)

**Step 1: 创建语音命令组件测试**

```python
# tests/test_voice_command.py
import pytest
from agents.components.voice_command import VoiceCommand

def test_voice_command_init():
    component = VoiceCommand(
        component_name="voice_command",
        trigger_topic="audio_input"
    )
    assert component.name == "voice_command"
```

**Step 2: 运行测试验证失败**

Run: `cd /media/hzm/data_disk/EmbodiedAgentsSys && pytest tests/test_voice_command.py::test_voice_command_init -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: 实现语音命令组件**

```python
# agents/components/voice_command.py
from agents.components.component_base import BaseComponent

class VoiceCommand(BaseComponent):
    """语音命令理解组件"""
    
    def __init__(self, component_name: str, trigger_topic: str, **kwargs):
        super().__init__(component_name)
        self.trigger_topic = trigger_topic
        # 初始化ASR客户端
        
    async def process(self, audio_data):
        # ASR识别 + 语义解析
        pass
```

**Step 4: 运行测试验证通过**

Run: `cd /media/hzm/data_disk/EmbodiedAgentsSys && pytest tests/test_voice_command.py -v`
Expected: PASS

---

### Task 2: 语义解析器实现

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/components/semantic_parser.py`
- Test: `tests/test_semantic_parser.py`

**Step 1: 编写语义解析测试**

```python
# tests/test_semantic_parser.py
import pytest
from agents.components.semantic_parser import SemanticParser

def test_parse_motion_command():
    parser = SemanticParser()
    result = parser.parse("向前20厘米")
    assert result["intent"] == "motion"
    assert result["direction"] == "forward"
    assert result["distance"] == 0.2
```

**Step 2: 运行测试**

Run: `pytest tests/test_semantic_parser.py::test_parse_motion_command -v`
Expected: FAIL

**Step 3: 实现语义解析器**

```python
# agents/components/semantic_parser.py
from typing import Dict, Any
import re

class SemanticParser:
    """语义解析器 - 解析语音指令为结构化动作"""
    
    # 方向映射
    DIRECTION_MAP = {
        "前": "forward", "后": "backward",
        "上": "up", "下": "down",
        "左": "left", "右": "right"
    }
    
    def parse(self, text: str) -> Dict[str, Any]:
        # 解析意图
        intent = self._parse_intent(text)
        
        # 解析参数
        params = self._parse_params(text)
        
        return {"intent": intent, **params}
```

**Step 4: 验证通过**

Run: `pytest tests/test_semantic_parser.py -v`
Expected: PASS

---

### Task 3: 机械臂控制Skill封装

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/arm_control/__init__.py`
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/arm_control/motion_skill.py`
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/arm_control/agx_arm_skill.py`
- Test: `tests/test_arm_control_skill.py`

**Step 1: 编写运动控制Skill测试**

```python
# tests/test_arm_control_skill.py
import pytest
from skills.arm_control.motion_skill import MotionSkill

@pytest.mark.asyncio
async def test_move_forward():
    skill = MotionSkill()
    result = await skill.execute(direction="forward", distance=0.2)
    assert result.status == "success"
```

**Step 2: 运行测试**

Run: `cd /media/hzm/data_disk/EmbodiedAgentsSys && pytest tests/test_arm_control_skill.py -v`
Expected: FAIL

**Step 3: 实现MotionSkill**

```python
# skills/arm_control/motion_skill.py
from agents.skills import BaseSkill, SkillResult, SkillStatus

class MotionSkill(BaseSkill):
    """机械臂运动控制Skill"""
    
    metadata = SkillMetadata(
        name="arm_motion",
        description="控制机械臂末端运动",
        inputs={"direction": str, "distance": float}
    )
    
    async def execute(self, direction: str, distance: float) -> SkillResult:
        # 调用机械臂控制接口
        # 实现运动逻辑
        return SkillResult(status=SkillStatus.SUCCESS)
```

**Step 4: 验证通过**

Run: `pytest tests/test_arm_control_skill.py -v`
Expected: PASS

---

### Task 4: 语音示教端到端集成

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/examples/voice_teaching_agent.py`
- Test: `tests/test_voice_teaching_integration.py`

**Step 1: 编写集成测试**

```python
# tests/test_voice_teaching_integration.py
@pytest.mark.asyncio
async def test_voice_teaching_flow():
    # 1. 语音输入
    audio = load_test_audio("forward_20cm.wav")
    
    # 2. 语音识别
    text = await asr.process(audio)
    assert text == "向前20厘米"
    
    # 3. 语义解析
    parser = SemanticParser()
    parsed = parser.parse(text)
    assert parsed["intent"] == "motion"
    
    # 4. 执行动作
    skill = MotionSkill()
    result = await skill.execute(**parsed["params"])
    assert result.status == "success"
```

**Step 2: 运行集成测试**

Run: `pytest tests/test_voice_teaching_integration.py -v`
Expected: FAIL (逐步实现各模块)

**Step 3: 创建示例Agent**

```python
# examples/voice_teaching_agent.py
from agents.components import SpeechToText, LLM
from agents.components.semantic_parser import SemanticParser
from skills.arm_control import MotionSkill

class VoiceTeachingAgent:
    """语音示教Agent"""
    
    def __init__(self):
        self.stt = SpeechToText(...)
        self.parser = SemanticParser()
        self.motion_skill = MotionSkill()
    
    async def process(self, audio_data):
        # 语音识别
        text = await self.stt.process(audio_data)
        
        # 语义解析
        parsed = self.parser.parse(text)
        
        # 执行
        result = await self.motion_skill.execute(**parsed)
        
        return result
```

---

## 阶段二：上料/预组装场景开发

### Task 5: 视觉感知Skill

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/vision/perception_skill.py`
- Test: `tests/test_vision_skill.py`

**Step 1: 创建视觉感知测试**

```python
# tests/test_vision_skill.py
import pytest
from skills.vision.perception_skill import VisionPerceptionSkill

@pytest.mark.asyncio
async def test_detect_workpiece():
    skill = VisionPerceptionSkill()
    # 模拟图像输入
    result = await skill.execute(image=mock_image)
    assert result.output["position"] is not None
```

**Step 2: 运行测试**

Run: `pytest tests/test_vision_skill.py -v`
Expected: FAIL

**Step 3: 实现视觉感知Skill**

```python
# skills/vision/perception_skill.py
from agents.skills import BaseSkill, SkillResult

class VisionPerceptionSkill(BaseSkill):
    """视觉感知Skill - 检测工件位置和姿态"""
    
    metadata = SkillMetadata(
        name="vision_perception",
        inputs={"image": object},
        outputs={"position": dict, "orientation": dict}
    )
    
    async def execute(self, image) -> SkillResult:
        # 调用视觉模型检测
        # 返回位置、姿态、类型
        pass
```

---

### Task 6: 抓取规划Skill

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/manipulation/grasp_skill.py`
- Test: `tests/test_grasp_skill.py`

---

### Task 7: 任务规划Agent增强

**Files:**
- Modify: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/components/llm.py`
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/components/task_planner.py`

**Step 1: 创建任务规划组件**

```python
# agents/components/task_planner.py
from agents.components.llm import LLMComponent

class TaskPlanner(LLMComponent):
    """任务规划组件 - 将高层指令拆解为Skill序列"""
    
    def __init__(self, skills: List[str], **kwargs):
        super().__init__(...)
        self.available_skills = skills
        
    async def plan(self, instruction: str) -> List[Dict]:
        # 构建Prompt包含可用Skills
        # 调用LLM生成执行计划
        pass
```

---

## 阶段三：柔性装配场景开发

### Task 8: 力控模块开发

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/force_control/force_sensor.py`
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/force_control/impedance_control.py`
- Test: `tests/test_force_control.py`

---

### Task 9: 3D感知集成

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/vision/reconstruction3d.py`
- Integrate: 与AIR项目的3DGS模块对接

---

### Task 10: 装配规划Skill

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/manipulation/assembly_skill.py`
- Test: `tests/test_assembly_skill.py`

---

## 阶段四：示教学习功能开发

### Task 11: 示教录制模块

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/learning/teleop_recorder.py`
- Test: `tests/test_teleop_recorder.py`

---

### Task 12: Skill生成器

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/learning/skill_generator.py`
- Test: `tests/test_skill_generator.py`

---

### Task 13: 参数优化模块

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/learning/parameter_optimizer.py`
- Test: `tests/test_parameter_optimizer.py`

---

## 实施顺序总结

| 阶段 | 优先级 | 任务数 | 预计时间 |
|-----|-------|-------|---------|
| Phase 1 | P0 | 4个 | 2周 |
| Phase 2 | P1 | 3个 | 3周 |
| Phase 3 | P1 | 3个 | 4周 |
| Phase 4 | P2 | 3个 | 3周 |
| **总计** | - | **13个** | **12周** |

---

## 依赖关系图

```
Phase 1 (语音示教)
├── Task 1: 语音输入
├── Task 2: 语义解析
├── Task 3: 运动控制
└── Task 4: 端到端集成

Phase 2 (上料场景)
├── Task 5: 视觉感知 ← Task 2依赖
├── Task 6: 抓取规划
└── Task 7: 任务规划 ← Task 2依赖

Phase 3 (柔性装配)
├── Task 8: 力控模块 ← Task 3依赖
├── Task 9: 3D感知 ← Task 5依赖
└── Task 10: 装配规划 ← Task 7依赖

Phase 4 (示教学习)
├── Task 11: 示教录制 ← Phase 1-3
├── Task 12: Skill生成
└── Task 13: 参数优化
```

---

## 验收标准

### Phase 1 验收
- [ ] 语音输入识别准确率 > 90%
- [ ] 语义解析准确率 > 85%
- [ ] 基础运动指令执行响应 < 500ms

### Phase 2 验收
- [ ] 视觉识别准确率 > 95%
- [ ] 抓取成功率 > 93%
- [ ] 单件cycle time < 30s

### Phase 3 验收
- [ ] 装配精度 ±0.5mm
- [ ] 装配成功率 > 88%
- [ ] 力控响应时间 < 10ms

### Phase 4 验收
- [ ] 单次示教生成可执行Skill
- [ ] Skill参数化调整成功率 > 90%
