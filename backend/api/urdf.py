"""URDF API endpoints."""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vuer_server.urdf_loader import URDFLoader, URDFModel

router = APIRouter(prefix="/api/urdf", tags=["urdf"])

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"
PREFERRED_URDF = "eu_ca_describtion_lbs6.urdf"


def _pick_urdf_file(urdf_files: list[Path]) -> Optional[Path]:
    if not urdf_files:
        return None
    for urdf in urdf_files:
        if urdf.name == PREFERRED_URDF:
            return urdf
    return sorted(urdf_files)[0]


class URDFListItem(BaseModel):
    robot_id: str
    name: str
    urdf_path: str


class URDFLoadRequest(BaseModel):
    robot_id: str


@router.get("/list", response_model=List[URDFListItem])
async def list_urdf_models():
    """List all available URDF models."""
    models = []

    if not ASSETS_DIR.exists():
        return models

    for robot_dir in ASSETS_DIR.iterdir():
        if robot_dir.is_dir():
            urdf_file = _pick_urdf_file(list(robot_dir.glob("*.urdf")))
            if urdf_file is None:
                continue
            loader = URDFLoader(robot_dir)
            try:
                model = loader.load(str(urdf_file))
                models.append(URDFListItem(
                    robot_id=robot_dir.name,
                    name=model.name,
                    urdf_path=str(urdf_file.relative_to(ASSETS_DIR))
                ))
            except Exception:
                continue

    return models


@router.get("/{robot_id}", response_model=URDFModel)
async def get_urdf_model(robot_id: str):
    """Get URDF model structure."""
    robot_dir = ASSETS_DIR / robot_id

    if not robot_dir.exists():
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

    urdf_file = _pick_urdf_file(list(robot_dir.glob("*.urdf")))
    if urdf_file is None:
        raise HTTPException(status_code=404, detail=f"No URDF found for {robot_id}")

    loader = URDFLoader(robot_dir)
    model = loader.load(str(urdf_file))

    return model


@router.post("/load")
async def load_urdf(request: URDFLoadRequest):
    """Load a specific URDF model."""
    robot_dir = ASSETS_DIR / request.robot_id

    if not robot_dir.exists():
        raise HTTPException(status_code=404, detail=f"Robot {request.robot_id} not found")

    urdf_file = _pick_urdf_file(list(robot_dir.glob("*.urdf")))
    if urdf_file is None:
        raise HTTPException(status_code=404, detail=f"No URDF found")

    loader = URDFLoader(robot_dir)
    model = loader.load(str(urdf_file))

    return {"status": "loaded", "robot_id": request.robot_id, "model": model}
