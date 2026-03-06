"""
Fara-7B模型配置模块
为EmbodiedAgentsSys提供Fara-7B本地vLLM服务配置

版本: v1.0
日期: 2026-03-03
作者: Claude AI

使用说明:
1. 确保vLLM服务器正在运行 (端口5000)
2. 导入本模块: from agents.config_fara import FaraConfig
3. 创建客户端: client = FaraConfig.create_client()
4. 使用客户端进行推理

示例:
    >>> from agents.config_fara import FaraConfig
    >>> client = FaraConfig.create_client()
    >>> result = client.inference({
    ...     "query": [{"role": "user", "content": "Hello!"}],
    ...     "stream": False
    ... })
    >>> print(result["output"])
"""

from typing import Dict, Any, Optional, Union
import logging

from agents.clients.generic import GenericHTTPClient
from agents.models import GenericLLM, TransformersLLM
from agents.config import LLMConfig

# 设置日志
logger = logging.getLogger(__name__)


class FaraConfig:
    """
    Fara-7B配置类

    提供创建Fara-7B模型配置、客户端和LLM配置的方法。
    """

    # 默认配置
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 5000
    DEFAULT_MODEL_NAME = "fara-7b"
    DEFAULT_CHECKPOINT = "Fara-7B"
    DEFAULT_TIMEOUT = 60

    @staticmethod
    def create_model_config(
        name: str = DEFAULT_MODEL_NAME,
        checkpoint: str = DEFAULT_CHECKPOINT,
        temperature: float = 0.7,
        max_new_tokens: int = 500,
        stream: bool = False,
        **kwargs
    ) -> GenericLLM:
        """
        创建Fara-7B模型配置

        参数:
            name: 模型名称(自定义)
            checkpoint: 模型检查点名称(在vLLM中注册的名称)
            temperature: 温度参数，控制生成随机性
            max_new_tokens: 最大生成token数
            stream: 是否启用流式输出
            **kwargs: 其他模型参数

        返回:
            GenericLLM: 配置好的模型实例
        """
        logger.info(f"创建Fara-7B模型配置: name={name}, checkpoint={checkpoint}")

        # 基础选项
        options = {
            "temperature": temperature,
            "max_new_tokens": max_new_tokens,
            "stream": stream,
        }

        # 添加额外选项
        if kwargs:
            options.update(kwargs)

        return GenericLLM(
            name=name,
            checkpoint=checkpoint,
            options=options
        )

    @staticmethod
    def create_client(
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        inference_timeout: int = DEFAULT_TIMEOUT,
        api_key: str = "",
        logging_level: str = "info",
        **model_kwargs
    ) -> GenericHTTPClient:
        """
        创建Fara-7B客户端

        参数:
            host: vLLM服务器主机地址
            port: vLLM服务器端口
            inference_timeout: 推理超时时间(秒)
            api_key: API密钥(vLLM通常不需要)
            logging_level: 日志级别
            **model_kwargs: 传递给create_model_config的参数

        返回:
            GenericHTTPClient: 配置好的客户端实例
        """
        logger.info(f"创建Fara-7B客户端: {host}:{port}, timeout={inference_timeout}s")

        # 创建模型配置
        model = FaraConfig.create_model_config(**model_kwargs)

        # 创建客户端
        client = GenericHTTPClient(
            model=model,
            host=host,
            port=port,
            api_key=api_key,  # vLLM通常不需要API密钥
            inference_timeout=inference_timeout,
            logging_level=logging_level
        )

        return client

    @staticmethod
    def create_llm_config(
        enable_rag: bool = False,
        collection_name: Optional[str] = None,
        chat_history: bool = True,
        history_size: int = 10,
        temperature: float = 0.7,
        max_new_tokens: int = 500,
        stream: bool = False,
        **llm_kwargs
    ) -> LLMConfig:
        """
        创建完整的LLM配置

        参数:
            enable_rag: 是否启用检索增强生成
            collection_name: RAG集合名称
            chat_history: 是否启用聊天历史
            history_size: 历史消息数量
            temperature: 温度参数
            max_new_tokens: 最大生成token数
            stream: 是否启用流式输出
            **llm_kwargs: 其他LLM配置参数

        返回:
            LLMConfig: 完整的LLM配置
        """
        logger.info(f"创建LLM配置: enable_rag={enable_rag}, chat_history={chat_history}")

        return LLMConfig(
            enable_rag=enable_rag,
            collection_name=collection_name,
            distance_func="l2" if enable_rag else None,
            n_results=3 if enable_rag else 1,
            chat_history=chat_history,
            history_size=history_size,
            history_reset_phrase="chat reset",
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            stream=stream,
            break_character="." if stream else "",
            response_terminator="<<Response Ended>>" if stream else "",
            **llm_kwargs
        )

    @staticmethod
    def create_quick_client(
        temperature: float = 0.7,
        max_new_tokens: int = 500,
        **kwargs
    ) -> GenericHTTPClient:
        """
        快速创建客户端(使用默认配置)

        参数:
            temperature: 温度参数
            max_new_tokens: 最大生成token数
            **kwargs: 其他客户端参数

        返回:
            GenericHTTPClient: 配置好的客户端
        """
        return FaraConfig.create_client(
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            **kwargs
        )


class FaraDemo:
    """
    Fara-7B演示类

    提供演示和测试功能。
    """

    def __init__(self, client: Optional[GenericHTTPClient] = None):
        """
        初始化演示类

        参数:
            client: 可选的客户端实例，如果为None则创建新客户端
        """
        self.client = client or FaraConfig.create_client()
        logger.info("FaraDemo初始化完成")

    def test_connection(self) -> bool:
        """
        测试与vLLM服务器的连接

        返回:
            bool: 连接是否成功
        """
        logger.info("测试vLLM服务器连接...")

        try:
            # 简单测试查询
            test_query = {
                "query": [
                    {
                        "role": "user",
                        "content": "Hello! Please respond with 'Fara-7B is ready'."
                    }
                ],
                "stream": False,
                "max_new_tokens": 50
            }

            result = self.client.inference(test_query)

            if result and "output" in result:
                logger.info(f"连接测试成功: {result['output'][:50]}...")
                return True
            else:
                logger.warning("连接测试失败: 无响应或响应格式错误")
                return False

        except Exception as e:
            logger.error(f"连接测试异常: {e}")
            return False

    def simple_query(self, prompt: str, **kwargs) -> Optional[str]:
        """
        简单查询

        参数:
            prompt: 用户提示
            **kwargs: 推理参数

        返回:
            Optional[str]: 模型响应，失败时返回None
        """
        logger.info(f"发送查询: {prompt[:50]}...")

        try:
            query = {
                "query": [{"role": "user", "content": prompt}],
                "stream": False,
                "max_new_tokens": kwargs.get("max_new_tokens", 500)
            }

            # 合并其他参数
            if "temperature" in kwargs:
                query["temperature"] = kwargs["temperature"]

            result = self.client.inference(query)

            if result and "output" in result:
                logger.info(f"查询成功，响应长度: {len(result['output'])}")
                return result["output"]
            else:
                logger.warning("查询失败: 无响应")
                return None

        except Exception as e:
            logger.error(f"查询异常: {e}")
            return None

    def conversation_demo(self, max_turns: int = 3):
        """
        对话演示

        参数:
            max_turns: 最大对话轮次
        """
        print("=" * 60)
        print("Fara-7B 对话演示")
        print("=" * 60)
        print("输入 'quit' 或 'exit' 退出")
        print()

        turns = 0
        while turns < max_turns:
            # 获取用户输入
            user_input = input(f"[Turn {turns + 1}] 你: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("退出对话")
                break

            if not user_input:
                print("输入不能为空")
                continue

            # 发送查询
            print("Fara-7B 正在思考...")
            response = self.simple_query(user_input)

            if response:
                print(f"[Turn {turns + 1}] Fara-7B: {response}")
            else:
                print(f"[Turn {turns + 1}] Fara-7B: 抱歉，我无法处理这个请求")

            turns += 1
            print()

        print("=" * 60)
        print(f"对话结束，共 {turns} 轮")
        print("=" * 60)


# 快捷函数
def create_fara_client(**kwargs) -> GenericHTTPClient:
    """快捷函数：创建Fara-7B客户端"""
    return FaraConfig.create_client(**kwargs)


def create_fara_llm_config(**kwargs) -> LLMConfig:
    """快捷函数：创建LLM配置"""
    return FaraConfig.create_llm_config(**kwargs)


def test_fara_service(host: str = "127.0.0.1", port: int = 5000) -> bool:
    """
    测试Fara-7B服务

    参数:
        host: 服务器地址
        port: 服务器端口

    返回:
        bool: 服务是否可用
    """
    try:
        client = FaraConfig.create_client(host=host, port=port)
        demo = FaraDemo(client)
        return demo.test_connection()
    except Exception as e:
        logger.error(f"服务测试失败: {e}")
        return False


# 导出
__all__ = [
    "FaraConfig",
    "FaraDemo",
    "create_fara_client",
    "create_fara_llm_config",
    "test_fara_service"
]


if __name__ == "__main__":
    """
    模块测试
    直接运行此模块进行基本测试
    """
    import sys

    print("测试 Fara-7B 配置模块")
    print("=" * 60)

    # 创建客户端
    try:
        client = create_fara_client()
        print("✓ 客户端创建成功")
    except Exception as e:
        print(f"✗ 客户端创建失败: {e}")
        sys.exit(1)

    # 测试连接
    demo = FaraDemo(client)
    if demo.test_connection():
        print("✓ 服务器连接测试成功")
    else:
        print("✗ 服务器连接测试失败")
        print("请确保vLLM服务器正在运行:")
        print("  ./start_fara_server.sh")
        sys.exit(1)

    # 简单查询测试
    test_response = demo.simple_query("What is artificial intelligence in one sentence?")
    if test_response:
        print(f"✓ 简单查询测试成功")
        print(f"  响应示例: {test_response[:100]}...")
    else:
        print("✗ 简单查询测试失败")

    print("=" * 60)
    print("模块测试完成")
    print("=" * 60)