:orphan:

# EmbodiedAgentsSys 下一步开发计划

> 创建时间: 2026-03-31
> 版本: 0.3.1

## 一、代码更新总结 (本次)

### 已完成的更新

| 文件 | 更新内容 |
|------|----------|
| `agents/clients/vla_adapters/act.py` | 添加ACT推理服务HTTP连接，支持离线fallback |
| `agents/clients/vla_adapters/gr00t.py` | 添加GR00T推理服务HTTP连接，支持离线fallback |
| `agents/clients/lerobot.py` | torch依赖改为可选，无torch时优雅降级 |
| `agents/components/vla.py` | 实现`_warmup()`方法，支持从配置读取image_shape和observation_prefix |
| `agents/config.py` | VLAConfig添加`image_shape`和`observation_prefix`字段 |

---

## 二、待完成的工作

### 优先级 1: ROS集成 (P0 - 关键路径)

**说明**: 多个skills模块包含`# TODO: ROS实现`占位符，需要在有ROS环境下实现。

| 文件 | 需要的实现 |
|------|-----------|
| `skills/vision/perception_3d_skill.py` | 深度图像话题订阅、点云处理、PCL/Open3D集成 |
| `skills/manipulation/force_control_skill.py` | 力传感器话题订阅、阻抗控制器初始化 |
| `skills/manipulation/assembly_skill.py` | 装配执行、路径规划、ROS服务调用 |

**依赖**: 需要实际的ROS2环境、传感器硬件或模拟器

### 优先级 2: VLA模型服务 (P1 - 核心功能)

| 任务 | 描述 |
|------|------|
| ACT推理服务 | 部署ACT模型推理服务 (参考端口8001) |
| GR00T推理服务 | 部署GR00T模型推理服务 (参考端口8002) |
| LeRobot服务器 | 完善LeRobot策略服务器，支持numpy输出 |

### 优先级 3: Agent Harness框架 (P2 - 测试基础设施)

**文档位置**: `docs/agent_harness/`

| 阶段 | 描述 |
|------|------|
| Phase 1 | 核心harness实现 (测试runner、模拟器、监控) |
| Phase 2 | 模拟环境集成 |
| Phase 3 | 测试用例编写 |

### 优先级 4: Web Dashboard扩展 (P3 - UI/UX)

当前dashboard是最小demo版本，需要扩展:
- 实时视频流
- 场景分析UI
- 任务状态可视化

---

## 三、开发时间线

### 短期目标 (1-2周)

1. **ROS集成**
   - [ ] perception_3d_skill ROS话题订阅
   - [ ] force_control_skill 力传感器集成
   - [ ] assembly_skill 装配技能ROS实现

2. **VLA服务部署**
   - [ ] 搭建ACT推理服务端
   - [ ] 搭建GR00T推理服务端

### 中期目标 (1-2月)

1. **测试框架**
   - [ ] Agent Harness核心功能
   - [ ] 模拟器环境
   - [ ] 集成测试用例

2. **功能完善**
   - [ ] Web Dashboard完整功能
   - [ ] 端到端任务执行测试
   - [ ] 性能优化

### 长期愿景

1. 多机器人协作支持
2. 分布式Agent系统
3. 云端训练支持
4. 商业化部署

---

## 四、风险与依赖

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| ROS环境不可用 | 无法验证ROS集成代码 | 使用ROS模拟器 |
| VLA模型训练数据不足 | 动作预测精度低 | 使用预训练模型 |
| 硬件依赖 | 无法进行实际测试 | 开发模拟模式 |

---

## 五、技术债务

1. **TODO清理**: 代码中有50+处TODO注释需要处理
2. **文档**: 部分文档是中文，需要统一
3. **测试覆盖**: 集成测试不足
4. **错误处理**: 部分模块错误处理不完善

---

## 六、建议的下一步行动

1. **立即**: 在ROS环境中验证perception_3d_skill
2. **本周**: 部署ACT/GR00T推理服务
3. **下周**: 开始Agent Harness Phase 1实现
4. **本月**: 完成ROS集成代码开发
