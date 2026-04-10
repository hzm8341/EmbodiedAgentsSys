"""Vuer Server main entry point."""
import argparse
from pathlib import Path
from urdf_loader import URDFLoader


def main():
    parser = argparse.ArgumentParser(description='Vuer URDF Server')
    parser.add_argument('--urdf-dir', type=str, default='../assets/eyoubot',
                        help='Directory containing URDF files')
    parser.add_argument('--port', type=int, default=8012,
                        help='WebSocket port')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind')
    args = parser.parse_args()

    print(f"Vuer Server starting on {args.host}:{args.port}")
    print(f"URDF directory: {args.urdf_dir}")

    urdf_loader = URDFLoader(Path(args.urdf_dir))
    urdf_path = Path(args.urdf_dir) / "eu_ca_describtion_lbs6.urdf"

    if urdf_path.exists():
        model = urdf_loader.load(str(urdf_path))
        print(f"Loaded robot: {model.name} with {len(model.links)} links and {len(model.joints)} joints")
    else:
        print(f"URDF file not found: {urdf_path}")

    print("Vuer Server placeholder - TODO: integrate with Vuer")


if __name__ == '__main__':
    main()
