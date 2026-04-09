# Lessons Learned Protocol

## Schema

```json
{
  "schema_version": "EmbodiedAgentsSys.lessons.v1",
  "lessons": [
    {
      "action_type": "grasp",
      "params": {"target": "red_ball"},
      "failure_reason": "Object too far from gripper",
      "avoidance_suggestion": "Move to within 0.1m before grasping"
    }
  ]
}
```

## Purpose

Following 《工业Agent设计准则》P4闭环:
- Records failed action attempts
- Used by CriticValidator to prevent repeated mistakes
- Provides avoidance suggestions for Planner

## Notes

- New lessons should be added after each failed action
- Duplicate lessons (same action_type + params) should be deduplicated
- This file is append-only for audit trail
