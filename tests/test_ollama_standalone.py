#!/usr/bin/env python3
"""
独立测试 Ollama 连接
不依赖 ROS2/agents 包
"""

import httpx

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
MODEL = "qwen3.5:9b"


def test_connection():
    """测试 Ollama 服务连接"""
    print(f"正在连接 Ollama ({OLLAMA_HOST}:{OLLAMA_PORT})...")

    try:
        response = httpx.get(f"http://{OLLAMA_HOST}:{OLLAMA_PORT}")
        print(f"✓ 服务状态: {response.text}")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False
    return True


def test_model():
    """测试模型推理"""
    print(f"\n使用模型: {MODEL}")

    try:
        from ollama import Client

        client = Client(host=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}")

        # 测试对话
        response = client.chat(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "Hello! Reply with 'OK' if you can hear me.",
                }
            ],
            options={"temperature": 0.7},
        )

        print(f"✓ 模型响应: {response['message']['content']}")
        return True
    except Exception as e:
        print(f"✗ 推理失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Ollama 连接测试")
    print("=" * 50)

    if test_connection():
        test_model()
