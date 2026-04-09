# Simulation Driver Profile

## Safety Whitelist (P6)

| Action | Parameters | Constraints |
|--------|------------|-------------|
| move_to | x, y, z | x,y ∈ [-2.0, 2.0], z ∈ [0.0, 1.5] |
| move_relative | dx, dy, dz | velocity ≤ 1.0 m/s |
| grasp | force | force ∈ [0.0, 1.0] |
| release | - | - |

## Emergency Stop

- Always available regardless of state
- Immediately halts all motion
- Logs event to audit trail

## 闭环确认

Every execute_action returns ExecutionReceipt with:
- receipt_id: Unique identifier for tracking
- status: SUCCESS/FAILED/TIMEOUT/EMERGENCY_STOP
- result_data: Detailed execution data
