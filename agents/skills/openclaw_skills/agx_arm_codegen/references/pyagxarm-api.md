# pyAgxArm API 速查与最小可运行模板

SDK: https://github.com/agilexrobotics/pyAgxArm

## 1. 连接与配置

```python
from pyAgxArm import create_agx_arm_config, AgxArmFactory

robot_cfg = create_agx_arm_config(
    robot="nero",      # nero / piper / piper_h / piper_l / piper_x
    comm="can",
    channel="can0",
    interface="socketcan",
)
robot = AgxArmFactory.create_arm(robot_cfg)
robot.connect()
```

- `create_agx_arm_config(...)`: 创建配置字典。
- `AgxArmFactory.create_arm(config)`: 创建机械臂实例。
- `robot.connect()`: 建立 CAN 连接并启动读取线程。

## 2. 使能与模式

```python
import time

# 普通模式（单臂控制）
robot.set_normal_mode()

# 轮询使能直到成功
while not robot.enable():
    time.sleep(0.01)

# 速度百分比 0~100
robot.set_speed_percent(80)

# 可选：退出前失能
while not robot.disable():
    time.sleep(0.01)
```

- 主从模式：`robot.set_master_mode()`、`robot.set_slave_mode()`。
- 模式切换前后建议 `time.sleep(1)`。

## 3. 运动模式与接口

- 关节位置速度模式：
  - `robot.set_motion_mode(robot.MOTION_MODE.J)`
  - `robot.move_j([j1, j2, ..., j7])`
- 关节快速响应模式（慎用）：
  - `robot.set_motion_mode(robot.MOTION_MODE.JS)`
  - `robot.move_js([j1, j2, ..., j7])`
- 笛卡尔点到点：
  - `robot.set_motion_mode(robot.MOTION_MODE.P)`
  - `robot.move_p([x, y, z, roll, pitch, yaw])`
- 笛卡尔直线：
  - `robot.set_motion_mode(robot.MOTION_MODE.L)`
  - `robot.move_l([x, y, z, roll, pitch, yaw])`
- 圆弧轨迹：
  - `robot.set_motion_mode(robot.MOTION_MODE.C)`
  - `robot.move_c(start_pose, mid_pose, end_pose)`

单位要求：
- 关节角为弧度。
- `x,y,z` 为米，`roll,pitch,yaw` 为弧度。

## 4. 运动完成检测

```python
import time

def wait_motion_done(robot, timeout: float = 3.0, poll_interval: float = 0.01) -> bool:
    start_t = time.monotonic()
    while True:
        status = robot.get_arm_status()
        if status is not None and getattr(status.msg, "motion_status", None) == 0:
            return True
        if time.monotonic() - start_t > timeout:
            return False
        time.sleep(poll_interval)
```

## 5. 常用状态接口

- `robot.get_joint_angles()`: 当前关节角。
- `robot.get_flange_pose()`: 当前法兰位姿。
- `robot.get_arm_status()`: 当前状态（`motion_status == 0` 代表动作完成）。

## 6. 其他接口

- 回零（Nero 7 轴示例）：`robot.move_j([0] * 7)`
- 急停：`robot.electronic_emergency_stop()`
- 急停恢复：`robot.reset()`
- MIT 模式（高级慎用）：
  - `robot.set_motion_mode(robot.MOTION_MODE.MIT)`
  - `robot.move_mit(joint_index, p_des, v_des, kp, kd, t_ff)`

## 7. 最小可运行模板

```python
#!/usr/bin/env python3
import time
from pyAgxArm import create_agx_arm_config, AgxArmFactory


def wait_motion_done(robot, timeout: float = 3.0, poll_interval: float = 0.01) -> bool:
    start_t = time.monotonic()
    while True:
        status = robot.get_arm_status()
        if status is not None and getattr(status.msg, "motion_status", None) == 0:
            return True
        if time.monotonic() - start_t > timeout:
            return False
        time.sleep(poll_interval)


def main():
    robot_cfg = create_agx_arm_config(
        robot="nero",
        comm="can",
        channel="can0",
        interface="socketcan",
    )
    robot = AgxArmFactory.create_arm(robot_cfg)
    robot.connect()

    # 模式切换前后建议 1s 延时
    time.sleep(1)
    robot.set_normal_mode()
    time.sleep(1)

    # 先使能，再运动
    while not robot.enable():
        time.sleep(0.01)

    robot.set_speed_percent(80)

    robot.set_motion_mode(robot.MOTION_MODE.J)
    robot.move_j([0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    time.sleep(0.01)
    wait_motion_done(robot, timeout=3.0)

    # 可选：结束时失能
    # while not robot.disable():
    #     time.sleep(0.01)


if __name__ == "__main__":
    main()
```
