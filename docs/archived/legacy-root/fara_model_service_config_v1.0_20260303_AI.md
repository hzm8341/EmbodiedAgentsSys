:orphan:

# Fara-7B模型服务配置方案 v1.0

**创建日期**: 2026-03-03
**文档版本**: v1.0
**作者**: Claude AI
**适用项目**: EmbodiedAgentsSys

---

## 目录

1. [项目概述](#1-项目概述)
2. [环境分析](#2-环境分析)
3. [方案设计](#3-方案设计)
4. [实施步骤](#4-实施步骤)
5. [配置详解](#5-配置详解)
6. [测试验证](#6-测试验证)
7. [故障排除](#7-故障排除)
8. [扩展建议](#8-扩展建议)

---

## 1. 项目概述

### 1.1 目标
将Microsoft Fara-7B模型配置为本地服务，供EmbodiedAgentsSys框架使用，实现本地大模型推理能力。

### 1.2 当前状态
- **EmbodiedAgentsSys**: 已安装，支持OpenAI兼容API
- **Fara-7B模型**: 已下载到HuggingFace缓存 (`~/.cache/huggingface/hub/models--microsoft--Fara-7B/`)
- **硬件环境**: NVIDIA RTX 3090 (24GB VRAM)，内存充足
- **服务状态**: 之前vLLM服务器尝试运行但崩溃

### 1.3 核心需求
1. 启动稳定的vLLM服务器托管Fara-7B模型
2. 配置EmbodiedAgentsSys使用本地vLLM服务
3. 确保服务稳定性和性能优化

---

## 2. 环境分析

### 2.1 硬件环境
| 组件 | 规格 | 状态 |
|------|------|------|
| GPU | NVIDIA RTX 3090 | 24GB VRAM，当前使用608MB |
| 内存 | 系统内存充足 | 模型加载后可用VRAM约20GB |
| 存储 | 模型已下载 | HuggingFace缓存完整 |

### 2.2 软件环境
| 组件 | 版本/状态 | 备注 |
|------|-----------|------|
| Python | 3.12 (fara虚拟环境) | fara目录有完整虚拟环境 |
| vLLM | 已安装 | fara虚拟环境包含 |
| EmbodiedAgentsSys | 生产级框架 | 支持OpenAI兼容API |
| CUDA | 12.4 | GPU驱动正常 |

### 2.3 依赖分析
- **Fara项目**: 包含完整vLLM启动脚本和客户端
- **EmbodiedAgentsSys**: 已有`GenericHTTPClient`支持OpenAI兼容API
- **兼容性**: vLLM提供OpenAI兼容接口，可直接集成

---

## 3. 方案设计

### 3.1 架构设计
```
┌─────────────────┐    HTTP    ┌──────────────┐    ┌──────────────┐
│ EmbodiedAgents  │───────────▶│  vLLM Server │────│  Fara-7B     │
│      Sys        │◀───────────│  (port 5000) │    │  模型        │
└─────────────────┘   OpenAI   └──────────────┘    └──────────────┘
                            兼容API
```

### 3.2 技术选型
| 组件 | 选择 | 理由 |
|------|------|------|
| 模型服务 | vLLM | 高性能推理，OpenAI兼容，Fara官方推荐 |
| 客户端 | GenericHTTPClient | EmbodiedAgentsSys内置，OpenAI兼容 |
| 配置方式 | Python配置脚本 | 灵活，可复用 |

### 3.3 关键参数设计
| 参数 | 推荐值 | 说明 |
|------|--------|------|
| 端口 | 5000 | 避免冲突，Fara默认 |
| dtype | auto | 自动选择最佳精度 |
| tensor-parallel-size | 1 | RTX 3090单卡足够 |
| gpu-memory-utilization | 0.9 | 最大化GPU利用率 |
| max-model-len | 4096 | 平衡性能与能力 |

---

## 4. 实施步骤

### 4.1 阶段一：vLLM服务器启动
```bash
# 1. 激活fara虚拟环境
cd /media/hzm/data_disk/fara
source .venv/bin/activate

# 2. 启动vLLM服务器（基础版）
vllm serve "microsoft/Fara-7B" \
  --port 5000 \
  --dtype auto \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9

# 3. 验证服务
curl http://127.0.0.1:5000/v1/models
```

### 4.2 阶段二：EmbodiedAgentsSys配置
```python
# 创建配置文件: config_fara_vllm.py
from agents.clients.generic import GenericHTTPClient
from agents.models import GenericLLM

# 模型配置
model_config = GenericLLM(
    name="fara-7b",
    checkpoint="Fara-7B",
    options={
        "temperature": 0.7,
        "max_new_tokens": 500,
    }
)

# 客户端配置
client = GenericHTTPClient(
    model=model_config,
    host="127.0.0.1",
    port=5000,
    api_key="",  # vLLM无需API密钥
    inference_timeout=60
)
```

### 4.3 阶段三：集成测试
```python
# 测试脚本: test_fara_integration.py
def test_fara_service():
    """测试Fara-7B服务集成"""
    # 1. 创建客户端
    client = create_fara_client()

    # 2. 测试连接
    result = client.inference({
        "query": [{"role": "user", "content": "Hello, are you ready?"}],
        "stream": False,
        "max_new_tokens": 50
    })

    # 3. 验证响应
    assert result["output"] is not None
    print(f"✓ 服务测试通过: {result['output'][:100]}...")
```

---

## 5. 配置详解

### 5.1 vLLM服务器配置脚本
创建文件: `start_fara_server.sh`
```bash
#!/bin/bash
# Fara-7B vLLM服务器启动脚本

# 设置环境
cd /media/hzm/data_disk/fara
source .venv/bin/activate

# 启动参数
MODEL="microsoft/Fara-7B"
PORT=5000
DTYPE="auto"
GPU_UTIL="0.9"

# 日志设置
LOG_FILE="/media/hzm/data_disk/fara/vllm_server_$(date +%Y%m%d_%H%M%S).log"

echo "启动 Fara-7B vLLM服务器..."
echo "端口: $PORT"
echo "日志: $LOG_FILE"

# 启动命令
vllm serve "$MODEL" \
  --port $PORT \
  --dtype $DTYPE \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization $GPU_UTIL \
  --max-model-len 4096 \
  --enforce-eager \
  2>&1 | tee $LOG_FILE
```

### 5.2 EmbodiedAgentsSys配置模块
创建文件: `agents/config_fara.py`
```python
"""
Fara-7B模型配置模块
为EmbodiedAgentsSys提供Fara-7B本地服务配置
"""

from typing import Dict, Any
from agents.clients.generic import GenericHTTPClient
from agents.models import GenericLLM, LLMConfig


class FaraConfig:
    """Fara-7B配置类"""

    @staticmethod
    def create_model_config(
        name: str = "fara-7b",
        temperature: float = 0.7,
        max_new_tokens: int = 500,
        stream: bool = False
    ) -> GenericLLM:
        """创建Fara-7B模型配置"""
        return GenericLLM(
            name=name,
            checkpoint="Fara-7B",
            options={
                "temperature": temperature,
                "max_new_tokens": max_new_tokens,
                "stream": stream
            }
        )

    @staticmethod
    def create_client(
        host: str = "127.0.0.1",
        port: int = 5000,
        inference_timeout: int = 60,
        **kwargs
    ) -> GenericHTTPClient:
        """创建Fara-7B客户端"""
        model = FaraConfig.create_model_config(**kwargs)

        return GenericHTTPClient(
            model=model,
            host=host,
            port=port,
            api_key="",  # vLLM无需API密钥
            inference_timeout=inference_timeout,
            logging_level="info"
        )

    @staticmethod
    def create_llm_config(
        enable_rag: bool = False,
        chat_history: bool = True,
        **llm_kwargs
    ) -> LLMConfig:
        """创建完整的LLM配置"""
        return LLMConfig(
            enable_rag=enable_rag,
            chat_history=chat_history,
            temperature=0.7,
            max_new_tokens=500,
            stream=False,
            **llm_kwargs
        )
```

### 5.3 使用示例
```python
# 示例: 在项目中集成Fara-7B
from agents.config_fara import FaraConfig

# 1. 创建客户端
fara_client = FaraConfig.create_client(
    host="127.0.0.1",
    port=5000,
    temperature=0.7
)

# 2. 创建LLM配置
llm_config = FaraConfig.create_llm_config(
    enable_rag=True,
    collection_name="fara_knowledge"
)

# 3. 在组件中使用
class FaraLLMComponent:
    def __init__(self):
        self.client = fara_client
        self.config = llm_config

    def query(self, prompt: str) -> str:
        """查询Fara-7B模型"""
        result = self.client.inference({
            "query": [{"role": "user", "content": prompt}],
            "stream": False
        })
        return result["output"]
```

---

## 6. 测试验证

### 6.1 服务健康检查
```bash
# 1. 检查服务器进程
ps aux | grep vllm | grep -v grep

# 2. 检查API端点
curl http://127.0.0.1:5000/v1/models
curl http://127.0.0.1:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Fara-7B",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'

# 3. 检查GPU使用
nvidia-smi
```

### 6.2 集成测试脚本
创建文件: `test_fara_integration.py`
```python
#!/usr/bin/env python3
"""
Fara-7B集成测试脚本
测试vLLM服务器与EmbodiedAgentsSys的集成
"""

import sys
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.config_fara import FaraConfig


def test_connection():
    """测试vLLM服务器连接"""
    print("=" * 60)
    print("测试 Fara-7B vLLM服务器连接")
    print("=" * 60)

    try:
        client = FaraConfig.create_client()

        # 简单查询测试
        test_prompt = "Hello, please respond with 'Fara-7B is ready'."

        print(f"发送测试请求: {test_prompt}")

        result = client.inference({
            "query": [{"role": "user", "content": test_prompt}],
            "stream": False,
            "max_new_tokens": 50
        })

        if result and "output" in result:
            print(f"✓ 连接测试通过")
            print(f"模型响应: {result['output']}")
            return True
        else:
            print("✗ 无响应或响应格式错误")
            return False

    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False


def test_performance():
    """测试性能"""
    print("\n" + "=" * 60)
    print("性能测试")
    print("=" * 60)

    client = FaraConfig.create_client()

    prompts = [
        "What is artificial intelligence?",
        "Explain machine learning in simple terms.",
        "What are the benefits of local AI models?"
    ]

    for i, prompt in enumerate(prompts, 1):
        start_time = time.time()

        result = client.inference({
            "query": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_new_tokens": 100
        })

        elapsed = time.time() - start_time

        if result and "output" in result:
            response = result["output"][:50] + "..." if len(result["output"]) > 50 else result["output"]
            print(f"查询 {i}: {elapsed:.2f}秒 - {response}")
        else:
            print(f"查询 {i}: 失败")


def main():
    """主测试函数"""
    print("Fara-7B集成测试开始...")

    # 测试1: 连接测试
    if not test_connection():
        print("\n✗ 连接测试失败，请检查vLLM服务器")
        return 1

    # 测试2: 性能测试
    test_performance()

    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## 7. 故障排除

### 7.1 常见问题及解决方案

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| **vLLM启动失败** | 内存不足 | 使用`--tensor-parallel-size 1`，降低`--gpu-memory-utilization` |
| **连接被拒绝** | 服务器未启动 | 检查端口占用：`netstat -tlnp | grep 5000` |
| **模型未找到** | HuggingFace缓存问题 | 手动下载：`huggingface-cli download microsoft/Fara-7B` |
| **GPU内存不足** | 其他进程占用 | 检查`nvidia-smi`，关闭不必要的GPU进程 |
| **API响应慢** | 首次加载或配置问题 | 使用`--enforce-eager`启用兼容模式 |

### 7.2 日志分析
```bash
# 查看vLLM日志
tail -f /media/hzm/data_disk/fara/vllm_server_*.log

# 关键日志信息
# ✓ 成功加载: "Model loaded successfully"
# ✓ API就绪: "Uvicorn running on http://0.0.0.0:5000"
# ✗ 内存不足: "CUDA out of memory"
# ✗ 模型错误: "Failed to load model"
```

### 7.3 性能优化建议
1. **首次加载**：模型首次加载需要2-5分钟，属正常现象
2. **批处理**：vLLM支持批处理，可提高吞吐量
3. **量化**：如需更低内存，考虑使用GGUF量化版本
4. **缓存**：vLLM内置KV缓存优化

---

## 8. 扩展建议

### 8.1 高级配置
```bash
# 高级启动参数（适用于生产环境）
vllm serve "microsoft/Fara-7B" \
  --port 5000 \
  --dtype half \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.95 \
  --max-model-len 8192 \
  --enforce-eager \
  --served-model-name "Fara-7B" \
  --api-key "optional-key" \
  --quantization awq \  # 可选量化
  --disable-custom-all-reduce
```

### 8.2 监控方案
1. **Prometheus监控**：vLLM提供Prometheus指标端点
2. **日志聚合**：使用ELK或Loki收集日志
3. **健康检查**：定期API健康检查脚本
4. **自动重启**：使用systemd或supervisor监控进程

### 8.3 安全建议
1. **防火墙**：限制访问IP，仅允许本地或内部网络
2. **API密钥**：生产环境建议启用API密钥验证
3. **速率限制**：配置Nginx或vLLM内置限流
4. **TLS加密**：生产环境启用HTTPS

---

## 附录

### A. 文件清单
| 文件路径 | 用途 | 状态 |
|----------|------|------|
| `docs/fara_model_service_config_v1.0_20260303_AI.md` | 配置方案文档 | 本文档 |
| `start_fara_server.sh` | vLLM启动脚本 | 待创建 |
| `agents/config_fara.py` | 配置模块 | 待创建 |
| `test_fara_integration.py` | 集成测试 | 待创建 |

### B. 命令参考
```bash
# 快速启动
cd /media/hzm/data_disk/fara
source .venv/bin/activate
vllm serve "microsoft/Fara-7B" --port 5000 --dtype auto

# 快速测试
curl http://127.0.0.1:5000/v1/models
python test_fara_integration.py

# 清理重启
pkill -f "vllm serve"
# 然后重新启动
```

### C. 资源链接
1. [Fara-7B HuggingFace页面](https://huggingface.co/microsoft/Fara-7B)
2. [vLLM官方文档](https://docs.vllm.ai/en/latest/)
3. [EmbodiedAgentsSys文档](https://automatika-robotics.github.io/embodied-agents/)
4. [OpenAI兼容API规范](https://platform.openai.com/docs/api-reference)

---

**文档版本历史**
- v1.0 (2026-03-03): 初始版本，完整配置方案

**下一步行动**
1. 创建配置脚本和测试文件
2. 启动vLLM服务器并验证
3. 集成测试和性能优化