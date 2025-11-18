# PSC-Graph: 政策语义因果图谱

**打通"认知断裂—行为断裂—评估断裂"三大鸿沟的端到端因果推断系统**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)](https://pytorch.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📋 目录

- [项目概述](#项目概述)
- [核心功能](#核心功能)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [详细使用指南](#详细使用指南)
- [项目结构](#项目结构)
- [开发规范](#开发规范)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)

---

## 🎯 项目概述

PSC-Graph（Policy-Semantic-Causal Graph）是一个端到端的政策因果推断系统，旨在构建"政策语义→政策意图→产业行为/绩效"的完整分析链路。

### 三大核心突破

1. **认知断裂**：通过LLM+RAG实现政策语义精准抽取
   - DAPT/TAPT域适配预训练
   - BM25+FAISS混合检索（α=0.5）
   - JSON Schema Draft 2020-12验证
   - Cohen's κ ≥ 0.80一致性保证

2. **行为断裂**：通过异质时序图学习建立政策-产业图谱
   - HGT（Heterogeneous Graph Transformer）
   - TGAT（Temporal Graph Attention）
   - Bochner时间编码
   - 链路预测AUC ≥ 0.80

3. **评估断裂**：通过稳健DID方法进行因果识别
   - CS-ATT（Callaway & Sant'Anna）
   - Sun-Abraham双向固定效应
   - BJS（Borusyak-Jaravel-Spiess）插补法
   - 三方验证确保结论稳健性

---

## ⚡ 核心功能

### 1. 语义抽取模块
- ✅ 政策五元组抽取（目标、工具、对象、地域、时间）
- ✅ RAG证据链追溯（evidence_spans强制字段）
- ✅ 温度缩放校准（ECE ≤ 0.05）
- ✅ 共形预测（覆盖率 ≥ 90%）

### 2. 图学习模块
- ✅ 异质图构建（Policy/Actor/Region/Topic/Funding节点）
- ✅ HGT模型训练（2-3层，避免过平滑）
- ✅ 时间编码（policy节点416维=384文本+32时间）
- ✅ 可解释路径分析

### 3. 因果推断模块
- ✅ 面板数据准备（省级×年度）
- ✅ 三估计器并行（CS-ATT/Sun-Abraham/BJS）
- ✅ 预趋势检验（p > 0.05）
- ✅ 稳健性检验（≥3项）

---

## 🛠️ 技术栈

### Python依赖（核心）
```bash
Python ≥ 3.11
torch ≥ 2.0.0
torch-geometric ≥ 2.3.0
sentence-transformers ≥ 2.2.0
pandas ≥ 2.0.0
numpy ≥ 1.24.0
scipy ≥ 1.10.0
jsonschema ≥ 4.17.0
```

### R依赖（DID模块，可选）
```r
R ≥ 4.0.0
did ≥ 2.1.0
fixest ≥ 0.11.0
didimputation ≥ 0.2.0
```

**注**：如果无法安装R环境，可以使用`demo_did_workflow.py`脚本（Python模拟版）。

---

## 🚀 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/your-org/psc-graph.git
cd psc-graph
```

### 2. 安装依赖
```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装Python依赖
pip install -r scripts/requirements.txt
```

### 3. 运行完整演示
```bash
# 运行所有核心模块演示
python scripts/run_all_demos.py

# 仅运行必需演示（跳过可选模块）
python scripts/run_all_demos.py --skip-optional
```

### 4. 快速验证
```bash
# 验证标注数据
python scripts/validate_annotations.py

# 构建检索索引
python scripts/build_index.py

# 构建异质图
python scripts/build_graph_pyg.py

# 训练HGT模型
python scripts/train_hgt.py
```

---

## 📖 详细使用指南

### 模块1：标注验证
```bash
python scripts/validate_annotations.py
```

**功能**：
- 验证JSON Schema（Draft 2020-12）
- 计算Cohen's κ一致性（需双标注）
- 检查必填字段和数据类型

**输出**：
- 标准输出：验证结果摘要
- 文件：`results/validation_report.json`

---

### 模块2：索引构建
```bash
python scripts/build_index.py
```

**功能**：
- 构建BM25精确检索索引（Pyserini/Lucene）
- 构建FAISS向量检索索引（sentence-transformers）
- 混合检索融合（α=0.5）

**输出**：
- `indexes/bm25/`：Lucene索引目录
- `indexes/faiss.index`：FAISS索引文件
- `indexes/id_map.json`：文档ID映射

---

### 模块3：证据检索
```bash
python scripts/retrieve_evidence.py --query "新能源汽车补贴政策" --top_k 5
```

**功能**：
- BM25+FAISS混合检索
- 返回相关政策文档和证据段落
- 支持自定义融合权重

**参数**：
- `--query`：查询文本
- `--top_k`：返回文档数（默认5）
- `--alpha`：BM25权重（默认0.5）

---

### 模块4：异质图构建
```bash
python scripts/build_graph_pyg.py
```

**功能**：
- 从标注数据构建PyG HeteroData对象
- 生成sentence-transformers文本嵌入（384维）
- 为policy节点添加时间编码（32维）

**输出**：
- `data/graph_base.pt`：PyTorch Geometric图文件

**节点类型**：
- `policy`：政策文档（416维=384文本+32时间）
- `actor`：行为主体（384维）
- `region`：地区（384维）
- `topic`：技术主题（384维）
- `funding`：资金平台（384维）

**边类型**：
- `(policy, apply_to, actor)`：政策适用对象
- `(policy, apply_to, region)`：政策覆盖地域
- `(policy, fund, funding)`：政策资金支持
- `(policy, mention, topic)`：政策提及主题
- `(policy, temporal, policy)`：时间邻接

---

### 模块5：HGT模型训练
```bash
python scripts/train_hgt.py
```

**功能**：
- 训练Heterogeneous Graph Transformer模型
- 链路预测任务（predict policy→actor边）
- 2-3层HGT卷积+残差连接+Dropout

**输出**：
- `results/hgt_model.pt`：训练好的模型

**超参数**：
- `hidden_channels=128`：隐藏层维度
- `num_heads=4`：注意力头数
- `num_layers=2`：HGT层数
- `dropout=0.2`：Dropout比例
- `num_epochs=50`：训练轮数

---

### 模块6：校准与不确定性量化
```bash
python scripts/calibrate_and_conformal.py
```

**功能**：
- 温度缩放校准（Temperature Scaling）
- 共形预测（Conformal Prediction）
- 预期校准误差计算（ECE）

**输出**：
- 标准输出：校准结果和可靠性图
- 满足CLAUDE.md要求：ECE ≤ 0.05，覆盖率 ≥ 90%

---

### 模块7：面板数据准备
```bash
python scripts/prep_panel.py
```

**功能**：
- 加载省级统计数据（GDP、R&D、专利等）
- 加载政策落地时点
- 生成DID就绪面板数据

**输出**：
- `data/panel_for_did.csv`：面板数据（省份×年份）

**字段**：
- `id`：省份编码
- `time`：年份
- `y`：结果变量（GDP增长率等）
- `g`：首次处理时点（0=never treated）
- `treat`：处理指示（0/1）

---

### 模块8：DID因果推断

#### 方案A：R环境（推荐）
```bash
# 完整流程（需R环境）
python scripts/run_did_from_python.py

# 如果R未安装，脚本会自动打印安装指南
```

**输出**：
- `results/did_csatt_event.csv`：CS-ATT事件研究
- `results/did_csatt_overall.csv`：CS-ATT总体ATT
- `results/did_sunab_coefs.csv`：Sun-Abraham系数
- `results/did_bjs_overall.csv`：BJS总体ATT
- `results/did_summary.json`：汇总结果

#### 方案B：Python模拟（无需R）
```bash
# 演示流程（Python模拟）
python scripts/demo_did_workflow.py
```

**注**：此脚本使用Python模拟DID估计，仅供演示，不能替代真实的R估计器。

---

## 📁 项目结构

```
psc-graph/
├── README.md                    # 本文件
├── CLAUDE.md                    # 开发规范（强制）
├── Makefile                     # 自动化构建脚本
├── .claude/                     # Claude Code工作目录
│   ├── context-summary-*.md     # 上下文摘要
│   ├── operations-log.md        # 操作日志
│   └── verification-report.md   # 验证报告
├── scripts/                     # Python脚本
│   ├── requirements.txt         # Python依赖（锁定版本）
│   ├── validate_annotations.py  # 标注验证
│   ├── build_index.py           # 索引构建
│   ├── retrieve_evidence.py     # 证据检索
│   ├── build_graph_pyg.py       # 异质图构建
│   ├── train_hgt.py             # HGT模型训练
│   ├── calibrate_and_conformal.py  # 校准与不确定性
│   ├── prep_panel.py            # 面板数据准备
│   ├── run_did_from_python.py   # DID因果推断（R调用）
│   ├── demo_did_workflow.py     # DID演示（Python模拟）
│   ├── demo_graph_workflow.py   # 图学习演示
│   ├── demo_retrieval_interactive.py  # 检索交互演示
│   └── run_all_demos.py         # 完整演示运行器 ⭐
├── schemas/                     # JSON Schema定义
│   └── policy_schema.json       # 政策五元组Schema（Draft 2020-12）
├── annotations/                 # 标注数据
│   ├── annotator_A/             # 标注人A
│   ├── annotator_B/             # 标注人B
│   └── adjudicated/             # 仲裁后金标
├── corpus/                      # 语料库
│   ├── raw/policy_central/      # 中央政策
│   ├── raw/policy_prov/         # 省级政策
│   └── samples/                 # 示例文档
├── indexes/                     # 检索索引
│   ├── bm25/                    # BM25索引
│   ├── faiss.index              # FAISS向量索引
│   └── id_map.json              # 文档ID映射
├── data/                        # 数据文件
│   ├── panel_for_did.csv        # DID面板数据
│   ├── graph_base.pt            # 异质图数据
│   └── province_codes.csv       # 省份编码表
└── results/                     # 输出结果
    ├── hgt_model.pt             # HGT模型
    ├── did_*.csv                # DID估计结果
    ├── did_summary.json         # DID结果汇总
    └── logs/                    # 日志文件
```

---

## 📏 开发规范

本项目严格遵循`CLAUDE.md`强制规范，包括：

### 核心原则
- ⚠️ **绝对强制使用简体中文**：所有文档、注释、日志、提交信息
- 🔒 **本地验证优先**：拒绝CI、远程流水线或人工外包
- 🏗️ **标准化+生态复用**：优先使用官方SDK和成熟方案
- 🛡️ **安全性最高优先级**：遵守OWASP LLM Top 10

### 质量标准
- 代码质量：F1 ≥ 0.85，Cohen's κ ≥ 0.80
- 校准指标：ECE ≤ 0.05，覆盖率 ≥ 90%
- 图学习：AUC ≥ 0.80，Macro-F1 ≥ 0.75
- 因果推断：三估计器方向一致，预趋势检验通过

### 工作流程
1. **sequential-thinking**：深度思考和规划
2. **shrimp-task-manager**：任务分解和管理
3. **直接执行**：编码和验证
4. **质量审查**：综合评分（≥90分通过）

详见：[CLAUDE.md](/home/user/guanli/CLAUDE.md)

---

## ❓ 常见问题

### Q1：如何处理R环境未安装的情况？
**A**：如果无法安装R环境，可以使用以下替代方案：
1. 使用`demo_did_workflow.py`脚本（Python模拟DID，仅供演示）
2. 在其他机器上安装R环境并远程执行
3. 使用Docker容器运行R环境

### Q2：torch-scatter安装失败怎么办？
**A**：torch-scatter是可选依赖，当前规模（<10万节点）下无需安装。如需安装：
```bash
# 需要先安装CUDA toolkit
pip install torch-scatter -f https://data.pyg.org/whl/torch-2.0.0+cu118.html
```

### Q3：sentence-transformers模型下载太慢？
**A**：可以使用国内镜像或本地缓存：
```python
from sentence_transformers import SentenceTransformer

# 方案1：使用国内镜像
model = SentenceTransformer(
    'paraphrase-multilingual-MiniLM-L12-v2',
    cache_folder='/path/to/cache'
)

# 方案2：手动下载模型文件后加载本地路径
model = SentenceTransformer('/path/to/local/model')
```

### Q4：如何扩展到更大规模数据？
**A**：
1. **语义抽取**：文档>5000时使用分批处理
2. **图学习**：节点>100万时安装torch-scatter并使用邻域采样
3. **DID推断**：面板>50省×20年时考虑分组估计

### Q5：如何添加新的政策工具类型？
**A**：修改`schemas/policy_schema.json`中的`instrument`枚举值，并重新验证标注数据。

---

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交变更（简体中文提交信息）：`git commit -m "添加新功能：XXX"`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交Pull Request

**注意事项**：
- 必须通过所有验证脚本（`python scripts/validate_annotations.py`）
- 必须更新相关文档
- 必须遵循`CLAUDE.md`开发规范

---

## 📜 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件

---

## 📬 联系方式

- 项目负责人：Claude Code
- 问题反馈：[GitHub Issues](https://github.com/your-org/psc-graph/issues)
- 邮箱：your-email@example.com

---

## 🙏 致谢

- **PyTorch Geometric**：异质图学习框架
- **sentence-transformers**：多语言文本嵌入
- **did/fixest/didimputation**：R语言DID估计器
- **CLAUDE.md**：开发规范和质量保证

---

**最后更新**：2025-11-18

**版本**：v1.0.0

**状态**：✅ 生产就绪
