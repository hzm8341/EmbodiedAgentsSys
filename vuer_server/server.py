"""Vuer Server - URDF visualization using Vuer."""
import asyncio
import argparse
import json
import aiohttp
from pathlib import Path

from vuer import Vuer
from vuer.schemas import Urdf, Scene
from aiohttp import web

# Map robot_id -> (urdf_dir, urdf_file)
ROBOT_URDF_MAP = {
    "eyoubot": ("assets/eyoubot", "eu_ca_describtion_lbs6.urdf"),
}

_current_robot = "eyoubot"
_current_joints = {}  # {joint_name: position}
_vuer_port = 8012
_backend_url = "http://localhost:8000"


def _make_urdf_url(urdf_dir: str, urdf_file: str) -> str:
    """Build HTTP URL for URDF so relative mesh paths resolve correctly."""
    return f"http://localhost:{_vuer_port}/static/{urdf_dir}/{urdf_file}"


async def switch_robot_handler(request):
    """HTTP endpoint to switch displayed robot: GET /switch_robot?robot=xxx"""
    global _current_robot
    robot_id = request.query.get("robot")
    if robot_id not in ROBOT_URDF_MAP:
        return web.json_response({"error": "unknown robot", "available": list(ROBOT_URDF_MAP.keys())}, status=404)
    _current_robot = robot_id
    return web.json_response({"status": "ok", "robot_id": robot_id})


async def joint_state_handler(request):
    """HTTP endpoint to update joint states: POST /api/joint_state"""
    global _current_joints
    try:
        data = await request.json()
        joints = data.get("joints", [])
        for joint in joints:
            joint_name = joint.get("joint_name")
            position = joint.get("position")
            if joint_name is not None and position is not None:
                _current_joints[joint_name] = position
        return web.json_response({"status": "ok", "joints": _current_joints})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


def create_app(host: str = "0.0.0.0", port: int = 8012):
    """Create Vuer app with URDF."""
    global _vuer_port
    _vuer_port = port
    app = Vuer(host=host, port=port)

    @app.spawn
    async def main(session):
        """Handle WebSocket connection and push URDF scene."""
        global _current_robot, _current_joints, _backend_url

        robot_id = _current_robot
        try:
            requested_robot = session.ws.url.query.get("robot")
            if requested_robot in ROBOT_URDF_MAP:
                robot_id = requested_robot
                _current_robot = requested_robot
        except Exception:
            pass
        urdf_dir, urdf_file = ROBOT_URDF_MAP[robot_id]
        urdf_url = _make_urdf_url(urdf_dir, urdf_file)

        print(f"Session {session.CURRENT_WS_ID} connected")

        # Push initial scene
        session.set @ Scene(
            children=[
                Urdf(
                    src=urdf_url,
                    key="robot",
                    position=[0, 0, 0],
                    stationary=True,
                    joints=_current_joints.copy() if _current_joints else None,
                ),
            ]
        )

        # Poll for joint state updates from backend
        last_update = 0
        while True:
            await asyncio.sleep(0.1)  # 100ms poll interval

            # Check if backend has new state
            try:
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(f"{_backend_url}/api/state/{robot_id}") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            joints = data.get("joints", [])
                            # Update if changed
                            if joints and (data.get("timestamp", 0) > last_update):
                                new_joints = {}
                                for j in joints:
                                    new_joints[j["joint_name"]] = j["position"]
                                if new_joints != _current_joints:
                                    _current_joints = new_joints
                                    last_update = data.get("timestamp", 0)
                                    session.update @ Urdf(key="robot", joints=_current_joints.copy())
            except Exception as e:
                # Silently ignore backend errors (backend might not be running)
                pass

    @app.add_handler("joints")
    async def on_joint_update(event, session, fps=60):
        """Handle joint state updates from client."""
        global _current_joints
        try:
            if isinstance(event.value, dict):
                _current_joints.update(event.value)
            elif isinstance(event.value, list):
                for item in event.value:
                    if isinstance(item, dict) and "joint_name" in item:
                        _current_joints[item["joint_name"]] = item.get("position", 0)
            session.update @ Urdf(key="robot", joints=_current_joints.copy())
        except Exception as e:
            print(f"Joint update error: {e}")

    # Register HTTP endpoints
    app.add_route("/switch_robot", switch_robot_handler, method="GET")
    app.add_route("/api/joint_state", joint_state_handler, method="POST")
    app._add_static("/static", ".")

    return app


def main():
    parser = argparse.ArgumentParser(description='Vuer URDF Server')
    parser.add_argument('--port', type=int, default=8012, help='WebSocket port')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind')
    args = parser.parse_args()

    print(f"Vuer Server starting on {args.host}:{args.port}")
    print(f"Available robots: {list(ROBOT_URDF_MAP.keys())}")
    print(f"Backend URL: {_backend_url}")

    app = create_app(args.host, args.port)
    app.start()


if __name__ == '__main__':
    main()
