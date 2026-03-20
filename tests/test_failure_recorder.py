# tests/test_failure_recorder.py
import pytest
import json
from pathlib import Path
from agents.data.failure_recorder import FailureDataRecorder, FailureRecord
from agents.components.scene_spec import SceneSpec

SCENE = SceneSpec(
    scene_type="warehouse_pick",
    environment="Warehouse",
    robot_type="arm",
    task_description="Pick red box",
)

PLAN_YAML = "plan_id: test-123\nstatus: failed\nsteps: []"


@pytest.fixture
def recorder(tmp_path):
    return FailureDataRecorder(base_dir=str(tmp_path / "failures"), max_size_gb=1.0)


@pytest.mark.anyio
async def test_record_creates_directory(recorder, tmp_path):
    record = FailureRecord(
        scene_spec=SCENE,
        plan_yaml=PLAN_YAML,
        failed_step_id="2",
        error_type="hard_gap",
    )
    path = await recorder.record(record)
    assert Path(path).exists()


@pytest.mark.anyio
async def test_record_saves_metadata_json(recorder, tmp_path):
    record = FailureRecord(
        scene_spec=SCENE,
        plan_yaml=PLAN_YAML,
        failed_step_id="2",
        error_type="hard_gap",
        notes="Test failure",
    )
    path = await recorder.record(record)
    meta_file = Path(path) / "metadata.json"
    assert meta_file.exists()
    meta = json.loads(meta_file.read_text())
    assert meta["error_type"] == "hard_gap"
    assert meta["failed_step_id"] == "2"


@pytest.mark.anyio
async def test_record_saves_plan_yaml(recorder):
    record = FailureRecord(
        scene_spec=SCENE,
        plan_yaml=PLAN_YAML,
        failed_step_id="1",
        error_type="execution_error",
    )
    path = await recorder.record(record)
    plan_file = Path(path) / "plan.yaml"
    assert plan_file.exists()
    assert "test-123" in plan_file.read_text()


@pytest.mark.anyio
async def test_record_saves_scene_spec_yaml(recorder):
    record = FailureRecord(
        scene_spec=SCENE,
        plan_yaml=PLAN_YAML,
        failed_step_id="1",
        error_type="execution_error",
    )
    path = await recorder.record(record)
    spec_file = Path(path) / "scene_spec.yaml"
    assert spec_file.exists()
    assert "warehouse_pick" in spec_file.read_text()


def test_list_records_empty(recorder):
    records = recorder.list_records()
    assert records == []


@pytest.mark.anyio
async def test_list_records_after_record(recorder):
    record = FailureRecord(
        scene_spec=SCENE,
        plan_yaml=PLAN_YAML,
        failed_step_id="1",
        error_type="hard_gap",
    )
    await recorder.record(record)
    records = recorder.list_records()
    assert len(records) == 1
