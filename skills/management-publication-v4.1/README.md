# Management Publication Skills v4.1 RC1

以“把管理学研究真正推进到可投稿论文”为目标的 Agent Skill Registry。

## 核心研究脊柱

`Research Object → Academic Mountain → Substantive Anchor → Paper Archetype → Paper Thesis → Novelty Delta → Study Design → Evidence → Belief Update → Submission`

## 目录

- `skills/`：8 个可独立安装的 Agent Skills。
- `shared/templates/`：项目级研究状态与证据/文献/概念/失败模板。
- `shared/runtime/`：确定性项目记忆与失败聚合脚本。
- `projects/`：真实项目运行状态与日志。
- `evaluations/`：冻结回归测试与真实项目评估协议。

## 研究记忆原则

- 项目级失败可以立即成为该项目的防复发规则。
- 全局 Skill **不自动自我改写**。
- 只有跨项目重复失败或 P0 失败才进入全局规则候选，并且必须经过回归测试后才能升级版本。

这是为了让系统“会学习”，但不因单一项目过拟合。

## 安装

将 `skills/<skill-name>/` 整个目录复制到目标 Agent 的 Skills 目录。每个 Skill 自包含 `SKILL.md`、`agents/openai.yaml` 和必要 `references/`。

项目记忆层不是 Skill 安装的硬依赖；在长期项目中启用它可以保持研究主线和失败经验。
