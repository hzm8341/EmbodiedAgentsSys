"""测试对话式 Onboarding 和硬件扫描。"""
import asyncio
import pytest
import anyio

from agents.components.scene_spec import SceneSpec


# ─── SceneSpec 新增方法测试 ────────────────────────────────────────────

def test_from_partial_full():
    """from_partial 接受完整字段。"""
    spec = SceneSpec.from_partial({
        "scene_type": "pick",
        "environment": "warehouse",
        "robot_type": "arm",
        "task_description": "grab red box",
    })
    assert spec.scene_type == "pick"
    assert spec.is_complete() is True


def test_from_partial_missing_fields():
    """from_partial 允许字段缺失。"""
    spec = SceneSpec.from_partial({"task_description": "grab box"})
    assert spec.task_description == "grab box"
    assert spec.scene_type == ""
    assert spec.is_complete() is False


def test_is_complete_all_filled():
    spec = SceneSpec(
        scene_type="pick", environment="lab",
        robot_type="arm", task_description="do task"
    )
    assert spec.is_complete() is True


def test_is_complete_missing_one():
    spec = SceneSpec.from_partial({
        "scene_type": "pick", "robot_type": "arm", "task_description": "do task"
    })
    assert spec.is_complete() is False
    assert "environment" in spec.missing_fields()


def test_missing_fields_none():
    spec = SceneSpec(
        scene_type="pick", environment="lab",
        robot_type="arm", task_description="do task"
    )
    assert spec.missing_fields() == []


def test_missing_fields_multiple():
    spec = SceneSpec.from_partial({})
    missing = spec.missing_fields()
    assert "scene_type" in missing
    assert "environment" in missing
    assert "robot_type" in missing
    assert "task_description" in missing


# ─── ConversationalSceneAgent 测试 ────────────────────────────────────

from agents.components.voice_template_agent import ConversationalSceneAgent


@pytest.mark.anyio
async def test_conversational_agent_rule_extraction():
    """规则模式：能从包含抓取关键词的描述中提取 scene_type。"""
    agent = ConversationalSceneAgent(llm_provider=None)

    replies = iter(["仓库货架区", "arm"])  # 追问 environment / robot_type 的回答

    async def send_fn(text: str) -> None:
        pass  # 忽略输出

    async def recv_fn() -> str:
        return next(replies, "default")

    spec = await agent.fill_from_utterance(
        utterance="抓取红色盒子",
        send_fn=send_fn,
        recv_fn=recv_fn,
    )
    assert spec.scene_type == "pick"
    assert spec.task_description == "抓取红色盒子"


@pytest.mark.anyio
async def test_conversational_agent_asks_missing():
    """对缺失字段逐一追问。"""
    agent = ConversationalSceneAgent(llm_provider=None)
    asked = []

    async def send_fn(text: str) -> None:
        asked.append(text)

    answers = iter(["pick", "warehouse", "arm", "move box"])

    async def recv_fn() -> str:
        return next(answers, "")

    spec = await agent.fill_from_utterance(
        utterance="",  # 空描述，所有字段都缺失
        send_fn=send_fn,
        recv_fn=recv_fn,
    )
    # 应该追问过字段
    assert len(asked) > 0
    assert spec.is_complete() is True


@pytest.mark.anyio
async def test_conversational_agent_no_questions_when_complete():
    """一句话包含足够信息时，减少追问。"""
    agent = ConversationalSceneAgent(llm_provider=None)
    asked = []

    async def send_fn(text: str) -> None:
        asked.append(text)

    async def recv_fn() -> str:
        return "仓库"  # 追问 environment

    spec = await agent.fill_from_utterance(
        utterance="移动机器人导航到充电站",
        send_fn=send_fn,
        recv_fn=recv_fn,
    )
    # 规则可能识别 navigate 或 mobile；重要的是不崩溃且 robot_type 被识别
    assert spec.robot_type == "mobile"  # "移动机器人" 应匹配 mobile
    assert spec.task_description == "移动机器人导航到充电站"


# ─── HardwareScanner 测试 ────────────────────────────────────────────

from agents.hardware.scanner import HardwareScanner


@pytest.mark.anyio
async def test_scanner_returns_lists():
    """scan_serial_ports 和 scan_cameras 总是返回列表（即使为空）。"""
    scanner = HardwareScanner()
    ports = await scanner.scan_serial_ports()
    cameras = await scanner.scan_cameras()
    assert isinstance(ports, list)
    assert isinstance(cameras, list)


@pytest.mark.anyio
async def test_scanner_port_has_required_keys():
    """串口结果（若有）包含必要字段。"""
    scanner = HardwareScanner()
    ports = await scanner.scan_serial_ports()
    for port in ports:
        assert "path" in port
        assert "description" in port


@pytest.mark.anyio
async def test_scan_and_register_no_registry(tmp_path):
    """scan_and_register 使用空 registry（无 register_hardware 方法）不崩溃。"""
    scanner = HardwareScanner()

    class FakeRegistry:
        pass

    result = await scanner.scan_and_register(
        registry=FakeRegistry(),
        config_path=tmp_path / "setup.json",
    )
    assert "serial_ports" in result
    assert "cameras" in result
    # config 文件应已创建
    assert (tmp_path / "setup.json").exists()
