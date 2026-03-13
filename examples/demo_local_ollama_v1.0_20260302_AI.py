"""
Demo配置: 使用本地Ollama服务

使用说明:
1. 确保Ollama服务正在运行: ollama serve
2. 确保模型已下载: ollama pull qwen2.5vl:latest
3. 运行此脚本: python examples/demo_local_ollama.py
"""

from agents.clients.ollama import OllamaClient
from agents.models import OllamaModel

# ============================================================
# Ollama连接配置
# ============================================================
OLLAMA_HOST = "127.0.0.1"  # Ollama服务地址
OLLAMA_PORT = 11434  # Ollama服务端口

# 模型配置 - 使用qwen3.5:9b (纯文本模型)
MODEL_CONFIG = {
    "name": "qwen_vl",  # 模型名称(自定义)
    "checkpoint": "qwen3.5:9b",  # Ollama模型名称
    "options": {
        "temperature": 0.7,
        "num_predict": 500,
    },
}


# ============================================================
# 创建Ollama客户端
# ============================================================
def create_ollama_client():
    """创建连接到本地Ollama服务的客户端"""

    # 创建模型配置
    model = OllamaModel(
        name=MODEL_CONFIG["name"],
        checkpoint=MODEL_CONFIG["checkpoint"],
        options=MODEL_CONFIG.get("options"),
    )

    # 创建客户端
    client = OllamaClient(
        model=model,
        host=OLLAMA_HOST,
        port=OLLAMA_PORT,
        inference_timeout=120,  # 推理超时时间(秒)
    )

    return client


# ============================================================
# 测试连接
# ============================================================
def test_connection(client):
    """测试Ollama连接是否正常"""
    print(f"正在连接到 Ollama服务 ({OLLAMA_HOST}:{OLLAMA_PORT})...")
    print(f"使用模型: {MODEL_CONFIG['checkpoint']}")

    # 简单测试 - 发送一个基础问题
    test_query = {
        "query": [
            {
                "role": "user",
                "content": "Hello! Please respond with 'OK' if you can hear me.",
            }
        ],
        "stream": False,
        "max_new_tokens": 50,
    }

    result = client.inference(test_query)

    if result and result.get("output"):
        print(f"✓ 连接成功!")
        print(f"模型响应: {result['output']}")
        return True
    else:
        print("✗ 连接失败或无响应")
        return False


# ============================================================
# 主函数 - 创建完整Demo
# ============================================================
def create_demo():
    """
    创建一个完整的Demo，展示如何使用Ollama

    这个Demo创建了一个简单的LLM组件，可以:
    - 接收文本输入
    - 使用Ollama模型处理
    - 输出文本响应
    """

    print("=" * 60)
    print("EmbodiedAgents + Ollama Demo")
    print("=" * 60)

    # 创建客户端
    client = create_ollama_client()

    # 测试连接
    if not test_connection(client):
        print("\n请确保:")
        print("1. Ollama服务正在运行: ollama serve")
        print("2. 模型已下载: ollama pull qwen2.5vl:latest")
        return None

    print("\n" + "=" * 60)
    print("Demo配置完成!")
    print("=" * 60)

    # 返回客户端，供后续使用
    return client


# ============================================================
# 以下是完整的Agent组件示例代码
# (取消注释即可使用)
# ============================================================
"""
# 完整的LLM组件示例:

from agents.components import LLM
from agents.ros import Topic, Launcher

# 定义输入输出Topic
llm_input = Topic(name="llm_input", msg_type="String")
llm_output = Topic(name="llm_output", msg_type="String")

# 创建LLM组件
llm_component = LLM(
    inputs=[llm_input],
    outputs=[llm_output],
    model_client=client,  # 使用上面创建的client
    trigger=llm_input,
    component_name="my_llm"
)

# 设置系统提示词
llm_component.set_component_prompt(
    template="You are a helpful robot assistant. Answer clearly and concisely."
)

# 启动Agent
launcher = Launcher()
launcher.add_pkg(components=[llm_component])
launcher.bringup()
"""

# ============================================================
# 以下是完整的VLM组件示例代码(处理图像)
# ============================================================
"""
# 完整的多模态(VLM)组件示例:

from agents.components import MLLM
from agents.ros import Topic, Launcher

# 定义输入Topic - 图像和文本
image_input = Topic(name="image_raw", msg_type="Image")
text_input = Topic(name="text_input", msg_type="String")
vlm_output = Topic(name="vlm_output", msg_type="String")

# 创建MLLM组件 (视觉语言模型)
vlm_component = MLLM(
    inputs=[text_input, image_input],
    outputs=[vlm_output],
    model_client=client,  # 使用上面创建的client
    trigger=text_input,
    component_name="my_vlm"
)

# 设置提示词模板
vlm_component.set_topic_prompt(
    text_input,
    template="You are a robot. Describe what you see in this image in detail."
)

# 启动Agent
launcher = Launcher()
launcher.add_pkg(components=[vlm_component])
launcher.bringup()
"""


if __name__ == "__main__":
    # 运行Demo
    create_demo()
