"""TrainingScriptGenerator — generates dataset requirements and training configs."""
from __future__ import annotations

from dataclasses import dataclass

from ..hardware.capability_registry import CapabilityResult

# Default training parameters by skill domain
_SKILL_CONFIGS: dict[str, dict] = {
    "manipulation": {"model_type": "act",     "epochs": 100, "batch_size": 16},
    "navigation":   {"model_type": "lerobot", "epochs": 50,  "batch_size": 32},
    "vision":       {"model_type": "gr00t",   "epochs": 30,  "batch_size": 8},
    "force":        {"model_type": "act",     "epochs": 80,  "batch_size": 16},
    "default":      {"model_type": "act",     "epochs": 100, "batch_size": 16},
}

_MIN_EPISODES: dict[str, int] = {
    "manipulation": 200,
    "navigation":   100,
    "vision":       150,
    "force":        300,
    "default":      200,
}


@dataclass
class TrainingConfig:
    """Training job configuration for a single skill gap."""
    skill_id: str
    dataset_path: str
    model_type: str         # "act" | "gr00t" | "lerobot"
    epochs: int
    batch_size: int
    output_dir: str = ""


class TrainingScriptGenerator:
    """Generates training configs, bash scripts, and gap reports for engineers."""

    def generate_training_config(
        self, gap: CapabilityResult, dataset_path: str
    ) -> TrainingConfig:
        """Return a TrainingConfig for the given gap and dataset path."""
        domain = gap.skill_id.split(".")[0] if "." in gap.skill_id else "default"
        cfg = _SKILL_CONFIGS.get(domain, _SKILL_CONFIGS["default"])
        return TrainingConfig(
            skill_id=gap.skill_id,
            dataset_path=dataset_path,
            model_type=cfg["model_type"],
            epochs=cfg["epochs"],
            batch_size=cfg["batch_size"],
            output_dir=f"models/{gap.skill_id.replace('.', '_')}",
        )

    def generate_dataset_requirements(
        self, gaps: list[CapabilityResult]
    ) -> dict[str, dict]:
        """Return per-gap dataset collection requirements dict.

        Format::

            { "manipulation.grasp": { "min_episodes": 200, "data_types": [...] } }
        """
        requirements: dict[str, dict] = {}
        for gap in gaps:
            domain = gap.skill_id.split(".")[0] if "." in gap.skill_id else "default"
            requirements[gap.skill_id] = {
                "min_episodes": _MIN_EPISODES.get(domain, 200),
                "data_types": ["rgb_frames", "joint_states", "gripper_state"],
                "robot_type": gap.robot_type,
                "gap_reason": gap.reason,
            }
        return requirements

    def render_bash_script(self, config: TrainingConfig) -> str:
        """Render a runnable bash training script for the given config."""
        return f"""#!/bin/bash
# Auto-generated training script for skill: {config.skill_id}
# Model: {config.model_type}, Epochs: {config.epochs}, Batch: {config.batch_size}
set -euo pipefail

SKILL_ID="{config.skill_id}"
DATASET_PATH="{config.dataset_path}"
OUTPUT_DIR="{config.output_dir}"
MODEL_TYPE="{config.model_type}"
EPOCHS={config.epochs}
BATCH_SIZE={config.batch_size}

echo "Training $SKILL_ID using $MODEL_TYPE model"
echo "Dataset: $DATASET_PATH"
echo "Output:  $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"

python -m agents.training.run_training \\
    --skill "$SKILL_ID" \\
    --model "$MODEL_TYPE" \\
    --dataset "$DATASET_PATH" \\
    --output "$OUTPUT_DIR" \\
    --epochs "$EPOCHS" \\
    --batch-size "$BATCH_SIZE"

echo "Training complete. Model saved to $OUTPUT_DIR"
"""

    def render_markdown_report(self, gaps: list[CapabilityResult]) -> str:
        """Render a Markdown report listing all gaps and required training actions."""
        lines = [
            "# 能力缺口训练报告",
            "",
            f"共检测到 **{len(gaps)}** 个能力缺口，需要收集数据并训练。",
            "",
        ]
        reqs = self.generate_dataset_requirements(gaps)
        for gap in gaps:
            req = reqs[gap.skill_id]
            lines += [
                f"## {gap.skill_id}",
                "",
                f"- **缺口类型:** {gap.gap_type.value}",
                f"- **机器人类型:** {gap.robot_type}",
                f"- **原因:** {gap.reason}",
                f"- **最少采集 episodes:** {req['min_episodes']}",
                f"- **需要数据类型:** {', '.join(req['data_types'])}",
                "",
            ]
        return "\n".join(lines)
