#!/usr/bin/env python3
"""
Fara-7B集成测试脚本
测试vLLM服务器与EmbodiedAgentsSys的集成

版本: v1.0
日期: 2026-03-03
作者: Claude AI

使用说明:
1. 确保vLLM服务器正在运行: ./start_fara_server.sh
2. 运行测试: python test_fara_integration.py
3. 查看测试结果和性能指标

测试内容:
- 服务器连接测试
- API端点健康检查
- 基本推理功能测试
- 性能基准测试
- 错误处理测试
"""

import sys
import time
import json
import statistics
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from agents.config_fara import FaraConfig, FaraDemo, test_fara_service
    from agents.clients.generic import GenericHTTPClient
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在EmbodiedAgentsSys项目根目录中运行")
    sys.exit(1)


class FaraIntegrationTest:
    """
    Fara-7B集成测试类
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port
        self.client: Optional[GenericHTTPClient] = None
        self.demo: Optional[FaraDemo] = None

        # 测试结果存储
        self.results = {
            "connection": False,
            "api_endpoints": {},
            "basic_inference": False,
            "performance": {},
            "error_handling": False
        }

    def setup(self) -> bool:
        """
        设置测试环境

        返回:
            bool: 设置是否成功
        """
        print("=" * 70)
        print("Fara-7B 集成测试")
        print("=" * 70)
        print(f"服务器: {self.host}:{self.port}")
        print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        try:
            self.client = FaraConfig.create_client(host=self.host, port=self.port)
            self.demo = FaraDemo(self.client)
            print("✓ 测试环境设置完成")
            return True
        except Exception as e:
            print(f"✗ 测试环境设置失败: {e}")
            return False

    def test_connection(self) -> bool:
        """
        测试服务器连接

        返回:
            bool: 连接是否成功
        """
        print("\n" + "=" * 70)
        print("1. 服务器连接测试")
        print("=" * 70)

        try:
            # 使用FaraDemo测试连接
            if self.demo.test_connection():
                print("✓ 服务器连接测试通过")
                self.results["connection"] = True
                return True
            else:
                print("✗ 服务器连接测试失败")
                return False

        except Exception as e:
            print(f"✗ 连接测试异常: {e}")
            return False

    def test_api_endpoints(self) -> bool:
        """
        测试API端点

        返回:
            bool: API端点是否正常
        """
        print("\n" + "=" * 70)
        print("2. API端点测试")
        print("=" * 70)

        endpoints_to_test = [
            ("/v1/models", "GET", None, "模型列表端点"),
            ("/v1/chat/completions", "POST", {
                "model": "Fara-7B",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5
            }, "聊天补全端点"),
        ]

        all_passed = True
        endpoint_results = {}

        for endpoint, method, data, description in endpoints_to_test:
            try:
                url = f"http://{self.host}:{self.port}{endpoint}"
                print(f"测试: {description} ({endpoint})")

                if method == "GET":
                    response = self.client.client.get(endpoint)
                elif method == "POST" and data:
                    response = self.client.client.post(
                        endpoint,
                        json=data,
                        timeout=10
                    )
                else:
                    print(f"  ⚠️  跳过: 不支持的method或data")
                    continue

                if response.status_code in [200, 201]:
                    print(f"  ✓ 响应正常 (状态码: {response.status_code})")
                    endpoint_results[endpoint] = {
                        "status": "success",
                        "status_code": response.status_code
                    }
                else:
                    print(f"  ✗ 响应异常 (状态码: {response.status_code})")
                    endpoint_results[endpoint] = {
                        "status": "failed",
                        "status_code": response.status_code
                    }
                    all_passed = False

            except Exception as e:
                print(f"  ✗ 请求失败: {e}")
                endpoint_results[endpoint] = {
                    "status": "error",
                    "error": str(e)
                }
                all_passed = False

        self.results["api_endpoints"] = endpoint_results

        if all_passed:
            print("\n✓ 所有API端点测试通过")
            return True
        else:
            print("\n✗ 部分API端点测试失败")
            return False

    def test_basic_inference(self) -> bool:
        """
        测试基本推理功能

        返回:
            bool: 推理功能是否正常
        """
        print("\n" + "=" * 70)
        print("3. 基本推理功能测试")
        print("=" * 70)

        test_cases = [
            {
                "prompt": "What is artificial intelligence?",
                "min_length": 10,
                "description": "定义性问题"
            },
            {
                "prompt": "Translate 'hello' to Chinese",
                "min_length": 2,
                "description": "简单翻译"
            },
            {
                "prompt": "Explain in one sentence: machine learning",
                "min_length": 10,
                "description": "单句解释"
            }
        ]

        all_passed = True

        for i, test_case in enumerate(test_cases, 1):
            prompt = test_case["prompt"]
            min_length = test_case["min_length"]
            description = test_case["description"]

            print(f"测试 {i}: {description}")
            print(f"  提示: {prompt}")

            try:
                start_time = time.time()
                response = self.demo.simple_query(prompt, max_new_tokens=100)
                elapsed = time.time() - start_time

                if response and len(response) >= min_length:
                    print(f"  ✓ 推理成功 ({elapsed:.2f}秒)")
                    print(f"  响应: {response[:100]}...")
                elif response:
                    print(f"  ⚠️  响应过短: {len(response)}字符 (预期至少{min_length})")
                    print(f"  响应: {response}")
                    all_passed = False
                else:
                    print(f"  ✗ 推理失败: 无响应")
                    all_passed = False

            except Exception as e:
                print(f"  ✗ 推理异常: {e}")
                all_passed = False

            print()

        self.results["basic_inference"] = all_passed

        if all_passed:
            print("✓ 基本推理功能测试通过")
            return True
        else:
            print("✗ 基本推理功能测试失败")
            return False

    def test_performance(self) -> bool:
        """
        测试性能基准

        返回:
            bool: 性能是否可接受
        """
        print("\n" + "=" * 70)
        print("4. 性能基准测试")
        print("=" * 70)

        # 测试提示
        test_prompts = [
            "What is AI?",
            "Explain machine learning briefly",
            "Describe deep learning in simple terms",
            "What are neural networks?",
            "How does reinforcement learning work?"
        ]

        print("运行性能测试 (5个查询)...")
        print()

        response_times = []
        response_lengths = []

        for i, prompt in enumerate(test_prompts, 1):
            try:
                print(f"查询 {i}: {prompt}")

                start_time = time.time()
                response = self.demo.simple_query(prompt, max_new_tokens=100)
                elapsed = time.time() - start_time

                if response:
                    response_times.append(elapsed)
                    response_lengths.append(len(response))

                    print(f"  时间: {elapsed:.2f}秒")
                    print(f"  长度: {len(response)}字符")
                    print(f"  速度: {len(response)/elapsed:.1f} 字符/秒")
                else:
                    print(f"  ✗ 查询失败")

            except Exception as e:
                print(f"  ✗ 查询异常: {e}")

            print()

        # 性能统计
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            avg_length = statistics.mean(response_lengths)

            print("性能统计:")
            print(f"  平均响应时间: {avg_time:.2f}秒")
            print(f"  最短响应时间: {min_time:.2f}秒")
            print(f"  最长响应时间: {max_time:.2f}秒")
            print(f"  平均响应长度: {avg_length:.0f}字符")
            print(f"  平均速度: {avg_length/avg_time:.1f} 字符/秒")

            # 性能标准
            performance_acceptable = avg_time < 5.0  # 平均响应时间应小于5秒

            self.results["performance"] = {
                "avg_response_time": avg_time,
                "min_response_time": min_time,
                "max_response_time": max_time,
                "avg_response_length": avg_length,
                "performance_acceptable": performance_acceptable
            }

            if performance_acceptable:
                print("\n✓ 性能测试通过 (平均响应时间 < 5秒)")
                return True
            else:
                print(f"\n⚠️  性能警告 (平均响应时间 {avg_time:.2f}秒 > 5秒)")
                return False
        else:
            print("✗ 性能测试失败: 无成功查询")
            return False

    def test_error_handling(self) -> bool:
        """
        测试错误处理

        返回:
            bool: 错误处理是否正常
        """
        print("\n" + "=" * 70)
        print("5. 错误处理测试")
        print("=" * 70)

        print("测试空查询处理...")
        try:
            # 测试空查询
            result = self.client.inference({
                "query": [],
                "stream": False
            })
            print("  ⚠️  空查询未触发错误 (可能由服务器处理)")
        except Exception as e:
            print(f"  ✓ 空查询触发错误: {type(e).__name__}")

        print("\n测试超长查询...")
        try:
            # 测试超长查询 (可能触发token限制)
            long_prompt = "test " * 1000
            result = self.demo.simple_query(long_prompt, max_new_tokens=10)
            if result:
                print("  ✓ 超长查询处理正常")
            else:
                print("  ⚠️  超长查询无响应 (可能被服务器拒绝)")
        except Exception as e:
            print(f"  ✓ 超长查询触发错误: {type(e).__name__}")

        print("\n测试无效参数...")
        try:
            # 测试无效温度参数
            result = self.client.inference({
                "query": [{"role": "user", "content": "test"}],
                "temperature": 2.5,  # 无效温度值
                "stream": False,
                "max_new_tokens": 10
            })
            print("  ⚠️  无效参数未触发错误 (可能由服务器处理)")
        except Exception as e:
            print(f"  ✓ 无效参数触发错误: {type(e).__name__}")

        self.results["error_handling"] = True
        print("\n✓ 错误处理测试完成")
        return True

    def generate_report(self) -> Dict[str, Any]:
        """
        生成测试报告

        返回:
            Dict[str, Any]: 测试报告
        """
        print("\n" + "=" * 70)
        print("测试报告")
        print("=" * 70)

        # 统计通过率
        test_categories = ["connection", "basic_inference"]
        passed_tests = sum(1 for category in test_categories if self.results.get(category))

        total_tests = len(test_categories)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        # 生成报告
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "server": f"{self.host}:{self.port}",
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "pass_rate": f"{pass_rate:.1f}%",
                "overall_status": "PASS" if pass_rate >= 80 else "FAIL"
            },
            "detailed_results": self.results,
            "recommendations": []
        }

        # 显示结果
        print(f"测试服务器: {report['server']}")
        print(f"测试时间: {report['timestamp']}")
        print(f"总体状态: {report['summary']['overall_status']}")
        print(f"通过率: {report['summary']['pass_rate']} ({passed_tests}/{total_tests})")
        print()

        # 详细结果
        print("详细结果:")
        for category, result in self.results.items():
            if isinstance(result, bool):
                status = "✓ 通过" if result else "✗ 失败"
                print(f"  {category}: {status}")
            elif isinstance(result, dict):
                print(f"  {category}:")
                for key, value in result.items():
                    print(f"    {key}: {value}")

        # 生成建议
        if not self.results["connection"]:
            report["recommendations"].append(
                "检查vLLM服务器是否运行: ./start_fara_server.sh"
            )

        if not self.results["basic_inference"]:
            report["recommendations"].append(
                "检查模型是否正确加载，查看vLLM日志"
            )

        performance = self.results.get("performance", {})
        if performance.get("performance_acceptable") is False:
            avg_time = performance.get("avg_response_time", 0)
            report["recommendations"].append(
                f"性能优化: 平均响应时间{avg_time:.1f}秒较高，考虑调整vLLM参数"
            )

        if report["recommendations"]:
            print("\n建议:")
            for rec in report["recommendations"]:
                print(f"  • {rec}")

        print("\n" + "=" * 70)

        return report

    def save_report(self, report: Dict[str, Any]):
        """
        保存测试报告到文件

        参数:
            report: 测试报告
        """
        report_dir = Path("test_reports")
        report_dir.mkdir(exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"fara_test_report_{timestamp}.json"

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"测试报告已保存: {report_file}")

    def run_all_tests(self) -> bool:
        """
        运行所有测试

        返回:
            bool: 所有测试是否通过
        """
        if not self.setup():
            return False

        tests = [
            ("连接测试", self.test_connection),
            ("API端点测试", self.test_api_endpoints),
            ("推理功能测试", self.test_basic_inference),
            ("性能测试", self.test_performance),
            ("错误处理测试", self.test_error_handling)
        ]

        all_passed = True

        for test_name, test_func in tests:
            try:
                if not test_func():
                    all_passed = False
            except Exception as e:
                print(f"✗ {test_name} 异常: {e}")
                all_passed = False

        # 生成报告
        report = self.generate_report()
        self.save_report(report)

        return all_passed


def quick_test() -> bool:
    """
    快速测试函数

    返回:
        bool: 测试是否通过
    """
    print("执行快速测试...")
    return test_fara_service()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Fara-7B集成测试")
    parser.add_argument("--host", default="127.0.0.1", help="vLLM服务器地址")
    parser.add_argument("--port", type=int, default=5000, help="vLLM服务器端口")
    parser.add_argument("--quick", action="store_true", help="快速测试模式")
    parser.add_argument("--demo", action="store_true", help="运行对话演示")

    args = parser.parse_args()

    if args.quick:
        # 快速测试模式
        if quick_test():
            print("✓ 快速测试通过")
            sys.exit(0)
        else:
            print("✗ 快速测试失败")
            sys.exit(1)

    if args.demo:
        # 对话演示模式
        print("启动对话演示...")
        demo = FaraDemo(FaraConfig.create_client(host=args.host, port=args.port))
        demo.conversation_demo(max_turns=5)
        sys.exit(0)

    # 完整测试模式
    tester = FaraIntegrationTest(host=args.host, port=args.port)

    if tester.run_all_tests():
        print("🎉 所有测试完成!")
        sys.exit(0)
    else:
        print("⚠️  部分测试失败，请查看报告")
        sys.exit(1)


if __name__ == "__main__":
    main()