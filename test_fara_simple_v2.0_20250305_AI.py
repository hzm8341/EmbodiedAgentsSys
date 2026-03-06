#!/usr/bin/env python3
"""
Fara-7B 轻量级测试脚本 (不依赖ROS2)
使用Ollama Python库

版本: v2.0
日期: 2026-03-05
"""

from ollama import chat, list as list_models


def test_connection():
    """测试连接"""
    print("\n" + "=" * 60)
    print("1. 连接测试")
    print("=" * 60)

    try:
        models = list_models()
        print("✓ Ollama服务正常")
        print("\n可用模型:")

        for m in models.models:
            size_gb = m.size / (1024**3)
            model_str = str(m.model)
            # 提取模型名
            if "=" in model_str:
                name = model_str.split("=")[1].strip("'")
            else:
                name = model_str
            print(f"  - {name} ({size_gb:.1f} GB)")
        return True
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False


def test_basic_chat():
    """测试基本对话"""
    print("\n" + "=" * 60)
    print("2. 基本对话测试")
    print("=" * 60)

    test_cases = [
        {"name": "简单问候", "content": "Hello! Please respond with 'OK'."},
        {"name": "自我介绍", "content": "Who are you? Answer in one sentence."},
        {"name": "知识问答", "content": "What is artificial intelligence?"},
    ]

    model = "maternion/fara"
    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test['name']}")
        print(f"  输入: {test['content'][:50]}...")

        try:
            response = chat(
                model=model, messages=[{"role": "user", "content": test["content"]}]
            )
            print(f"  ✓ 成功")
            print(f"  输出: {response.message.content[:100]}...")
        except Exception as e:
            print(f"  ✗ 异常: {e}")
            all_passed = False

    return all_passed


def test_streaming():
    """测试流式输出"""
    print("\n" + "=" * 60)
    print("3. 流式输出测试")
    print("=" * 60)

    print("\n测试流式输出...")
    print("  输出: ", end="", flush=True)

    try:
        stream = chat(
            model="maternion/fara",
            messages=[{"role": "user", "content": "Count from 1 to 5."}],
            stream=True,
        )
        for chunk in stream:
            print(chunk.message.content, end="", flush=True)
        print("\n  ✓ 流式输出成功")
        return True
    except Exception as e:
        print(f"\n  ✗ 流式输出失败: {e}")
        return False


def interactive_demo():
    """交互式演示"""
    print("\n" + "=" * 60)
    print("4. 交互式演示")
    print("=" * 60)
    print("\n输入 'quit' 或 'exit' 退出\n")

    model = "maternion/fara"
    messages = []

    while True:
        try:
            user_input = input("你: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                print("退出对话")
                break
            if not user_input:
                continue

            messages.append({"role": "user", "content": user_input})
            print("Fara-7B: ", end="", flush=True)

            stream = chat(model=model, messages=messages, stream=True)
            response_content = ""
            for chunk in stream:
                print(chunk.message.content, end="", flush=True)
                response_content += chunk.message.content

            print()
            messages.append({"role": "assistant", "content": response_content})
        except KeyboardInterrupt:
            print("\n退出对话")
            break
        except Exception as e:
            print(f"\n错误: {e}")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Fara-7B 测试套件")
    print("=" * 60)

    results = {}
    results["connection"] = test_connection()
    results["chat"] = test_basic_chat()
    results["streaming"] = test_streaming()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(results.values())
    print("\n" + ("✓ 所有测试通过!" if all_passed else "✗ 部分测试失败"))

    return all_passed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fara-7B轻量级测试")
    parser.add_argument("--chat", action="store_true", help="交互式对话")
    parser.add_argument("--test", action="store_true", help="运行所有测试")
    args = parser.parse_args()

    if args.chat:
        interactive_demo()
    else:
        run_all_tests()
