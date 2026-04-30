:orphan:

# Phase 2：功能扩展与优化计划

**周期**: 2-3 周
**开始日期**: 2026-04-04
**方法论**: TDD（RED → GREEN → REFACTOR）
**开发模式**: 个人开发者，周期性交付

---

## 总体计划概览

```
Phase 2 架构：
├─ 第 1 周（W7）：REFACTOR 代码优化
├─ 第 2 周（W8）：具体工具实现 (Gripper, Move, Vision)
├─ 第 3 周（W9）：具体插件实现 (Preprocessor, Postprocessor)
├─ 第 4 周（W10）：性能优化和文档完善
└─ 第 5 周（W11）：ROS2 适配层

总体交付：
├─ 3 个具体工具 + 9 个工具测试
├─ 3 个具体插件 + 9 个插件测试
├─ 性能基准数据 + 集成测试
├─ 完整的 API 文档
└─ 可选的 ROS2 桥接模块
```

---

## 第 1 周（W7）：REFACTOR 代码优化

### 目标
优化现有代码，提高可维护性和可读性，同时保持所有测试通过

### 任务 1.1：代码审查和重构

**RED（编写失败测试）**
```python
# tests/unit/test_refactor_validation.py
def test_code_duplication_removed():
    """消除代码重复"""
    # 验证没有重复的三层实现

def test_naming_conventions():
    """遵循命名约定"""
    # 验证所有命名都遵循 snake_case

def test_docstring_coverage():
    """文档字符串完整"""
    # 验证所有公开方法都有文档

def test_type_hints_complete():
    """类型注解完整"""
    # 验证所有方法都有类型注解
```

**GREEN（实现）**
- 统一层级实现的模式
- 改进变量命名
- 添加缺失的文档字符串
- 添加缺失的类型注解

**REFACTOR**
- 提取公共的层级基类逻辑
- 简化重复的初始化代码
- 优化导入结构

**预期时间**: 4 小时
**预期新测试**: 4 个

### 任务 1.2：架构优化

**优化内容**：
- 统一所有模块的导入结构
- 创建 agents/__init__.py 统一入口
- 优化 SimpleAgent 中的依赖注入
- 简化配置管理的初始化

**验收标准**：
- ✓ 所有现有测试仍然通过
- ✓ 代码复杂度降低 10%
- ✓ 导入结构清晰
- ✓ 文档完整率 100%

**预期时间**: 2 小时
**预期新测试**: 0 个（重构，无新功能）

### 任务 1.3：性能基线

**建立基线**：
- 初始化时间测试
- 单步执行时间测试
- 内存占用测试
- 并发性能测试

**预期时间**: 2 小时
**预期新测试**: 4 个（性能测试）

**W7 总计**：
- 时间：8 小时
- 新测试：8 个
- 目标：提高代码质量，为后续功能开发奠定基础

---

## 第 2 周（W8）：具体工具实现

### 目标
实现 3 个真实的机器人操作工具，演示工具框架的实用性

### 任务 2.1：Gripper 控制工具

**RED（编写失败测试）**
```python
# tests/unit/test_gripper_tool.py
def test_gripper_open():
    """机械爪可以打开"""

def test_gripper_close():
    """机械爪可以关闭"""

def test_gripper_grasp_force():
    """机械爪支持力度控制"""

def test_gripper_position_feedback():
    """机械爪返回位置反馈"""
```

**GREEN（实现）**
```python
# agents/execution/tools/gripper_tool.py
class GripperTool(ToolBase):
    name = "gripper"
    description = "Robotic gripper control"
    keywords = ["gripper", "grasp", "open", "close"]

    async def execute(self, action: str, force: float = 1.0) -> dict:
        """执行机械爪动作"""
        pass
```

**REFACTOR**：
- 提取参数验证逻辑
- 优化力度计算

**预期时间**: 3 小时
**预期新测试**: 4 个

### 任务 2.2：移动规划工具

**RED（编写失败测试）**
```python
# tests/unit/test_move_tool.py
def test_move_to_position():
    """可以移动到指定位置"""

def test_move_relative():
    """支持相对移动"""

def test_collision_avoidance():
    """支持避碰规划"""

def test_move_trajectory():
    """支持轨迹规划"""
```

**GREEN（实现）**
```python
# agents/execution/tools/move_tool.py
class MoveTools(ToolBase):
    name = "move"
    description = "Robot motion planning"
    keywords = ["move", "position", "trajectory"]

    async def execute(self, target, mode: str = "direct") -> dict:
        """执行移动规划"""
        pass
```

**预期时间**: 3 小时
**预期新测试**: 4 个

### 任务 2.3：视觉处理工具

**RED（编写失败测试）**
```python
# tests/unit/test_vision_tool.py
def test_detect_objects():
    """可以检测对象"""

def test_segment_image():
    """支持图像分割"""

def test_pose_estimation():
    """支持姿态估计"""

def test_camera_calibration():
    """支持相机标定"""
```

**GREEN（实现）**
```python
# agents/execution/tools/vision_tool.py
class VisionTool(ToolBase):
    name = "vision"
    description = "Computer vision processing"
    keywords = ["vision", "detect", "segment", "pose"]

    async def execute(self, image, task: str) -> dict:
        """执行视觉处理任务"""
        pass
```

**预期时间**: 3 小时
**预期新测试**: 4 个

### 任务 2.4：工具集成测试

**RED（编写失败测试）**
```python
# tests/unit/test_tools_integration.py
def test_tool_composition():
    """工具可以组合使用"""

def test_tool_error_recovery():
    """工具失败可以恢复"""

def test_tool_performance():
    """工具性能满足要求"""
```

**预期时间**: 2 小时
**预期新测试**: 3 个

**W8 总计**：
- 时间：11 小时
- 新测试：15 个
- 新工具：3 个（Gripper, Move, Vision）
- 目标：完整的工具框架实现演示

---

## 第 3 周（W9）：具体插件实现

### 目标
实现 3 个实用的插件，展示扩展框架的灵活性

### 任务 3.1：预处理插件

**RED（编写失败测试）**
```python
# tests/unit/test_preprocessor_plugin.py
def test_data_normalization():
    """支持数据归一化"""

def test_noise_filtering():
    """支持噪声过滤"""

def test_format_conversion():
    """支持格式转换"""
```

**GREEN（实现）**
```python
# agents/extensions/plugins/preprocessor.py
class PreprocessorPlugin(PluginBase):
    name = "preprocessor"

    async def execute(self, data, operation: str) -> dict:
        """执行预处理"""
        pass
```

**预期时间**: 3 小时
**预期新测试**: 4 个

### 任务 3.2：后处理插件

**RED（编写失败测试）**
```python
# tests/unit/test_postprocessor_plugin.py
def test_result_validation():
    """验证执行结果"""

def test_result_formatting():
    """格式化结果"""

def test_result_logging():
    """记录结果"""
```

**GREEN（实现）**
```python
# agents/extensions/plugins/postprocessor.py
class PostprocessorPlugin(PluginBase):
    name = "postprocessor"

    async def execute(self, result, options: dict) -> dict:
        """执行后处理"""
        pass
```

**预期时间**: 3 小时
**预期新测试**: 4 个

### 任务 3.3：可视化插件

**RED（编写失败测试）**
```python
# tests/unit/test_visualization_plugin.py
def test_render_trajectory():
    """可以渲染轨迹"""

def test_visualize_state():
    """可以可视化状态"""

def test_export_visualization():
    """支持导出可视化"""
```

**GREEN（实现）**
```python
# agents/extensions/plugins/visualization.py
class VisualizationPlugin(PluginBase):
    name = "visualization"

    async def execute(self, data, format: str) -> dict:
        """执行可视化"""
        pass
```

**预期时间**: 3 小时
**预期新测试**: 4 个

### 任务 3.4：插件集成测试

**RED（编写失败测试）**
```python
# tests/unit/test_plugins_integration.py
def test_plugin_pipeline():
    """插件可以形成管道"""

def test_plugin_chaining():
    """支持插件链接"""

def test_plugin_error_handling():
    """插件错误处理"""
```

**预期时间**: 2 小时
**预期新测试**: 3 个

**W9 总计**：
- 时间：11 小时
- 新测试：15 个
- 新插件：3 个（Preprocessor, Postprocessor, Visualization）
- 目标：完整的插件框架演示

---

## 第 4 周（W10）：性能优化和文档完善

### 目标
优化系统性能，完成全面的 API 文档和集成测试

### 任务 4.1：性能优化

**RED（编写性能测试）**
```python
# tests/unit/test_performance_targets.py
def test_initialization_time():
    """初始化时间 < 50ms"""

def test_single_step_latency():
    """单步执行 < 100ms"""

def test_memory_efficiency():
    """内存占用 < 50MB"""

def test_concurrent_execution():
    """支持 10 个并发任务"""
```

**GREEN（实现优化）**
- 并发优化（使用 asyncio.gather）
- 内存优化（移除不必要的副本）
- 缓存优化（配置缓存）
- 批处理优化

**REFACTOR**
- 提取性能关键路径
- 优化热点代码

**预期时间**: 4 小时
**预期新测试**: 4 个

### 任务 4.2：API 文档完善

**内容**：
- 生成 API 参考文档
- 编写用户指南
- 编写开发者指南
- 编写架构文档

**输出文件**：
```
docs/
├── api-reference.md
├── user-guide.md
├── developer-guide.md
└── architecture.md
```

**预期时间**: 3 小时
**预期新文件**: 4 个

### 任务 4.3：集成测试扩展

**RED（编写集成测试）**
```python
# tests/integration/test_full_workflows.py
def test_pick_and_place_workflow():
    """完整的拿取-放置工作流"""

def test_multi_step_task():
    """多步骤任务执行"""

def test_error_recovery_workflow():
    """错误恢复工作流"""

def test_learning_workflow():
    """带学习的工作流"""
```

**GREEN（实现集成测试）**
- 端到端测试（完整的任务流程）
- 场景测试（实际使用场景）
- 压力测试（长时间运行）

**预期时间**: 3 小时
**预期新测试**: 8 个

**W10 总计**：
- 时间：10 小时
- 新测试：12 个
- 新文档：4 个
- 目标：系统性能优化，文档完善

---

## 第 5 周（W11）：ROS2 适配层（可选）

### 目标
创建可选的 ROS2 桥接模块，保持核心纯 Python

### 任务 5.1：ROS2 节点适配器

**RED（编写失败测试）**
```python
# tests/integration/test_ros2_adapter.py
def test_ros2_node_creation():
    """可以创建 ROS2 节点"""

def test_ros2_subscription():
    """支持 ROS2 订阅"""

def test_ros2_publication():
    """支持 ROS2 发布"""

def test_ros2_service_call():
    """支持 ROS2 服务调用"""
```

**GREEN（实现）**
```python
# agents/adapters/ros2_adapter.py
class ROS2NodeAdapter:
    """ROS2 节点适配器"""

    async def create_node(self, agent):
        """为代理创建 ROS2 节点"""
        pass
```

**预期时间**: 4 小时
**预期新测试**: 4 个

### 任务 5.2：传感器和执行器集成

**RED（编写失败测试）**
```python
# tests/integration/test_ros2_integration.py
def test_camera_topic_integration():
    """集成 ROS2 相机话题"""

def test_joint_state_integration():
    """集成 ROS2 关节状态"""

def test_action_server_integration():
    """集成 ROS2 动作服务"""
```

**GREEN（实现）**
- ROS2 相机话题订阅
- ROS2 关节状态订阅
- ROS2 动作服务客户端

**预期时间**: 3 小时
**预期新测试**: 3 个

### 任务 5.3：ROS2 适配层文档

**输出**：
```
docs/
└── ros2-integration.md
```

**内容**：
- ROS2 安装和配置
- 节点启动指南
- 话题和服务说明
- 集成示例

**预期时间**: 2 小时

**W11 总计**：
- 时间：9 小时
- 新测试：7 个
- 新适配器：1 个
- 新文档：1 个
- 目标：完整的 ROS2 集成方案（可选）

---

## Phase 2 总体统计

```
总体工作量：
├─ W7（REFACTOR）：8 小时，8 个新测试
├─ W8（工具）：11 小时，15 个新测试，3 个工具
├─ W9（插件）：11 小时，15 个新测试，3 个插件
├─ W10（优化）：10 小时，12 个新测试，4 个文档
└─ W11（ROS2）：9 小时，7 个新测试，1 个适配器

总计：49 小时，57 个新测试

预期完成时间：
- 快速模式（每周 15 小时）：3 周
- 中等模式（每周 10 小时）：5 周
- 悠闲模式（每周 7 小时）：7 周
```

---

## 每周检查清单

### 周末检查点
```
□ 所有新测试通过
□ 无新增技术债
□ 代码覆盖率 > 95%
□ 文档更新完整
□ 性能基准达成
```

### 跨周审查
```
每周结束：
□ 周总结文档已生成
□ 代码已提交
□ 性能指标已记录
□ 下周计划已确认
```

---

## 关键指标跟踪

### 代码质量
```
当前状态：99% 测试通过（713/720）
目标状态：100% 测试通过（所有新增）
质量指标：
├─ 文档覆盖率：100%
├─ 类型注解覆盖率：100%
├─ 代码重复率：< 5%
└─ 复杂度：低
```

### 性能目标
```
初始化：< 50ms
单步：< 100ms
内存：< 50MB
并发：10+ 任务
```

### 功能完整性
```
工具：3/3 ✓
插件：3/3 ✓
文档：4/4 ✓
集成测试：8/8 ✓
ROS2 适配：1/1 ✓（可选）
```

---

## 可选加速方案

如果想更快完成，可以：
1. **并行执行**：W8 和 W9 任务可以并行进行
2. **减少测试**：每个任务保留核心测试，减少边界情况测试
3. **简化文档**：生成自动化 API 文档，减少手写文档
4. **跳过 ROS2**：如果不需要 ROS2 集成，可以完全跳过 W11

---

## 风险和缓解

| 风险 | 可能性 | 影响 | 缓解 |
|------|--------|------|------|
| 性能指标难以达成 | 中 | 高 | 提前开始性能优化 |
| 文档更新滞后 | 低 | 中 | 使用自动化文档生成 |
| 集成测试复杂 | 中 | 中 | 简化集成场景 |
| ROS2 兼容性问题 | 低 | 中 | 充分的版本测试 |

---

## 下一步

**立即开始**：
1. 读取本计划
2. 同意计划内容
3. 开始 W7 REFACTOR 任务
4. 每周末生成周总结

**准备工作**：
```bash
# 创建新的测试目录
mkdir -p tests/integration/

# 创建新的文档目录
mkdir -p docs/guides/

# 准备工具目录
mkdir -p agents/execution/tools/implementations/

# 准备插件目录
mkdir -p agents/extensions/plugins/
```

---

**计划版本**: 1.0
**更新时间**: 2026-04-04
**下一个审查**: 2026-04-11（W7 完成）
