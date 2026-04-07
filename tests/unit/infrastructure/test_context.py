import asyncio
import pytest
from agents.context.budget import ContextBudget, BudgetStatus
from agents.context.compressor import MicroCompressor


class TestContextBudget:
    def _make_messages(self, n_tokens_approx: int) -> list[dict]:
        content = "x" * (n_tokens_approx * 4)
        return [{"role": "user", "content": content}]

    def test_ok_when_below_warning(self):
        budget = ContextBudget(max_tokens=1000)
        msgs = self._make_messages(700)
        assert budget.check_budget(msgs) == BudgetStatus.OK

    def test_warning_at_80_percent(self):
        budget = ContextBudget(max_tokens=1000)
        msgs = self._make_messages(820)
        assert budget.check_budget(msgs) == BudgetStatus.WARNING

    def test_critical_at_95_percent(self):
        budget = ContextBudget(max_tokens=1000)
        msgs = self._make_messages(960)
        assert budget.check_budget(msgs) == BudgetStatus.CRITICAL

    def test_estimate_tokens_is_positive(self):
        budget = ContextBudget()
        msgs = [{"role": "user", "content": "hello world"}]
        assert budget.estimate_tokens(msgs) > 0

    def test_should_warn_true_when_warning(self):
        budget = ContextBudget(max_tokens=1000)
        msgs = self._make_messages(820)
        assert budget.should_warn(msgs) is True

    def test_should_compress_true_when_critical(self):
        budget = ContextBudget(max_tokens=1000)
        msgs = self._make_messages(960)
        assert budget.should_compress(msgs) is True


class TestMicroCompressor:
    def test_truncate_long_content(self):
        compressor = MicroCompressor()
        msg = {"role": "user", "content": "x" * 5000}
        result = compressor.truncate_long_content(msg, max_chars=100)
        assert len(result["content"]) <= 120

    def test_short_content_unchanged(self):
        compressor = MicroCompressor()
        msg = {"role": "user", "content": "hello"}
        result = compressor.truncate_long_content(msg, max_chars=1000)
        assert result["content"] == "hello"

    def test_strip_images_removes_image_content(self):
        compressor = MicroCompressor()
        msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": "describe this"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
            ],
        }
        result = compressor.strip_images(msg)
        content = result["content"]
        if isinstance(content, list):
            assert all(item.get("type") != "image_url" for item in content)

    def test_compress_message_combines_strategies(self):
        compressor = MicroCompressor()
        msg = {"role": "user", "content": "x" * 10000}
        result = compressor.compress_message(msg)
        assert len(result["content"]) < len(msg["content"])


class TestContextManager:
    def _make_small_msgs(self):
        return [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]

    def _make_large_msgs(self, n_tokens=96000):
        content = "x" * (n_tokens * 4)
        return [{"role": "user", "content": content}]

    def test_process_small_returns_unchanged(self):
        from agents.context.manager import ContextManager
        mgr = ContextManager(max_tokens=100_000)
        msgs = self._make_small_msgs()
        result = asyncio.run(mgr.process(msgs))
        assert result == msgs

    def test_process_critical_compresses(self):
        from agents.context.manager import ContextManager
        mgr = ContextManager(max_tokens=100_000)
        msgs = self._make_large_msgs(n_tokens=96000)
        result = asyncio.run(mgr.process(msgs))
        original_len = sum(len(m.get("content", "")) for m in msgs)
        result_len = sum(len(m.get("content", "")) for m in result)
        assert result_len < original_len

    def test_get_status_returns_budget_status(self):
        from agents.context.manager import ContextManager
        from agents.context.budget import BudgetStatus
        mgr = ContextManager(max_tokens=100_000)
        msgs = self._make_small_msgs()
        status = mgr.get_status(msgs)
        assert status == BudgetStatus.OK
