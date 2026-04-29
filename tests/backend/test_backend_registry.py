import pytest

from backend.backends.base import BackendDescriptor
from backend.backends.mujoco_backend import MujocoBackend
from backend.services.backend_registry import BackendRegistry


def test_list_backends_returns_registered_descriptors():
    registry = BackendRegistry()
    backend = MujocoBackend()

    registry.register(backend)

    backends = registry.list_backends()

    assert len(backends) == 1
    assert isinstance(backends[0], BackendDescriptor)
    assert backends[0].backend_id == "mujoco"
    assert backends[0].display_name == "MuJoCo"


def test_select_backend_tracks_selected_backend():
    registry = BackendRegistry()
    backend = MujocoBackend()
    registry.register(backend)

    selected = registry.select_backend("mujoco")

    assert selected is backend
    assert registry.get_selected_backend() is backend


def test_register_auto_selects_first_backend():
    registry = BackendRegistry()
    backend = MujocoBackend()

    registry.register(backend)

    assert registry.get_selected_backend() is backend


def test_select_backend_rejects_unknown_backend():
    registry = BackendRegistry()

    with pytest.raises(KeyError):
        registry.select_backend("unknown")


def test_get_selected_backend_raises_when_uninitialized():
    registry = BackendRegistry()

    with pytest.raises(RuntimeError):
        registry.get_selected_backend()


def test_descriptor_metadata_is_not_shared_for_mutation():
    first = MujocoBackend().descriptor
    second = MujocoBackend().descriptor

    with pytest.raises(AttributeError):
        first.capabilities.append("extra")

    with pytest.raises(TypeError):
        first.extensions["extra"] = "value"

    assert second.capabilities == ("scene", "state", "command")
    assert "extra" not in second.extensions


def test_backend_descriptor_normalizes_mutable_metadata_inputs():
    descriptor = BackendDescriptor(
        backend_id="test",
        display_name="Test",
        kind="simulation",
        capabilities=["scene", "state"],
        extensions={"config": {"enabled": True}},
    )

    assert descriptor.capabilities == ("scene", "state")
    assert isinstance(descriptor.capabilities, tuple)
    assert descriptor.extensions["config"] == {"enabled": True}

    with pytest.raises(AttributeError):
        descriptor.capabilities.append("command")

    with pytest.raises(TypeError):
        descriptor.extensions["extra"] = "value"


def test_backend_descriptor_deep_freezes_nested_extension_metadata():
    descriptor = BackendDescriptor(
        backend_id="test",
        display_name="Test",
        kind="simulation",
        extensions={
            "config": {
                "flags": ["scene", "state"],
                "limits": {"max_steps": 3},
            }
        },
    )

    config = descriptor.extensions["config"]

    with pytest.raises(TypeError):
        config["limits"]["max_steps"] = 4

    with pytest.raises(AttributeError):
        config["flags"].append("command")


def test_duplicate_backend_registration_is_rejected():
    registry = BackendRegistry()

    registry.register(MujocoBackend())

    with pytest.raises(ValueError):
        registry.register(MujocoBackend())
