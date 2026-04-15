"""MuJoCo 仿真配置常量"""

# 仿真参数
DEFAULT_TIMESTEP = 0.002  # 2ms, MuJoCo 推荐
DEFAULT_FRAME_SKIP = 1

# 物理参数
DEFAULT_GRAVITY = (0.0, 0.0, -9.81)
CONTACT_STIFFNESS = 1.0e4
CONTACT_DAMPING = 1.0e3

# 动作约束
POSITION_LIMIT = 2.0  # 工作空间半径 (m)
Z_HEIGHT_LIMIT = 1.5  # Z 轴最大高度 (m)
VELOCITY_LIMIT = 1.0  # 最大速度 (m/s)
FORCE_LIMIT = 100.0  # 最大力 (N)

# 场景参数
DEFAULT_SCENE = {
    "ground": True,
    "table_height": 0.0,
    "table_size": (1.0, 1.0),
}

# URDF 路径配置
DEFAULT_URDF_PATH = "assets/eyoubot/eu_ca_simple.urdf"

# 传感器参数
FORCE_SENSOR_SIZE = 6  # Fx, Fy, Fz, Mx, My, Mz
CONTACT_SENSOR_SIZE = 100  # 最大接触点数
