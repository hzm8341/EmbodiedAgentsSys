"""HardwareScanner — 自动扫描串口/摄像头设备并注册到 RobotCapabilityRegistry。

参考：roboclaw/embodied/scan.py + setup.py
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Callable, Awaitable, Any

logger = logging.getLogger(__name__)


class HardwareScanner:
    """扫描串口和摄像头设备，注册到 RobotCapabilityRegistry，并持久化配置。"""

    async def scan_serial_ports(self) -> list[dict]:
        """扫描串口设备。

        优先使用 /dev/serial/by-id（稳定路径），回退到 /dev/serial/by-path。

        Returns:
            list of dict: {path, by_id_path, description}
        """
        results = []

        by_id_dir = Path("/dev/serial/by-id")
        if by_id_dir.exists():
            for link in sorted(by_id_dir.iterdir()):
                try:
                    real_path = link.resolve()
                    results.append({
                        "path": str(real_path),
                        "by_id_path": str(link),
                        "description": link.name,
                        "stable": True,
                    })
                    logger.info("Found serial (by-id): %s → %s", link.name, real_path)
                except Exception as exc:
                    logger.warning("Serial scan error: %s", exc)
        else:
            # fallback：扫描 /dev/ttyUSB* /dev/ttyACM*
            import glob
            for pattern in ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyS[0-9]"]:
                for dev in sorted(glob.glob(pattern)):
                    results.append({
                        "path": dev,
                        "by_id_path": "",
                        "description": Path(dev).name,
                        "stable": False,
                    })
                    logger.info("Found serial (fallback): %s", dev)

        return results

    async def scan_cameras(self) -> list[dict]:
        """扫描摄像头设备（/dev/video*），用 cv2 验证可用性。

        Returns:
            list of dict: {path, index, width, height, available}
        """
        results = []
        try:
            import cv2
            _has_cv2 = True
        except ImportError:
            _has_cv2 = False
            logger.warning("cv2 not available, camera validation skipped")

        import glob
        for dev_path in sorted(glob.glob("/dev/video*")):
            try:
                index = int(Path(dev_path).name.replace("video", ""))
            except ValueError:
                continue

            info: dict = {"path": dev_path, "index": index, "available": False, "width": 0, "height": 0}

            if _has_cv2:
                cap = cv2.VideoCapture(index)
                if cap.isOpened():
                    info["available"] = True
                    info["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    info["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
                    logger.info("Camera %s: %dx%d", dev_path, info["width"], info["height"])
                else:
                    cap.release()
            else:
                info["available"] = True  # 无 cv2 时假设可用

            results.append(info)

        return results

    async def scan_and_register(
        self,
        registry: Any,                          # RobotCapabilityRegistry
        config_path: Optional[Path] = None,     # 持久化到此 JSON 文件
        send_fn: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> dict:
        """完整流程：扫描 → 汇报 → 注册 → 持久化。

        Args:
            registry: RobotCapabilityRegistry 实例
            config_path: 若提供，将发现结果保存为 setup.json
            send_fn: 发送进度消息的异步函数（可为 None）

        Returns:
            dict: {serial_ports: [...], cameras: [...]}
        """
        async def _notify(msg: str) -> None:
            logger.info(msg)
            if send_fn:
                await send_fn(msg)

        await _notify("🔍 开始硬件扫描...")

        # 并行扫描串口和摄像头
        serial_ports, cameras = await asyncio.gather(
            self.scan_serial_ports(),
            self.scan_cameras(),
        )

        # 汇报结果
        await _notify(f"发现 {len(serial_ports)} 个串口设备，{len(cameras)} 个摄像头")

        # 注册到 registry（调用 registry.register_hardware 如果存在）
        for port in serial_ports:
            if hasattr(registry, "register_hardware"):
                try:
                    registry.register_hardware("serial_port", port["path"], port)
                except Exception as exc:
                    logger.warning("Register serial %s failed: %s", port["path"], exc)

        for cam in cameras:
            if cam.get("available") and hasattr(registry, "register_hardware"):
                try:
                    registry.register_hardware("camera", cam["path"], cam)
                except Exception as exc:
                    logger.warning("Register camera %s failed: %s", cam["path"], exc)

        result = {"serial_ports": serial_ports, "cameras": cameras}

        # 持久化
        if config_path:
            config_path = Path(config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            await _notify(f"配置已保存到 {config_path}")

        return result
