# EmbodiedAgentsSys - エージェントデジタルワーカーフレームワーク

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="_static/EMBODIED_AGENTS_DARK.png">
  <source media="(prefers-color-scheme: light)" srcset="_static/EMBODIED_AGENTS_LIGHT.png">
  <img alt="EmbodiedAgentsSys Logo" src="_static/EMBODIED_AGENTS_DARK.png" width="600">
</picture>

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ROS2](https://img.shields.io/badge/ROS2-Humble%2B-green)](https://docs.ros.org/en/humble/index.html)

**汎用具身知性ロボットフレームワーク - VLAモデル対応エージェントデジタルワーカーシステム**

[**インストール**](#インストール) | [**クイックスタート**](#クイックスタート) | [**機能一覧**](#機能一覧) | [**ガイド**](#ガイド)

</div>

---

## 概要

**EmbodiedAgentsSys** はROS2ベースの汎用具身知性ロボットフレームワークで、VLA（Vision-Language-Action）モデルに基づくエージェントデジタルワーカーをサポートします。

### コア機能

- **VLAマルチモデルサポート**
  - LeRobot、ACT、GR00Tなどの様々なVLAモデル・アダプター
  - 統一されたVLAインターフェース設計で新モデルへの拡張が容易

- **豊富なスキルライブラリ**
  - アトミックスキル：把握、配置、到達、関節動作、検査
  - スキルチェーンのオーケストレーションとタスクプランニングをサポート

- **イベント駆動アーキテクチャ**
  - 非同期ノンブロッキング実行
  - イベントバスによる疎結合コンポーネント通信

- **タスクプランニング機能**
  - ルールベースのタスクプランニング
  - LLM駆動のインテリジェントなタスク分解

- **コア実行ループ（フェーズ1）**
  - ハードウェア抽象化層：統一されたアームインターフェース＋マルチベンダーアダプター
  - スキルレジストリ＋能力ギャップ検出（YAML駆動）
  - シーン仕様＋音声インタラクションによる入力
  - デュアルフォーマット実行計画（YAML機械可読＋Markdown人間可読）
  - 失敗データの自動記録＋トレーニングスクリプト自動生成

---

## 機能一覧

### VLAアダプター

| アダプター | 説明 | ステータス |
|-----------|------|-----------|
| VLAAdapterBase | VLAアダプター基底クラス | ✅ |
| LeRobotVLAAdapter | LeRobotフレームワーク・アダプター | ✅ |
| ACTVLAAdapter | ACT（Action Chunking Transformer）アダプター | ✅ |
| GR00TVLAAdapter | GR00T Diffusion Transformerアダプター | ✅ |

### スキル

| スキル | 説明 | ステータス |
|-------|------|-----------|
| GraspSkill | 把握スキル | ✅ |
| PlaceSkill | 配置スキル | ✅ |
| ReachSkill | 到達スキル | ✅ |
| MoveSkill | 関節動作スキル | ✅ |
| InspectSkill | 検査・認識スキル | ✅ |
| AssemblySkill | 組立スキル | ✅ |
| Perception3DSkill | 3D知覚スキル | ✅ |

### コンポーネント

| コンポーネント | 説明 | ステータス |
|--------------|------|-----------|
| VoiceCommand | 音声コマンド理解 | ✅ |
| SemanticParser | セマンティックパーサー（LLM強化） | ✅ |
| TaskPlanner | タスクプランナー（実行メモリ付き） | ✅ |
| EventBus | イベントバス | ✅ |
| DistributedEventBus | 分散イベントバス | ✅ |
| SkillGenerator | スキルコードジェネレーター | ✅ |

### ツール

| ツール | 説明 | ステータス |
|------|------|-----------|
| AsyncCache | 非同期キャッシュ | ✅ |
| BatchProcessor | バッチプロセッサー | ✅ |
| RateLimiter | レートリミッター | ✅ |
| ForceController | 力控制器 | ✅ |

### ハードウェア抽象化層（フェーズ1）

| モジュール | 説明 | ステータス |
|----------|------|-----------|
| ArmAdapter | アーム抽象基底クラス（ABC）、`move_to_pose` / `move_joints` / `set_gripper` 等の統一インターフェースを定義 | ✅ |
| AGXArmAdapter | AGXアームアダプター（非同期、モックモード対応） | ✅ |
| LeRobotArmAdapter | LeRobotアームアダプター（LeRobotClientを再利用） | ✅ |
| RobotCapabilityRegistry | YAML駆動のスキルレジストリ、`robot_type`によるクエリをサポート、`GapType`列挙型を返す | ✅ |
| GapDetectionEngine | 実行計画ステップをハードギャップ分類、`GapReport`を出力 | ✅ |

### プランニング層拡張（フェーズ1）

| モジュール | 説明 | ステータス |
|----------|------|-----------|
| SceneSpec | 構造化シーン記述データクラス、YAMLシリアライズ/デシリアライズをサポート | ✅ |
| PlanGenerator | TaskPlannerをラップ、フラットアクションをドット記法スキル名にマッピング、YAML + Markdownデュアルフォーマット出力 | ✅ |
| VoiceTemplateAgent | ガイド付き音声Q&A、段階的にSceneSpecフィールドを入力 | ✅ |

### データとトレーニング（フェーズ1）

| モジュール | 説明 | ステータス |
|----------|------|-----------|
| FailureDataRecorder | 失敗時に`metadata.json` + `scene_spec.yaml` + `plan.yaml`を自動保存 | ✅ |
| TrainingScriptGenerator | 能力ギャップに基づいてデータセット要件レポートとbashトレーニングスクリプトを生成 | ✅ |

---

## インストール

### 1. ROS2 Humbleのインストール

```bash
sudo apt install ros-humble-desktop
```

### 2. Sugarcoat依存関係のインストール

```bash
sudo apt install ros-humble-automatika-ros-sugar
```

またはソースからビルド:

```bash
git clone https://github.com/automatika-robotics/sugarcoat
cd sugarcoat
pip install -e .
```

### 3. EmbodiedAgentsSysのインストール

```bash
pip install -e .
```

---

## クイックスタート

### VLAアダプターの作成

```python
from agents.clients.vla_adapters import LeRobotVLAAdapter

# LeRobotアダプターを作成
adapter = LeRobotVLAAdapter(config={
    "policy_name": "panda_policy",
    "checkpoint": "lerobot/act_...",
    "host": "127.0.0.1",
    "port": 8080,
    "action_dim": 7
})

adapter.reset()
```

### スキルの作成と実行

```python
import asyncio
from agents.skills.manipulation import GraspSkill

# 把握スキルを作成
skill = GraspSkill(
    object_name="cube",
    vla_adapter=adapter
)

# 観測データを準備
observation = {
    "object_detected": True,
    "grasp_success": False
}

# スキルを実行
result = asyncio.run(skill.execute(observation))

print(f"Status: {result.status}")
print(f"Output: {result.output}")
```

---

## ガイド

### 1. VLAアダプターの使用

#### LeRobotアダプター

```python
from agents.clients.vla_adapters import LeRobotVLAAdapter

adapter = LeRobotVLAAdapter(config={
    "policy_name": "panda_policy",
    "checkpoint": "lerobot/act_sim_transfer_cube_human",
    "host": "127.0.0.1",
    "port": 8080,
    "action_dim": 7
})

adapter.reset()

# アクションを生成
observation = {
    "image": image_data,
    "joint_positions": joints
}
action = adapter.act(observation, "grasp(object=cube)")

# アクションを実行
result = adapter.execute(action)
```

#### ACTアダプター

```python
from agents.clients.vla_adapters import ACTVLAAdapter

adapter = ACTVLAAdapter(config={
    "model_path": "/models/act",
    "chunk_size": 100,
    "horizon": 1,
    "action_dim": 7
})
```

#### GR00Tアダプター

```python
from agents.clients.vla_adapters import GR00TVLAAdapter

adapter = GR00TVLAAdapter(config={
    "model_path": "/models/gr00t",
    "inference_steps": 10,
    "action_dim": 7,
    "action_horizon": 8
})
```

### 2.スキルの使用

#### GraspSkill - 把握

```python
from agents.skills.manipulation import GraspSkill

skill = GraspSkill(
    object_name="cube",
    vla_adapter=adapter
)

# 事前条件をチェック
observation = {"object_detected": True}
if skill.check_preconditions(observation):
    result = asyncio.run(skill.execute(observation))
```

#### PlaceSkill - 配置

```python
from agents.skills.manipulation import PlaceSkill

skill = PlaceSkill(
    target_position=[0.5, 0.0, 0.1],  # x, y, z
    vla_adapter=adapter
)
```

#### ReachSkill - 到達

```python
from agents.skills.manipulation import ReachSkill

skill = ReachSkill(
    target_position=[0.3, 0.0, 0.2],
    vla_adapter=adapter
)
```

#### MoveSkill - 関節動作

```python
from agents.skills.manipulation import MoveSkill

# 関節モード
skill = MoveSkill(
    target_joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    vla_adapter=adapter
)

# エンドエフェクタポーズモード
skill = MoveSkill(
    target_pose=[0.3, 0.0, 0.2, 0.0, 0.0, 0.0],  # x, y, z, roll, pitch, yaw
    vla_adapter=adapter
)
```

#### InspectSkill - 検査

```python
from agents.skills.manipulation import InspectSkill

skill = InspectSkill(
    target_object="cup",
    inspection_type="detect",  # detect/verify/quality
    vla_adapter=adapter
)
```

### 3. スキルチェーン実行

```python
import asyncio
from agents.skills.manipulation import ReachSkill, GraspSkill, PlaceSkill

async def pick_and_place():
    adapter = LeRobotVLAAdapter(config={"action_dim": 7})

    # スキルチェーンを作成
    reach = ReachSkill(target_position=[0.3, 0.0, 0.2], vla_adapter=adapter)
    grasp = GraspSkill(object_name="cube", vla_adapter=adapter)
    place = PlaceSkill(target_position=[0.5, 0.0, 0.1], vla_adapter=adapter)

    # 順次実行
    observation = await get_observation()

    await reach.execute(observation)
    await grasp.execute(observation)
    await place.execute(observation)

asyncio.run(pick_and_place())
```

### 4. イベントバスの使用

```python
from agents.events.bus import EventBus, Event

bus = EventBus()

async def on_skill_started(event: Event):
    print(f"Skill started: {event.data}")

# イベントを購読
bus.subscribe("skill.started", on_skill_started)

# イベントを発行
await bus.publish(Event(
    type="skill.started",
    source="agent",
    data={"skill": "grasp", "object": "cube"}
))
```

### 5. タスクプランナーの使用

```python
from agents.components.task_planner import TaskPlanner, PlanningStrategy

# プランナー作成（ルールベース）
planner = TaskPlanner(strategy=PlanningStrategy.RULE_BASED)

# タスクを計画
task = planner.plan("カップをつかんでテーブルの上に置いて")

print(f"Task: {task.name}")
print(f"Skills: {task.skills}")
# 出力: ['reach', 'grasp', 'reach', 'place']
```

### 6. セマンティックパーサーの使用

```python
from agents.components.semantic_parser import SemanticParser

# LLM強化パーシングを使用
parser = SemanticParser(use_llm=True, ollama_model="qwen2.5:3b")

# 同期パーシング（ルールモード）
result = parser.parse("前方20cm")
# {'intent': 'motion', 'direction': 'forward', 'distance': 0.2}

# 非同期パーシング（LLMモード）
result = await parser.parse_async("あの丸い部品を移動して")
# {'intent': 'motion', 'params': {'direction': 'forward', ...}}
```

### 7. 力制御モジュールの使用

```python
from skills.force_control import ForceController, ForceControlMode

controller = ForceController(
    max_force=10.0,
    contact_threshold=0.5
)

# 力制御モードを設定
controller.set_mode(ForceControlMode.FORCE)

#力を適用
target_force = np.array([0.0, 0.0, -5.0])
result = await controller.execute(target_force)
```

### 8. パフォーマンス最適化ツール

#### 非同期キャッシュ

```python
from agents.utils.performance import AsyncCache, get_cache

cache = get_cache(ttl_seconds=60)

@cache.cached
async def expensive_operation(data):
    # 時間がかかる処理
    return result
```

#### バッチプロセッサー

```python
from agents.utils.performance import BatchProcessor

processor = BatchProcessor(batch_size=10, timeout=0.1)

async def handler(items):
    # バッチ処理
    return [process(item) for item in items]

# 処理開始
asyncio.create_task(processor.process(handler))

# タスク追加
result = await processor.add(item)
```

### 9. SkillGeneratorの使用

```python
from skills.teaching.skill_generator import SkillGenerator

generator = SkillGenerator(output_dir="./generated_skills", _simulated=False)

# ティーチングアクションからスキルを生成
teaching_action = {
    "action_id": "demo_001",
    "name": "pick_and_place",
    "frames": [
        {"joint_positions": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
        {"joint_positions": [0.5, 0.2, 0.1, 0.0, 0.0, 0.0, 0.0]},
    ]
}

result = await generator.generate_skill(
    teaching_action=teaching_action,
    skill_name="demo_pick_place"
)

# ファイルにエクスポート
export_result = await generator.export_skill(result["skill_id"])
# 実行可能なPythonファイルを生成
```

### 10. フェーズ1 コア実行ループ

#### シーン記述＋音声インタラクション入力

```python
import asyncio
from agents.components.scene_spec import SceneSpec
from agents.components.voice_template_agent import VoiceTemplateAgent

# 方法1: 直接SceneSpecを構築
scene = SceneSpec(
    task_description="赤い部品をAエリアからBエリアに移動",
    robot_type="arm",
    objects=["red_part"],
    target_positions={"red_part": [0.5, 0.2, 0.1]},
)

# 方法2: ガイド付き音声インタラクション入力
agent = VoiceTemplateAgent()
scene = asyncio.run(agent.interactive_fill())
```

#### 実行計画の生成（YAML + Markdown デュアルフォーマット）

```python
from agents.components.plan_generator import PlanGenerator

generator = PlanGenerator(backend="mock")  # backend="ollama"でLLM使用
plan = asyncio.run(generator.generate(scene))

print(plan.yaml_content)    # YAML実行計画（機械可読）
print(plan.markdown_report) # Markdownレポート（人間可読）
print(plan.steps)           # ステップリスト、ドット記法スキル名を含む
# 例: [{'action': 'manipulation.grasp', 'object': 'red_part', ...}]
```

#### スキルレジストリ＋能力ギャップ検出

```python
from agents.hardware.capability_registry import RobotCapabilityRegistry, GapType
from agents.hardware.gap_detector import GapDetectionEngine

registry = RobotCapabilityRegistry()

# 単一スキルをクエリ
result = registry.query("manipulation.grasp", robot_type="arm")
print(result.gap_type)  # GapType.NONE - サポート済み

result = registry.query("navigation.goto", robot_type="arm")
print(result.gap_type)  # GapType.HARD - 未サポート

# 計画ステップのギャップをバッチ検出
engine = GapDetectionEngine(registry)
report = engine.detect(plan.steps, robot_type="arm")
print(report.has_gaps)        # True/False
print(report.gap_steps)       # ギャップのあるステップのリスト
annotated = engine.annotate_steps(plan.steps, robot_type="arm")
# 各ステップに新しいステータス: "pending" または "gap"
```

#### 失敗データ記録＋トレーニングスクリプト生成

```python
from agents.data.failure_recorder import FailureDataRecorder
from agents.training.script_generator import TrainingScriptGenerator

# 実行失敗時に現場データを保存
recorder = FailureDataRecorder(base_dir="./failure_data")
record_path = asyncio.run(recorder.record(
    scene=scene,
    plan=plan,
    error="manipulation.grasp 実行タイムアウト",
))
# 保存: failure_data/<timestamp>/metadata.json + scene_spec.yaml + plan.yaml

# 能力ギャップに基づいてトレーニングスクリプトを生成
generator = TrainingScriptGenerator()
config = generator.generate_config(gap_report=report, scene=scene)
script = generator.generate_script(config)
print(script)  # bashトレーニングスクリプトの内容
req_report = generator.generate_requirements_report(config)
print(req_report)  # データセット要件レポート（Markdown）
```

#### アームアダプトーの使用

```python
from agents.hardware.agx_arm_adapter import AGXArmAdapter
from agents.hardware.arm_adapter import Pose6D

# アダプターを作成（mock=Trueでテスト用、実機不要）
arm = AGXArmAdapter(host="192.168.1.100", mock=True)
asyncio.run(arm.connect())

# 準備状態を確認
ready = asyncio.run(arm.is_ready())

# 目標ポーズに移動
pose = Pose6D(x=0.3, y=0.0, z=0.2, roll=0.0, pitch=0.0, yaw=0.0)
success = asyncio.run(arm.move_to_pose(pose, speed=0.1))

# グリッパーを制御
asyncio.run(arm.set_gripper(opening=0.8, force=5.0))

# 能力をクエリ
caps = arm.get_capabilities()
print(caps.robot_type)   # "arm"
print(caps.skill_ids)    # ["manipulation.grasp", "manipulation.place", ...]
```

### 11. 分散イベントバス（マルチロボットコラボレーション）

```python
from agents.events.bus import DistributedEventBus

# 分散イベントバスを作成（ROS2ノードが必要）
bus = DistributedEventBus(ros_node=my_ros_node, namespace="/robots/events")

# イベントを購読
async def on_robot_status(event):
    print(f"Robot status: {event.data}")

bus.subscribe("robot.status", on_robot_status)

# イベントを発行（他のROS2ノードに自動ブロードキャスト）
await bus.publish(Event(
    type="robot.status",
    source="robot_1",
    data={"status": "working", "battery": 85}
))
```

---

## 設定ファイル

### VLA設定 (config/vla_config.yaml)

```yaml
lerobot:
  policy_name: "default_policy"
  checkpoint: null
  host: "127.0.0.1"
  port: 8080
  action_dim: 7

vla_type: "lerobot"

skills:
  max_retries: 3
  observation_timeout: 5.0
```

---

## プロジェクト構造

```
agents/
├── clients/
│   ├── vla_adapters/          # VLAアダプター
│   │   ├── base.py
│   │   ├── lerobot.py
│   │   ├── act.py
│   │   └── gr00t.py
│   └── ollama.py              # Ollama LLMクライアント
├── components/                # コンポーネント
│   ├── voice_command.py
│   ├── semantic_parser.py
│   ├── task_planner.py        # _SKILL_NAMESPACE_MAPを含む
│   ├── scene_spec.py          # [フェーズ1] シーン仕様データクラス
│   ├── plan_generator.py      # [フェーズ1] デュアルフォーマット実行計画ジェネレーター
│   └── voice_template_agent.py# [フェーズ1] ガイド付き音声インタラクション入力
├── hardware/                  # [フェーズ1] ハードウェア抽象化層
│   ├── arm_adapter.py         # ArmAdapter ABC + Pose6D / RobotState / RobotCapabilities
│   ├── agx_arm_adapter.py     # AGXアームアダプター
│   ├── lerobot_arm_adapter.py # LeRobotアームアダプター
│   ├── capability_registry.py # RobotCapabilityRegistry + GapType列挙型
│   ├── gap_detector.py        # GapDetectionEngine
│   └── skills_registry.yaml   # スキルレジストリ（9スキル）
├── data/                      # [フェーズ1] データ層
│   └── failure_recorder.py    # 自動失敗データ記録
├── training/                  # [フェーズ1] トレーニング層
│   └── script_generator.py    # トレーニングスクリプト + データセット要件レポート生成
├── skills/
│   ├── vla_skill.py           # スキル基底クラス
│   └── manipulation/          # 操作スキル
│       ├── grasp.py
│       ├── place.py
│       ├── reach.py
│       ├── move.py
│       └── inspect.py
├── events/                    # イベントシステム
│   └── bus.py                 # EventBus + DistributedEventBus
└── utils/                     # ユーティリティ
    └── performance.py

skills/
├── force_control/             # 力制御モジュール
│   └── force_control.py
├── vision/                    # ビジョンスキル
│   └── perception_3d_skill.py
└── teaching/                  # ティーチングモジュール
    └── skill_generator.py

tests/                         # テスト（57テストケース）
docs/
├── api/                       # APIドキュメント
├── guides/                    # ガイド
└── plans/                     # 開発計画
```

---

## Webフロントエンドダッシュボード

Agent Dashboardはリアルタイムカメラプレビュー、シーン説明、オブジェクト検出機能を提供します。React + FastAPIで構築され、ローカルOllama `qwen2.5vl` visionモデル用于推論。

### デモプレビュー

<div align="center">
<img src="_static/dashboard_demo_1.png" alt="シーン分析パネル - シーン説明とオブジェクト検出" width="800"/>
<p><em>シーン分析パネル: リアルタイムプレビュー + qwen2.5vlシーン説明 + オブジェクト検出信頼度</em></p>

<img src="_static/dashboard_demo_2.png" alt="シーン分析パネル - マルチオブジェクト検出結果" width="800"/>
<p><em>検出結果: 事務机上のモニター、フォルダ、PCなどのオブジェクトを自動識別</em></p>
</div>

### 前提条件

- USBカメラ接続済み（デフォルト `/dev/video0`）
- Ollamaインストール済み、visionモデルを取得済み:
  ```bash
  ollama pull qwen2.5vl
  ```
- Python依存関係:
  ```bash
  pip install fastapi uvicorn opencv-python ollama
  ```
- Node.js依存関係（初回）:
  ```bash
  cd web-dashboard && npm install
  ```

### 起動方法

**ターミナル1 — バックエンド**（USBカメラ + qwen2.5vl推論）:

```bash
cd /path/to/EmbodiedAgentsSys
python examples/agent_dashboard_backend.py
# バックエンドは http://localhost:8000 で動作
```

**ターミナル2 — フロントエンド**（React開発サーバー）:

```bash
cd web-dashboard
npx vite
# フロントエンドは http://localhost:5173 で動作
```

ブラウザで `http://localhost:5173` を開く

### 機能ページ

| サイドバー | 機能 |
|-----------|------|
| **カメラ** | リアルタイムカメラプレビュー（約10 fps）、開始/停止ボタン |
| **シーン分析** | リアルタイムプレビュー + 「シーン分析」をクリックしてqwen2.5vlを呼び出し、シーン説明とオブジェクトリストを返す |
| **検出** | 検出されたオブジェクトと信頼度スコアをテーブル表示 |
| **チャット** | バックエンドAgentとのテキストインタラクション |

### APIエンドポイント

バックエンドは次のRESTエンドポイントを提供（ポート8000）:

| メソッド | パス | 説明 |
|---------|-----|------|
| GET | `/api/camera/frame` | 現在のフレームを取得（base64 JPEG） |
| POST | `/api/scene/describe` | qwen2.5vlシーン理解をトリガーし、説明とオブジェクトリストを返す |
| GET | `/api/detection/result` | 最新のオブジェクト検出結果を取得 |
| GET | `/healthz` | ヘルスチェック |

---

## 関連ドキュメント

- [VLAアダプターAPI](docs/api/vla_adapter.md)
- [スキルAPI](docs/api/skills.md)
- [はじめに](docs/guides/getting_started.md)
- [統合プラン](docs/integration_plan_v1.0_20260303_AI.md)

---

## ライセンス

MIT License - Copyright (c) 2024-2026

---

## 連絡先

- GitHub: https://github.com/hzm8341/EmbodiedAgentsSys
- ドキュメント: https://automatika-robotics.github.io/embodied-agents/
