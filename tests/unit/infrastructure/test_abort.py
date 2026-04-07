import asyncio
import pytest
from agents.abort import AbortController, AbortScope
from agents.exceptions import AbortError


class TestAbortController:
    def test_not_aborted_by_default(self):
        ctrl = AbortController()
        assert ctrl.is_aborted is False
        assert ctrl.abort_reason is None

    def test_abort_sets_flag(self):
        ctrl = AbortController()
        ctrl.abort("user cancelled")
        assert ctrl.is_aborted is True
        assert ctrl.abort_reason == "user cancelled"

    def test_abort_is_idempotent(self):
        ctrl = AbortController()
        ctrl.abort("first")
        ctrl.abort("second")
        assert ctrl.abort_reason == "first"

    def test_child_aborted_when_parent_aborts(self):
        parent = AbortController()
        child = parent.create_child()
        parent.abort("parent gone")
        assert child.is_aborted is True
        assert child.abort_reason == "parent gone"

    def test_parent_not_aborted_when_child_aborts(self):
        parent = AbortController()
        child = parent.create_child()
        child.abort("child only")
        assert parent.is_aborted is False

    def test_grandchild_cascade(self):
        root = AbortController()
        mid = root.create_child()
        leaf = mid.create_child()
        root.abort("root gone")
        assert leaf.is_aborted is True

    def test_done_callback_called_on_abort(self):
        called = []
        ctrl = AbortController()
        ctrl.add_done_callback(lambda: called.append(1))
        ctrl.abort()
        assert called == [1]

    def test_done_callback_not_called_without_abort(self):
        called = []
        ctrl = AbortController()
        ctrl.add_done_callback(lambda: called.append(1))
        assert called == []

    def test_signal_is_read_only_view(self):
        ctrl = AbortController()
        signal = ctrl.signal
        assert signal.is_aborted is False
        ctrl.abort("test")
        assert signal.is_aborted is True


class TestAbortScope:
    def test_normal_exit_does_not_raise(self):
        ctrl = AbortController()
        async def run():
            async with AbortScope(ctrl):
                pass
        asyncio.run(run())

    def test_aborted_inside_scope_raises_abort_error(self):
        ctrl = AbortController()
        async def run():
            async with AbortScope(ctrl):
                ctrl.abort("cancelled inside")
        with pytest.raises(AbortError):
            asyncio.run(run())

    def test_context_manager_yields_controller(self):
        ctrl = AbortController()
        async def run():
            async with AbortScope(ctrl) as c:
                assert c is ctrl
        asyncio.run(run())

    def test_nested_scopes(self):
        root = AbortController()
        child = root.create_child()
        async def run():
            async with AbortScope(root):
                async with AbortScope(child):
                    root.abort("root cancelled")
        with pytest.raises(AbortError):
            asyncio.run(run())
