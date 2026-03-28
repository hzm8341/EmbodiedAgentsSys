"""
最简单的 Agent Harness 示例
依赖: pip install openai  (或换成任何你用的模型API)

结构:
  TaskSet    → 题库
  Environment → 模拟环境（这里用简单的字典模拟）
  Tracer     → 记录每步
  Evaluator  → 判断对错
  Scorer     → 输出分数
"""

import json
from openai import OpenAI  # 换成你用的API

import os
# 方法1（推荐）：从环境变量读取，不要把KEY写死在代码里
client = OpenAI(
    api_key="sk-c06f88da1e3045dbb8e35cda41abe64a",  # 换成你的 DeepSeek API Key
    base_url="https://api.deepseek.com",
)

# ============================================================
# 1. 任务集 TaskSet
# ============================================================
TASKS = [
    {
        "id": "task_001",
        "instruction": "今天北京的天气怎么样？",
        "expected_keywords": ["北京", "天气"],   # 答案里应该包含这些词
    },
    {
        "id": "task_002",
        "instruction": "1+1等于几？",
        "expected_keywords": ["2", "二"],
    },
    {
        "id": "task_003",
        "instruction": "用Python写一个打印Hello World的程序",
        "expected_keywords": ["print", "Hello"],
    },
]

# ============================================================
# 2. 模拟环境 Environment
# （真实项目里可以是假网站、沙箱、Docker等）
# ============================================================
class SimpleEnvironment:
    def __init__(self):
        self.call_log = []  # 记录所有工具调用

    def reset(self):
        self.call_log = []

    def run_agent(self, instruction: str) -> str:
        """让 Agent 回答这道题，并记录过程"""
        self.call_log.append({"step": "call_agent", "input": instruction})

        # 这里调用真实的模型
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": instruction}]
        )
        answer = response.choices[0].message.content

        self.call_log.append({"step": "agent_response", "output": answer[:100]})
        return answer

# ============================================================
# 3. 追踪器 Tracer
# ============================================================
class Tracer:
    def __init__(self):
        self.records = []

    def log(self, task_id: str, env: SimpleEnvironment):
        self.records.append({
            "task_id": task_id,
            "steps": env.call_log.copy()
        })

    def show(self):
        for r in self.records:
            print(f"\n[Tracer] Task: {r['task_id']}")
            for s in r["steps"]:
                print(f"  → {s['step']}: {list(s.values())[1][:60]}")

# ============================================================
# 4. 评估器 Evaluator
# ============================================================
class Evaluator:
    def evaluate(self, answer: str, expected_keywords: list, match_mode: str = "all") -> bool:
        """
        match_mode="all" : 所有关键词都必须出现（默认，适合复杂任务）
        match_mode="any" : 任意一个关键词出现即通过（适合同义词/多种正确表达）
        """
        answer_lower = answer.lower()
        fn = all if match_mode == "all" else any
        return fn(kw.lower() in answer_lower for kw in expected_keywords)

# ============================================================
# 5. 打分器 Scorer
# ============================================================
class Scorer:
    def __init__(self):
        self.results = []

    def record(self, task_id: str, passed: bool):
        self.results.append({"task_id": task_id, "passed": passed})

    def report(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        print("\n" + "="*40)
        print(f"[Scorer] 总任务数: {total}")
        print(f"[Scorer] 通过数:   {passed}")
        print(f"[Scorer] 得分:     {passed/total*100:.1f}%")
        print("="*40)
        for r in self.results:
            status = "✅" if r["passed"] else "❌"
            print(f"  {status} {r['task_id']}")

# ============================================================
# 6. 主流程：把所有模块串起来
# ============================================================
def run_harness():
    env = SimpleEnvironment()
    tracer = Tracer()
    evaluator = Evaluator()
    scorer = Scorer()

    print("🚀 开始运行 Harness...\n")

    for task in TASKS:
        print(f"▶ 运行任务: {task['id']} — {task['instruction']}")

        # 重置环境
        env.reset()

        # 让 Agent 执行任务
        answer = env.run_agent(task["instruction"])

        # 追踪记录
        tracer.log(task["id"], env)

        # 评估结果
        passed = evaluator.evaluate(answer, task["expected_keywords"], task.get("match_mode", "all"))

        # 记录分数
        scorer.record(task["id"], passed)

        print(f"   答案片段: {answer[:80]}...")
        print(f"   评估结果: {'通过 ✅' if passed else '未通过 ❌'}\n")

    # 打印追踪日志
    tracer.show()

    # 打印最终报告
    scorer.report()


if __name__ == "__main__":
    run_harness()