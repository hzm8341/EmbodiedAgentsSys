"""API 路由"""
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.backends.base import BackendDescriptor
from backend.services.backend_registry import backend_registry, ensure_default_backends
from backend.services.scene_service import scene_service

router = APIRouter()

class ExecuteRequest(BaseModel):
    action: str
    params: dict[str, Any] = {}

class ExecuteResponse(BaseModel):
    status: str
    message: str
    data: dict = {}


class SelectBackendRequest(BaseModel):
    backend_id: str


class BackendCommandRequest(BaseModel):
    params: dict[str, Any] = {}


def _simulation_service():
    from backend.services.simulation import simulation_service

    return simulation_service


def _descriptor_to_dict(descriptor: BackendDescriptor) -> dict[str, Any]:
    return {
        "backend_id": descriptor.backend_id,
        "display_name": descriptor.display_name,
        "kind": descriptor.kind,
        "available": descriptor.available,
        "capabilities": list(descriptor.capabilities),
        "extensions": dict(descriptor.extensions),
    }


@router.post("/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest):
    """执行动作"""
    receipt = _simulation_service().execute_action(req.action, req.params)
    return ExecuteResponse(
        status=receipt.status.value,
        message=receipt.result_message,
        data=receipt.result_data or {}
    )


@router.get("/backends")
def list_backends():
    ensure_default_backends()
    selected_backend = backend_registry.get_selected_backend().backend_id
    return {
        "selected_backend": selected_backend,
        "backends": [_descriptor_to_dict(backend) for backend in backend_registry.list_backends()],
    }


@router.post("/backends/select")
def select_backend(req: SelectBackendRequest):
    try:
        selected = backend_registry.select_backend(req.backend_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown backend: {req.backend_id}") from exc
    return {"selected_backend": selected.backend_id}


@router.get("/backends/{backend_id}/capabilities")
def get_backend_capabilities(backend_id: str):
    try:
        backend = backend_registry.get_backend(backend_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown backend: {backend_id}") from exc
    return _descriptor_to_dict(backend.descriptor)


@router.post("/backends/{backend_id}/commands/{command}")
def execute_backend_command(backend_id: str, command: str, req: BackendCommandRequest):
    try:
        backend = backend_registry.get_backend(backend_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown backend: {backend_id}") from exc

    try:
        result = backend.execute_command(command, req.params)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return result


@router.post("/backends/{backend_id}/lifecycle/{operation}")
def backend_lifecycle(backend_id: str, operation: str):
    try:
        backend = backend_registry.get_backend(backend_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown backend: {backend_id}") from exc

    method_map = {
        "init": "initialize",
        "heartbeat": "heartbeat",
        "reconnect": "reconnect",
        "shutdown": "shutdown",
    }
    method_name = method_map.get(operation)
    if method_name is None or not hasattr(backend, method_name):
        raise HTTPException(status_code=404, detail=f"Unsupported operation: {operation}")
    method = getattr(backend, method_name)
    return method()


@router.get("/view/scene")
def get_scene_view():
    ensure_default_backends()
    selected = backend_registry.get_selected_backend()
    return scene_service.build_snapshot(selected)


@router.get("/scene")
def get_scene():
    """获取场景状态"""
    return _simulation_service().get_scene()

@router.post("/reset")
def reset():
    """重置环境"""
    return _simulation_service().reset()
