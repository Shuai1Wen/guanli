# PSC-Graph简化实现问题修复行动清单

生成时间：2025-12-01
状态：待执行
预计完成：3周（17个工作日）

---

## 快速概览

| 问题 | 优先级 | 工时 | 状态 |
|-----|-------|------|-----|
| P3: PDF解析未集成 | 🔴 高 | 2-3天 | ⏸ 待开始 |
| P4: Bochner编码未实现 | 🔴 高 | 1-2天 | ⏸ 待开始 |
| P1: TGAT模型未实现 | 🟡 中 | 3-5天 | ⏸ 待开始 |
| P2: DAPT/TAPT未实现 | 🟢 低 | 5-7天 | ⏸ 待开始 |

---

## Week 1行动清单（P3 + P4）

### Day 1-2：环境准备与框架搭建

**□ Task 1.1：验证PDF解析环境**
```bash
# 验证pdfplumber安装
python3 -c "import pdfplumber; print('✓ pdfplumber已安装')"

# 下载示例PDF（手动）
# 访问：https://www.cnipa.gov.cn/col/col3482/
# 下载：2023年5月、6月统计月报.pdf
# 保存到：data/cnipa_raw/
```

**□ Task 1.2：创建PDF解析脚本框架**
```bash
# 创建文件
touch scripts/fetch_cnipa_reports.py
touch scripts/parse_cnipa_pdf_tables.py

# 参考：.claude/context-summary-simplification-analysis.md
# 章节：方案P3 - Day 2-3
```

**□ Task 1.3：实现Bochner编码器**
```bash
# 创建模型文件
mkdir -p scripts/models
touch scripts/models/__init__.py
touch scripts/models/bochner_time_encoder.py

# 参考：.claude/context-summary-simplification-analysis.md
# 章节：方案P4 - Day 1
```

**验收标准**：
- ✓ pdfplumber可正常导入
- ✓ 2个示例PDF已下载到data/cnipa_raw/
- ✓ BochnerTimeEncoder类可实例化

---

### Day 3-4：核心逻辑实现

**□ Task 3.1：实现PDF表格解析**
```python
# scripts/parse_cnipa_pdf_tables.py
# 核心功能：
# 1. 打开PDF文件
# 2. 提取表格
# 3. 识别省份行
# 4. 解析专利授权量
# 5. 输出DataFrame

# 测试
python scripts/parse_cnipa_pdf_tables.py --pdf data/cnipa_raw/2023-05.pdf
```

**□ Task 3.2：集成Bochner编码到图构建**
```bash
# 修改 scripts/build_graph_pyg.py
# 位置：_generate_time_encoding 方法（第325-395行）

# 步骤：
# 1. 导入BochnerTimeEncoder
# 2. 替换固定频率编码为Bochner编码
# 3. 返回可学习的时间编码

# 测试
python scripts/build_graph_pyg.py
```

**验收标准**：
- ✓ 2个PDF解析成功，输出31省份数据
- ✓ Bochner编码维度[num_nodes, 32]
- ✓ 可学习参数初始化正常

---

### Day 5：验证与测试

**□ Task 5.1：批量PDF解析验证**
```bash
# 下载12个月份PDF（2023-01至2023-12）
# 执行批量解析
python scripts/parse_cnipa_pdf_tables.py --batch data/cnipa_raw/*.pdf

# 检查输出
head -20 data/cnipa_panel_long.csv
wc -l data/cnipa_panel_long.csv  # 应≥1000行
```

**□ Task 5.2：Bochner编码训练测试**
```bash
# 运行图构建
python scripts/build_graph_pyg.py

# 运行训练（验证梯度）
python scripts/train_hgt.py --epochs 5

# 检查日志
grep "NaN" results/logs/*.log  # 应无NaN错误
```

**□ Task 5.3：人工质检**
```bash
# PDF解析质检
# 随机抽2个月份，对比PDF原文合计值
# 误差应<0.1%

# Bochner编码质检
# 检查参数梯度：model.time_encoder.w.weight.grad
# 应有非零梯度
```

**Week 1交付物**：
- ✓ data/cnipa_panel_long.csv（≥1000行）
- ✓ scripts/models/bochner_time_encoder.py
- ✓ 修改后的scripts/build_graph_pyg.py
- ✓ 验证报告（PDF解析+Bochner编码）

---

## Week 2行动清单（P1）

### Day 6-7：TGAT核心模块

**□ Task 6.1：实现时序注意力机制**
```bash
# 创建文件
touch scripts/models/tgat_model.py

# 实现TemporalAttention类
# 参考：.claude/context-summary-simplification-analysis.md
# 章节：方案P1 - Day 1-2

# 核心功能：
# 1. 时间编码融合
# 2. 多头注意力
# 3. 时序消息传递
```

**□ Task 6.2：单元测试TGAT**
```python
# 测试脚本
import torch
from scripts.models.tgat_model import TemporalAttention

# 创建测试数据
h_src = torch.randn(100, 128)
h_dst = torch.randn(100, 128)
edge_time = torch.randint(0, 365, (100,))

# 前向传播
tgat = TemporalAttention(hidden_dim=128)
h_out = tgat(h_src, h_dst, edge_time)

# 验证
assert h_out.shape == (100, 128), "输出维度错误"
assert not torch.isnan(h_out).any(), "存在NaN"
print("✓ TGAT单元测试通过")
```

**验收标准**：
- ✓ TemporalAttention类可实例化
- ✓ 前向传播输出维度正确
- ✓ 无NaN或Inf

---

### Day 8-9：HGT-TGAT融合

**□ Task 8.1：实现融合模型**
```bash
# 创建文件
touch scripts/models/hgt_tgat_model.py

# 实现HGT_TGAT_Model类
# 参考：.claude/context-summary-simplification-analysis.md
# 章节：方案P1 - Day 3-4

# 核心功能：
# 1. HGT分支（异质信息）
# 2. TGAT分支（时序信息）
# 3. 双分支融合
```

**□ Task 8.2：边时间戳提取**
```python
# 修改 scripts/build_graph_pyg.py
# 添加edge_time_dict提取逻辑

def extract_edge_timestamps(data):
    """从标注中提取边时间戳"""
    edge_time_dict = {}

    for edge_type in data.edge_types:
        # 从annotations中提取effective_date
        # 转换为Unix时间戳或相对天数
        # ...

    return edge_time_dict
```

**验收标准**：
- ✓ HGT_TGAT_Model可实例化
- ✓ 双分支可正常前向传播
- ✓ 融合输出维度正确

---

### Day 10：训练与评测

**□ Task 10.1：集成到训练循环**
```bash
# 修改 scripts/train_hgt.py
# 位置：main()函数

# 步骤：
# 1. 初始化HGT_TGAT_Model
# 2. 提取edge_time_dict
# 3. 修改forward调用
# 4. 训练50个epoch

python scripts/train_hgt.py --model hgt_tgat --epochs 50
```

**□ Task 10.2：消融实验**
```bash
# 对比三组模型
# 1. HGT-only (baseline)
python scripts/train_hgt.py --model hgt --epochs 50

# 2. TGAT-only (无异质)
# 需要额外实现，可选

# 3. HGT+TGAT (full)
python scripts/train_hgt.py --model hgt_tgat --epochs 50

# 评测
python scripts/evaluate_link_prediction.py --model1 hgt --model2 hgt_tgat
```

**□ Task 10.3：性能验证**
```bash
# 检查指标
# 目标：
# - HGT+TGAT AUC ≥ 0.80
# - HGT+TGAT AUC > HGT-only AUC (提升≥5%)

# 输出结果
# [HGT-only]  AUC=0.75, AP=0.72
# [HGT+TGAT]  AUC=0.81, AP=0.78  ✓ 提升8%
```

**Week 2交付物**：
- ✓ scripts/models/tgat_model.py
- ✓ scripts/models/hgt_tgat_model.py
- ✓ 修改后的scripts/train_hgt.py
- ✓ 消融实验报告（HGT vs HGT+TGAT）

---

## Week 3行动清单（P2）

### Day 11-12：DAPT语料与训练启动

**□ Task 11.1：语料准备**
```bash
# 创建脚本
touch scripts/prep_dapt_corpus.py

# 执行
python scripts/prep_dapt_corpus.py

# 检查输出
wc -l data/dapt_corpus.jsonl  # 应≥500条
head -5 data/dapt_corpus.jsonl
```

**□ Task 11.2：DAPT训练启动**
```bash
# 创建脚本
touch scripts/run_dapt.py

# 检查GPU
nvidia-smi

# 启动训练（后台运行）
nohup python scripts/run_dapt.py > logs/dapt_train.log 2>&1 &

# 监控
tail -f logs/dapt_train.log
```

**验收标准**：
- ✓ DAPT语料≥500万字
- ✓ 训练启动成功，无OOM错误
- ✓ 困惑度逐步下降

---

### Day 13-15：DAPT训练监控

**□ Task 13：训练监控**
```bash
# 每日检查
tail -100 logs/dapt_train.log | grep "perplexity"

# 预期输出：
# Epoch 1, Step 5000: loss=2.34, perplexity=10.38
# Epoch 2, Step 10000: loss=2.01, perplexity=7.46
# Epoch 3, Step 15000: loss=1.89, perplexity=6.62  ✓ 下降

# TensorBoard可视化（可选）
tensorboard --logdir models/dapt_checkpoint/logs
```

**□ Task 14：验证集评测**
```python
# 计算验证集困惑度
from transformers import RobertaForMaskedLM

model = RobertaForMaskedLM.from_pretrained("models/dapt_checkpoint")
# 计算perplexity
# 对比基线：hfl/chinese-roberta-wwm-ext-large

# 目标：DAPT困惑度 < 基线困惑度
```

**□ Task 15：保存检查点**
```bash
# 检查模型文件
ls -lh models/dapt_checkpoint/
# 应包含：
# - pytorch_model.bin (>1GB)
# - config.json
# - tokenizer_config.json
```

**验收标准**：
- ✓ 训练完成3个epoch
- ✓ 验证集困惑度 < 基线模型
- ✓ 模型文件完整可加载

---

### Day 16-17：TAPT训练与验证

**□ Task 16.1：TAPT任务准备**
```bash
# 创建脚本
touch scripts/prep_tapt_task.py
touch scripts/run_tapt.py

# 准备NER数据
python scripts/prep_tapt_task.py \
    --annotations annotations/adjudicated/*.json \
    --output data/tapt_task.jsonl

# 检查
wc -l data/tapt_task.jsonl  # 应≥500条
```

**□ Task 16.2：TAPT训练**
```bash
# 启动训练
python scripts/run_tapt.py \
    --base_model models/dapt_checkpoint \
    --task_data data/tapt_task.jsonl \
    --output models/tapt_checkpoint \
    --epochs 10

# 监控
tail -f logs/tapt_train.log
```

**□ Task 17：NER评测**
```bash
# 评测NER F1
python scripts/evaluate_ner.py \
    --model models/tapt_checkpoint \
    --test_data annotations/adjudicated/test/*.json

# 预期输出：
# Entity F1: 0.87  ✓ ≥0.85
# Relation F1: 0.82
```

**□ Task 17.2：消融实验**
```bash
# 对比三组模型
# 1. 零样本LLM (GPT-4 zero-shot)
# 2. DAPT模型
# 3. DAPT+TAPT模型

# 执行
python scripts/run_ablation_nlp.py

# 预期结果：
# Zero-shot: F1=0.72
# DAPT:      F1=0.80
# DAPT+TAPT: F1=0.87  ✓ 显著提升
```

**Week 3交付物**：
- ✓ models/dapt_checkpoint/（DAPT模型）
- ✓ models/tapt_checkpoint/（TAPT模型）
- ✓ scripts/prep_dapt_corpus.py
- ✓ scripts/run_dapt.py
- ✓ scripts/prep_tapt_task.py
- ✓ scripts/run_tapt.py
- ✓ 消融实验报告（零样本 vs DAPT vs DAPT+TAPT）

---

## 资源需求

### 硬件需求

```yaml
Week 1 (P3+P4):
  GPU: 无需（CPU可运行）
  RAM: 16GB
  磁盘: 10GB

Week 2 (P1):
  GPU: 1x RTX 3090 24GB（可选，CPU也可）
  RAM: 32GB
  磁盘: 20GB

Week 3 (P2):
  GPU: 1x A100 40GB（必需）或 2x RTX 3090 24GB
  RAM: 64GB
  磁盘: 50GB（模型+语料）
```

### 备选方案（GPU不足）

```yaml
方案A: 梯度累积
  gradient_accumulation_steps: 4
  effective_batch_size: 保持不变
  GPU需求: 降低到16GB

方案B: LoRA微调
  library: peft
  显存需求: 降低50%
  训练速度: 稍慢

方案C: 云GPU租用
  平台: Google Colab Pro, AWS, Azure
  成本: ~$30-50 (3天训练)
```

---

## 风险预警

### 高风险项

1. **P2 GPU资源不足**
   - 风险：DAPT训练需要A100
   - 缓解：使用LoRA或云GPU

2. **P1 TGAT性能不佳**
   - 风险：实现有bug或性能差
   - 缓解：参考官方实现，渐进式集成

3. **P3 PDF扫描件**
   - 风险：部分PDF是扫描件，pdfplumber无法解析
   - 缓解：使用OCR或手动整理

### 中风险项

4. **时间压力**
   - 风险：17天工期紧张
   - 缓解：优先P3+P4，P2可延期

5. **依赖冲突**
   - 风险：新增依赖与现有库冲突
   - 缓解：使用虚拟环境，锁定版本

---

## 验收检查清单

### 最终验收标准

**□ P3: PDF解析**
- ✓ data/cnipa_panel_long.csv 行数≥1000
- ✓ 31省份数据完整
- ✓ 人工抽查2个月份，合计值误差<0.1%

**□ P4: Bochner编码**
- ✓ BochnerTimeEncoder类可实例化
- ✓ 编码维度[num_nodes, 32]
- ✓ 梯度可反向传播，无NaN

**□ P1: TGAT模型**
- ✓ 链路预测AUC≥0.80
- ✓ HGT+TGAT > HGT-only (提升≥5%)
- ✓ 消融实验报告完整

**□ P2: DAPT/TAPT**
- ✓ DAPT困惑度 < 基线模型
- ✓ TAPT NER F1≥0.85
- ✓ 消融实验：零样本 vs DAPT vs DAPT+TAPT

**□ 代码质量**
- ✓ 所有注释使用简体中文
- ✓ 所有脚本有docstring
- ✓ 无硬编码路径或参数
- ✓ 错误处理完整

**□ 文档交付**
- ✓ 每个新脚本有使用说明
- ✓ 修改后的文件有changelog
- ✓ 验收报告（每个问题一份）

---

## 快速启动命令

```bash
# Week 1启动
cd /home/user/guanli
source .venv/bin/activate

# 创建目录
mkdir -p scripts/models data/cnipa_raw

# 开始Task 1.1
python3 -c "import pdfplumber; print('✓ 环境就绪')"

# 查看详细分析
cat .claude/context-summary-simplification-analysis.md
```

---

**生成时间**：2025-12-01
**维护者**：Claude Code
**下一步**：启动Week 1 Task 1.1
