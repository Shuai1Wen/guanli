## 项目上下文摘要（PSC-Graph深度分析）
生成时间：2025-12-02

### 1. 相似实现分析

#### 实现1：HGT模型训练（scripts/train_hgt.py）
- **模式**：异质图Transformer（HGTConv）
- **架构**：2层HGTConv + Residual连接 + Dropout
- **可复用**：
  - TrainingConfig数据类（超参数管理）
  - setup_device()（设备管理）
  - train_link_prediction()（链路预测训练循环）
- **需注意**：
  - 已修复梯度失效和NaN问题（commit d0b6bba）
  - 使用Linear(-1, hidden_channels)自动推断输入维度
  - 梯度裁剪（max_grad_norm=1.0）防止梯度爆炸
  - 仅实现HGT，缺少TGAT

#### 实现2：异质图构建（scripts/build_graph_pyg.py）
- **模式**：从标注数据构建PyG HeteroData
- **时间编码**：使用正弦-余弦编码（非Bochner）
  - policy节点：384维文本嵌入 + 32维时间编码 = 416维
  - 其他节点：384维文本嵌入
- **可复用**：
  - GraphBuilder类（节点/边管理）
  - _generate_node_embeddings()（使用sentence-transformers）
  - _generate_time_encoding()（正弦-余弦编码）
- **需注意**：
  - **关键问题**：使用简单时间编码，未使用Bochner编码
  - 时间戳解析失败率>10%会报错
  - 支持5种节点类型和5种边类型

#### 实现3：Bochner时间编码器（scripts/models/bochner_time_encoder.py）
- **模式**：基于随机傅里叶特征（RFF）的可学习时间编码
- **理论**：Bochner定理，频率可学习
- **可复用**：
  - BochnerTimeEncoder类（基础版）
  - BochnerTimeEncoderV2类（多尺度+MLP）
  - forward()方法（支持Unix时间戳输入）
- **需注意**：
  - **关键问题**：已实现但未被build_graph_pyg.py使用
  - 频率从N(0, σ²)初始化，可训练
  - 支持多尺度（低频捕捉年度，高频捕捉月度）
  - 数值稳定性良好（已测试）

#### 实现4：RAG混合检索（scripts/retrieve_evidence.py）
- **模式**：BM25（精确）+ FAISS（语义，可选）
- **融合**：α=0.5混合融合（可配置）
- **可复用**：
  - HybridRetriever类
  - bm25_search()、faiss_search()、hybrid_search()
  - 分数归一化和融合逻辑
- **需注意**：
  - FAISS是可选的（需sentence-transformers）
  - 当前默认使用纯BM25（use_faiss=False）
  - **缺失**：没有DAPT/TAPT预训练脚本

### 2. 项目约定

#### 命名约定
- 文件名：snake_case（如build_graph_pyg.py）
- 类名：PascalCase（如HGT、GraphBuilder）
- 函数名：snake_case（如load_graph、train_link_prediction）
- 变量名：snake_case（如hidden_channels、num_layers）
- 常量：UPPER_CASE（如TORCH_AVAILABLE）

#### 文件组织
```
scripts/
├── build_graph_pyg.py          # 图构建
├── train_hgt.py                # HGT训练（缺TGAT）
├── retrieve_evidence.py        # RAG检索
├── models/
│   └── bochner_time_encoder.py # Bochner编码（未使用）
data/
├── graph_base.pt               # 异质图数据
├── seeds/seeds_sites.yaml      # 爬虫配置
schemas/
└── policy_schema.json          # 标注规范
```

#### 导入顺序
1. 标准库（os, sys, pathlib等）
2. 第三方库（torch, numpy, pandas等）
3. 项目模块（相对导入）

#### 代码风格
- 缩进：4空格
- 行长度：≤100字符（文档字符串可更长）
- 文档字符串："""三引号"""，包含Args、Returns、Raises
- 注释：使用简体中文
- 类型提示：使用typing模块

### 3. 可复用组件清单

#### 图学习组件
- `scripts/train_hgt.py::HGT`：异质图Transformer模型
- `scripts/train_hgt.py::TrainingConfig`：训练配置数据类
- `scripts/build_graph_pyg.py::GraphBuilder`：图构建器

#### 时间编码组件
- `scripts/models/bochner_time_encoder.py::BochnerTimeEncoder`：可学习时间编码
- `scripts/models/bochner_time_encoder.py::BochnerTimeEncoderV2`：多尺度版本

#### 检索组件
- `scripts/retrieve_evidence.py::HybridRetriever`：混合检索器

#### 工具函数
- `scripts/train_hgt.py::setup_device()`：设备管理
- `scripts/train_hgt.py::load_graph()`：图数据加载
- `scripts/build_graph_pyg.py::_generate_node_embeddings()`：文本嵌入生成

### 4. 测试策略

#### 测试框架
- 未明确（需要推断或询问）
- bochner_time_encoder.py包含内置测试函数test_bochner_encoder()

#### 测试模式
- 单元测试：每个模块的基本功能
- 集成测试：端到端工作流（如demo_graph_workflow.py）
- 数值稳定性测试：NaN/Inf检测

#### 参考文件
- `scripts/models/bochner_time_encoder.py::test_bochner_encoder()`：测试示例
  - 基本功能测试（输入输出维度）
  - 梯度反向传播测试
  - 数值稳定性测试（大时间戳）
  - 多尺度编码器测试

#### 覆盖要求
- 正常流程：基本前向传播
- 边界条件：空输入、大时间戳、异常时间格式
- 错误处理：NaN检测、维度不匹配、缺失依赖

### 5. 依赖和集成点

#### 外部依赖
- **PyTorch生态**：torch, torch-geometric, torch-scatter, torch-sparse
- **NLP**：sentence-transformers（paraphrase-multilingual-MiniLM-L12-v2, 384维）
- **检索**：jieba, scikit-learn, faiss-cpu（可选）
- **数据处理**：pandas, numpy
- **工具**：pdfplumber, beautifulsoup4, requests

#### 内部依赖
- build_graph_pyg.py → annotations/标注数据
- train_hgt.py → data/graph_base.pt
- retrieve_evidence.py → indexes/（BM25、FAISS、元数据）

#### 集成方式
- 文件I/O：torch.save/load（图数据）、json（元数据）、pickle（索引）
- 直接调用：模块间通过import导入
- 数据流：标注数据 → 图结构 → HGT训练 → 链路预测

#### 配置来源
- data/seeds/seeds_sites.yaml：爬虫种子配置
- schemas/policy_schema.json：标注规范
- TrainingConfig数据类：训练超参数

### 6. 技术选型理由

#### 为什么用HGT？
- **优势**：
  - 支持异质图（多种节点/边类型）
  - 注意力机制捕捉结构信息
  - 可扩展到大规模图
- **劣势和风险**：
  - **缺少时序建模**：仅依赖静态时间编码，无法捕捉时序动态
  - 计算开销大（注意力O(n²)）
  - 过平滑风险（需限制2-3层）

#### 为什么需要TGAT？
- **CLAUDE.md强制要求**：HGT+TGAT架构
- **时序图注意力**：显式建模时间邻接关系
- **互补关系**：
  - HGT捕捉异质性（不同节点/边类型）
  - TGAT捕捉时序性（政策发布→生效→影响的时间演化）
- **缺失影响**：当前实现无法捕捉政策的时序依赖关系

#### 为什么用Bochner编码？
- **优势**：
  - 频率可学习（vs 固定的正弦-余弦编码）
  - 多尺度（年度周期+月度周期）
  - 理论保证（Bochner定理）
- **当前问题**：已实现但未被使用
- **替代方案**：build_graph_pyg.py使用简单正弦-余弦编码

#### 为什么用RAG？
- **CLAUDE.md规范**：BM25+FAISS混合检索
- **避免LLM幻觉**：强制evidence_spans追溯原文
- **当前状态**：基础BM25实现完成，FAISS可选

### 7. 关键风险点

#### 架构完整性风险
- **风险**：缺少TGAT，无法完成端到端时序建模
- **影响**：高（违反CLAUDE.md强制规范）
- **缓解**：优先实现TGAT或论证HGT+Bochner足够

#### 时间编码不一致风险
- **风险**：Bochner已实现但未使用，build_graph_pyg.py使用简单编码
- **影响**：中（性能可能不最优，但系统可运行）
- **缓解**：集成Bochner到build_graph_pyg.py

#### NLP管道缺失风险
- **风险**：没有DAPT/TAPT预训练脚本
- **影响**：高（影响语义抽取质量）
- **缓解**：实现DAPT/TAPT或使用零样本LLM（不符合规范）

#### 数据采集不完整风险
- **风险**：5个省份采集失败
- **影响**：中（训练数据不足）
- **缓解**：诊断已完成，需修复或降级处理

#### 依赖缺失风险
- **风险**：torch-scatter/torch-sparse可能未安装
- **影响**：中（HGT无法运行）
- **缓解**：检查并安装依赖
