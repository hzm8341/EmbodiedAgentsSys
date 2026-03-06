"""
VoiceCommand组件 - 语音命令理解组件

该组件用于接收语音输入并解析为结构化的命令。
设计用于语音示教场景，支持运动指令、复合动作和任务级指令的解析。

注意: 这是核心逻辑实现，ROS集成部分可在环境准备好后添加。
"""
import re
from typing import Dict, Any, Optional, List


class VoiceCommandResult:
    """语音命令解析结果"""
    
    def __init__(self, intent: str, params: Dict[str, Any] = None, 
                 raw_text: str = "", confidence: float = 1.0):
        self.intent = intent
        self.params = params or {}
        self.raw_text = raw_text
        self.confidence = confidence


class VoiceCommand:
    """
    语音命令理解组件
    
    负责将语音识别结果解析为结构化的机器人控制命令。
    支持三种级别的指令:
    - L1 基础运动: "向前20cm", "向上5cm"
    - L2 复合动作: "把夹爪打开", "移动到料框上方"
    - L3 任务级: "把零件拿到拍照位置"
    """
    
    # 方向映射
    DIRECTION_MAP = {
        "前": ("direction", "forward"),
        "后": ("direction", "backward"),
        "上": ("direction", "up"),
        "下": ("direction", "down"),
        "左": ("direction", "left"),
        "右": ("direction", "right"),
    }
    
    # 夹爪动作映射
    GRIPPER_MAP = {
        "打开": "open",
        "张开": "open",
        "关闭": "close",
        "闭合": "close",
        "松开": "open",
        "抓紧": "close",
    }
    
    # 预设位置映射
    POSITION_MAP = {
        "拍照位置": "photo_position",
        "料框": "bin",
        "产线": "production_line",
        "原点": "home",
        "等待位": "wait_position",
    }
    
    def __init__(self, component_name: str = "voice_command", trigger_topic: str = "audio_input"):
        """
        初始化语音命令组件
        
        Args:
            component_name: 组件名称
            trigger_topic: 触发话题
        """
        self.name = component_name
        self.trigger_topic = trigger_topic
        self._initialized = True
    
    def parse(self, text: str) -> VoiceCommandResult:
        """
        解析语音文本为结构化命令
        
        Args:
            text: 语音识别结果文本
            
        Returns:
            VoiceCommandResult: 解析结果
        """
        text = text.strip()
        
        # 尝试解析不同级别的指令
        # 1. 任务级指令
        if result := self._parse_task_level(text):
            return result
        
        # 2. 复合动作指令
        if result := self._parse_composite(text):
            return result
        
        # 3. 基础运动指令
        if result := self._parse_motion(text):
            return result
        
        # 无法解析
        return VoiceCommandResult(
            intent="unknown",
            params={},
            raw_text=text,
            confidence=0.0
        )
    
    def _parse_motion(self, text: str) -> Optional[VoiceCommandResult]:
        """解析基础运动指令"""
        # 匹配模式: "方向 + 距离" 如 "向前20厘米", "向上5cm"
        motion_pattern = r'([前后上下左右])(\d+\.?\d*)(厘米|cm|毫米|mm)?'
        match = re.search(motion_pattern, text)
        
        if match:
            direction, distance, unit = match.groups()
            
            # 转换单位
            distance = float(distance)
            if unit in ("毫米", "mm"):
                distance = distance / 1000  # 转换为米
            elif unit in ("厘米", "cm"):
                distance = distance / 100  # 转换为米
            
            # 获取方向
            direction_key = self.DIRECTION_MAP.get(direction)
            if direction_key:
                _, dir_value = direction_key
                
                return VoiceCommandResult(
                    intent="motion",
                    params={
                        "action": "move",
                        "direction": dir_value,
                        "distance": distance,
                        "unit": "m"
                    },
                    raw_text=text,
                    confidence=0.95
                )
        
        return None
    
    def _parse_composite(self, text: str) -> Optional[VoiceCommandResult]:
        """解析复合动作指令"""
        # 夹爪动作
        for keyword, action in self.GRIPPER_MAP.items():
            if keyword in text:
                return VoiceCommandResult(
                    intent="gripper",
                    params={
                        "action": action
                    },
                    raw_text=text,
                    confidence=0.95
                )
        
        # 移动到预设位置
        for keyword, position in self.POSITION_MAP.items():
            if keyword in text and ("移动" in text or "去" in text or "到" in text):
                return VoiceCommandResult(
                    intent="composite",
                    params={
                        "action": "move_to",
                        "target": position
                    },
                    raw_text=text,
                    confidence=0.90
                )
        
        return None
    
    def _parse_task_level(self, text: str) -> Optional[VoiceCommandResult]:
        """解析任务级指令"""
        # 模式: "把[物体]拿到[位置]" 或类似
        task_patterns = [
            r'把(.+?)拿到(.+)',  # 贪婪匹配目标位置
            r'把(.+?)放到(.+)',
            r'把(.+?)移动到(.+)',
            r'把(.+?)搬运到(.+)',
        ]
        
        for pattern in task_patterns:
            match = re.search(pattern, text)
            if match:
                source = match.group(1).strip()
                target = match.group(2).strip()
                
                return VoiceCommandResult(
                    intent="task",
                    params={
                        "action": "transfer",
                        "source": source,
                        "target": target
                    },
                    raw_text=text,
                    confidence=0.85
                )
        
        return None
    
    async def process(self, audio_data: Any) -> VoiceCommandResult:
        """
        处理音频数据（异步接口）
        
        注意: 实际的ASR处理应该在外部完成，此处仅做语义解析
        """
        # 这是一个占位实现
        # 实际使用时，ASR部分由SpeechToText组件处理
        # 此组件专注于语义解析
        raise NotImplementedError("ASR processing should be done externally")


def create_voice_command(component_name: str = "voice_command", 
                         trigger_topic: str = "audio_input") -> VoiceCommand:
    """
    工厂函数: 创建VoiceCommand实例
    """
    return VoiceCommand(component_name=component_name, trigger_topic=trigger_topic)
