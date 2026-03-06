#!/usr/bin/env python3
"""
EmbodiedAgents Web UI Demo - 使用Fara-7B (Ollama)

功能:
- 使用本地Ollama服务运行Fara-7B模型
- 启动Dynamic Web UI进行交互

使用说明:
1. 确保Ollama服务正在运行: ollama serve
2. 确保Fara-7B模型已下载: ollama pull maternion/fara
3. 运行: python demo_fara_webui.py

版本: v1.0
日期: 2026-03-05
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.clients.ollama import OllamaClient
from agents.models import OllamaModel
from agents.components import LLM
from agents.ros import Topic, Launcher


def create_fara_demo():
    """
    创建使用Fara-7B的Web UI Demo

    这个Demo创建一个简单的LLM组件，通过Web UI进行交互。
    Launcher会自动启动Dynamic Web UI。
    """

    print("=" * 60)
    print("EmbodiedAgents + Fara-7B Web UI Demo")
    print("=" * 60)

    # ============================================================
    # 1. 配置Fara-7B模型 (通过Ollama)
    # ============================================================
    OLLAMA_HOST = "127.0.0.1"
    OLLAMA_PORT = 11434
    MODEL_NAME = "maternion/fara"  # Fara-7B模型名

    print(f"\n配置:")
    print(f"  - Ollama: {OLLAMA_HOST}:{OLLAMA_PORT}")
    print(f"  - 模型: {MODEL_NAME}")

    # 创建模型配置
    fara_model = OllamaModel(
        name="fara_vllm",
        checkpoint=MODEL_NAME,
        options={
            "temperature": 0.7,
            "num_predict": 500,
        },
    )

    # 创建Ollama客户端
    print(f"\n连接Ollama服务...")
    fara_client = OllamaClient(
        model=fara_model,
        host=OLLAMA_HOST,
        port=OLLAMA_PORT,
        inference_timeout=120,  # Fara-7B推理可能需要更长时间
    )
    print("✓ 客户端创建成功")

    # ============================================================
    # 2. 定义输入输出Topic
    # ============================================================
    # 输入Topic - 接收用户文本
    text_input = Topic(name="user_input", msg_type="String")
    # 输出Topic - 返回模型响应
    text_output = Topic(name="model_output", msg_type="String")

    # ============================================================
    # 3. 创建LLM组件
    # ============================================================
    llm_component = LLM(
        inputs=[text_input],
        outputs=[text_output],
        model_client=fara_client,
        trigger=text_input,
        component_name="fara_llm",
    )

    # 设置系统提示词
    llm_component.set_component_prompt(
        template="""You are Fara-7B, an efficient agentic AI assistant.
Answer questions helpfully and concisely."""
    )

    print("✓ LLM组件创建成功")

    # ============================================================
    # 4. 启动Launcher (自动启动Web UI)
    # ============================================================
    print("\n启动Agent (Web UI)...")
    launcher = Launcher()
    launcher.add_pkg(components=[llm_component])

    print("\n" + "=" * 60)
    print("启动完成!")
    print("=" * 60)
    print("\n访问Web UI: http://localhost:7860 (或其他端口)")
    print("发送消息到 topic: user_input")
    print("从 topic 接收: model_output")
    print("\n按 Ctrl+C 停止")
    print("=" * 60)

    # 启动
    launcher.bringup()


def test_connection():
    """快速测试连接"""
    print("\n快速连接测试...")

    try:
        model = OllamaModel(
            name="fara_test", checkpoint="maternion/fara", options={"temperature": 0.7}
        )
        client = OllamaClient(
            model=model, host="127.0.0.1", port=11434, inference_timeout=120
        )

        # 简单测试
        result = client.inference({
            "query": [{"role": "user", "content": "Hello! Say 'OK' if you work."}],
            "stream": False,
            "max_new_tokens": 50,
        })

        if result and result.get("output"):
            print(f"✓ 连接成功!")
            print(f"  响应: {result['output']}")
            return True
        else:
            print("✗ 无响应")
            return False

    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fara-7B Web UI Demo")
    parser.add_argument("--test", action="store_true", help="仅测试连接")
    args = parser.parse_args()

    if args.test:
        test_connection()
    else:
        create_fara_demo()
