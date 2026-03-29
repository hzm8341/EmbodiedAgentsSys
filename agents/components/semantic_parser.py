# agents/components/semantic_parser.py
"""语义解析器

解析语音/文本指令为结构化动作，支持 LLM 增强和规则 fallback。
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
import re
import json
import asyncio

if TYPE_CHECKING:
    from agents.llm.provider import LLMProvider


class SemanticParser:
    """语义解析器 - 解析语音指令为结构化动作

    支持两种模式:
    1. LLM 模式: 使用 Ollama 进行自然语言理解
    2. 规则模式: 基于关键词的规则解析 (fallback)
    """

    DIRECTION_MAP = {
        "前": "forward",
        "后": "backward",
        "上": "up",
        "下": "down",
        "左": "left",
        "右": "right",
    }

    GRASP_KEYWORDS = ["抓", "拿", "取", "拾"]
    PLACE_KEYWORDS = ["放", "置", "投", "放"]

    VALID_INTENTS = ["motion", "grasp", "place", "task", "gripper", "reach", "move"]

    def __init__(
        self,
        use_llm: bool = True,
        ollama_model: str = "qwen2.5:3b",
        llm_provider: Optional["LLMProvider"] = None,
    ):
        """初始化语义解析器

        Args:
            use_llm: 是否使用 LLM 增强解析
            ollama_model: Ollama 模型名称
            llm_provider: 可选 LLMProvider，优先级高于直接 ollama 调用
        """
        self.use_llm = use_llm
        self._ollama_client = None
        self._ollama_model = ollama_model
        self._llm_provider = llm_provider

        if use_llm:
            self._init_ollama()

    def _init_ollama(self) -> None:
        """初始化 Ollama 客户端"""
        try:
            from ollama import Client

            self._ollama_client = Client(host="http://127.0.0.1:11434")
        except Exception:
            self.use_llm = False

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

    async def parse_async(self, text: str) -> Dict[str, Any]:
        """异步解析文本为结构化指令 (LLM 增强)

        Args:
            text: 输入文本

        Returns:
            包含 intent 和参数的字典
        """
        if self.use_llm and self._ollama_client:
            try:
                result = await self._llm_parse(text)
                if result:
                    return result
            except Exception:
                pass
        return self.parse(text)

    async def _llm_parse(self, text: str) -> Optional[Dict[str, Any]]:
        """使用 LLM 解析指令"""
        prompt = f"""将以下机器人操作指令解析为JSON格式。
输出格式: {{"intent": "motion|grasp|place|task|gripper|reach|move", "params": {{...}}}}
指令: {text}
只输出JSON，不要其他内容:"""

        # 若有 llm_provider，优先使用它
        if self._llm_provider is not None:
            try:
                response_text = await self._llm_provider.chat_with_retry(
                    user=prompt,
                )
                response_text = response_text.strip()
                parsed = json.loads(response_text)
                if parsed.get("intent") in self.VALID_INTENTS:
                    return parsed
            except Exception:
                pass
            return None

        # 原有 ollama 调用路径（向后兼容）
        try:
            response = self._ollama_client.generate(
                model=self._ollama_model, prompt=prompt, options={"num_predict": 128}
            )
            response_text = response.get("response", "").strip()
            parsed = json.loads(response_text)
            if parsed.get("intent") in self.VALID_INTENTS:
                return parsed
        except Exception:
            pass
        return None

    def _parse_intent(self, text: str) -> str:
        """解析意图类型"""
        # 放置指令优先于运动指令（"放到上面" 含方向词但属于放置）
        if any(kw in text for kw in self.PLACE_KEYWORDS):
            return "place"

        # 抓取指令
        if any(kw in text for kw in self.GRASP_KEYWORDS):
            return "grasp"

        # 运动指令：包含方向关键词
        if any(kw in text for kw in list(self.DIRECTION_MAP.keys())):
            return "motion"

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
