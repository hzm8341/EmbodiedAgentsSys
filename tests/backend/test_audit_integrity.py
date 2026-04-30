from backend.services.trace_store import TraceStore


def test_trace_store_persists_operator_identity(tmp_path):
    store = TraceStore(root_dir=str(tmp_path))
    trace_id = "trace_audit_1"

    store.append_event(trace_id, {"type": "task_start", "payload": {"task": "x"}}, operator="operator:127.0.0.1")
    store.append_result(
        trace_id,
        task="x",
        result={"success": True},
        operator="operator:127.0.0.1",
    )

    trace = store.get_trace(trace_id)
    assert trace is not None
    assert trace["operator"] == "operator:127.0.0.1"
    assert trace["events"][0]["operator"] == "operator:127.0.0.1"

