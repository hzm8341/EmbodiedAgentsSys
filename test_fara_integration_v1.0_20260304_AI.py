#!/usr/bin/env python
"""
Fara-7B 集成测试脚本
测试与vLLM服务的连接和基本推理功能

版本: v1.0
日期: 2026-03-04
"""

import sys
import os

# 确保可以导入agents模块
sys.path.insert(0, "/media/hzm/data_disk/EmbodiedAgentsSys")

from agents.config_fara import FaraConfig, FaraDemo, test_fara_service


def main():
    print("=" * 60)
    print("Fara-7B 集成测试")
    print("=" * 60)
    print()

    # 测试服务连接
    print("1. 测试vLLM服务连接...")
    if test_fara_service(host="127.0.0.1", port=5000):
        print("   ✓ 服务连接成功")
    else:
        print("   ✗ 服务连接失败")
        print("   请先启动vLLM服务:")
        print("   /media/hzm/data_disk/fara/start_fara_server.sh")
        return False

    # 创建客户端和测试
    print()
    print("2. 创建Fara客户端...")
    client = FaraConfig.create_client(
        host="127.0.0.1",
        port=5000,
        inference_timeout=120
    )
    print("   ✓ 客户端创建成功")

    # 测试推理
    print()
    print("3. 测试基本推理...")
    demo = FaraDemo(client)
    response = demo.simple_query(
        "What is artificial intelligence? Answer in one sentence.",
        max_new_tokens=100
    )

    if response:
        print(f"   ✓ 推理成功!")
        print(f"   响应: {response[:200]}...")
    else:
        print("   ✗ 推理失败")
        return False

    print()
    print("=" * 60)
    print("测试完成!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
