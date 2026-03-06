---
name: agx-arm-codegen
description: 引导 OpenClaw 根据用户自然语言生成基于 pyAgxArm 的机械臂控制代码。
metadata:
  openclaw:
    emoji: "🤖"
    requires:
      bins: ["python3", "pip3"]
---

## 功能概览

本技能用于根据用户自然语言描述，生成可执行的 pyAgxArm 控制代码。

- 参考 SDK: pyAgxArm（https://github.com/agilexrobotics/pyAgxArm）
- 目标机型: Nero/Piper 等 AgileX 机械臂

## 何时使用本技能

- 用户说“写一段代码控制机械臂”
- 用户说“根据我的描述生成控制脚本”
- 用户说“让机械臂按顺序做多个动作”
- 用户明确要求生成可运行的 Python 脚本

## 使用本技能生成代码

- 根据用户提示，结合 `references/pyagxarm-api.md` 的 API 与模板生成代码。
- 生成后说明：脚本需在已安装 `pyAgxArm` 和 `python-can` 的环境中运行，且 CAN 已激活。

## 生成代码规则

1. 连接与配置
- 使用 `create_agx_arm_config(robot="nero", comm="can", channel="can0", interface="socketcan")`
- 使用 `AgxArmFactory.create_arm(robot_cfg)` 创建机械臂实例
- 调用 `robot.connect()` 建立连接

2. 使能与运动前
- 运动前切换普通模式：`robot.set_normal_mode()`
- 轮询使能直到成功：`while not robot.enable(): time.sleep(0.01)`
- 每次使用 `move_*` 前，显式设置运动模式：`robot.set_motion_mode(...)`

3. 运动接口与单位
- `robot.move_j([j1..j7])`：关节运动，单位弧度（Nero 为 7 关节）
- `robot.move_p(pose)` / `robot.move_l(pose)`：笛卡尔运动，`[x,y,z,roll,pitch,yaw]`
- `robot.move_c(start_pose, mid_pose, end_pose)`：圆弧运动
- 单位要求：`x,y,z` 为米，`roll,pitch,yaw` 为弧度

4. 模式切换
- 模式切换前后都需 1 秒延时
- 可用模式接口：
  - `robot.set_normal_mode()`
  - `robot.set_master_mode()`
  - `robot.set_slave_mode()`

5. 运动完成检测
- 轮询 `robot.get_arm_status().msg.motion_status == 0` 视为运动完成
- 建议使用 2~3 秒短超时并高频轮询

6. 安全与结尾
- 提醒用户确认工作区无人员和障碍物
- 首次建议小幅度动作
- 若用户要求任务结束后失能，则在脚本末尾调用 `robot.disable()`

## 安全注意事项

- 生成的代码将驱动真实机械臂，必须强调执行安全。
- `move_js`、`move_mit` 属于高风险动作，应添加风险提示。
- 本技能仅负责生成代码，不直接执行控制动作。

## 参考文件

- API 与最小可运行模板：`references/pyagxarm-api.md`
