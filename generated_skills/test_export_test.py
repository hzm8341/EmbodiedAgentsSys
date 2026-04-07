
"""
测试export_test
"""
import asyncio
import pytest
from export_test import ExportTestSkill


async def test_export_test_basic():
    """基础测试"""
    skill = ExportTestSkill()
    
    # 初始化
    initialized = await skill.initialize()
    assert initialized is True
    
    # 执行
    result = await skill.execute()
    
    # 验证
    assert result["success"] is True
    assert result["skill_name"] == "export_test"


async def test_export_test_validation():
    """参数验证测试"""
    skill = ExportTestSkill()
    await skill.initialize()
    
    # 测试无效输入
    result = await skill.execute()
    # 应该能处理并返回结果
