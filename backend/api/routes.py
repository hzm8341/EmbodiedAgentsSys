"""API 路由"""
from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.simulation import simulation_service

router = APIRouter()

class ExecuteRequest(BaseModel):
    action: str
    params: dict = {}

class ExecuteResponse(BaseModel):
    status: str
    message: str
    data: dict = {}

@router.post("/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest):
    """执行动作"""
    receipt = simulation_service.execute_action(req.action, req.params)
    return ExecuteResponse(
        status=receipt.status.value,
        message=receipt.result_message,
        data=receipt.result_data or {}
    )

@router.get("/scene")
def get_scene():
    """获取场景状态"""
    return simulation_service.get_scene()

@router.post("/reset")
def reset():
    """重置环境"""
    return simulation_service.reset()