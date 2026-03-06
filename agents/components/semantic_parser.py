# agents/components/semantic_parser.py
"""语义解析器

解析语音/文本指令为结构化动作。
"""

from typing import Dict, Any
import re


class SemanticParser:
    """语义解析器 - 解析语音指令为结构化动作"""

    # 方向映射（中 -> 英）
    DIRECTION_MAP = {
        "前": "forward",
        "后": "backward",
        "上": "up",
        "下": "down",
        "左": "left",
        "右": "right",
    }

    # 抓取关键词
    GRASP_KEYWORDS = ["抓", "拿", "取", "拾"]

    # 放置关键词
    PLACE_KEYWORDS = ["放", "置", "投", "放"]

    def __init__(self):
        """初始化语义解析器"""
        pass

    def parse(self, text: str) -> Dict[str, Any]:
        """解析文本为结构化指令

        Args:
            text: 输入文本

        Returns:
            包含 intent 和参数的字典
        """
        text = text.strip()

        # 解析意图
        intent = self._parse_intent(text)

        # 解析参数
        params = self._parse_params(text)

        return {"intent": intent, **params}

    def _parse_intent(self, text: str) -> str:
        """解析意图类型"""
        # 运动指令：包含方向关键词
        if any(kw in text for kw in list(self.DIRECTION_MAP.keys())):
            return "motion"

        # 抓取指令
        if any(kw in text for kw in self.GRASP_KEYWORDS):
            return "grasp"

        # 放置指令
        if any(kw in text for kw in self.PLACE_KEYWORDS):
            return "place"

        return "unknown"

    def _parse_params(self, text: str) -> Dict[str, Any]:
        """解析参数"""
        params = {}

        # 解析方向
        for cn, en in self.DIRECTION_MAP.items():
            if cn in text:
                params["direction"] = en
                break

        # 解析距离
        distance = self._parse_distance(text)
        if distance is not None:
            params["distance"] = distance

        return params

    def _parse_distance(self, text: str) -> float:
        """解析距离数值

        Returns:
            距离值（米），未找到返回 None
        """
        # 匹配模式: 数字 + 单位
        pattern = r"(\d+\.?\d*)\s*(厘米|cm|毫米|mm|m|米)"
        match = re.search(pattern, text)

        if not match:
            return None

        value = float(match.group(1))
        unit = match.group(2)

        # 单位转换
        if unit in ["厘米", "cm"]:
            return value / 100
        elif unit in ["毫米", "mm"]:
            return value / 1000
        elif unit in ["米", "m"]:
            return value

        return value
