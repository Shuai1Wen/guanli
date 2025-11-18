# PSC-Graph: 政策语义因果图谱

[![项目状态](https://img.shields.io/badge/状态-开发中-yellow.svg)]()
[![Python版本](https://img.shields.io/badge/python-3.8+-blue.svg)]()
[![许可证](https://img.shields.io/badge/license-MIT-green.svg)]()

---

## 📖 项目简介

**PSC-Graph**（Policy Semantic Causal Graph，政策语义因果图谱）旨在构建"政策语义→政策意图→产业行为/绩效"的端到端分析体系，打通政策研究中的三大鸿沟：

- **认知断裂**：通过LLM+RAG实现政策语义抽取
- **行为断裂**：通过异质时序图学习(HGT+TGAT)建立政策-产业图谱
- **评估断裂**：通过稳健DID方法(CS-ATT/Sun-Abraham/BJS)进行因果识别

---

## 🚀 快速开始

### 环境要求

**必须依赖**：
- Python 3.8+
- Java 11+（用于Lucene/BM25索引）
- R 4.0+（用于因果推断）

**可选依赖**：
- CUDA 11.8+（用于GPU加速图学习）
- Docker（用于容器化部署）

### 一键安装

```bash
# 1. 克隆仓库
git clone https://github.com/Shuai1Wen/guanli.git
cd guanli

# 2. 环境初始化（创建虚拟环境、安装依赖）
bash scripts/bootstrap.sh

# 3. 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

### 快速演示

我们提供了3个独立的演示脚本，无需完整数据即可快速验证系统功能：

```bash
# Demo 1: DID因果推断工作流（无需R环境）
python3 scripts/demo_did_workflow.py

# Demo 2: 图学习工作流（torch-optional）
python3 scripts/demo_graph_workflow.py

# Demo 3: 语义检索交互演示
python3 scripts/demo_retrieval_interactive.py
```

---

## 📁 项目结构

```
psc-graph/
├── README.md                 # 本文件
├── CLAUDE.md                 # 开发准则（强制遵守）
├── Makefile                  # 自动化构建目标
├── scripts/                  # 核心脚本
│   ├── bootstrap.sh          # 环境初始化
│   ├── crawl_gov_central.py  # 中央政策爬虫
│   ├── build_index.py        # BM25+FAISS索引构建
│   ├── build_graph_pyg.py    # 异质图构建
│   ├── train_hgt.py          # HGT模型训练
│   ├── prep_panel.py         # DID面板准备
│   ├── run_did_from_python.py# Python→R桥接
│   └── did_run.R             # DID三估计器实现
├── docs/                     # 文档
│   ├── 01_数据爬取方案.md
│   ├── 02_语义抽取方案.md
│   ├── 03_标注与评估方案.md
│   ├── 04_图学习方案.md
│   ├── 05_因果推断方案.md
│   └── annotation_guide.md   # 标注指南
├── schemas/
│   └── policy_schema.json    # JSON Schema验证规范
├── corpus/                   # 政策文档语料
│   ├── raw/                  # 原始HTML/JSON
│   └── samples/              # 示例文档
├── indexes/                  # 检索索引
│   ├── bm25/                 # Lucene索引
│   ├── faiss.index           # 向量索引
│   └── doc_metadata.json     # 文档元数据
├── data/                     # 数据文件
│   ├── panel_for_did.csv     # DID面板数据
│   └── policy_landing.csv    # 政策落地时点
└── results/                  # 输出结果
    ├── logs/                 # 日志文件
    └── checkpoints/          # 断点续爬状态
```

---

## 🛠️ 核心功能

### 1. 数据采集层

**支持的数据源**：
- ✅ 国务院政策文件库（中央政策）
- ✅ 广东省科技厅（省级政策示范）
- ✅ 国家统计局（宏观经济指标）
- ✅ 国家知识产权局（专利数据）

**合规保证**：
- QPS ≤ 1.0（政府网站）
- 遵守robots.txt
- 断点续爬+SHA256去重

**示例**：
```bash
# 爬取中央政策（2009-2024）
python3 scripts/crawl_gov_central.py \
  --start-year 2009 \
  --end-year 2024 \
  --qps 0.8
```

### 2. 语义抽取层

**技术栈**：
- LLM：Claude/GPT-4（DAPT/TAPT域适配）
- 检索：BM25（精确匹配）+ FAISS（语义相似）
- 嵌入：sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2（384维）
- 校准：温度缩放（ECE ≤ 0.05）

**五元组抽取**：
```json
{
  "goal": "完善绿色贸易政策制度体系",
  "instrument": ["funding", "tax", "platform"],
  "target_actor": "出口企业",
  "strength": 2,
  "evidence_spans": [{"start": 120, "end": 250, "from_doc": "policy"}],
  "confidence": 0.92
}
```

**质量门槛**：
- F1 ≥ 0.85（实体/关系抽取）
- Cohen's κ ≥ 0.80（标注一致性）
- ARES评测：上下文相关性≥0.85、忠实度≥0.90

**示例**：
```bash
# 构建混合检索索引
python3 scripts/build_index.py \
  --corpus-dir corpus/raw/policy_central \
  --output-dir indexes

# 交互式检索演示
python3 scripts/demo_retrieval_interactive.py
```

### 3. 图学习层

**模型架构**：
- 异质图：5种节点类型（policy, actor, region, topic, funding）
- 时序建模：HGT（异质图Transformer）+ TGAT（时序图注意力）
- 特征维度：
  - policy节点：416维（384文本嵌入 + 32时间编码）
  - 其他节点：384维（文本嵌入）

**示例**：
```bash
# 构建异质图（PyTorch Geometric格式）
python3 scripts/build_graph_pyg.py \
  --corpus-dir corpus/raw \
  --output data/graph_base.pt

# 训练HGT模型（需要GPU）
python3 scripts/train_hgt.py \
  --graph-path data/graph_base.pt \
  --hidden-dim 128 \
  --num-layers 2 \
  --epochs 100
```

### 4. 因果推断层

**DID估计器（三方验证）**：
- CS-ATT：Callaway & Sant'Anna (2021)
- Sun-Abraham：Sun & Abraham (2021)
- BJS：Borusyak-Jaravel-Spiess (2024)

**必须满足**：
- 预趋势检验（p > 0.05）
- 三估计器方向一致
- 稳健性检验≥3项

**示例**：
```bash
# 准备DID面板数据
python3 scripts/prep_panel.py \
  --nbs-panel data/nbs_panel_long.csv \
  --policy-landing data/policy_landing.csv \
  --output data/panel_for_did.csv

# 运行三估计器（需要R环境）
python3 scripts/run_did_from_python.py \
  --panel data/panel_for_did.csv \
  --output-dir results/did_estimates

# 简化DID演示（无需R）
python3 scripts/demo_did_workflow.py
```

---

## 📦 依赖说明

### Python依赖（requirements.txt）

**核心依赖**：
```
# 数据处理
pandas>=1.5.0
numpy>=1.23.0

# NLP与嵌入
sentence-transformers>=2.2.0
jieba>=0.42.1

# 检索
faiss-cpu>=1.7.4  # 或 faiss-gpu（需要CUDA）
scikit-learn>=1.2.0

# 图学习
torch>=2.0.0
torch-geometric>=2.3.0
# torch-scatter  # 需要手动编译或conda安装
# torch-sparse   # 需要手动编译或conda安装

# 爬虫
requests>=2.28.0
beautifulsoup4>=4.11.0
pdfplumber>=0.9.0

# 验证与序列化
jsonschema>=4.17.0
```

**安装方式**：
```bash
# 标准安装
pip install -r scripts/requirements.txt

# 使用conda安装图学习依赖（推荐）
conda install pytorch-geometric -c pyg

# 或使用预编译wheel
pip install torch-scatter torch-sparse -f https://data.pyg.org/whl/torch-2.0.0+cu118.html
```

### R依赖

**必须R包**：
```r
install.packages(c(
  "did",              # Callaway & Sant'Anna
  "fixest",           # Sun & Abraham
  "didimputation",    # BJS
  "ggplot2",          # 可视化
  "dplyr"             # 数据处理
))
```

**快速安装**：
```bash
# 自动安装R包（首次运行时）
python3 scripts/run_did_from_python.py
# 脚本会自动检测并安装缺失的R包
```

---

## 🔧 Makefile目标

我们提供了标准化的Make目标简化工作流：

```bash
# 环境初始化
make setup          # 创建venv、安装依赖、配置Java/R

# 数据验证
make validate       # 标注校验 + Cohen's κ

# 索引构建
make index          # BM25 + FAISS构建

# 检索演示
make retrieve       # 混合检索演示

# 图学习
make graph          # HGT模型前向

# DID面板
make panel          # DID面板准备

# 因果推断
make did            # CS-ATT + SA + BJS并行

# 完整流程
make all            # validate → index → panel → did

# 清理
make clean          # 清理缓存与中间文件
```

---

## 📊 质量验收标准

### 模块A：语义抽取
- ✅ F1 ≥ 0.85（实体/关系）
- ✅ Cohen's κ ≥ 0.80（一致性）
- ✅ ARES评测：上下文相关性≥0.85、忠实度≥0.90、答案相关性≥0.88
- ✅ 证据命中率≥0.90

### 模块B：图学习
- ✅ 链路预测 AUC ≥ 0.80
- ✅ 节点分类 Macro-F1 ≥ 0.75
- ✅ 路径可解释性：≥10个高权重路径回查成功

### 模块C：因果推断
- ✅ 三估计器方向一致
- ✅ 预趋势检验 p > 0.05
- ✅ 稳健性检验≥3项通过

### 端到端：校准与不确定性
- ✅ ECE ≤ 0.05（温度缩放后）
- ✅ 共形预测覆盖率≥90%（α=0.1）
- ✅ 关键决策附不确定性说明

---

## 📝 开发准则

本项目遵循严格的开发规范，详见 **[CLAUDE.md](CLAUDE.md)**：

**强制要求**：
- ✅ 所有文档、注释、提交信息使用**简体中文**
- ✅ 所有验证由**本地AI自动执行**，禁止CI、远程流水线或人工外包
- ✅ 每次改动必须提供可重复的**本地验证步骤**
- ✅ 代码质量强制标准（SOLID、DRY、测试覆盖）
- ✅ 安全性原则（OWASP LLM Top 10、数据合规）

**工作流程**：
1. 使用sequential-thinking梳理问题
2. 执行7步强制上下文检索（编码前必做）
3. 通过充分性验证（7项检查）
4. 生成上下文摘要文件
5. 编码实现
6. 本地验证
7. 提交

---

## 🧪 测试与验证

### 单元测试

```bash
# 运行所有测试（待实现）
pytest tests/

# 测试覆盖率
pytest --cov=scripts tests/
```

### 演示脚本验证

```bash
# DID工作流验证（已通过）
python3 scripts/demo_did_workflow.py
# ✓ 加载403行面板数据
# ✓ 平衡性、一致性、完整性检验通过
# ✓ 处理效应估计: 0.0320（接近真实0.03）

# 图学习验证（torch-optional）
python3 scripts/demo_graph_workflow.py
# ✓ 显示预期图结构
# ✓ 维度验证（policy=416, 其他=384）

# 检索系统验证（已通过）
python3 scripts/demo_retrieval_interactive.py
# ✓ BM25索引加载成功
# ✓ FAISS索引可用
# ✓ 检索结果正确返回
```

---

## 🔍 故障排查

### 常见问题

**Q1: torch-scatter/torch-sparse安装失败**

A: 使用conda或预编译wheel：
```bash
# 方案1：conda（推荐）
conda install pytorch-geometric -c pyg

# 方案2：预编译wheel
pip install torch-scatter torch-sparse \
  -f https://data.pyg.org/whl/torch-2.0.0+cu118.html

# 方案3：Docker
docker pull pyg/pyg:latest
```

**Q2: R脚本执行失败**

A: 检查R环境和包：
```bash
# 检查R版本
R --version  # 需要 ≥4.0.0

# 手动安装R包
Rscript -e 'install.packages(c("did", "fixest", "didimputation"))'

# 测试R环境
Rscript scripts/did_run.R data/panel_for_did.csv results/did_test
```

**Q3: FAISS索引构建内存不足**

A: 使用IVF量化或分批处理：
```python
# 修改 scripts/build_index.py
# 将 IndexFlatIP 改为 IndexIVFFlat
quantizer = faiss.IndexFlatIP(dim)
index = faiss.IndexIVFFlat(quantizer, dim, nlist=100)
```

**Q4: 爬虫被封禁**

A: 降低QPS并添加随机延迟：
```bash
python3 scripts/crawl_gov_central.py \
  --qps 0.5 \            # 降低到0.5
  --random-delay 1-3     # 添加1-3秒随机延迟
```

---

## 📚 相关文档

**设计文档**：
- [01_数据爬取方案.md](./01_数据爬取方案.md)
- [02_语义抽取方案.md](./02_语义抽取方案.md)
- [03_标注与评估方案.md](./03_标注与评估方案.md)
- [04_图学习方案.md](./04_图学习方案.md)
- [05_因果推断方案.md](./05_因果推断方案.md)

**操作指南**：
- [标注指南](./docs/annotation_guide.md)
- [开发准则](./CLAUDE.md)

**审查报告**：
- [代码自动化审查](./.claude/code-review-auto.md)
- [代码深度审查](./.claude/code-review-comprehensive.md)
- [综合总结报告](./.claude/review-and-demo-summary.md)

---

## 🤝 贡献指南

欢迎贡献！请遵循以下流程：

1. Fork本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 遵循[CLAUDE.md](CLAUDE.md)开发准则
4. 提交更改：`git commit -m "添加某某功能"`（使用简体中文）
5. 推送分支：`git push origin feature/amazing-feature`
6. 提交Pull Request

**代码审查要求**：
- ✅ 通过所有本地验证
- ✅ 遵循代码质量标准（评分≥90/100）
- ✅ 提供测试覆盖
- ✅ 更新相关文档

---

## 📄 许可证

本项目采用 [MIT许可证](LICENSE)。

---

## 📧 联系方式

**项目维护者**：PSC-Graph开发组

**问题反馈**：请通过[GitHub Issues](https://github.com/Shuai1Wen/guanli/issues)提交

**技术讨论**：参见[项目Wiki](https://github.com/Shuai1Wen/guanli/wiki)

---

## 🙏 致谢

本项目使用了以下开源项目：

- [PyTorch Geometric](https://github.com/pyg-team/pytorch_geometric) - 图神经网络框架
- [sentence-transformers](https://github.com/UKPLab/sentence-transformers) - 文本嵌入
- [FAISS](https://github.com/facebookresearch/faiss) - 向量检索
- [did (R)](https://github.com/bcallaway11/did) - DID估计器
- [fixest (R)](https://github.com/lrberge/fixest) - 固定效应估计

感谢所有开源社区的贡献者！

---

**最后更新**：2025-11-18
**项目状态**：核心功能开发完成（94/100），演示脚本验证通过
