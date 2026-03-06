# tests/test_semantic_parser.py
"""语义解析器测试"""
import pytest


def test_semantic_parser_init():
    """验证语义解析器初始化"""
    from agents.components.semantic_parser import SemanticParser

    parser = SemanticParser()
    assert parser is not None


def test_parse_motion_command():
    """验证解析运动指令"""
    from agents.components.semantic_parser import SemanticParser

    parser = SemanticParser()
    result = parser.parse("向前20厘米")

    assert result["intent"] == "motion"
    assert result["direction"] == "forward"
    assert result["distance"] == 0.2  # 20厘米 = 0.2米


def test_parse_distance_units():
    """验证不同单位的解析"""
    from agents.components.semantic_parser import SemanticParser

    parser = SemanticParser()

    # 厘米
    result_cm = parser.parse("向前10厘米")
    assert result_cm["distance"] == 0.1

    # 毫米
    result_mm = parser.parse("向前50毫米")
    assert result_mm["distance"] == 0.05

    # 米
    result_m = parser.parse("向前2米")
    assert result_m["distance"] == 2.0


def test_parse_grasp_command():
    """验证解析抓取指令"""
    from agents.components.semantic_parser import SemanticParser

    parser = SemanticParser()

    result = parser.parse("抓取杯子")
    assert result["intent"] == "grasp"

    result2 = parser.parse("拿一个零件")
    assert result2["intent"] == "grasp"


def test_parse_place_command():
    """验证解析放置指令"""
    from agents.components.semantic_parser import SemanticParser

    parser = SemanticParser()

    result = parser.parse("放到桌子上")
    assert result["intent"] == "place"

    result2 = parser.parse("放置到料框")
    assert result2["intent"] == "place"


def test_parse_direction_mapping():
    """验证方向映射"""
    from agents.components.semantic_parser import SemanticParser

    parser = SemanticParser()

    # 前
    assert parser.parse("向前")["direction"] == "forward"
    # 后
    assert parser.parse("向后")["direction"] == "backward"
    # 上
    assert parser.parse("向上")["direction"] == "up"
    # 下
    assert parser.parse("向下")["direction"] == "down"
    # 左
    assert parser.parse("向左")["direction"] == "left"
    # 右
    assert parser.parse("向右")["direction"] == "right"


def test_parse_unknown_command():
    """验证未知指令"""
    from agents.components.semantic_parser import SemanticParser

    parser = SemanticParser()
    result = parser.parse("你好")

    assert result["intent"] == "unknown"
