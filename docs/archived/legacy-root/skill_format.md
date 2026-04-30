:orphan:

# Skill Frontmatter 格式规范

本文档定义 EmbodiedAgentsSys Skill 的 Markdown frontmatter 格式。

## 完整示例

```yaml
---
name: manipulation.grasp
description: "抓取指定物体"
requires:
  bins: ["lerobot"]          # 需要的 CLI 工具（由 shutil.which 检查）
  env: ["LEROBOT_HOST"]      # 需要的环境变量
always: false                # true = 始终加载到 context（用于核心技能）
metadata:
  tags: [manipulation, vla]
  robot_types: [arm, mobile_arm]
  eap:
    has_reverse: true                          # 是否存在配对的 reset 策略
    reverse_skill: "manipulation.reverse_grasp" # 逆向技能 ID（论文 §3.2）
---
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 技能唯一标识，推荐 `domain.action` 格式 |
| description | string | ✅ | 一句话描述技能功能 |
| requires.bins | list[str] | ❌ | 需要的 CLI 工具，缺失时 `available=false` |
| requires.env | list[str] | ❌ | 需要的环境变量，缺失时 `available=false` |
| always | bool | ❌ | true=始终注入 prompt，默认 false |
| metadata.eap.has_reverse | bool | ❌ | 是否有 EAP 逆向重置技能 |
| metadata.eap.reverse_skill | string | ❌ | 逆向技能的 name |

## 向后兼容

无 `requires` 和 `eap` 字段的旧 skill 默认 `available=true`，`eap_has_reverse=false`。

## EAP（Entangled Action Pairs）

论文 §3.2：每个技能可配对一个逆向 reset 技能，使机器人无需人工 reset 即可持续采集数据。

```yaml
# 正向技能（grasp）
---
name: manipulation.grasp
eap:
  has_reverse: true
  reverse_skill: "manipulation.reverse_grasp"
---

# 逆向技能（place-back）
---
name: manipulation.reverse_grasp
description: "将物体放回原位（EAP reset 策略）"
---
```
