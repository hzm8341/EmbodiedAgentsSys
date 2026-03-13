import numpy as np
from typing import Dict, List, Any, Optional
import asyncio
import json
import re
from dataclasses import dataclass


@dataclass
class SceneUnderstandingResult:
    """Scene understanding result"""
    objects: List[Dict[str, Any]]
    scene_description: str
    target_object: Optional[str]
    grasp_hints: Dict[str, Any]
    confidence: float


class Qwen3LProcessor:
    """
    qwen3-l scene understanding processor.

    Uses qwen3-l model to understand scenes and parse instructions.
    In production, loads the actual qwen3-l model. In development, uses mock inference.
    """

    def __init__(
        self,
        model_path: str,
        device: str = "cuda",
        temperature: float = 0.1,
        max_tokens: int = 500
    ):
        self.model_path = model_path
        self.device = device
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._model = None
        self._tokenizer = None
        self._model_loaded = False

    def _load_model(self) -> Any:
        """Load qwen3-l model (lazy loading)."""
        if self._model_loaded and self._model is not None:
            return self._model
        try:
            self._model = _MockQwen3LModel()
            self._model_loaded = True
            return self._model
        except Exception as e:
            raise RuntimeError(f"Failed to load qwen3-l model: {e}")

    def _load_tokenizer(self) -> Any:
        """Load tokenizer (lazy loading)."""
        if self._tokenizer is not None:
            return self._tokenizer
        try:
            self._tokenizer = _MockTokenizer()
            return self._tokenizer
        except Exception as e:
            raise RuntimeError(f"Failed to load tokenizer: {e}")

    def _build_prompt(self, instruction: str, segmentation_result: Dict[str, Any]) -> str:
        """Build prompt for scene understanding."""
        num_objects = len(segmentation_result.get("masks", []))
        return f"""你是一个视觉语言助手，需要分析场景并理解用户指令。

图像中有 {num_objects} 个分割出的物体区域。

用户指令："{instruction}"

请按照以下JSON格式输出：
{{
  "scene_description": "场景描述文本",
  "objects": [
    {{
      "name": "物体名称",
      "category": "物体类别",
      "confidence": 0.95,
      "attributes": {{"颜色": "黄色"}}
    }}
  ],
  "target_object": "目标物体名称或null"
}}"""

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse model response, with fallback for invalid JSON."""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Fallback: keyword matching
        result: Dict[str, Any] = {
            "scene_description": "场景分析完成",
            "objects": [],
            "target_object": None
        }
        common_objects = {
            "香蕉": "水果", "苹果": "水果", "梨子": "水果",
            "橙子": "水果", "工具": "工具", "盒子": "容器", "杯子": "容器"
        }
        detected = [
            {"name": name, "category": cat, "confidence": 0.8, "attributes": {}}
            for name, cat in common_objects.items()
            if name in response
        ]
        if detected:
            result["objects"] = detected
            result["scene_description"] = f"场景中有 {', '.join(o['name'] for o in detected)}"
        return result

    async def understand(
        self,
        image: np.ndarray,
        segmentation_result: Dict[str, Any],
        instruction: str
    ) -> Dict[str, Any]:
        """
        Understand scene from image and segmentation results.

        Args:
            image: Input image (H, W, 3) uint8
            segmentation_result: Segmentation results dict
            instruction: User instruction text

        Returns:
            Dict with objects, scene_description, target_object keys
        """
        self._load_model()
        self._load_tokenizer()

        prompt = self._build_prompt(instruction, segmentation_result)

        # Mock inference — replace with real qwen3-l call in production
        mock_response = json.dumps({
            "scene_description": "场景中有若干物体",
            "objects": [
                {
                    "name": "物体1",
                    "category": "未知",
                    "confidence": 0.85,
                    "attributes": {}
                }
            ],
            "target_object": None
        })

        return self._parse_response(mock_response)


class _MockQwen3LModel:
    """Mock qwen3-l model for development/testing."""
    def generate(self, input_ids: Any, **kwargs: Any) -> List[List[int]]:
        return [[0]]


class _MockTokenizer:
    """Mock tokenizer for development/testing."""
    def encode(self, text: str, return_tensors: Optional[str] = None) -> List[List[int]]:
        return [[0] * len(text.split())]

    def decode(self, token_ids: List[int], skip_special_tokens: bool = True) -> str:
        return '{"scene_description": "mock", "objects": [], "target_object": null}'
