"""测试 Skill frontmatter 的 requires/eap 字段解析和可用性检查。"""
import os
import sys
import shutil
import textwrap
import importlib.util
from pathlib import Path
import pytest

# 直接加载模块文件，绕过 agents/__init__.py 对 sugarcoat 的强制检查
_ADAPTER_PATH = Path(__file__).parent.parent / "agents" / "skills" / "md_skill_adapter.py"
_spec = importlib.util.spec_from_file_location("md_skill_adapter", _ADAPTER_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore

MDSkillConfig = _mod.MDSkillConfig
MDSkillManager = _mod.MDSkillManager
SKILLMDParser = _mod.SKILLMDParser


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def make_skill_md(name: str, extra_frontmatter: str = "") -> str:
    """生成包含 frontmatter 的 skill MD 内容。"""
    extra = textwrap.dedent(extra_frontmatter).strip()
    extra_block = f"\n{extra}" if extra else ""
    return (
        f"---\n"
        f"name: {name}\n"
        f"description: \"test skill\""
        f"{extra_block}\n"
        f"---\n\n"
        f"# {name}\n\n"
        f"Test skill body.\n"
    )


def write_skill_dir(base: Path, skill_name: str, extra_frontmatter: str = "") -> Path:
    """在 base 目录下创建一个以 skill_name 命名的子目录，并写入 SKILL.md。"""
    skill_dir = base / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = make_skill_md(skill_name, extra_frontmatter)
    (skill_dir / "SKILL.md").write_text(content)
    return skill_dir


# ---------------------------------------------------------------------------
# 测试：requires.bins 解析
# ---------------------------------------------------------------------------

def test_parse_requires_bins(tmp_path):
    """验证 requires.bins 解析。"""
    extra = "requires:\n  bins: [lerobot, ffmpeg]"
    skill_dir = write_skill_dir(tmp_path, "test_skill", extra)

    parser = SKILLMDParser()
    config = parser.parse(str(skill_dir))

    assert config.requires_bins == ["lerobot", "ffmpeg"]
    assert config.requires_env == []


def test_parse_requires_env(tmp_path):
    """验证 requires.env 解析。"""
    extra = "requires:\n  env: [LEROBOT_HOST, ROBOT_TOKEN]"
    skill_dir = write_skill_dir(tmp_path, "test_env_skill", extra)

    parser = SKILLMDParser()
    config = parser.parse(str(skill_dir))

    assert config.requires_env == ["LEROBOT_HOST", "ROBOT_TOKEN"]
    assert config.requires_bins == []


def test_parse_always_field(tmp_path):
    """验证 always 字段解析。"""
    extra = "always: true"
    skill_dir = write_skill_dir(tmp_path, "core_skill", extra)

    parser = SKILLMDParser()
    config = parser.parse(str(skill_dir))

    assert config.always is True


def test_parse_always_default(tmp_path):
    """无 always 字段时默认 False。"""
    skill_dir = write_skill_dir(tmp_path, "no_always_skill")

    parser = SKILLMDParser()
    config = parser.parse(str(skill_dir))

    assert config.always is False


# ---------------------------------------------------------------------------
# 测试：eap 字段解析
# ---------------------------------------------------------------------------

def test_parse_eap_toplevel(tmp_path):
    """验证顶层 eap.has_reverse + eap.reverse_skill 解析。"""
    extra = textwrap.dedent("""\
        eap:
          has_reverse: true
          reverse_skill: "manipulation.reverse_grasp"
        """)
    skill_dir = write_skill_dir(tmp_path, "grasp_skill", extra)

    parser = SKILLMDParser()
    config = parser.parse(str(skill_dir))

    assert config.eap_has_reverse is True
    assert config.eap_reverse_skill == "manipulation.reverse_grasp"


def test_parse_eap_nested_in_metadata(tmp_path):
    """验证 metadata.eap 嵌套格式解析。"""
    extra = textwrap.dedent("""\
        metadata:
          eap:
            has_reverse: true
            reverse_skill: "manipulation.reverse_grasp"
        """)
    skill_dir = write_skill_dir(tmp_path, "grasp_skill2", extra)

    parser = SKILLMDParser()
    config = parser.parse(str(skill_dir))

    assert config.eap_has_reverse is True
    assert config.eap_reverse_skill == "manipulation.reverse_grasp"


# ---------------------------------------------------------------------------
# 测试：向后兼容（无 requires / eap）
# ---------------------------------------------------------------------------

def test_backward_compat_no_requires(tmp_path):
    """无 requires 字段的旧 skill：requires_bins/env 均为空列表。"""
    skill_dir = write_skill_dir(tmp_path, "legacy_skill")

    parser = SKILLMDParser()
    config = parser.parse(str(skill_dir))

    assert config.requires_bins == []
    assert config.requires_env == []
    assert config.eap_has_reverse is False
    assert config.eap_reverse_skill == ""


# ---------------------------------------------------------------------------
# 测试：check_availability
# ---------------------------------------------------------------------------

def test_check_availability_no_deps(tmp_path):
    """无依赖的 skill 始终 available=True。"""
    skill_dir = write_skill_dir(tmp_path, "nodep_skill")

    manager = MDSkillManager(skills_base_dir=str(tmp_path))
    manager.load_config("nodep_skill")

    available, missing = manager.check_availability("nodep_skill")
    assert available is True
    assert missing == []


def test_check_availability_bin_present(tmp_path):
    """系统中存在的 bin（使用 'python3' 保证在测试环境中存在）。"""
    extra = "requires:\n  bins: [python3]"
    write_skill_dir(tmp_path, "py_skill", extra)

    manager = MDSkillManager(skills_base_dir=str(tmp_path))
    manager.load_config("py_skill")

    available, missing = manager.check_availability("py_skill")
    assert available is True
    assert missing == []


def test_check_availability_missing_bin(tmp_path):
    """缺少 bin 时 available=False，missing_deps 包含 bin:xxx。"""
    extra = "requires:\n  bins: [__nonexistent_bin_xyz__]"
    write_skill_dir(tmp_path, "bad_bin_skill", extra)

    manager = MDSkillManager(skills_base_dir=str(tmp_path))
    manager.load_config("bad_bin_skill")

    available, missing = manager.check_availability("bad_bin_skill")
    assert available is False
    assert "bin:__nonexistent_bin_xyz__" in missing


def test_check_availability_missing_env(tmp_path, monkeypatch):
    """缺少环境变量时 available=False，missing_deps 包含 env:xxx。"""
    extra = "requires:\n  env: [__NONEXISTENT_ENV_VAR_XYZ__]"
    write_skill_dir(tmp_path, "bad_env_skill", extra)

    # 确保环境变量不存在
    monkeypatch.delenv("__NONEXISTENT_ENV_VAR_XYZ__", raising=False)

    manager = MDSkillManager(skills_base_dir=str(tmp_path))
    manager.load_config("bad_env_skill")

    available, missing = manager.check_availability("bad_env_skill")
    assert available is False
    assert "env:__NONEXISTENT_ENV_VAR_XYZ__" in missing


def test_check_availability_env_present(tmp_path, monkeypatch):
    """环境变量存在时 available=True。"""
    extra = "requires:\n  env: [MY_TEST_VAR]"
    write_skill_dir(tmp_path, "env_skill", extra)

    monkeypatch.setenv("MY_TEST_VAR", "some_value")

    manager = MDSkillManager(skills_base_dir=str(tmp_path))
    manager.load_config("env_skill")

    available, missing = manager.check_availability("env_skill")
    assert available is True
    assert missing == []


def test_check_availability_skill_not_found(tmp_path):
    """查询不存在的 skill 时返回 (False, ['skill ... not found'])。"""
    manager = MDSkillManager(skills_base_dir=str(tmp_path))

    available, missing = manager.check_availability("ghost_skill")
    assert available is False
    assert any("not found" in m for m in missing)


# ---------------------------------------------------------------------------
# 测试：discover_skills_with_availability
# ---------------------------------------------------------------------------

def test_discover_skills_with_availability(tmp_path):
    """discover_skills_with_availability 返回包含 available 的列表。"""
    write_skill_dir(tmp_path, "skill_a")
    write_skill_dir(tmp_path, "skill_b", "requires:\n  bins: [__nonexistent_bin_xyz__]")

    manager = MDSkillManager(skills_base_dir=str(tmp_path))
    # 先加载两个 skill
    manager.load_config("skill_a")
    manager.load_config("skill_b")

    results = manager.discover_skills_with_availability()

    names = {r["name"] for r in results}
    assert "skill_a" in names
    assert "skill_b" in names

    skill_a_result = next(r for r in results if r["name"] == "skill_a")
    assert skill_a_result["available"] is True
    assert skill_a_result["missing_deps"] == []

    skill_b_result = next(r for r in results if r["name"] == "skill_b")
    assert skill_b_result["available"] is False
    assert "bin:__nonexistent_bin_xyz__" in skill_b_result["missing_deps"]
