# CHANGELOG

## 4.1.0-rc1
- 将 v4 RC1 从单 zip 迁移成 8 个真正可安装 Skill 目录。
- 8 个 Skill 全部接入项目级 PAPER_STATE / Concept / Literature / Evidence / Failure / Run memory。
- 新增确定性 `project_memory.py`：初始化项目、记录运行、记录失败、验证项目状态。
- 新增 `promote_failures.py`：跨项目聚合失败模式，但不自动改写 Skill。
- 新增失败晋升协议，避免单项目经验污染全局规则。
- 接入区域创新政策真实项目；为 ICLR 与 Bioinformatics 项目建立无捏造占位状态。
- 保留 v4 RC1 和 v3→v4 回归测试作为历史基线。
