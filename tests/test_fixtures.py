"""Tests for fixture factories and helper utilities."""
import asyncio
import pytest


class TestMockVLAFactory:
    """Tests for mock VLA factory."""

    def test_factory_returns_adapter(self):
        """Test that factory returns an adapter instance."""
        from tests.fixtures.mock_vla import make_mock_vla
        adapter = make_mock_vla()
        assert adapter is not None

    def test_factory_success_rate_param(self):
        """Test that success_rate parameter is set."""
        from tests.fixtures.mock_vla import make_mock_vla
        adapter = make_mock_vla(success_rate=1.0)
        assert adapter.success_rate == 1.0

    def test_act_returns_7dof_action(self):
        """Test that act returns a 7-DOF action."""
        from tests.fixtures.mock_vla import make_mock_vla
        adapter = make_mock_vla(action_noise=False)
        action = asyncio.run(adapter.act({"image": "test"}, "grasp"))
        assert len(action) == 7


class TestMockArmFactory:
    """Tests for mock arm adapter factory."""

    def test_factory_returns_adapter(self):
        """Test that factory returns an adapter instance."""
        from tests.fixtures.mock_arm import make_mock_arm
        arm = make_mock_arm()
        assert arm is not None

    def test_move_to_pose_returns_bool(self):
        """Test that move_to_pose returns a boolean."""
        from tests.fixtures.mock_arm import make_mock_arm
        from agents.hardware.arm_adapter import Pose6D
        arm = make_mock_arm(joint_error_rate=0.0)
        result = asyncio.run(arm.move_to_pose(Pose6D(0.3, 0, 0.2, 0, 0, 0)))
        assert result is True


class TestMockLLMProvider:
    """Tests for mock LLM provider factory."""

    def test_returns_configured_response(self):
        """Test that provider returns configured responses."""
        from tests.fixtures.mock_llm import make_mock_llm
        provider = make_mock_llm(responses=["response1", "response2"])
        result = asyncio.run(provider.chat([{"role": "user", "content": "hello"}]))
        assert result.content == "response1"

    def test_cycles_through_responses(self):
        """Test that provider cycles through responses."""
        from tests.fixtures.mock_llm import make_mock_llm
        provider = make_mock_llm(responses=["a", "b"])
        asyncio.run(provider.chat([{"role": "user", "content": "1"}]))
        r2 = asyncio.run(provider.chat([{"role": "user", "content": "2"}]))
        assert r2.content == "b"


class TestMockEventBus:
    """Tests for mock event bus."""

    def test_publish_and_subscribe(self):
        """Test publish and subscribe functionality."""
        from tests.fixtures.mock_events import MockEventBus
        bus = MockEventBus()
        received = []
        bus.subscribe("test_event", lambda e: received.append(e))
        bus.publish("test_event", {"data": 42})
        assert received == [{"data": 42}]


class TestAsyncHelpers:
    """Tests for async helper utilities."""

    def test_run_async_runs_coroutine(self):
        """Test that run_async executes a coroutine."""
        from tests.helpers.async_helpers import run_async
        async def coro():
            return 42
        assert run_async(coro()) == 42

    def test_assert_eventually_passes_when_condition_met(self):
        """Test that assert_eventually passes when condition is true."""
        from tests.helpers.async_helpers import assert_eventually
        counter = {"n": 0}
        async def condition():
            counter["n"] += 1
            return counter["n"] >= 3
        asyncio.run(assert_eventually(condition, timeout=1.0, interval=0.01))

    def test_assert_eventually_raises_on_timeout(self):
        """Test that assert_eventually raises when condition times out."""
        from tests.helpers.async_helpers import assert_eventually
        async def always_false():
            return False
        with pytest.raises(AssertionError):
            asyncio.run(assert_eventually(always_false, timeout=0.05, interval=0.01))


class TestAssertionHelpers:
    """Tests for domain-specific assertion helpers."""

    def test_assert_skill_called(self):
        """Test assert_skill_called passes for called skill."""
        from tests.helpers.assertion_helpers import assert_skill_called
        class FakeTrace:
            skill_calls = ["manipulation.grasp", "manipulation.place"]
        assert_skill_called(FakeTrace(), "manipulation.grasp")

    def test_assert_skill_called_raises_if_missing(self):
        """Test assert_skill_called raises for missing skill."""
        from tests.helpers.assertion_helpers import assert_skill_called
        class FakeTrace:
            skill_calls = []
        with pytest.raises(AssertionError):
            assert_skill_called(FakeTrace(), "manipulation.grasp")

    def test_assert_no_abort(self):
        """Test assert_no_abort passes when not aborted."""
        from tests.helpers.assertion_helpers import assert_no_abort
        class FakeTrace:
            failure_reason = None
            final_status = "completed"
        assert_no_abort(FakeTrace())

    def test_assert_no_abort_raises_on_abort(self):
        """Test assert_no_abort raises when aborted."""
        from tests.helpers.assertion_helpers import assert_no_abort
        class FakeTrace:
            failure_reason = "user cancelled"
            final_status = "aborted"
        with pytest.raises(AssertionError):
            assert_no_abort(FakeTrace())
