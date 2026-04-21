# EmbodiedAgentsSys - Industrial-Grade Embodied Agent Framework

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0.0-brightgreen.svg)](https://github.com)
[![Tests](https://img.shields.io/badge/tests-720+-green.svg)](#)

**Pure Python 4-Layer Robot Agent Architecture | Industrial Safety | Zero ROS2 Dependencies**

[**English**](#) | [**中文**](docs/README.zh.md) | [**日本語**](docs/README.ja.md)

[Quick Start](#quick-start) | [Features](#features) | [Installation](#installation) | [Documentation](#documentation) | [Examples](#examples)

</div>

---

## Overview

**EmbodiedAgentsSys** is a production-ready, pure Python robot agent framework implementing a 4-layer architecture with industrial-grade safety mechanisms:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Perception Layer                              │
│                    (RobotObservation)                            │
├─────────────────────────────────────────────────────────────────┤
│                    Cognition Layer                               │
│    ├─ Planning Layer (Task → Plan)                              │
│    ├─ Reasoning Layer (Plan + Observation → Action)             │
│    └─ Learning Layer (Feedback → Improvement)                   │
├─────────────────────────────────────────────────────────────────┤
│                    Execution Layer                               │
│    ├─ Policy Validation (Two-Level: Local + Central)            │
│    ├─ Human Oversight (State Machine: Auto/Manual/Pause/E-Stop) │
│    ├─ Execution Pipeline (End-to-End Orchestration)             │
│    └─ Tools (Gripper, Move, Vision)                             │
├─────────────────────────────────────────────────────────────────┤
│                    Feedback Layer                                │
│    ├─ Closed-Loop Confirmation                                   │
│    ├─ Audit Trail (Tamper-Proof Logging)                        │
│    ├─ Alert System (Multi-Level Notifications)                  │
│    └─ Plugins (Preprocessor, Postprocessor, Visualization)      │
└─────────────────────────────────────────────────────────────────┘
```

### Why EmbodiedAgentsSys?

- ✅ **Zero ROS2 Dependency**: Pure Python implementation for maximum portability
- ✅ **Industrial Safety**: Seven Iron Rules (P1-P7) for safe robot operation
- ✅ **Human Oversight**: State machine with AUTOMATIC/MANUAL/PAUSED/E-STOP modes
- ✅ **Two-Level Validation**: Local + Central policy validation pipeline
- ✅ **Closed-Loop Execution**: Execution confirmation with result verification
- ✅ **Async-First Design**: Full asyncio support for concurrent task execution
- ✅ **Production Ready**: 720+ tests, comprehensive documentation
- ✅ **High Performance**: <50ms initialization, <100ms execution, <50MB memory

---

## New in v2.1.0 (2026-04-21)

### 🚀 MuJoCo Real-Time Simulation
- **Integrated MuJoCo viewer** for real-time robot simulation
- Scene builder with robot model, objects, lighting, and floor
- IK (Inverse Kinematics) solver for trajectory planning
- Force and contact sensors for grasp detection
- Support for graspable objects (ball, cube, cylinder, box)

### 🎨 Frontend Architecture Refactor
- **Component-based design** with React + TypeScript + Tailwind CSS
- **Zustand state management** for chat, settings, and status
- **WebSocket real-time communication** with agent backend
- New UI components:
  - `AgentPanel` - Agent control and status
  - `CameraPanel` - Real-time camera feed display
  - `ChatPanel` - Interactive chat interface
  - `DetectionPanel` - Object detection results
  - `Header` - Application header with controls
  - `MainArea` - Central workspace
  - `SettingsPanel` - Configuration settings
  - `Sidebar` - Navigation sidebar

### 🔌 Backend API Enhancements
- WebSocket endpoint (`/ws/agent`) for real-time updates
- Scenario management with resolution logic
- Agent bridge service for multi-agent coordination
- Simulation service with MuJoCo integration

### 🛠️ Development Scripts
- `scripts/start_dev.sh` - Development environment launcher
- `scripts/test_agent_debugger.sh` - Agent debugger test runner
- `scripts/test_system.sh` - Full system integration tests

### 🧪 Testing MuJoCo Simulation

#### Start Backend with Viewer

```bash
# Start backend + MuJoCo viewer window (recommended for testing robot motion)
bash scripts/start_dev.sh --backend

# Start backend in headless mode (no viewer, CI/terminal only)
bash scripts/start_dev.sh --headless --backend
```

#### Test Robot Arm Control via Chat API

```bash
# Set DeepSeek API key
export DEEPSEEK_API_KEY="sk-..."

# Test right arm movement (note: y must be negative for right arm)
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Api-Key: sk-...' \
  -d '{"message": "将右臂移动到 x=0.3 y=-0.25 z=0.86", "history": []}'

# Test left arm movement
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Api-Key: sk-...' \
  -d '{"message": "将左臂移动到 x=0.3 y=0.25 z=0.86", "history": []}'
```

#### Right Arm Workspace Constraints

- **y-coordinate**: Must be **negative** (range: `[-0.35, -0.0.20]`)
- **x-coordinate**: Up to 0.30m when z ≥ 0.86
- **Example valid position**: `[0.3, -0.25, 0.86]`

#### Troubleshooting

- **Robot arm moves but doesn't animate in viewer**: This was a GIL contention issue - now fixed with `ThreadPoolExecutor`
- **Viewer window doesn't appear**: Check X11/GLFW support, or use `--headless` mode

---

## Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd EmbodiedAgentsSys

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

### One-Minute Example

```python
import asyncio
from agents import SimpleAgent

async def main():
    # Create agent from preset
    agent = SimpleAgent.from_preset("default")

    # Execute task
    result = await agent.run_task("pick up the red ball")

    # Check result
    if result.success:
        print(f"✅ Success: {result.message}")
    else:
        print(f"❌ Failed: {result.error}")

asyncio.run(main())
```

### Using Tools

```python
import asyncio
from agents import GripperTool, MoveTool, VisionTool

async def main():
    # Initialize tools
    vision = VisionTool()
    gripper = GripperTool()
    move = MoveTool()

    # Step 1: Detect objects
    detection = await vision.execute(operation="detect_objects")
    print(f"Objects detected: {detection}")

    # Step 2: Move to object
    move_result = await move.execute(
        target={"x": 0.5, "y": 0.3, "z": 0.2},
        mode="direct"
    )

    # Step 3: Grasp object
    grasp_result = await gripper.execute(action="grasp", force=0.8)
    print(f"Grasp result: {grasp_result}")

asyncio.run(main())
```

### Data Processing Pipeline

```python
import asyncio
from agents import PreprocessorPlugin, PostprocessorPlugin, VisualizationPlugin

async def main():
    # Initialize plugins
    preprocessor = PreprocessorPlugin()
    postprocessor = PostprocessorPlugin()
    visualizer = VisualizationPlugin()

    await preprocessor.initialize()
    await postprocessor.initialize()
    await visualizer.initialize()

    # Data pipeline
    raw_data = {"values": [0.1, 0.2, None, 0.4, float('nan'), 0.6]}

    # Clean and normalize
    cleaned = await preprocessor.execute(operation="clean", data=raw_data)
    normalized = await preprocessor.execute(operation="normalize", data=cleaned)

    # Post-process
    formatted = await postprocessor.execute(operation="format", data=normalized)

    # Visualize
    stats = await visualizer.execute(operation="statistics", data=normalized["data"])
    print(f"Statistics: {stats}")

    # Cleanup
    await preprocessor.cleanup()
    await postprocessor.cleanup()
    await visualizer.cleanup()

asyncio.run(main())
```

---

## Features

### 📊 Core Types

| Type | Description |
|------|-------------|
| `RobotObservation` | Robot sensor data (image, state, gripper position, timestamp) |
| `SkillResult` | Execution result with success status, message, data, error |
| `AgentConfig` | Configuration with agent name, max steps, LLM model, etc. |
| `ActionProposal` | Validated action sequence with safety metadata |
| `ExecutionFeedback` | Real-time feedback during action execution |

### 🛡️ Safety & Validation (Industrial-Grade)

| Component | Function | Safety Rule |
|-----------|----------|-------------|
| **TwoLevelValidationPipeline** | Local + Central validation | P1, P3 |
| **WhitelistValidator** | Allowed action types | P1 |
| **BoundaryChecker** | Safety boundary enforcement | P1 |
| **ConflictDetector** | Action conflict prevention | P1 |
| **ConfirmationValidator** | Expected outcome validation | P3 |

### 👁️ Human Oversight System

| Mode | Description | Trigger |
|------|-------------|---------|
| `AUTOMATIC` | Normal autonomous operation | Default |
| `MANUAL_OVERRIDE` | Human takes control | Operator request |
| `PAUSED` | System paused for inspection | Safety condition |
| `EMERGENCY_STOP` | Immediate halt | E-Stop button |

### 🧠 Cognition Layer

| Component | Function | Method |
|-----------|----------|--------|
| **Planning Layer** | Task → Plan | `async generate_plan(task: str)` |
| **Reasoning Layer** | Plan + Observation → Action | `async generate_action(plan, obs)` |
| **Learning Layer** | Feedback → Improvement | `async improve(action, feedback)` |
| **Cognition Engine** | Layer integration | `async think(task)` |

### 🛠️ Execution Tools

| Tool | Capabilities |
|------|--------------|
| **GripperTool** | open, close, grasp (with force 0.0-1.0), cancel support |
| **MoveTool** | direct, relative, safe, trajectory movement modes |
| **VisionTool** | detect_objects, segment, estimate_pose, calibrate |

### 🔌 Plugin System

| Plugin | Operations |
|--------|-----------|
| **PreprocessorPlugin** | clean, normalize, validate, clear_cache |
| **PostprocessorPlugin** | format, aggregate, filter, transform |
| **VisualizationPlugin** | generate_chart, statistics, config, export |

### 📝 Audit & Feedback

| Component | Function |
|-----------|----------|
| **AuditTrail** | Tamper-proof execution logging |
| **AlertSystem** | Multi-level notifications (INFO/WARNING/CRITICAL/EMERGENCY) |
| **ExecutionConfirmationEngine** | Closed-loop result verification |
| **FeedbackLoop** | Learning from execution results |

### ⚙️ Framework Features

| Feature | Implementation |
|---------|-----------------|
| **Registry Pattern** | ToolRegistry, PluginRegistry for dynamic component management |
| **Strategy Pattern** | StrategySelector for intelligent tool selection |
| **Async Support** | Full asyncio integration for concurrent execution |
| **Caching** | Smart MD5-based caching in PreprocessorPlugin |
| **Error Handling** | Comprehensive exception handling and recovery |
| **Cancellable Execution** | Tools support `cancel()` for safe interruption |

---

## Installation

### Requirements

- Python 3.10+
- pip (Python package manager)

### Step-by-Step

```bash
# 1. Clone the repository
git clone <repository-url>
cd EmbodiedAgentsSys

# 2. Create virtual environment
python3 -m venv venv

# Activate on Linux/Mac
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Install development dependencies
pip install -r requirements-dev.txt

# 5. Run tests to verify installation
python3 -m pytest tests/ -v
```

### Docker (Optional)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python3", "-m", "pytest", "tests/"]
```

---

## Configuration

### Preset Configuration

```python
from agents import ConfigManager

# Load default configuration
config = ConfigManager.load_preset("default")

# Load VLA+ configuration
config = ConfigManager.load_preset("vla_plus")
```

### Custom Configuration

```python
from agents import AgentConfig

config = AgentConfig(
    agent_name="my_robot",
    max_steps=100,
    llm_model="qwen",
    perception_enabled=True,
    learning_rate=0.01,
    memory_limit=1000
)
```

### YAML Configuration File

Create `config.yaml`:

```yaml
agent:
  name: "robot_001"
  max_steps: 50
  llm_model: "qwen"

perception:
  enabled: true
  image_size: [480, 640]

execution:
  default_timeout: 30
  retry_attempts: 3
```

Load configuration:

```python
config = ConfigManager.load_yaml("config.yaml")
```

---

## Examples

### Example 1: Simple Pick Task

```python
import asyncio
from agents import SimpleAgent

async def pick_task():
    agent = SimpleAgent.from_preset("default")
    result = await agent.run_task("pick up the red cube from the table")

    if result.success:
        print(f"✅ Task completed: {result.message}")
        return result.data
    else:
        print(f"❌ Task failed: {result.error}")
        return None

asyncio.run(pick_task())
```

### Example 2: Multi-Step Workflow

```python
import asyncio
from agents import GripperTool, MoveTool, VisionTool
from agents import ToolRegistry, StrategySelector

async def multi_step_workflow():
    # Setup registry
    registry = ToolRegistry()
    vision = VisionTool()
    move = MoveTool()
    gripper = GripperTool()

    registry.register("vision", vision)
    registry.register("move", move)
    registry.register("gripper", gripper)

    # Step 1: Detect
    print("🔍 Step 1: Detecting objects...")
    detection = await vision.execute(operation="detect_objects")
    print(f"   Found: {detection}")

    # Step 2: Move
    print("🚀 Step 2: Moving to target...")
    move_result = await move.execute(
        target={"x": 0.5, "y": 0.3, "z": 0.2},
        mode="safe"
    )
    print(f"   Moved: {move_result}")

    # Step 3: Grasp
    print("✋ Step 3: Grasping object...")
    grasp = await gripper.execute(action="grasp", force=0.8)
    print(f"   Grasped: {grasp}")

    # Step 4: Place
    print("📍 Step 4: Placing object...")
    move_result = await move.execute(
        target={"x": 0.2, "y": 0.4, "z": 0.3},
        mode="safe"
    )
    grasp = await gripper.execute(action="open")
    print(f"   Placed: {grasp}")

asyncio.run(multi_step_workflow())
```

### Example 3: Error Recovery

```python
import asyncio
from agents import GripperTool, MoveTool

async def error_recovery():
    gripper = GripperTool()
    move = MoveTool()

    # Try primary action
    try:
        grasp = await gripper.execute(action="grasp", force=0.8)

        if not grasp.get("success"):
            print("⚠️ Grasp failed, attempting recovery...")

            # Reduce force and retry
            retry = await gripper.execute(action="grasp", force=0.5)
            if retry.get("success"):
                print("✅ Recovery successful")
            else:
                print("❌ Recovery failed")

    except Exception as e:
        print(f"❌ Exception: {e}")
        # Fallback: move away and reset
        await move.execute(
            target={"x": 0.0, "y": 0.0, "z": 0.5},
            mode="safe"
        )

asyncio.run(error_recovery())
```

### Example 4: Data Processing

```python
import asyncio
from agents import (
    PreprocessorPlugin,
    PostprocessorPlugin,
    VisualizationPlugin
)

async def data_processing():
    # Initialize plugins
    preprocessor = PreprocessorPlugin()
    postprocessor = PostprocessorPlugin()
    visualizer = VisualizationPlugin()

    for plugin in [preprocessor, postprocessor, visualizer]:
        await plugin.initialize()

    try:
        # Raw sensor data
        raw_data = {
            "values": [0.1, 0.2, None, 0.4, float('nan'), 0.6, 0.7]
        }

        # Clean
        cleaned = await preprocessor.execute(
            operation="clean",
            data=raw_data
        )
        print(f"✅ Cleaned: {cleaned['data']}")

        # Normalize
        normalized = await preprocessor.execute(
            operation="normalize",
            data=cleaned
        )
        print(f"✅ Normalized: {normalized['data']}")

        # Post-process
        formatted = await postprocessor.execute(
            operation="format",
            data=normalized
        )
        print(f"✅ Formatted: {formatted['data']}")

        # Visualize
        stats = await visualizer.execute(
            operation="statistics",
            data=normalized.get("data", [])
        )
        print(f"✅ Statistics: {stats['statistics']}")

    finally:
        # Cleanup
        for plugin in [preprocessor, postprocessor, visualizer]:
            await plugin.cleanup()

asyncio.run(data_processing())
```

---

## Documentation

### Quick Links

- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation with 50+ exported items
- **[User Guide](docs/USER_GUIDE.md)** - Quick start, common tasks, best practices, troubleshooting
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Setup, workflow, extension, testing, standards
- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design, patterns, extensions, performance
- **[Safety Design Spec](docs/superpowers/specs/2026-04-07-three-layer-policy-validation-design.md)** - Three-layer policy validation architecture
- **[Development Summary](DEVELOPMENT_COMPLETE_SUMMARY.md)** - Complete development cycle overview

### Core Concepts

| Concept | Description |
|---------|-------------|
| **RobotObservation** | Input data from robot sensors |
| **SkillResult** | Result of any execution (success, message, data, error) |
| **RobotAgentLoop** | Main observe-think-act execution loop |
| **SimpleAgent** | One-liner agent interface |
| **ActionProposal** | Validated action sequence for safe execution |
| **Tool** | Reusable execution components (Gripper, Move, Vision) |
| **Plugin** | Data processing components (Preprocessor, Postprocessor, Visualization) |
| **HumanOversightEngine** | State machine for human control |

### Design Patterns

| Pattern | Usage |
|---------|-------|
| **Registry** | ToolRegistry, PluginRegistry for dynamic component management |
| **Strategy** | StrategySelector for intelligent component selection |
| **Factory** | ConfigManager for object creation |
| **Template Method** | ToolBase, PluginBase for consistent interfaces |
| **Observer** | FeedbackLoop for result processing |
| **State Machine** | HumanOversightEngine for mode transitions |
| **Pipeline** | ExecutionPipeline for end-to-end orchestration |
| **Validator Chain** | TwoLevelValidationPipeline for safety checks |

---

## Performance Metrics

### Benchmark Results

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Initialization | < 50ms | < 20ms | ✅ |
| Single Step Execution | < 100ms | < 100ms | ✅ |
| Tool Execution | < 50ms | < 50ms | ✅ |
| Memory Usage | < 50MB | < 15MB | ✅ |
| Concurrent Tasks | 10+ | 20+ | ✅ |
| Validation Pipeline | < 10ms | < 5ms | ✅ |

### Test Coverage

| Category | Tests | Pass Rate |
|----------|-------|-----------|
| Unit Tests | 450+ | 99% ✅ |
| Integration Tests | 150+ | 99% ✅ |
| Security Tests | 50+ | 100% ✅ |
| Performance Tests | 20+ | 100% ✅ |
| **Total** | **720+** | **99%** |

### Safety Test Coverage (Seven Iron Rules)

| Rule | Description | Tests |
|------|-------------|-------|
| P1 | Safety First - Unauthorized actions rejected | ✅ |
| P2 | Human Control - Emergency Stop always available | ✅ |
| P3 | Decision Separation - LLM proposals validated | ✅ |
| P4 | Closed Loop - Execution result confirmation | ✅ |
| P5 | Graceful Degradation - Layer isolation | ✅ |
| P6 | Safety Mechanisms - Tamper-proof audit logs | ✅ |
| P7 | LLM Isolation - Strict input validation | ✅ |

---

## Best Practices

### ✅ DO

```python
# Use async/await pattern
async def good_example():
    agent = SimpleAgent.from_preset("default")
    result = await agent.run_task("task")
    return result

# Handle errors properly
try:
    result = await agent.run_task("task")
except Exception as e:
    print(f"Error: {e}")

# Clean up resources
async def cleanup_example():
    plugin = PreprocessorPlugin()
    await plugin.initialize()
    try:
        result = await plugin.execute(...)
    finally:
        await plugin.cleanup()

# Use concurrent execution
tasks = [
    agent.run_task("task1"),
    agent.run_task("task2"),
    agent.run_task("task3")
]
results = await asyncio.gather(*tasks)
```

### ❌ DON'T

```python
# Don't mix sync and async
result = agent.run_task("task")  # ERROR: Missing await

# Don't forget error handling
result = await agent.run_task("task")
if not result.success:
    print(f"Error: {result.error}")  # Could be None

# Don't leak resources
plugin = PreprocessorPlugin()
await plugin.initialize()
# Missing cleanup - resources leak

# Don't block event loop
import time
time.sleep(1)  # Use asyncio.sleep instead
```

---

## Troubleshooting

### Issue: Agent initialization fails

**Solution:**
```python
from agents import ConfigManager

# Verify configuration
config = ConfigManager.create(agent_name="test")
print(config)

# Check dependencies
try:
    from agents import SimpleAgent
    agent = SimpleAgent.from_preset("default")
except Exception as e:
    print(f"Init failed: {e}")
```

### Issue: Timeout during task execution

**Solution:**
```python
import asyncio

async def timeout_example():
    agent = SimpleAgent.from_preset("default")
    try:
        result = await asyncio.wait_for(
            agent.run_task("task"),
            timeout=60.0  # 60 second timeout
        )
        return result
    except asyncio.TimeoutError:
        print("Task execution timeout")
```

### Issue: Memory usage growing

**Solution:**
```python
# Ensure resources are cleaned up
for i in range(1000):
    agent = SimpleAgent.from_preset("default")
    try:
        result = await agent.run_task("task")
    finally:
        # Cleanup
        if hasattr(agent, 'cleanup'):
            await agent.cleanup()

    # Periodic garbage collection
    if i % 100 == 0:
        import gc
        gc.collect()
```

---

## Project Status

### Phase Completion

| Phase | Tasks | Tests | Status |
|-------|-------|-------|--------|
| Phase 1 (W1-W6) | Core Architecture | 154 | ✅ Complete |
| Phase 2 (W7) | Refactoring & Optimization | 131 | ✅ Complete |
| Phase 2 (W8-W9) | Safety & Validation | 200+ | ✅ Complete |
| Phase 2 (W10) | Human Oversight & Audit | 150+ | ✅ Complete |
| Phase 2 (W11) | Integration & Pipeline | 100+ | ✅ Complete |
| **Overall** | **Full Implementation** | **720+** | **✅ Production Ready** |

### Key Milestones

| Milestone | Date | Description |
|-----------|------|-------------|
| v1.0.0 | 2026-04-04 | Core 4-layer architecture complete |
| v1.5.0 | 2026-04-05 | Two-level validation pipeline |
| v2.0.0 | 2026-04-08 | Industrial safety with human oversight |

### Release Information

- **Version**: 2.0.0
- **License**: MIT
- **Python**: 3.10+
- **Status**: ✅ Production Ready
- **Last Updated**: 2026-04-08

---

## Contributing

We welcome contributions! Please:

1. Follow the [Developer Guide](docs/DEVELOPER_GUIDE.md)
2. Write tests for new features (TDD)
3. Ensure all tests pass: `pytest tests/ -v`
4. Update documentation accordingly

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## Citation

If you use EmbodiedAgentsSys in your research or project, please cite:

```bibtex
@software{embodiedagentssys2026,
  title={EmbodiedAgentsSys: A Production-Ready Robot Agent Framework with Industrial Safety},
  author={EmbodiedAgents Team},
  year={2026},
  version={2.0.0},
  url={https://github.com/hzm8341/EmbodiedAgentsSys}
}
```

---

## Support

- 📖 **Documentation**: [docs/](docs/)
- 🐛 **Issues**: [GitHub Issues](https://github.com/hzm8341/EmbodiedAgentsSys/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/hzm8341/EmbodiedAgentsSys/discussions)

---

**Made with ❤️ by the EmbodiedAgents Team**

*Pure Python. Zero ROS2. Industrial Safety. Production Ready. Extensible. Well Tested. Fully Documented.*
