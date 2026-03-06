"""
测试TeachingRecorder组件
"""
import asyncio
import sys
import os
import importlib.util

# 直接加载teaching_recorder模块
spec = importlib.util.spec_from_file_location(
    "teaching_recorder",
    "/media/hzm/data_disk/EmbodiedAgentsSys/skills/teaching/teaching_recorder.py"
)
teaching_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teaching_module)

TeachingRecorder = teaching_module.TeachingRecorder
TeachingFrame = teaching_module.TeachingFrame
FrameType = teaching_module.FrameType
RecordingState = teaching_module.RecordingState


async def test_start_stop_recording():
    """测试开始/停止录制"""
    print("\n" + "="*60)
    print("测试1: 开始/停止录制")
    print("="*60)
    
    recorder = TeachingRecorder(_simulated=True)
    await recorder.initialize()
    
    # 开始录制
    result = await recorder.start_recording(
        name="测试动作1",
        description="这是一个测试动作"
    )
    
    print(f"  开始录制:")
    print(f"    成功: {result['success']}")
    print(f"    动作名称: {result['name']}")
    print(f"    动作ID: {result['action_id']}")
    print(f"    状态: {result['state']}")
    
    # 记录一些帧
    for i in range(10):
        await recorder.record_frame(
            joint_positions=[0.1 * i, 0.2 * i, 0.3 * i],
            ee_position=[0.3, 0.1 * i, 0.05],
            gripper_position=0.5 if i % 2 == 0 else 0.8
        )
    
    print(f"\n  已记录10帧")
    print(f"    当前状态: {recorder.get_state().value}")
    
    # 停止录制
    result = await recorder.stop_recording()
    
    print(f"\n  停止录制:")
    print(f"    成功: {result['success']}")
    print(f"    动作ID: {result['action_id']}")
    print(f"    帧数: {result['frame_count']}")
    print(f"    时长: {result['duration']:.2f}s")
    print(f"    关键帧数: {result['keyframe_count']}")


async def test_pause_resume():
    """测试暂停/恢复"""
    print("\n" + "="*60)
    print("测试2: 暂停/恢复录制")
    print("="*60)
    
    recorder = TeachingRecorder(_simulated=True)
    await recorder.initialize()
    
    # 开始录制
    await recorder.start_recording(name="测试动作2")
    
    # 记录几帧
    for i in range(5):
        await recorder.record_frame(joint_positions=[0.1 * i] * 6)
    
    print(f"  记录5帧后")
    
    # 暂停
    result = await recorder.pause_recording()
    print(f"  暂停: {result['success']}, 状态: {result['state']}")
    
    # 尝试在暂停时记录（应该失败）
    result = await recorder.record_frame(joint_positions=[0.5] * 6)
    print(f"  暂停时记录: {result['success']} (预期失败)")
    
    # 恢复
    result = await recorder.resume_recording()
    print(f"  恢复: {result['success']}, 状态: {result['state']}")
    
    # 继续记录
    await recorder.record_frame(joint_positions=[0.6] * 6)
    print(f"  恢复后记录成功")
    
    # 停止
    result = await recorder.stop_recording()
    print(f"  总帧数: {result['frame_count']}")


async def test_keyframe_extraction():
    """测试关键帧提取"""
    print("\n" + "="*60)
    print("测试3: 关键帧提取")
    print("="*60)
    
    recorder = TeachingRecorder(_simulated=True)
    await recorder.initialize()
    
    # 开始录制
    await recorder.start_recording(name="测试动作3")
    
    # 记录有明显变化的帧
    positions = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        [0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
        [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
        [0.31, 0.31, 0.31, 0.31, 0.31, 0.31],  # 小变化
        [0.32, 0.32, 0.32, 0.32, 0.32, 0.32],  # 小变化
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],  # 大变化
        [0.6, 0.6, 0.6, 0.6, 0.6, 0.6],
    ]
    
    for pos in positions:
        await recorder.record_frame(joint_positions=pos)
    
    # 提取关键帧 (阈值0.1)
    result = await recorder.extract_keyframes(threshold=0.1, min_distance=1)
    
    print(f"  提取关键帧 (阈值0.1):")
    print(f"    成功: {result['success']}")
    print(f"    关键帧索引: {result['keyframe_indices']}")
    print(f"    关键帧数: {result['keyframe_count']}")
    
    # 停止
    result = await recorder.stop_recording()
    print(f"  总帧数: {result['frame_count']}, 关键帧数: {result['keyframe_count']}")


async def test_manual_keyframe():
    """测试手动添加关键帧"""
    print("\n" + "="*60)
    print("测试4: 手动添加关键帧")
    print("="*60)
    
    recorder = TeachingRecorder(_simulated=True)
    await recorder.initialize()
    
    # 开始录制
    await recorder.start_recording(name="测试动作4")
    
    # 记录一些帧
    for i in range(10):
        await recorder.record_frame(joint_positions=[0.1 * i] * 6)
    
    # 手动添加关键帧
    result = await recorder.add_keyframe(frame_id=5)
    print(f"  添加关键帧ID=5:")
    print(f"    成功: {result['success']}")
    print(f"    当前关键帧数: {result['keyframe_count']}")
    
    # 删除帧
    result = await recorder.delete_frame(frame_id=3)
    print(f"  删除帧ID=3:")
    print(f"    成功: {result['success']}")
    print(f"    剩余帧数: {result['remaining_frames']}")
    
    # 停止
    result = await recorder.stop_recording()
    print(f"  最终关键帧数: {result['keyframe_count']}")


async def test_preview():
    """测试预览"""
    print("\n" + "="*60)
    print("测试5: 动作预览")
    print("="*60)
    
    recorder = TeachingRecorder(_simulated=True)
    await recorder.initialize()
    
    # 开始录制
    await recorder.start_recording(name="测试动作5")
    
    # 记录几帧
    for i in range(5):
        await recorder.record_frame(
            joint_positions=[0.1 * i] * 6,
            ee_position=[0.3, 0.1 * i, 0.05]
        )
    
    # 停止
    result = await recorder.stop_recording()
    action_id = result['action_id']
    
    # 预览
    result = await recorder.preview_action(action_id=action_id, speed=2.0)
    
    print(f"  预览动作:")
    print(f"    成功: {result['success']}")
    print(f"    动作名称: {result['name']}")
    print(f"    播放帧数: {result['frames_played']}")
    print(f"    时长: {result['duration']:.2f}s")


async def test_action_library():
    """测试动作库"""
    print("\n" + "="*60)
    print("测试6: 动作库管理")
    print("="*60)
    
    recorder = TeachingRecorder(_simulated=True)
    await recorder.initialize()
    
    # 录制多个动作
    for i in range(3):
        await recorder.start_recording(name=f"动作{i+1}")
        
        for j in range(5):
            await recorder.record_frame(joint_positions=[0.1 * j] * 6)
        
        await recorder.stop_recording()
    
    # 列出动作
    result = await recorder.list_actions()
    
    print(f"  动作库:")
    print(f"    成功: {result['success']}")
    print(f"    动作数量: {result['count']}")
    
    for action in result['actions']:
        print(f"    - {action['name']}: {action['frame_count']}帧, {action['duration']:.2f}s")
    
    # 删除动作
    action_id = result['actions'][0]['action_id']
    result = await recorder.delete_action(action_id=action_id)
    print(f"\n  删除动作: {result['success']}")
    
    # 再次列出
    result = await recorder.list_actions()
    print(f"  剩余动作数量: {result['count']}")


async def test_save():
    """测试保存"""
    print("\n" + "="*60)
    print("测试7: 保存动作")
    print("="*60)
    
    recorder = TeachingRecorder(_simulated=True)
    await recorder.initialize()
    
    # 录制动作
    await recorder.start_recording(name="保存测试动作")
    
    for i in range(10):
        await recorder.record_frame(
            joint_positions=[0.1 * i] * 6,
            ee_position=[0.3, 0.1 * i, 0.05],
            gripper_position=0.5
        )
    
    # 保存
    result = await recorder.save_teaching("test_action.json")
    
    print(f"  保存动作:")
    print(f"    成功: {result['success']}")
    print(f"    文件名: {result['filename']}")
    print(f"    动作ID: {result['action_id']}")
    print(f"    数据预览:")
    print(f"      名称: {result['data_preview']['name']}")
    print(f"      帧数: {result['data_preview']['frame_count']}")
    print(f"      关键帧数: {result['data_preview']['keyframe_count']}")
    print(f"      时长: {result['data_preview']['duration']:.2f}s")


async def test_frame_data():
    """测试帧数据"""
    print("\n" + "="*60)
    print("测试8: 帧数据转换")
    print("="*60)
    
    # 创建帧
    frame = TeachingFrame(
        frame_id=0,
        timestamp=1.5,
        frame_type=FrameType.KEYFRAME,
        joint_state=teaching_module.JointState(
            positions=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            velocities=[0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
        ),
        ee_state=teaching_module.EndEffectorState(
            position=[0.3, 0.1, 0.05],
            orientation=[0.0, 0.0, 0.0]
        ),
        gripper_state=teaching_module.GripperState(
            position=0.5,
            force=1.0,
            object_detected=True
        ),
        force_data=[0.1, 0.2, 0.3, 0.0, 0.0, 0.0]
    )
    
    # 转换为字典
    data = frame.to_dict()
    print(f"  帧数据:")
    print(f"    frame_id: {data['frame_id']}")
    print(f"    timestamp: {data['timestamp']}")
    print(f"    frame_type: {data['frame_type']}")
    print(f"    joint_positions: {data['joint_positions']}")
    print(f"    ee_position: {data['ee_position']}")
    print(f"    gripper_position: {data['gripper_position']}")
    print(f"    force_data: {data['force_data']}")
    
    # 从字典创建
    frame2 = TeachingFrame.from_dict(data)
    print(f"\n  从字典恢复:")
    print(f"    frame_id: {frame2.frame_id}")
    print(f"    joint_positions: {frame2.joint_state.positions}")


async def main():
    print("\n" + "="*60)
    print("TeachingRecorder测试")
    print("="*60)
    
    await test_start_stop_recording()
    await test_pause_resume()
    await test_keyframe_extraction()
    await test_manual_keyframe()
    await test_preview()
    await test_action_library()
    await test_save()
    await test_frame_data()
    
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
