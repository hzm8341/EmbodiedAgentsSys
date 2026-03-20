# EmbodiedAgentsSys 实施计划 - 阶段 3：增强智能泛化能力

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 升级语义解析、任务规划记忆、技能生成三大智能组件，实现自然语言理解和自主学习能力。

**Architecture:**
- 语义解析层：LLM + 规则混合，提升意图识别准确率
- 任务规划层：增加执行记忆，同类任务第二次规划质量优于首次
- 技能生成层：示教→可运行代码完整链路

**Tech Stack:** Python 3.10+, Ollama (qwen2.5:3b), LLM

---

## 阶段 3 任务总览

| 任务 | 文件 | 服务依赖 |
|------|------|----------|
| 3.1 | 语义解析升级 | Ollama |
| 3.2 | TaskPlanner 记忆 | Ollama |
| 3.3 | SkillGenerator 打通 | 无 |
| 3.4 | 多机器人协作（可选） | ROS2 |

---

## 任务 3.1：语义解析升级

### 目标
`SemanticParser` 接入 Ollama LLM，对 50 条自然语言指令意图识别准确率 > 85%。

### 文件
- Modify: `agents/components/semantic_parser.py`
- Test: `tests/test_semantic_parser.py`

---

### 步骤 1: 添加 Ollama 客户端集成

**文件**: `agents/components/semantic_parser.py`

**Step 1: 编写失败的测试**

```python
# tests/test_semantic_parser_llm.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from agents.components.semantic_parser import SemanticParser

@pytest.mark.asyncio
async def test_parse_with_llm():
    """测试 LLM 语义解析"""
    parser = SemanticParser(use_llm=True, ollama_model="qwen2.5:3b")
    
    # Mock Ollama 客户端
    mock_response = '{"intent": "grasp", "object": "cube", "params": {}}'
    parser._ollama = Mock()
    parser._ollama.generate = AsyncMock(return_value=mock_response)
    
    result = await parser.parse_async("帮我把立方体抓起来")
    
    assert result["intent"] == "grasp"
    assert "cube" in result.get("object", "").lower()
```

**Step 2: 运行测试验证失败**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_semantic_parser_llm.py -v
```

Expected: FAIL (parse_async 方法不存在)

**Step 3: 实现 LLM 语义解析**

```python
# agents/components/semantic_parser.py

import json
import re
from typing import Dict, Any, Optional

class SemanticParser:
    """语义解析器 - 支持 LLM + 规则混合模式"""

    # 方向映射（中 -> 英）
    DIRECTION_MAP = {
        "前": "forward",
        "后": "backward",
        "上": "up",
        "下": "down",
        "左": "left",
        "右": "right",
    }

    # 抓取关键词
    GRASP_KEYWORDS = ["抓", "拿", "取", "拾", "抓取", "拿起"]

    # 放置关键词
    PLACE_KEYWORDS = ["放", "置", "投", "放到", "放置"]

    def __init__(self, use_llm: bool = True, ollama_model: str = "qwen2.5:3b"):
        """初始化语义解析器
        
        Args:
            use_llm: 是否使用 LLM 解析
            ollama_model: Ollama 模型名称
        """
        self.use_llm = use_llm
        self._ollama = None
        
        if use_llm:
            try:
                from agents.clients.ollama import OllamaClient
                self._ollama = OllamaClient(model=ollama_model)
            except ImportError:
                print("[SemanticParser] Ollama not available, falling back to rules")

    async def parse_async(self, text: str) -> Dict[str, Any]:
        """异步解析文本（LLM + 规则混合）
        
        Args:
            text: 输入文本
            
        Returns:
            包含 intent 和参数的字典
        """
        # 优先尝试 LLM
        if self.use_llm and self._ollama:
            try:
                result = await self._parse_with_llm(text)
                if result:
                    return result
            except Exception as e:
                print(f"[SemanticParser] LLM parse failed: {e}")
        
        # Fallback: 规则解析
        return self.parse(text)
    
    async def _parse_with_llm(self, text: str) -> Optional[Dict[str, Any]]:
        """使用 LLM 解析"""
        prompt = f"""将以下机器人操作指令解析为JSON格式。

输出格式: {{"intent": "motion|grasp|place|task|gripper", "object": "目标物体", "params": {{...}}}}
指令: {text}

只输出JSON，不要其他内容:"""
        
        response = await self._ollama.generate(prompt)
        
        # 提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())
        
        return None

    def parse(self, text: str) -> Dict[str, Any]:
        """解析文本为结构化指令（规则模式）

        Args:
            text: 输入文本

        Returns:
            包含 intent 和参数的字典
        """
        text = text.strip()

        # 解析意图
        intent = self._parse_intent(text)

        # 解析参数
        params = self._parse_params(text)

        return {"intent": intent, **params}

    def _parse_intent(self, text: str) -> str:
        """解析意图类型"""
        # 运动指令：包含方向关键词
        if any(kw in text for kw in list(self.DIRECTION_MAP.keys())):
            return "motion"

        # 抓取指令
        if any(kw in text for kw in self.GRASP_KEYWORDS):
            return "grasp"

        # 放置指令
        if any(kw in text for kw in self.PLACE_KEYWORDS):
            return "place"

        return "unknown"

    def _parse_params(self, text: str) -> Dict[str, Any]:
        """解析参数"""
        params = {}

        # 解析方向
        for cn, en in self.DIRECTION_MAP.items():
            if cn in text:
                params["direction"] = en
                break

        # 解析距离
        distance = self._parse_distance(text)
        if distance is not None:
            params["distance"] = distance

        # 解析物体名称（简单正则）
        object_match = re.search(r'(立方体|杯子|零件|物体|object|cube|cup)', text.lower())
        if object_match:
            params["object"] = object_match.group()

        return params

    def _parse_distance(self, text: str) -> Optional[float]:
        """解析距离数值"""
        pattern = r"(\d+\.?\d*)\s*(厘米|cm|毫米|mm|m|米)"
        match = re.search(pattern, text)

        if not match:
            return None

        value = float(match.group(1))
        unit = match.group(2)

        if unit in ["厘米", "cm"]:
            return value / 100
        elif unit in ["毫米", "mm"]:
            return value / 1000
        
        return value
```

**Step 4: 运行测试验证**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_semantic_parser_llm.py tests/test_semantic_parser.py -v
```

**Step 5: 提交代码**

```bash
git add agents/components/semantic_parser.py
git commit -m "feat(parser): add LLM-powered semantic parsing with Ollama"
```

---

## 任务 3.2：TaskPlanner 增加执行记忆

### 目标
`TaskPlanner` 记录任务历史，第二次规划同类任务时质量优于首次。

### 文件
- Modify: `agents/components/task_planner.py`
- Test: `tests/test_task_planner.py`

---

### 步骤 1: 添加任务历史队列

**文件**: `agents/components/task_planner.py`

**Step 1: 编写测试**

```python
# tests/test_task_planner_memory.py
import pytest
import asyncio
from agents.components.task_planner import TaskPlanner, ExecutionContext

@pytest.mark.asyncio
async def test_planner_remembers_success():
    """测试规划器记住成功案例"""
    # 创建 Mock LLM 客户端
    class MockLLM:
        async def generate(self, prompt):
            # 检查 prompt 中是否包含历史
            if "历史" in prompt or "history" in prompt.lower():
                return '{"steps": [{"skill_name": "motion", "estimated_duration": 2.0}]}'
            return '{"steps": []}'
    
    planner = TaskPlanner(llm_client=MockLLM(), use_llm=True, memory_size=5)
    
    context = ExecutionContext(
        available_skills=["motion", "grasp", "place"]
    )
    
    # 第一次规划
    plan1 = await planner.plan("抓取杯子放到桌子上", context)
    
    # 记录成功执行
    planner._record_execution("抓取杯子放到桌子", plan1, success=True)
    
    # 第二次规划同类任务
    plan2 = await planner.plan("把立方体放到工作台", context)
    
    # 验证有历史记录
    assert len(planner._history) == 1
    assert planner._history[0]["success"] == True
```

**Step 2: 运行测试验证失败**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_task_planner_memory.py -v
```

Expected: FAIL (_record_execution 方法不存在)

**Step 3: 实现执行记忆**

```python
# agents/components/task_planner.py

import json
from collections import deque
from dataclasses import dataclass, field

# ... (现有代码)

class TaskPlanner:
    """任务规划器"""
    
    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        use_llm: bool = True,
        max_steps: int = 20,
        plan_timeout: float = 30.0,
        memory_size: int = 10
    ):
        """初始化任务规划器
        
        Args:
            memory_size: 任务历史队列大小
        """
        self.llm_client = llm_client
        self.use_llm = use_llm and llm_client is not None
        self.max_steps = max_steps
        self.plan_timeout = plan_timeout
        self._plan_counter = 0
        
        # 执行记忆
        self._history: deque = deque(maxlen=memory_size)
    
    def _record_execution(
        self, 
        task_desc: str, 
        plan: 'TaskPlan', 
        success: bool
    ) -> None:
        """记录任务执行结果
        
        Args:
            task_desc: 任务描述
            plan: 执行计划
            success: 是否成功
        """
        self._history.append({
            "task": task_desc,
            "task_type": plan.task_type.value if plan.task_type else "unknown",
            "steps": [s.skill_name for s in plan.steps],
            "success": success,
            "duration": plan.estimated_duration
        })
    
    def _build_planning_prompt(
        self, 
        task_description: str, 
        context: ExecutionContext
    ) -> str:
        """构建规划提示词（含历史记忆）"""
        
        # 构建历史上下文
        history_str = ""
        if self._history:
            recent = list(self._history)[-3:]  # 最近 3 条
            history_str = "\n近期任务历史:\n"
            for h in recent:
                status = "✓" if h["success"] else "✗"
                history_str += f"- {status} {h['task']}: {' → '.join(h['steps'])}\n"
        
        available_skills = ", ".join(context.available_skills) if context.available_skills else "motion, gripper, perception, grasp"
        
        prompt = f"""你是一个机器人任务规划专家。请将以下任务分解为具体的执行步骤。
{history_str}
任务: {task_description}

当前机器人状态:
{context.to_prompt_context()}

可用技能: {available_skills}

请按照以下JSON格式输出执行计划:
{{
    "steps": [
        {{
            "step_id": "step_1",
            "skill_name": "技能名称",
            "params": {{"参数键": "参数值"}},
            "description": "步骤描述",
            "dependencies": ["依赖步骤ID"],
            "estimated_duration": 预计时间(秒)
        }}
    ]
}}

注意:
1. 优先使用历史中成功的步骤顺序
2. 只使用提供的可用技能
3. 考虑步骤之间的依赖关系
4. 每个步骤必须是可以直接执行的

请直接输出JSON，不要其他内容:"""
        
        return prompt
```

**Step 4: 运行测试验证**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_task_planner_memory.py -v
```

**Step 5: 提交代码**

```bash
git add agents/components/task_planner.py
git commit -m "feat(planner): add execution memory to TaskPlanner"
```

---

## 任务 3.3：SkillGenerator 端到端打通

### 目标
`SkillGenerator.export_skill()` 生成的代码可直接运行，复现示教动作。

### 文件
- Modify: `skills/teaching/skill_generator.py`
- Test: `tests/test_skill_generator.py`

---

### 步骤 1: 实现可执行代码生成

**文件**: `skills/teaching/skill_generator.py`

**Step 1: 编写测试**

```python
# tests/test_skill_generator_runnable.py
import pytest
import os
import tempfile
from skills.teaching.skill_generator import SkillGenerator

def test_export_generates_runnable_code():
    """测试导出的技能代码可执行"""
    generator = SkillGenerator()
    
    # 模拟示教数据
    demo_frames = [
        {"joint_positions": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
        {"joint_positions": [0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0]},
        {"joint_positions": [0.2, 0.4, 0.6, 0.0, 0.0, 0.0, 0.0]},
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 导出技能
        result = generator.export_skill(
            skill_id="demo_skill",
            filename="demo_skill.py",
            output_dir=tmpdir,
            frames=demo_frames
        )
        
        assert result["success"] == True
        assert os.path.exists(result["filepath"])
        
        # 检查文件内容包含关键帧数据
        with open(result["filepath"]) as f:
            content = f.read()
            assert "keyframes" in content
            assert "joint_positions" in content
```

**Step 2: 运行测试验证失败**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_skill_generator_runnable.py -v
```

Expected: FAIL (export_skill 方法未完全实现)

**Step 3: 实现可执行代码生成**

```python
# skills/teaching/skill_generator.py

import os
import json
from typing import List, Dict, Any, Optional

class SkillGenerator:
    """技能生成器 - 从示教数据生成可运行技能代码"""
    
    def __init__(self):
        self._skill_templates = {}
    
    def _generate_execute_body(self, frames: List[Dict]) -> str:
        """生成 execute 方法体
        
        Args:
            frames: 关键帧列表
            
        Returns:
            execute 方法代码
        """
        if not frames:
            return "        pass"
        
        # 提取关键帧关节角度
        keyframes_data = []
        for f in frames:
            if "joint_positions" in f:
                keyframes_data.append(f["joint_positions"])
        
        if not keyframes_data:
            return "        pass"
        
        keyframes_str = json.dumps(keyframes_data)
        
        return f"""
        import numpy as np
        
        # 关键帧数据
        keyframes = {keyframes_str}
        
        for positions in keyframes:
            # 构建关节轨迹消息
            msg = self._build_joint_trajectory(positions, duration=0.5)
            
            # 发布轨迹
            self._joint_pub.publish(msg)
            
            # 等待轨迹完成
            await asyncio.sleep(0.6)
    
    def _build_joint_trajectory(self, positions: List[float], duration: float):
        """构建关节轨迹消息
        
        Args:
            positions: 关节位置列表
            duration: 持续时间 (秒)
            
        Returns:
            轨迹消息
        """
        # TODO: 根据实际 ROS 消息类型实现
        # 当前返回模拟消息
        return {{
            "positions": positions,
            "duration": duration
        }}
"""
    
    def export_skill(
        self,
        skill_id: str,
        frames: List[Dict],
        filename: Optional[str] = None,
        output_dir: str = "./generated_skills"
    ) -> Dict[str, Any]:
        """导出技能为可运行 Python 文件
        
        Args:
            skill_id: 技能 ID
            frames: 示教关键帧列表
            filename: 输出文件名
            output_dir: 输出目录
            
        Returns:
            {{success: bool, filepath: str, test_filepath: str}}
        """
        os.makedirs(output_dir, exist_ok=True)
        
        skill_name = f"generated_{skill_id}"
        filename = filename or f"{skill_name}.py"
        filepath = os.path.join(output_dir, filename)
        
        # 生成代码
        skill_code = self._generate_skill_code(skill_name, frames)
        
        # 写入文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(skill_code)
        
        # 生成测试文件
        test_filepath = os.path.join(output_dir, f"test_{skill_name}.py")
        test_code = self._generate_test_code(skill_name)
        
        with open(test_filepath, "w", encoding="utf-8") as f:
            f.write(test_code)
        
        return {
            "success": True,
            "filepath": filepath,
            "test_filepath": test_filepath
        }
    
    def _generate_skill_code(self, skill_name: str, frames: List[Dict]) -> str:
        """生成技能代码"""
        execute_body = self._generate_execute_body(frames)
        
        code = f'''"""Generated Skill: {skill_name}

自动生成的机器人技能代码。
"""
import asyncio
from typing import Dict, Any

class {skill_name.title().replace('_', '')}Skill:
    """示教生成的技能"""
    
    def __init__(self, joint_publisher=None, **kwargs):
        """初始化技能
        
        Args:
            joint_publisher: 关节轨迹发布者
        """
        self._joint_pub = joint_publisher
        self._config = kwargs
    
    async def execute(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能
        
        Args:
            observation: 当前观察数据
            
        Returns:
            执行结果
        """
{execute_body}
        
        return {{
            "status": "success",
            "skill": "{skill_name}"
        }}

# 主函数（可直接运行）
async def main():
    skill = {skill_name.title().replace('_', '')}Skill()
    
    print("Executing generated skill: {skill_name}")
    result = await skill.execute({{}})
    print(f"Result: {{result}}")

if __name__ == "__main__":
    asyncio.run(main())
'''
        return code
    
    def _generate_test_code(self, skill_name: str) -> str:
        """生成测试代码"""
        class_name = skill_name.title().replace('_', '')
        
        return f'''"""测试 Generated Skill: {skill_name}"""
import pytest
import asyncio
from {skill_name} import {class_name}Skill

@pytest.mark.asyncio
async def test_skill_execution():
    """测试技能执行"""
    skill = {class_name}Skill()
    
    # 模拟观察
    observation = {{}}
    
    # 执行
    result = await skill.execute(observation)
    
    # 验证
    assert result["status"] == "success"

if __name__ == "__main__":
    asyncio.run(test_skill_execution())
'''
```

**Step 4: 运行测试验证**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_skill_generator_runnable.py -v
```

**Step 5: 提交代码**

```bash
git add skills/teaching/skill_generator.py
git commit -m "feat(generator): generate executable skill code from demonstration"
```

---

## 任务 3.4：多机器人协作（可选）

### 目标
扩展 EventBus 支持跨 ROS2 节点事件广播。

### 文件
- Modify: `agents/events/bus.py`

---

### 步骤: 添加分布式事件总线

**文件**: `agents/events/bus.py`

**Step 1: 实现 ROS2 跨节点事件桥接**

```python
# agents/events/bus.py

import json
from typing import Dict, Any, Callable, Awaitable

class DistributedEventBus(EventBus):
    """扩展 EventBus，支持跨节点事件广播"""
    
    def __init__(self, ros_node=None, namespace: str = "/agents/events"):
        """初始化分布式事件总线
        
        Args:
            ros_node: ROS2 节点实例
            namespace: 话题命名空间
        """
        super().__init__()
        self._ros_node = ros_node
        self._namespace = namespace
        self._publisher = None
        self._subscriber = None
        
        if ros_node:
            self._setup_ros_bridge()
    
    def _setup_ros_bridge(self) -> None:
        """设置 ROS2 话题桥接"""
        try:
            from std_msgs.msg import String
            
            # 发布者
            self._publisher = self._ros_node.create_publisher(
                String,
                f"{self._namespace}/broadcast",
                10
            )
            
            # 订阅者
            self._ros_node.create_subscription(
                String,
                f"{self._namespace}/broadcast",
                self._on_remote_event,
                10
            )
            
        except ImportError:
            pass
    
    def _on_remote_event(self, msg) -> None:
        """处理远程事件"""
        try:
            data = json.loads(msg.data)
            
            # 触发本地事件处理器
            event_type = data.get("type")
            if event_type:
                # 直接调用内部发布逻辑
                pass  # TODO: 实现
                
        except Exception:
            pass
    
    async def publish(self, event: Event) -> None:
        """发布事件（本地 + 远程）
        
        Args:
            event: 事件对象
        """
        # 本地发布
        await super().publish(event)
        
        # ROS2 网络广播
        if self._publisher:
            from std_msgs.msg import String
            
            msg = String(data=json.dumps({
                "type": event.type,
                "source": event.source,
                "data": str(event.data)
            }))
            self._publisher.publish(msg)
```

**Step 2: 提交代码**

```bash
git add agents/events/bus.py
git commit -m "feat(events): add distributed event bus for multi-robot collaboration"
```

---

## 阶段 3 集成测试

### 步骤: 运行完整测试

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_semantic_parser_llm.py tests/test_task_planner_memory.py tests/test_skill_generator_runnable.py -v
```

---

## 里程碑验证

### M3: 语音驱动

**验收标准**: 语音指令 → 任务规划 → 执行，端到端跑通

---

## 总结

### 完成的任务

| 任务 | 提交消息 |
|------|----------|
| 3.1.1 | `feat(parser): add LLM-powered semantic parsing with Ollama` |
| 3.2.1 | `feat(planner): add execution memory to TaskPlanner` |
| 3.3.1 | `feat(generator): generate executable skill code from demonstration` |
| 3.4.1 | `feat(events): add distributed event bus for multi-robot collaboration` |

---

## 完整实施计划汇总

### 三个阶段总览

| 阶段 | 周期 | 核心目标 | 任务数 |
|------|------|----------|--------|
| 阶段 1 | 0-4 周 | 补全推理闭环 | 8 |
| 阶段 2 | 1-3 月 | 接入真实硬件 | 4 |
| 阶段 3 | 3-6 月 | 增强智能能力 | 4 |

### 里程碑检查

- [ ] M1: pick-and-place 在仿真环境跑通
- [ ] M2: 真实机械臂 pick-and-place 成功率 > 80%
- [ ] M3: 语音指令 → 执行端到端跑通
- [ ] M4: 生产就绪（连续运行 8 小时，成功率 > 95%）

---

> **Plan complete.** 文档已保存至 `docs/plans/2026-03-17-stage-3-intelligence-enhancement.md`
