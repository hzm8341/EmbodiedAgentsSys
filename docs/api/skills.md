# Skills API 文档

## VLASkill

所有 VLA 驱动技能的基类。

```python
from agents.skills.vla_skill import VLASkill, SkillResult, SkillStatus
```

### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| vla | VLAAdapterBase | VLA 适配器 |
| status | SkillStatus | 当前状态 |
| max_steps | int | 最大执行步数 |

### 方法

#### build_skill_token() -> str

构建 VLA 推理用的任务描述。

#### check_preconditions(observation) -> bool

检查执行前置条件。

#### check_termination(observation) -> bool

检查是否满足终止条件。

#### async execute(observation) -> SkillResult

执行技能。

---

## GraspSkill

抓取技能。

```python
from agents.skills.manipulation import GraspSkill
```

### 初始化

```python
skill = GraspSkill(
    object_name="cube",
    vla_adapter=adapter
)
```

### 前置条件

- `object_detected`: 物体在视野内

### 终止条件

- `grasp_success`: 抓取成功

---

## PlaceSkill

放置技能。

```python
from agents.skills.manipulation import PlaceSkill
```

### 初始化

```python
skill = PlaceSkill(
    target_position=[0.5, 0.0, 0.1],
    vla_adapter=adapter
)
```

### 前置条件

- `object_held`: 物体已被抓取

### 终止条件

- `placement_success`: 放置成功

---

## ReachSkill

到达技能。

```python
from agents.skills.manipulation import ReachSkill
```

### 初始化

```python
skill = ReachSkill(
    target_position=[0.3, 0.0, 0.2],
    vla_adapter=adapter
)
```

### 前置条件

- `collision_detected`: 无碰撞

### 终止条件

- `position_reached`: 到达目标
- `distance_to_target`: 距离小于阈值

---

## MoveSkill

关节运动技能。

```python
from agents.skills.manipulation import MoveSkill
```

### 初始化

```python
# 关节模式
skill = MoveSkill(
    target_joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    vla_adapter=adapter
)

# 末端位姿模式
skill = MoveSkill(
    target_pose=[0.3, 0.0, 0.2, 0.0, 0.0, 0.0],
    vla_adapter=adapter
)
```

---

## InspectSkill

检查技能。

```python
from agents.skills.manipulation import InspectSkill
```

### 初始化

```python
skill = InspectSkill(
    target_object="cube",
    inspection_type="detect",  # detect/verify/quality
    vla_adapter=adapter
)
```

### 前置条件

- 视觉输入可用 (`image`, `rgb`, `depth`)

### 终止条件

- `inspection_complete`: 检查完成
- 检测到目标物体
