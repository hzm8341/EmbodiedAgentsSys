from pathlib import Path

from backend.api import ik as ik_api


def test_get_ik_chain_resolves_relative_urdf_from_repo_root(monkeypatch):
    monkeypatch.setattr(
        ik_api,
        "__file__",
        "/media/hzm/SSD_2T/GitHub/EmbodiedAgentsSys/.worktrees/dual-backend-platform/backend/api/ik.py",
    )
    monkeypatch.setattr(ik_api, "_ik_chain_cache", {})
    monkeypatch.setitem(
        ik_api.ROBOT_CONFIGS,
        "testbot",
        {"urdf_path": "assets/testbot.urdf", "end_effectors": {"left": "ee_link"}},
    )

    expected_urdf = Path("/media/hzm/SSD_2T/GitHub/EmbodiedAgentsSys/assets/testbot.urdf")
    seen: dict[str, str] = {}

    class FakeIKChain:
        def __init__(self, urdf_path: str, target_link: str):
            seen["urdf_path"] = urdf_path
            seen["target_link"] = target_link

    monkeypatch.setattr(ik_api, "IKChain", FakeIKChain)
    monkeypatch.setattr(ik_api.os.path, "exists", lambda path: path == str(expected_urdf))

    chain = ik_api.get_ik_chain("testbot", "ee_link")

    assert isinstance(chain, FakeIKChain)
    assert seen["urdf_path"] == str(expected_urdf)
    assert seen["target_link"] == "ee_link"
