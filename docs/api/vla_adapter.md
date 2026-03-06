# VLA 适配器 API 文档

## VLAAdapterBase

所有 VLA 适配器的基类。

```python
from agents.clients.vla_adapters import VLAAdapterBase
```

### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| config | Dict[str, Any] | 配置字典 |
| action_dim | int | 动作维度 |

### 方法

#### reset()

重置 VLA 状态。

```python
adapter.reset()
```

#### act(observation, skill_token, termination=None)

根据观察和技能令牌生成动作。

```python
action = adapter.act(
    observation={"image": image, "joint_positions": joints},
    skill_token="grasp(object=cube)",
    termination={"max_steps": 100}
)
# Returns: np.ndarray
```

#### execute(action)

执行动作。

```python
result = adapter.execute(action)
# Returns: Dict[str, Any]
```

---

## LeRobotVLAAdapter

基于 LeRobot 框架的 VLA 适配器。

```python
from agents.clients.vla_adapters import LeRobotVLAAdapter
```

### 初始化

```python
adapter = LeRobotVLAAdapter(config={
    "policy_name": "panda_policy",
    "checkpoint": "lerobot/act_...",
    "host": "127.0.0.1",
    "port": 8080,
    "action_dim": 7
})
```

---

## ACTVLAAdapter

基于 ACT (Action Chunking Transformer) 的 VLA 适配器。

```python
from agents.clients.vla_adapters import ACTVLAAdapter
```

### 初始化

```python
adapter = ACTVLAAdapter(config={
    "model_path": "/models/act",
    "chunk_size": 100,
    "horizon": 1,
    "action_dim": 7
})
```

---

## GR00TVLAAdapter

基于 GR00T Diffusion Transformer 的 VLA 适配器。

```python
from agents.clients.vla_adapters import GR00TVLAAdapter
```

### 初始化

```python
adapter = GR00TVLAAdapter(config={
    "model_path": "/models/gr00t",
    "inference_steps": 10,
    "action_dim": 7,
    "action_horizon": 8
})
```
