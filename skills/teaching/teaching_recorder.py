"""
TeachingRecorder - 示教录制模块
===========================

该模块用于录制用户示教的动作，包括关节角度、末端位置、夹爪状态等。
支持手动示教和拖拽示教模式。

功能:
- 动作录制: 记录示教过程中的所有状态数据
- 关键帧提取: 自动或手动提取关键帧
- 动作编辑: 插入、删除、修改关键帧
- 动作预览: 回放录制的内容
- 动作保存/加载: 持久化存储示教动作

使用示例:
    from skills.teaching.teaching_recorder import TeachingRecorder
    
    recorder = TeachingRecorder()
    
    # 开始录制
    await recorder.start_recording(teach_name="拾取动作")
    
    # 记录帧数据
    await recorder.record_frame(joint_positions=[0.1, 0.2, ...], gripper_state="open")
    
    # 提取关键帧
    await recorder.extract_keyframes(threshold=0.05)
    
    # 保存动作
    await recorder.save_teaching("pick_action.json")
    
    # 加载动作
    await recorder.load_teaching("pick_action.json")
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import numpy as np


class RecordingState(Enum):
    """录制状态"""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"


class FrameType(Enum):
    """帧类型"""
    NORMAL = "normal"         # 普通帧
    KEYFRAME = "keyframe"     # 关键帧
    START = "start"           # 开始帧
    END = "end"               # 结束帧


@dataclass
class JointState:
    """关节状态"""
    positions: List[float] = field(default_factory=list)  # 关节位置 (rad 或 m)
    velocities: List[float] = field(default_factory=list)  # 关节速度
    torques: List[float] = field(default_factory=list)    # 关节力矩


@dataclass
class EndEffectorState:
    """末端执行器状态"""
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # 位置 (m)
    orientation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # 姿态 (rad)
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # 速度
    

@dataclass
class GripperState:
    """夹爪状态"""
    position: float = 0.0      # 夹爪位置 (0=closed, 1=open)
    force: float = 0.0         # 夹爪力
    object_detected: bool = False  # 是否检测到物体


@dataclass
class TeachingFrame:
    """示教帧"""
    frame_id: int
    timestamp: float
    frame_type: FrameType
    
    # 关节数据
    joint_state: JointState = field(default_factory=JointState)
    
    # 末端执行器数据
    ee_state: EndEffectorState = field(default_factory=EndEffectorState)
    
    # 夹爪数据
    gripper_state: GripperState = field(default_factory=GripperState)
    
    # 额外数据 (力传感器、视觉等)
    force_data: List[float] = field(default_factory=lambda: [0.0] * 6)
    external_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "frame_type": self.frame_type.value,
            "joint_positions": self.joint_state.positions,
            "joint_velocities": self.joint_state.velocities,
            "joint_torques": self.joint_state.torques,
            "ee_position": self.ee_state.position,
            "ee_orientation": self.ee_state.orientation,
            "ee_velocity": self.ee_state.velocity,
            "gripper_position": self.gripper_state.position,
            "gripper_force": self.gripper_state.force,
            "object_detected": self.gripper_state.object_detected,
            "force_data": self.force_data,
            "external_data": self.external_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeachingFrame':
        """从字典创建"""
        return cls(
            frame_id=data["frame_id"],
            timestamp=data["timestamp"],
            frame_type=FrameType(data["frame_type"]),
            joint_state=JointState(
                positions=data.get("joint_positions", []),
                velocities=data.get("joint_velocities", []),
                torques=data.get("joint_torques", [])
            ),
            ee_state=EndEffectorState(
                position=data.get("ee_position", [0.0, 0.0, 0.0]),
                orientation=data.get("ee_orientation", [0.0, 0.0, 0.0]),
                velocity=data.get("ee_velocity", [0.0, 0.0, 0.0])
            ),
            gripper_state=GripperState(
                position=data.get("gripper_position", 0.0),
                force=data.get("gripper_force", 0.0),
                object_detected=data.get("object_detected", False)
            ),
            force_data=data.get("force_data", [0.0] * 6),
            external_data=data.get("external_data", {})
        )


@dataclass
class TeachingAction:
    """示教动作"""
    name: str
    action_id: str
    description: str = ""
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    
    # 帧数据
    frames: List[TeachingFrame] = field(default_factory=list)
    keyframe_indices: List[int] = field(default_factory=list)
    
    # 元数据
    duration: float = 0.0          # 总时长 (s)
    frame_count: int = 0           # 总帧数
    keyframe_count: int = 0        # 关键帧数
    joint_count: int = 0           # 关节数量
    sample_rate: float = 0.0      # 采样率 (Hz)
    
    # 参数
    playback_speed: float = 1.0    # 回放速度
    loop_count: int = 1            # 循环次数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "action_id": self.action_id,
            "description": self.description,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "frames": [f.to_dict() for f in self.frames],
            "keyframe_indices": self.keyframe_indices,
            "duration": self.duration,
            "frame_count": self.frame_count,
            "keyframe_count": self.keyframe_count,
            "joint_count": self.joint_count,
            "sample_rate": self.sample_rate,
            "playback_speed": self.playback_speed,
            "loop_count": self.loop_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeachingAction':
        """从字典创建"""
        action = cls(
            name=data["name"],
            action_id=data["action_id"],
            description=data.get("description", ""),
            created_at=data.get("created_at", time.time()),
            modified_at=data.get("modified_at", time.time()),
            keyframe_indices=data.get("keyframe_indices", []),
            duration=data.get("duration", 0.0),
            frame_count=data.get("frame_count", 0),
            keyframe_count=data.get("keyframe_count", 0),
            joint_count=data.get("joint_count", 0),
            sample_rate=data.get("sample_rate", 0.0),
            playback_speed=data.get("playback_speed", 1.0),
            loop_count=data.get("loop_count", 1)
        )
        
        # 加载帧数据
        for frame_data in data.get("frames", []):
            action.frames.append(TeachingFrame.from_dict(frame_data))
        
        return action


class TeachingRecorder:
    """
    示教录制器 - 录制和管理示教动作
    
    功能:
    1. 动作录制: 实时记录示教过程中的状态数据
    2. 关键帧提取: 基于阈值自动提取关键帧
    3. 动作编辑: 插入、删除、修改关键帧
    4. 动作预览: 回放录制的内容
    5. 动作保存/加载: 持久化存储
    
    注意: 这是逻辑实现，ROS集成部分可在环境准备好后添加。
    """
    
    def __init__(
        self,
        component_name: str = "teaching_recorder",
        sample_rate: float = 50.0,  # 50Hz采样率
        _simulated: bool = True
    ):
        """
        初始化示教录制器
        
        Args:
            component_name: 组件名称
            sample_rate: 采样率 (Hz)
            _simulated: 是否使用模拟模式
        """
        self.name = component_name
        self.sample_rate = sample_rate
        self._simulated = _simulated
        
        # 录制状态
        self._state = RecordingState.IDLE
        self._current_action: Optional[TeachingAction] = None
        self._frame_counter = 0
        self._start_time = 0.0
        self._last_frame_time = 0.0
        
        # 动作库
        self._action_library: Dict[str, TeachingAction] = {}
        
        # 回调函数
        self._on_frame_recorded = None
        self._on_keyframe_extracted = None
    
    async def initialize(self) -> bool:
        """初始化录制器"""
        self._state = RecordingState.IDLE
        self._current_action = None
        return True
    
    async def execute(self, action: str, **params) -> Dict[str, Any]:
        """
        执行操作
        
        Args:
            action: 操作类型
            **params: 操作参数
            
        Returns:
            操作结果
        """
        action_map = {
            "start_recording": self.start_recording,
            "stop_recording": self.stop_recording,
            "pause_recording": self.pause_recording,
            "resume_recording": self.resume_recording,
            "record_frame": self.record_frame,
            "extract_keyframes": self.extract_keyframes,
            "add_keyframe": self.add_keyframe,
            "delete_frame": self.delete_frame,
            "preview": self.preview_action,
            "save": self.save_teaching,
            "load": self.load_teaching,
            "list_actions": self.list_actions,
            "delete_action": self.delete_action,
        }
        
        if action in action_map:
            return await action_map[action](**params)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    async def start_recording(
        self,
        name: str = "untitled",
        description: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        开始录制
        
        Args:
            name: 动作名称
            description: 动作描述
            
        Returns:
            录制状态
        """
        if self._state == RecordingState.RECORDING:
            return {"success": False, "error": "Already recording"}
        
        # 创建新动作
        import uuid
        action_id = str(uuid.uuid4())[:8]
        
        self._current_action = TeachingAction(
            name=name,
            action_id=action_id,
            description=description
        )
        
        self._frame_counter = 0
        self._start_time = time.time()
        self._last_frame_time = self._start_time
        self._state = RecordingState.RECORDING
        
        # 记录开始帧
        start_frame = TeachingFrame(
            frame_id=0,
            timestamp=0.0,
            frame_type=FrameType.START
        )
        self._current_action.frames.append(start_frame)
        
        return {
            "success": True,
            "action": "start_recording",
            "name": name,
            "action_id": action_id,
            "state": self._state.value
        }
    
    async def stop_recording(self, **kwargs) -> Dict[str, Any]:
        """
        停止录制
        """
        if self._state != RecordingState.RECORDING:
            return {"success": False, "error": "Not recording"}
        
        # 记录结束帧
        end_frame = TeachingFrame(
            frame_id=self._frame_counter + 1,
            timestamp=time.time() - self._start_time,
            frame_type=FrameType.END
        )
        self._current_action.frames.append(end_frame)
        
        # 更新元数据
        self._update_metadata()
        
        # 保存到库
        self._action_library[self._current_action.action_id] = self._current_action
        
        self._state = RecordingState.STOPPED
        
        result = {
            "success": True,
            "action": "stop_recording",
            "action_id": self._current_action.action_id,
            "frame_count": self._current_action.frame_count,
            "duration": self._current_action.duration,
            "keyframe_count": self._current_action.keyframe_count
        }
        
        # 重置当前动作
        self._current_action = None
        self._frame_counter = 0
        
        return result
    
    async def pause_recording(self, **kwargs) -> Dict[str, Any]:
        """暂停录制"""
        if self._state != RecordingState.RECORDING:
            return {"success": False, "error": "Not recording"}
        
        self._state = RecordingState.PAUSED
        
        return {
            "success": True,
            "action": "pause_recording",
            "state": self._state.value
        }
    
    async def resume_recording(self, **kwargs) -> Dict[str, Any]:
        """恢复录制"""
        if self._state != RecordingState.PAUSED:
            return {"success": False, "error": "Not paused"}
        
        self._state = RecordingState.RECORDING
        self._last_frame_time = time.time()
        
        return {
            "success": True,
            "action": "resume_recording",
            "state": self._state.value
        }
    
    async def record_frame(
        self,
        joint_positions: List[float] = None,
        joint_velocities: List[float] = None,
        joint_torques: List[float] = None,
        ee_position: List[float] = None,
        ee_orientation: List[float] = None,
        gripper_position: float = 0.0,
        gripper_force: float = 0.0,
        force_data: List[float] = None,
        external_data: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        记录单帧数据
        
        Args:
            joint_positions: 关节位置
            joint_velocities: 关节速度
            joint_torques: 关节力矩
            ee_position: 末端位置
            ee_orientation: 末端姿态
            gripper_position: 夹爪位置
            gripper_force: 夹爪力
            force_data: 力传感器数据
            external_data: 外部数据
        """
        if self._state != RecordingState.RECORDING:
            return {"success": False, "error": "Not recording"}
        
        # 计算时间戳
        timestamp = time.time() - self._start_time
        
        # 创建帧
        frame = TeachingFrame(
            frame_id=self._frame_counter,
            timestamp=timestamp,
            frame_type=FrameType.NORMAL,
            joint_state=JointState(
                positions=joint_positions or [],
                velocities=joint_velocities or [],
                torques=joint_torques or []
            ),
            ee_state=EndEffectorState(
                position=ee_position or [0.0, 0.0, 0.0],
                orientation=ee_orientation or [0.0, 0.0, 0.0]
            ),
            gripper_state=GripperState(
                position=gripper_position,
                force=gripper_force
            ),
            force_data=force_data or [0.0] * 6,
            external_data=external_data or {}
        )
        
        self._current_action.frames.append(frame)
        self._frame_counter += 1
        self._last_frame_time = time.time()
        
        # 触发回调
        if self._on_frame_recorded:
            await self._on_frame_recorded(frame)
        
        return {
            "success": True,
            "action": "record_frame",
            "frame_id": frame.frame_id,
            "timestamp": timestamp,
            "total_frames": self._frame_counter
        }
    
    async def extract_keyframes(
        self,
        threshold: float = 0.05,
        min_distance: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        自动提取关键帧
        
        Args:
            threshold: 变化阈值
            min_distance: 最小帧间距
        """
        if not self._current_action or len(self._current_action.frames) < 2:
            return {"success": False, "error": "No action or not enough frames"}
        
        frames = self._current_action.frames
        keyframe_indices = [0]  # 开始帧总是关键帧
        
        for i in range(1, len(frames) - 1):  # 跳过开始和结束帧
            # 计算与前一关键帧的差异
            prev_kf_idx = keyframe_indices[-1]
            prev_frame = frames[prev_kf_idx]
            curr_frame = frames[i]
            
            # 关节位置差异
            if prev_frame.joint_state.positions and curr_frame.joint_state.positions:
                diff = np.linalg.norm(
                    np.array(curr_frame.joint_state.positions) -
                    np.array(prev_frame.joint_state.positions)
                )
                
                if diff > threshold and (i - prev_kf_idx) >= min_distance:
                    keyframe_indices.append(i)
                    frames[i].frame_type = FrameType.KEYFRAME
        
        # 添加结束帧
        keyframe_indices.append(len(frames) - 1)
        
        self._current_action.keyframe_indices = keyframe_indices
        self._current_action.keyframe_count = len(keyframe_indices)
        
        # 触发回调
        if self._on_keyframe_extracted:
            await self._on_keyframe_extracted(keyframe_indices)
        
        return {
            "success": True,
            "action": "extract_keyframes",
            "keyframe_indices": keyframe_indices,
            "keyframe_count": len(keyframe_indices)
        }
    
    async def add_keyframe(
        self,
        frame_id: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        手动添加关键帧
        
        Args:
            frame_id: 要标记为关键帧的帧ID
        """
        if not self._current_action:
            return {"success": False, "error": "No action"}
        
        if frame_id is None:
            frame_id = len(self._current_action.frames) - 1
        
        if frame_id < 0 or frame_id >= len(self._current_action.frames):
            return {"success": False, "error": "Invalid frame_id"}
        
        frame = self._current_action.frames[frame_id]
        frame.frame_type = FrameType.KEYFRAME
        
        if frame_id not in self._current_action.keyframe_indices:
            self._current_action.keyframe_indices.append(frame_id)
            self._current_action.keyframe_indices.sort()
            self._current_action.keyframe_count = len(self._current_action.keyframe_indices)
        
        return {
            "success": True,
            "action": "add_keyframe",
            "frame_id": frame_id,
            "keyframe_count": self._current_action.keyframe_count
        }
    
    async def delete_frame(
        self,
        frame_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        删除帧
        
        Args:
            frame_id: 要删除的帧ID
        """
        if not self._current_action:
            return {"success": False, "error": "No action"}
        
        if frame_id <= 0 or frame_id >= len(self._current_action.frames) - 1:
            return {"success": False, "error": "Cannot delete start or end frame"}
        
        # 删除帧
        del self._current_action.frames[frame_id]
        
        # 重新编号
        for i, frame in enumerate(self._current_action.frames):
            frame.frame_id = i
        
        # 更新关键帧索引
        if frame_id in self._current_action.keyframe_indices:
            self._current_action.keyframe_indices.remove(frame_id)
        
        # 更新元数据
        self._update_metadata()
        
        return {
            "success": True,
            "action": "delete_frame",
            "frame_id": frame_id,
            "remaining_frames": len(self._current_action.frames)
        }
    
    async def preview_action(
        self,
        action_id: str = None,
        speed: float = 1.0,
        loop: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        预览动作
        
        Args:
            action_id: 动作ID
            speed: 回放速度
            loop: 是否循环
        """
        action = self._current_action
        if action_id and action_id in self._action_library:
            action = self._action_library[action_id]
        
        if not action:
            return {"success": False, "error": "No action to preview"}
        
        frames = action.frames
        frame_time = 1.0 / self.sample_rate
        
        # 模拟回放
        playback_frames = []
        for i, frame in enumerate(frames):
            await asyncio.sleep(frame_time / speed)
            playback_frames.append({
                "frame_id": frame.frame_id,
                "timestamp": frame.timestamp,
                "joint_positions": frame.joint_state.positions,
                "ee_position": frame.ee_state.position
            })
            
            if not loop and i >= len(frames) - 1:
                break
        
        return {
            "success": True,
            "action": "preview",
            "action_id": action.action_id,
            "name": action.name,
            "frames_played": len(playback_frames),
            "duration": action.duration
        }
    
    async def save_teaching(
        self,
        filename: str,
        action_id: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        保存示教动作到文件
        
        Args:
            filename: 文件名
            action_id: 动作ID
        """
        action = self._current_action
        if action_id and action_id in self._action_library:
            action = self._action_library[action_id]
        
        if not action:
            return {"success": False, "error": "No action to save"}
        
        # 更新修改时间
        action.modified_at = time.time()
        
        # 转换为JSON并保存
        data = action.to_dict()
        
        if self._simulated:
            # 在模拟模式下，只返回保存的内容
            return {
                "success": True,
                "action": "save",
                "filename": filename,
                "action_id": action.action_id,
                "data_preview": {
                    "name": action.name,
                    "frame_count": action.frame_count,
                    "keyframe_count": action.keyframe_count,
                    "duration": action.duration
                }
            }
        else:
            # TODO: 实际保存到文件
            pass
    
    async def load_teaching(
        self,
        filename: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        从文件加载示教动作
        
        Args:
            filename: 文件名
        """
        if self._simulated:
            # 在模拟模式下，返回错误（因为没有实际文件）
            return {
                "success": False,
                "error": "Simulated mode: Cannot load from file"
            }
        else:
            # TODO: 从文件加载
            pass
    
    async def list_actions(self, **kwargs) -> Dict[str, Any]:
        """列出所有保存的示教动作"""
        actions = []
        for action_id, action in self._action_library.items():
            actions.append({
                "action_id": action_id,
                "name": action.name,
                "description": action.description,
                "frame_count": action.frame_count,
                "keyframe_count": action.keyframe_count,
                "duration": action.duration,
                "created_at": action.created_at
            })
        
        return {
            "success": True,
            "action": "list_actions",
            "count": len(actions),
            "actions": actions
        }
    
    async def delete_action(
        self,
        action_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """删除示教动作"""
        if action_id in self._action_library:
            del self._action_library[action_id]
            return {
                "success": True,
                "action": "delete_action",
                "action_id": action_id
            }
        else:
            return {
                "success": False,
                "error": f"Action {action_id} not found"
            }
    
    def _update_metadata(self):
        """更新动作元数据"""
        if not self._current_action:
            return
        
        frames = self._current_action.frames
        if not frames:
            return
        
        # 计算时长
        self._current_action.duration = frames[-1].timestamp - frames[0].timestamp
        
        # 帧数
        self._current_action.frame_count = len(frames)
        
        # 关键帧数
        self._current_action.keyframe_count = len(self._current_action.keyframe_indices)
        
        # 关节数
        if frames[0].joint_state.positions:
            self._current_action.joint_count = len(frames[0].joint_state.positions)
        
        # 采样率
        if self._current_action.duration > 0:
            self._current_action.sample_rate = self._current_action.frame_count / self._current_action.duration
    
    def get_state(self) -> RecordingState:
        """获取录制状态"""
        return self._state
    
    def get_current_action(self) -> Optional[TeachingAction]:
        """获取当前动作"""
        return self._current_action
    
    def set_callbacks(
        self,
        on_frame_recorded=None,
        on_keyframe_extracted=None
    ):
        """设置回调函数"""
        self._on_frame_recorded = on_frame_recorded
        self._on_keyframe_extracted = on_keyframe_extracted


def create_teaching_recorder(
    component_name: str = "teaching_recorder",
    sample_rate: float = 50.0,
    simulated: bool = True
) -> TeachingRecorder:
    """
    工厂函数: 创建TeachingRecorder实例
    """
    return TeachingRecorder(
        component_name=component_name,
        sample_rate=sample_rate,
        _simulated=simulated
    )
