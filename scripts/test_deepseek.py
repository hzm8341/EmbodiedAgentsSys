#!/usr/bin/env python3
"""Test DeepSeek API with LiteLLM provider."""

import os
import sys

# 设置 API Key
os.environ['DEEPSEEK_API_KEY'] = 'sk-e5d01fe06cc64d45a022c447a31ab518'

import litellm


def test_deepseek_chat():
    """Test basic chat with DeepSeek."""
    print("=" * 50)
    print("Test 1: Basic Chat")
    print("=" * 50)

    response = litellm.completion(
        model='deepseek/deepseek-chat',
        messages=[
            {'role': 'user', 'content': '你好，请用一句话介绍你自己'}
        ],
        api_key=os.environ['DEEPSEEK_API_KEY']
    )

    print(f"Model: deepseek/deepseek-chat")
    print(f"Response: {response.choices[0].message.content}")
    print("✓ Test passed!\n")


def test_deepseek_coder():
    """Test code generation with DeepSeek Coder."""
    print("=" * 50)
    print("Test 2: Code Generation (deepseek-coder)")
    print("=" * 50)

    response = litellm.completion(
        model='deepseek/deepseek-coder',
        messages=[
            {'role': 'user', 'content': '写一个 Python 函数，计算斐波那契数列第 n 项'}
        ],
        api_key=os.environ['DEEPSEEK_API_KEY']
    )

    print(f"Model: deepseek/deepseek-coder")
    print(f"Response: {response.choices[0].message.content[:200]}...")
    print("✓ Test passed!\n")


def test_with_system_prompt():
    """Test with system prompt for robot context."""
    print("=" * 50)
    print("Test 3: Robot Task Planning")
    print("=" * 50)

    response = litellm.completion(
        model='deepseek/deepseek-chat',
        messages=[
            {'role': 'system', 'content': '你是一个机器人任务规划助手。请用 JSON 格式输出任务步骤。'},
            {'role': 'user', 'content': '任务：从桌子上抓取红色方块放到篮子里'}
        ],
        api_key=os.environ['DEEPSEEK_API_KEY']
    )

    print(f"Model: deepseek/deepseek-chat")
    print(f"Response: {response.choices[0].message.content}")
    print("✓ Test passed!\n")


if __name__ == '__main__':
    try:
        test_deepseek_chat()
        test_deepseek_coder()
        test_with_system_prompt()

        print("=" * 50)
        print("✓ All DeepSeek tests passed!")
        print("=" * 50)
    except Exception as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)