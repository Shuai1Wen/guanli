## 项目上下文摘要（代码重构优化任务）
生成时间: 2025-11-18

### 1. 相似实现分析

**实现1**: scripts/demo_graph_workflow.py:34-87 (main函数)
- 模式: 直接函数调用模式
- 可复用: `Path(__file__).parent.parent` 获取项目根目录
- 需注意:
  - 每个子函数职责单一（加载、统计、分布、验证、元数据）
  - 主函数仅负责流程编排和错误处理
  - 使用明确的步骤标记（【步骤1】等）

**实现2**: scripts/prep_panel.py:32-361 (类方法模式)
- 模式: 类封装 + 方法拆分
- 可复用:
  - `PanelDataPreparer` 类封装所有逻辑
  - `run()` 方法作为主流程入口
  - 每个方法返回明确的结果类型
- 需注意:
  - 类初始化中处理配置和路径
  - 使用类型注解增强可读性
  - 私有方法使用 `_` 前缀

**实现3**: scripts/validate_annotations.py:31-354 (类方法模式)
- 模式: 类封装 + 命令行参数
- 可复用:
  - 配置常量在 `__init__` 中定义（`QUALITY_THRESHOLDS`）
  - 方法返回值使用 `Tuple[返回类型, ...]`
  - 详细的文档字符串说明参数和返回值
- 需注意:
  - 使用 `argparse` 处理命令行参数
  - 主函数仅负责参数解析和流程调用

**实现4**: scripts/calibrate_and_conformal.py:455-484 (demo_calibration函数)
- 模式: 函数拆分模式（目标重构对象）
- 当前状态: 已经拆分为5个子函数
  - `generate_mock_data()` - 数据生成
  - `evaluate_uncalibrated_model()` - 未校准评估
  - `perform_temperature_scaling()` - 温度缩放
  - `perform_conformal_prediction()` - 共形预测
  - `print_reliability_diagram()` - 可靠性图
- 需注意: 函数已经拆分良好，主要问题是参数传递

**实现5**: scripts/train_hgt.py:359-389 (main函数)
- 模式: 函数拆分模式（目标重构对象）
- 当前状态: 已经拆分为4个子函数
  - `load_graph()` - 加载图数据
  - `initialize_model_and_data()` - 初始化模型
  - `run_training_loop()` - 训练循环
  - `save_trained_model()` - 保存模型
- 需注意: 函数拆分已经完成，主要问题是参数硬编码

### 2. 项目约定

**命名约定**:
- 类名: PascalCase (如 `HybridRetriever`, `PanelDataPreparer`)
- 函数名: snake_case (如 `load_graph`, `perform_temperature_scaling`)
- 私有方法: `_前缀` (如 `_load_schema`, `_generate_node_embeddings`)
- 常量: UPPER_CASE (如 `QUALITY_THRESHOLDS`, `PROJECT_ROOT`)

**文件组织**:
- 项目根目录获取: `Path(__file__).parent.parent`
- 数据目录: `project_root / 'data'`
- 输出目录: `project_root / 'results'`
- 临时/Claude文件: `project_root / '.claude'`

**导入顺序**:
1. 标准库 (sys, json, pathlib等)
2. 第三方库 (torch, numpy, pandas等)
3. 项目内模块

**代码风格**:
- 使用类型注解 (`-> Tuple[bool, List[str]]`)
- 详细的docstring（描述功能、参数、返回值）
- 4空格缩进
- 中文注释和文档字符串

### 3. 可复用组件清单

- `pathlib.Path` 对象: 统一路径处理
  - 路径拼接: `path / 'subdir' / 'file.txt'`
  - 创建目录: `path.mkdir(parents=True, exist_ok=True)`
  - 文件存在检查: `path.exists()`
  - 遍历文件: `path.glob('*.json')`

- 步骤标记模式: `print("\n【步骤X】 描述")`
- 分隔线: `print("-" * 80)` 或 `print("=" * 80)`
- 参数验证: 在函数开始处检查参数有效性
- 错误处理: 使用 try-except 并输出清晰的错误信息

### 4. 测试策略

项目使用演示脚本（demo_*.py）作为测试验证：
- `demo_graph_workflow.py`: 图数据验证
- `demo_retrieval_interactive.py`: 检索功能测试
- `demo_did_workflow.py`: DID流程测试

**测试模式**:
- 每个模块有独立的 `main()` 函数用于演示
- 使用 `if __name__ == "__main__":` 保护执行代码
- 输出详细的进度信息和验证结果

### 5. 依赖和集成点

**train_hgt.py 依赖**:
- PyTorch + PyTorch Geometric
- 图数据文件: `data/graph_base.pt`
- 输出模型: `results/hgt_model.pt`

**calibrate_and_conformal.py 依赖**:
- numpy, scipy (温度缩放优化)
- 无外部数据依赖（使用mock数据）
- 输出: JSON格式的校准报告

### 6. 技术选型理由

**为什么使用函数拆分而非类**:
- `train_hgt.py` 和 `calibrate_and_conformal.py` 都是线性流程
- 函数之间无共享状态
- 简化代码结构，避免过度工程化

**为什么使用pathlib.Path**:
- 跨平台兼容性（自动处理 `/` vs `\`）
- 更清晰的API（`/` 运算符拼接路径）
- 内置方法丰富（exists, mkdir, glob等）
- 符合现代Python最佳实践

### 7. 关键风险点

**重构风险**:
- 过度拆分: 导致参数传递复杂
- 向后兼容: 修改函数签名可能影响其他脚本
- 测试覆盖: 缺少自动化测试，需要手动验证

**Path对象统一风险**:
- 字符串到Path的转换: 某些库只接受字符串路径
- 性能影响: Path对象创建有轻微开销（可忽略）
- 代码一致性: 需要全面检查并修改所有路径操作

**建议的缓解措施**:
1. 保留原有函数签名，添加新函数
2. 使用 `str(path)` 转换给需要字符串的库
3. 分批重构，每次提交运行演示脚本验证
4. 在operations-log.md记录所有修改

### 8. 当前代码状态评估

**train_hgt.py::main() 分析**:
- 实际代码行数: 31行（359-389）
- 已拆分函数: 4个
- **评估**: 拆分已经完成，结构清晰
- **问题**:
  - 参数硬编码（graph_path, hidden_channels, num_epochs等）
  - 无配置文件支持
  - 设备选择逻辑简单（仅CPU/CUDA）
- **建议**: 提取配置而非继续拆分

**calibrate_and_conformal.py::demo_calibration() 分析**:
- 实际代码行数: 30行（455-484）
- 已拆分函数: 5个
- **评估**: 拆分已经完成，结构优秀
- **问题**:
  - 参数硬编码（n_samples, n_classes, alpha等）
  - 改进信息计算逻辑在main中
- **建议**: 提取参数传递逻辑，优化信息流

### 9. pathlib.Path使用现状

**已使用Path的文件** (25个):
- build_graph_pyg.py ✓
- train_hgt.py ✓
- calibrate_and_conformal.py ✓
- prep_panel.py ✓
- validate_annotations.py ✓
- 其他20个文件...

**未完全统一**:
- 某些函数参数仍接受 `str` 类型路径
- 某些地方混用 `str` 和 `Path`
- 需要统一为：函数参数接受 `Path` 或 `str`，内部统一转换为 `Path`

### 10. 重构优先级评估

**优先级1（高）- Path统一**:
- 影响范围: 所有文件
- 收益: 代码一致性、可维护性
- 风险: 低（向后兼容，逐步迁移）
- 工作量: 中等

**优先级2（中）- 配置提取**:
- 影响范围: train_hgt.py, calibrate_and_conformal.py
- 收益: 灵活性、可配置性
- 风险: 低
- 工作量: 低

**优先级3（低）- 继续拆分main函数**:
- 影响范围: 2个文件
- 收益: 有限（已经拆分得很好）
- 风险: 中（过度拆分可能降低可读性）
- 工作量: 低
- **建议**: 不建议继续拆分

### 11. 推荐重构方案

**方案A（推荐）- 配置驱动重构**:
1. 为 train_hgt.py 添加配置类/字典
2. 为 calibrate_and_conformal.py 添加配置参数
3. 统一路径为 Path 对象
4. 保持现有函数拆分结构

**方案B（不推荐）- 继续拆分**:
1. 将 main 中的硬编码部分拆分为 `setup_config()`
2. 将设备选择拆分为 `select_device()`
3. 风险: 过度拆分，参数传递复杂

**方案C（折中）- 类封装重构**:
1. 创建 `HGTTrainer` 类封装训练逻辑
2. 创建 `CalibrationWorkflow` 类封装校准逻辑
3. 风险: 引入复杂性，可能不符合项目简洁风格
