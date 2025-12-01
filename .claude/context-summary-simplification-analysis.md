# PSC-Graph项目简化实现问题深度分析报告

生成时间：2025-12-01
分析范围：图学习、NLP预训练、数据爬取、时间编码
严重程度：高（影响核心技术路线）

---

## 一、执行摘要

经过系统性代码检索和文档对比，确认PSC-Graph项目存在**4个关键简化实现**，均违反CLAUDE.md规范中"禁止MVP、最小实现或占位符"的强制要求。这些简化实现导致项目无法达到预期的技术指标，需要立即补全。

### 1.1 问题概览

| 问题编号 | 问题描述 | 严重程度 | 影响范围 | 预计工时 |
|---------|---------|---------|---------|---------|
| **P1** | TGAT模型未实现 | 🔴 高 | 图学习性能、时序建模 | 3-5天 |
| **P2** | DAPT/TAPT预训练未实现 | 🔴 高 | 语义抽取质量、F1指标 | 5-7天 |
| **P3** | PDF解析未集成 | 🟡 中 | CNIPA专利数据采集 | 2-3天 |
| **P4** | Bochner时间编码未实现 | 🟡 中 | 时序特征质量 | 1-2天 |

**总预计工时**：11-17天

### 1.2 核心发现

1. **文档-代码不一致**：技术方案文档详细定义了实现要求，但实际代码使用了简化替代方案
2. **关键能力缺失**：TGAT（时序建模）、DAPT/TAPT（域适应）等核心技术未实现
3. **质量指标风险**：当前实现可能无法达到CLAUDE.md规定的质量门槛（如F1≥0.85）

---

## 二、问题详细分析

### P1: TGAT模型未实现

#### 2.1.1 问题描述

**要求**（CLAUDE.md + 04_图学习方案.md）：
```yaml
图学习强制规范:
  model: "HGT + TGAT (异质图 + 时序图注意力)"
  时间编码: "Bochner时间编码"
  消融实验:
    - HGT only (无时序编码) → 性能应低于HGT+TGAT
    - TGAT only (无异质类型) → 性能应低于HGT+TGAT
```

**实际实现**（scripts/train_hgt.py）：
```python
# 仅实现了HGT，未集成TGAT
class HGT(nn.Module):
    def __init__(self, node_types, edge_types, ...):
        # HGT卷积层
        self.convs = nn.ModuleList()
        for _ in range(num_layers):
            conv = HGTConv(...)  # 仅HGT
            self.convs.append(conv)

    def forward(self, x_dict, edge_index_dict):
        # 无TGAT集成
        for conv in self.convs:
            h_dict_new = conv(h_dict, edge_index_dict)
```

**缺失内容**：
1. ❌ TGAT模型类（Temporal Graph Attention Network）
2. ❌ 时序注意力机制
3. ❌ 边时间戳处理逻辑
4. ❌ HGT-TGAT融合模块
5. ❌ 时序消息传递机制

#### 2.1.2 影响分析

**技术影响**：
- ✗ 无法捕捉政策演化的动态特性
- ✗ 时间维度信息未充分利用
- ✗ 无法满足消融实验要求（HGT vs HGT+TGAT）

**指标影响**：
- 链路预测AUC可能<0.80（目标≥0.80）
- 无法验证"TGAT提升≥5%"的假设

**代码位置**：
- `scripts/train_hgt.py`：仅实现HGT
- `scripts/build_graph_pyg.py`：边数据未包含时间戳

#### 2.1.3 根本原因

1. **设计-实现断层**：04_图学习方案.md详细定义了TGAT，但实现时简化为纯HGT
2. **依赖缺失**：未找到TGAT参考实现或第三方库集成
3. **复杂度低估**：TGAT实现难度高于HGT，可能被推迟

---

### P2: DAPT/TAPT预训练未实现

#### 2.2.1 问题描述

**要求**（CLAUDE.md + 02_语义抽取方案.md）：
```yaml
NLP强制规范:
  预训练: "DAPT (域适应) + TAPT (任务适应)"
  基座模型: "chinese-roberta-wwm-ext-large"
  DAPT语料: "500万-1000万字政策文本"
  TAPT数据: "500-1000条金标标注"
```

**实际实现**：
```bash
# 检索结果：无DAPT/TAPT相关脚本
$ find scripts/ -name "*dapt*" -o -name "*tapt*"
# 无结果

# 仅在文档中有定义
$ grep -r "run_dapt.py" scripts/
# 无结果
```

**缺失内容**：
1. ❌ `scripts/prep_dapt_corpus.py`（语料准备）
2. ❌ `scripts/run_dapt.py`（DAPT训练）
3. ❌ `scripts/prep_tapt_task.py`（任务数据准备）
4. ❌ `scripts/run_tapt.py`（TAPT训练）
5. ❌ `models/dapt_checkpoint/`（预训练模型保存目录）

#### 2.2.2 影响分析

**技术影响**：
- ✗ 无法适应政策领域的语言分布
- ✗ 专业术语识别能力弱
- ✗ 抽取质量依赖零样本LLM（不稳定）

**指标影响**：
- 实体/关系F1可能<0.85（目标≥0.85）
- 消融实验缺失关键对照组：
  - ✗ 无法对比"零样本LLM vs DAPT+TAPT+RAG"
  - ✗ 无法验证假设H1（域适应预训练提升效果）

**代码位置**：
- `scripts/`目录：完全缺失DAPT/TAPT脚本
- `02_语义抽取方案.md`：仅有设计，无实现

#### 2.2.3 根本原因

1. **GPU资源限制**：DAPT训练需要A100 40GB，可能因资源不足跳过
2. **时间压力**：预训练周期长（2-3天），可能因赶进度省略
3. **依赖RAG补偿**：认为RAG检索可以部分替代预训练效果（错误假设）

---

### P3: PDF解析未集成

#### 2.3.1 问题描述

**要求**（CLAUDE.md + 01_数据爬取方案.md）：
```yaml
数据采集层强制依赖:
  - pdfplumber (PDF表格抽取)
  - 解析对象: CNIPA专利统计月报/年报
  - 目标: 31省×12月×3年≈1116条记录
```

**实际实现**：
```bash
# requirements.txt中有依赖
$ grep pdfplumber scripts/requirements.txt
pdfplumber==0.11.8  # ✓ 依赖已声明

# 但无具体实现脚本
$ find scripts/ -name "*cnipa*" -o -name "*pdf*"
# 无parse_cnipa_pdf_tables.py
```

**缺失内容**：
1. ❌ `scripts/parse_cnipa_pdf_tables.py`（PDF表格解析）
2. ❌ `scripts/fetch_cnipa_reports.py`（PDF下载与调度）
3. ❌ `data/cnipa_raw/*.pdf`（原始PDF文件）
4. ❌ `data/cnipa_panel_long.csv`（解析后的长表）

#### 2.3.2 影响分析

**技术影响**：
- ✗ 无法获取CNIPA专利统计数据
- ✗ 缺失专利授权量、申请量等关键指标
- ✗ DID面板数据不完整（缺少专利变量）

**数据影响**：
- 产业指标不完整：仅有NBS统计数据，缺少专利数据
- 因果推断受限：无法分析政策对专利产出的影响

**代码位置**：
- `scripts/`目录：缺失PDF解析脚本
- `01_数据爬取方案.md`：仅有设计，无实现

#### 2.3.3 根本原因

1. **技术门槛**：PDF表格解析复杂（扫描件、复杂排版）
2. **数据优先级**：可能优先实现NBS数据，CNIPA被推迟
3. **替代数据源**：可能尝试手动整理或使用其他来源

---

### P4: Bochner时间编码未正确实现

#### 2.4.1 问题描述

**要求**（CLAUDE.md + 04_图学习方案.md）：
```python
# 要求：Bochner核时间编码
class BochnerTimeEncoder(torch.nn.Module):
    def __init__(self, time_dim=32):
        super().__init__()
        self.w = torch.nn.Linear(1, time_dim)  # 可学习频率

    def forward(self, timestamps):
        t = timestamps.unsqueeze(-1).float()
        omega = self.w(t)  # 可学习频率
        # Bochner定理: e^{i*omega*t} 的实部和虚部
        time_enc = torch.cat([torch.cos(omega), torch.sin(omega)], dim=-1)
        return time_enc
```

**实际实现**（scripts/build_graph_pyg.py:325-395）：
```python
# 实际：标准正弦-余弦位置编码（Transformer原始方案）
def _generate_time_encoding(self, timestamps, encoding_dim=32):
    # 计算相对天数
    days = (dt - base_date).days

    # 标准正弦-余弦编码（固定频率）
    for j in range(encoding_dim // 2):
        freq = 1.0 / (10000 ** (2 * j / encoding_dim))  # ❌ 固定频率
        time_encodings[i, 2*j] = np.sin(days * freq)
        time_encodings[i, 2*j + 1] = np.cos(days * freq)
```

**差异分析**：

| 特性 | Bochner编码（要求） | 正弦-余弦编码（实际） |
|-----|------------------|-------------------|
| **频率** | 可学习（nn.Linear） | 固定（10000底数） |
| **适应性** | 数据驱动，自适应 | 固定模式，不适应 |
| **灵活性** | 可捕捉任意周期 | 仅捕捉固定周期 |
| **理论基础** | Bochner定理（随机傅里叶特征） | Transformer位置编码 |

#### 2.4.2 影响分析

**技术影响**：
- ✗ 时间特征表达能力受限（固定频率无法适应政策周期）
- ✗ 无法捕捉政策发布的周期性规律
- ✗ 与TGAT集成时性能不佳

**指标影响**：
- 图学习性能可能受限（时间特征质量差）
- 消融实验"去时序 vs 有时序"对比不公平

**代码位置**：
- `scripts/build_graph_pyg.py:325-395`：`_generate_time_encoding`方法

#### 2.4.3 根本原因

1. **快速实现**：使用Transformer位置编码作为临时方案
2. **理论理解不足**：可能未深入理解Bochner编码的优势
3. **集成复杂性**：Bochner编码需要在训练循环中优化参数

---

## 三、改进计划

### 3.1 优先级排序

基于技术影响和实施难度，建议优先级：

```
优先级1（立即开始）：
  P3 - PDF解析集成        （2-3天，数据依赖）
  P4 - Bochner编码实现    （1-2天，快速修复）

优先级2（第2周）：
  P1 - TGAT模型实现      （3-5天，核心技术）

优先级3（第3周）：
  P2 - DAPT/TAPT预训练   （5-7天，资源密集）
```

### 3.2 详细实施方案

#### 方案P3：PDF解析集成

**实施步骤**：

**Day 1：环境准备与PDF下载**
```bash
# 1. 验证pdfplumber安装
pip install pdfplumber==0.11.8

# 2. 创建脚本框架
scripts/fetch_cnipa_reports.py       # PDF下载器
scripts/parse_cnipa_pdf_tables.py    # PDF解析器

# 3. 下载示例PDF（2023-05, 2023-06）
wget https://www.cnipa.gov.cn/.../2023-05.pdf
```

**Day 2-3：解析逻辑实现**
```python
# scripts/parse_cnipa_pdf_tables.py
import pdfplumber
import pandas as pd
import re

def parse_monthly_report(pdf_path):
    """解析CNIPA月报PDF"""
    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue

            # 识别表头
            header, *data = table

            # 过滤省份行
            for row in data:
                if not row or not row[0]:
                    continue
                # 仅保留省份行
                if re.search(r"(省|市|自治区)", row[0]):
                    rows.append({
                        "province_name": row[0].strip(),
                        "invention_grant": int(row[1]),
                        "utility_grant": int(row[2]),
                        "design_grant": int(row[3])
                    })

    return pd.DataFrame(rows)

def main():
    # 批量解析
    pdf_files = glob.glob("data/cnipa_raw/*.pdf")
    all_data = []

    for pdf in pdf_files:
        df = parse_monthly_report(pdf)
        period = extract_period_from_filename(pdf)
        df["period"] = period
        all_data.append(df)

    # 保存长表
    final_df = pd.concat(all_data, ignore_index=True)
    final_df.to_csv("data/cnipa_panel_long.csv", index=False)
```

**验证标准**：
- ✓ 解析≥12个月份PDF
- ✓ 31省份数据完整
- ✓ 合计值与PDF表格一致（误差<0.1%）

---

#### 方案P4：Bochner时间编码

**实施步骤**：

**Day 1：理论验证与实现**
```python
# scripts/models/bochner_time_encoder.py
import torch
import torch.nn as nn

class BochnerTimeEncoder(nn.Module):
    """Bochner核时间编码器

    理论基础：
    - Bochner定理：平稳核可表示为随机傅里叶特征
    - 可学习频率ω，使模型自适应时间周期

    优势：
    - 相比固定频率编码，可捕捉任意周期性
    - 数据驱动，自动学习政策发布周期
    """

    def __init__(self, time_dim=32):
        super().__init__()
        self.time_dim = time_dim
        self.w = nn.Linear(1, time_dim)  # 可学习频率

    def forward(self, timestamps):
        """
        Args:
            timestamps: (num_edges,) Unix时间戳或相对天数

        Returns:
            time_enc: (num_edges, 2*time_dim) 时间编码
        """
        t = timestamps.unsqueeze(-1).float()  # (num_edges, 1)
        omega = self.w(t)  # (num_edges, time_dim)

        # Bochner定理: e^{i*omega*t} = cos(omega*t) + i*sin(omega*t)
        # 实部和虚部作为特征
        time_enc = torch.cat([
            torch.cos(omega),
            torch.sin(omega)
        ], dim=-1)  # (num_edges, 2*time_dim)

        return time_enc
```

**Day 2：集成到图构建**
```python
# 修改 scripts/build_graph_pyg.py
def _generate_time_encoding(self, timestamps, encoding_dim=32):
    """使用Bochner编码替代标准编码"""
    # ❌ 删除旧代码（固定频率编码）
    # for j in range(encoding_dim // 2):
    #     freq = 1.0 / (10000 ** (2 * j / encoding_dim))
    #     ...

    # ✓ 使用Bochner编码（可学习）
    encoder = BochnerTimeEncoder(time_dim=encoding_dim // 2)

    # 转换为tensor
    days_tensor = torch.tensor([
        (datetime.fromisoformat(ts) - base_date).days
        for ts in timestamps
    ], dtype=torch.float32)

    # 编码
    time_encodings = encoder(days_tensor)

    return time_encodings
```

**验证标准**：
- ✓ 编码维度正确（[num_nodes, 32]）
- ✓ 可学习参数初始化正常
- ✓ 梯度可反向传播

---

#### 方案P1：TGAT模型实现

**实施步骤**：

**Day 1-2：TGAT核心模块**
```python
# scripts/models/tgat_model.py
import torch
import torch.nn as nn
import torch.nn.functional as F

class TemporalAttention(nn.Module):
    """时序注意力模块

    参考：Xu et al., ICLR 2020
    "Inductive Representation Learning on Temporal Graphs"
    """

    def __init__(self, hidden_dim, num_heads=4):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads

        # 查询、键、值投影
        self.q_proj = nn.Linear(hidden_dim, hidden_dim)
        self.k_proj = nn.Linear(hidden_dim, hidden_dim)
        self.v_proj = nn.Linear(hidden_dim, hidden_dim)

        # 时间编码器
        self.time_encoder = BochnerTimeEncoder(time_dim=hidden_dim)

    def forward(self, h_src, h_dst, edge_time):
        """
        Args:
            h_src: (num_edges, hidden_dim) 源节点特征
            h_dst: (num_edges, hidden_dim) 目标节点特征
            edge_time: (num_edges,) 边时间戳

        Returns:
            h_out: (num_edges, hidden_dim) 更新后的特征
        """
        # 时间编码
        time_enc = self.time_encoder(edge_time)  # (num_edges, 2*time_dim)

        # 融合时间特征
        h_src_time = h_src + time_enc[:, :self.hidden_dim]
        h_dst_time = h_dst + time_enc[:, self.hidden_dim:]

        # 多头注意力
        Q = self.q_proj(h_dst_time).view(-1, self.num_heads, self.head_dim)
        K = self.k_proj(h_src_time).view(-1, self.num_heads, self.head_dim)
        V = self.v_proj(h_src_time).view(-1, self.num_heads, self.head_dim)

        # 缩放点积注意力
        attn = (Q @ K.transpose(-2, -1)) / (self.head_dim ** 0.5)
        attn = F.softmax(attn, dim=-1)

        # 聚合
        h_out = (attn @ V).view(-1, self.hidden_dim)

        return h_out
```

**Day 3-4：HGT-TGAT融合**
```python
# scripts/models/hgt_tgat_model.py
class HGT_TGAT_Model(nn.Module):
    """HGT + TGAT融合模型"""

    def __init__(self, metadata, hidden_channels=128, num_heads=4, num_layers=2):
        super().__init__()

        # HGT层（异质图）
        self.hgt_layers = nn.ModuleList()
        for _ in range(num_layers):
            self.hgt_layers.append(
                HGTConv(hidden_channels, hidden_channels, metadata, num_heads)
            )

        # TGAT层（时序图）
        self.tgat_layers = nn.ModuleList()
        for _ in range(num_layers):
            self.tgat_layers.append(
                TemporalAttention(hidden_channels, num_heads)
            )

        # 融合层
        self.fusion = nn.Linear(2 * hidden_channels, hidden_channels)

    def forward(self, x_dict, edge_index_dict, edge_time_dict):
        """
        Args:
            x_dict: {node_type: Tensor} 节点特征
            edge_index_dict: {edge_type: Tensor} 边索引
            edge_time_dict: {edge_type: Tensor} 边时间戳
        """
        # HGT分支（异质信息）
        h_hgt = x_dict.copy()
        for hgt_layer in self.hgt_layers:
            h_hgt = hgt_layer(h_hgt, edge_index_dict)

        # TGAT分支（时序信息）
        h_tgat = {}
        for edge_type in edge_index_dict.keys():
            src_type, rel, dst_type = edge_type
            edge_index = edge_index_dict[edge_type]
            edge_time = edge_time_dict.get(edge_type)

            if edge_time is None:
                continue  # 无时间戳的边跳过

            # 提取源节点和目标节点特征
            h_src = x_dict[src_type][edge_index[0]]
            h_dst = x_dict[dst_type][edge_index[1]]

            # TGAT聚合
            for tgat_layer in self.tgat_layers:
                h_dst = tgat_layer(h_src, h_dst, edge_time)

            # 更新节点特征
            if dst_type not in h_tgat:
                h_tgat[dst_type] = torch.zeros_like(x_dict[dst_type])
            h_tgat[dst_type].index_add_(0, edge_index[1], h_dst)

        # 融合HGT和TGAT
        h_final = {}
        for node_type in x_dict.keys():
            if node_type in h_tgat:
                h_final[node_type] = self.fusion(
                    torch.cat([h_hgt[node_type], h_tgat[node_type]], dim=-1)
                )
            else:
                h_final[node_type] = h_hgt[node_type]

        return h_final
```

**Day 5：训练集成与测试**
```python
# 修改 scripts/train_hgt.py
def main():
    # 初始化HGT-TGAT模型
    model = HGT_TGAT_Model(
        metadata=data.metadata(),
        hidden_channels=128,
        num_heads=4,
        num_layers=2
    )

    # 准备边时间戳
    edge_time_dict = extract_edge_timestamps(data)

    # 训练循环
    for epoch in range(num_epochs):
        loss = train_epoch(model, data, x_dict, edge_index_dict, edge_time_dict)
        print(f"Epoch {epoch}, Loss: {loss:.4f}")
```

**验证标准**：
- ✓ 模型可正常前向传播
- ✓ 梯度可反向传播
- ✓ 链路预测AUC ≥ HGT-only基线

---

#### 方案P2：DAPT/TAPT预训练

**实施步骤**：

**Day 1-2：DAPT语料准备**
```python
# scripts/prep_dapt_corpus.py
import json
import glob
from pathlib import Path

def clean_text(text):
    """清洗HTML标签，统一标点"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('　', ' ')
    return text.strip()

def main():
    corpus_files = glob.glob("corpus/raw/**/*.json", recursive=True)

    output = Path("data/dapt_corpus.jsonl")
    with open(output, "w", encoding="utf-8") as f:
        for file_path in corpus_files:
            doc = json.load(open(file_path, "r", encoding="utf-8"))

            # 提取纯文本
            text = clean_text(doc["content_text"])

            # 写入JSONL
            f.write(json.dumps({
                "id": doc.get("sha256", doc.get("doc_id")),
                "text": text,
                "meta": {
                    "title": doc.get("title"),
                    "pub_date": doc.get("pub_date"),
                    "issuer": doc.get("issuer")
                }
            }, ensure_ascii=False) + "\n")

    print(f"✓ DAPT语料已保存到: {output}")
    print(f"  文档数: {len(corpus_files)}")
```

**Day 3-5：DAPT训练**
```python
# scripts/run_dapt.py
from transformers import (
    RobertaForMaskedLM,
    RobertaTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments
)

def main():
    # 加载基座模型
    model_name = "hfl/chinese-roberta-wwm-ext-large"
    model = RobertaForMaskedLM.from_pretrained(model_name)
    tokenizer = RobertaTokenizer.from_pretrained(model_name)

    # 加载语料
    dataset = load_dataset("json", data_files="data/dapt_corpus.jsonl")

    # Tokenize
    def tokenize_function(examples):
        return tokenizer(examples["text"], truncation=True, max_length=512)

    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    # 训练配置
    training_args = TrainingArguments(
        output_dir="models/dapt_checkpoint",
        overwrite_output_dir=True,
        num_train_epochs=3,
        per_device_train_batch_size=32,
        save_steps=5000,
        save_total_limit=3,
        learning_rate=5e-5,
        fp16=True,  # 混合精度
        logging_steps=100
    )

    # 数据整理器（MLM）
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=0.15
    )

    # 训练器
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        data_collator=data_collator
    )

    # 训练
    trainer.train()

    # 保存
    model.save_pretrained("models/dapt_checkpoint")
    tokenizer.save_pretrained("models/dapt_checkpoint")
```

**Day 6-7：TAPT任务训练**
```python
# scripts/run_tapt.py
from transformers import RobertaForTokenClassification

def main():
    # 加载DAPT模型
    model = RobertaForTokenClassification.from_pretrained(
        "models/dapt_checkpoint",
        num_labels=5  # O, B-GOAL, I-GOAL, B-ACTOR, I-ACTOR
    )

    # 加载金标标注（NER格式）
    train_dataset = load_ner_dataset("annotations/adjudicated/train/*.json")

    # 训练配置
    training_args = TrainingArguments(
        output_dir="models/tapt_checkpoint",
        num_train_epochs=10,
        per_device_train_batch_size=16,
        learning_rate=2e-5,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1"
    )

    # 训练
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_ner_metrics
    )

    trainer.train()
    model.save_pretrained("models/tapt_checkpoint")
```

**验证标准**：
- ✓ DAPT困惑度 < 基线模型
- ✓ TAPT NER F1 > DAPT模型
- ✓ 消融实验：零样本 vs DAPT vs DAPT+TAPT

---

### 3.3 风险评估与缓解

#### 风险1：GPU资源不足

**风险描述**：
- DAPT训练需要A100 40GB
- 可能因资源不足无法训练

**缓解措施**：
```yaml
方案A: 使用梯度累积
  gradient_accumulation_steps: 4
  effective_batch_size: 32 * 4 = 128
  GPU需求: 降低到16GB（RTX 3090可运行）

方案B: 使用LoRA微调
  library: peft (Parameter-Efficient Fine-Tuning)
  优势: 显存需求降低50%

方案C: 使用云GPU
  平台: Google Colab Pro, AWS, Azure
  成本: ~$1-2/小时
```

#### 风险2：TGAT性能不佳

**风险描述**：
- TGAT实现可能有bug
- 性能可能不如预期

**缓解措施**：
```yaml
方案A: 参考官方实现
  - PyG TGAT示例：torch_geometric.nn.models.TGAT
  - 原始论文代码：https://github.com/twitter-research/tgn

方案B: 渐进式集成
  - 先实现纯TGAT（无HGT）
  - 验证性能后再融合HGT

方案C: 消融实验验证
  - 对比：HGT vs TGAT vs HGT+TGAT
  - 确认TGAT带来正向提升
```

#### 风险3：PDF解析失败

**风险描述**：
- CNIPA PDF可能是扫描件
- 表格排版复杂

**缓解措施**：
```yaml
方案A: OCR后备方案
  - 检测PDF类型（电子/扫描）
  - 扫描件使用Tesseract OCR

方案B: 手动验证
  - 随机抽查10个PDF
  - 人工核对解析结果

方案C: 多工具对比
  - pdfplumber（首选）
  - camelot-py（复杂表格）
  - tabula-py（备选）
```

---

## 四、执行时间表

### 4.1 三周冲刺计划

```yaml
Week 1（P3 + P4）:
  Day 1-2:
    - ✓ PDF下载与环境准备
    - ✓ Bochner编码实现与测试

  Day 3-4:
    - ✓ PDF解析逻辑开发
    - ✓ Bochner集成到图构建

  Day 5:
    - ✓ PDF解析验证（≥12个月份）
    - ✓ Bochner编码训练测试

Week 2（P1）:
  Day 6-7:
    - ✓ TGAT核心模块实现
    - ✓ 时序注意力机制

  Day 8-9:
    - ✓ HGT-TGAT融合
    - ✓ 训练循环集成

  Day 10:
    - ✓ TGAT验证与消融实验

Week 3（P2）:
  Day 11-12:
    - ✓ DAPT语料准备与训练启动

  Day 13-15:
    - ✓ DAPT训练（2-3天）

  Day 16-17:
    - ✓ TAPT训练与验证
```

### 4.2 里程碑检查点

| 里程碑 | 日期 | 交付物 | 验收标准 |
|-------|------|-------|---------|
| **M1: P3完成** | Day 5 | CNIPA数据完整 | ≥1000行，合计值误差<0.1% |
| **M2: P4完成** | Day 5 | Bochner编码集成 | 梯度可反向传播 |
| **M3: P1完成** | Day 10 | TGAT模型就绪 | AUC ≥ HGT-only基线 |
| **M4: P2完成** | Day 17 | DAPT/TAPT模型 | NER F1 ≥ 基线+5% |

---

## 五、质量验收标准

### 5.1 技术验收

```yaml
P3 (PDF解析):
  必须达到:
    - 解析成功率: ≥95% (至少36个月份中≥34个成功)
    - 数据完整性: 31省份全覆盖
    - 准确性: 人工抽查2个月份，合计值误差<0.1%

  验证方式:
    - 运行: python scripts/parse_cnipa_pdf_tables.py
    - 检查: data/cnipa_panel_long.csv 行数≥1000
    - 对比: 随机2个月份与PDF原文核对

P4 (Bochner编码):
  必须达到:
    - 编码维度: [num_nodes, 32]
    - 可学习参数: nn.Linear可训练
    - 梯度传播: 无NaN或Inf

  验证方式:
    - 前向传播: encoder(timestamps) 输出维度正确
    - 反向传播: loss.backward() 参数有梯度
    - 对比: 与固定频率编码对比，性能≥基线

P1 (TGAT模型):
  必须达到:
    - 链路预测AUC: ≥0.80
    - 对比HGT-only: TGAT提升≥5%
    - 消融实验: HGT vs TGAT vs HGT+TGAT 三组对比

  验证方式:
    - 运行: python scripts/train_hgt.py --model hgt_tgat
    - 评测: python scripts/evaluate_link_prediction.py
    - 对比: 对比三种模型的AUC/AP指标

P2 (DAPT/TAPT):
  必须达到:
    - DAPT困惑度: < 基线模型
    - TAPT NER F1: ≥0.85
    - 消融实验: 零样本 vs DAPT vs DAPT+TAPT

  验证方式:
    - DAPT: 计算验证集困惑度
    - TAPT: 评测NER F1（开发集+测试集）
    - 消融: 对比三组模型的F1指标
```

### 5.2 代码质量验收

```yaml
强制要求:
  注释语言: 简体中文
  代码风格: 遵循PEP 8
  错误处理: 所有异常有try-except
  日志记录: 关键步骤有日志输出

文档要求:
  每个脚本: 文件头注释（功能、依赖、用法）
  每个函数: docstring（参数、返回值、示例）
  每个模型类: 理论基础、参考文献

测试要求:
  单元测试: 核心函数有测试覆盖
  集成测试: 端到端流程可运行
  验收测试: 人工抽查关键输出
```

---

## 六、附录

### 6.1 参考文献

```yaml
TGAT:
  - 论文: "Inductive Representation Learning on Temporal Graphs"
  - 作者: Xu et al., ICLR 2020
  - 链接: https://arxiv.org/abs/2002.07962
  - 代码: https://github.com/twitter-research/tgn

Bochner编码:
  - 论文: "On the Spectral Bias of Neural Networks"
  - 作者: Rahaman et al., ICML 2019
  - 链接: https://arxiv.org/abs/1806.08734

DAPT/TAPT:
  - 论文: "Don't Stop Pretraining: Adapt Language Models to Domains and Tasks"
  - 作者: Gururangan et al., ACL 2020
  - 链接: https://aclanthology.org/2020.acl-main.740/

pdfplumber:
  - 文档: https://github.com/jsvine/pdfplumber
  - 示例: https://github.com/jsvine/pdfplumber/tree/stable/examples
```

### 6.2 关键代码位置

```
需要修改的文件:
  scripts/build_graph_pyg.py        # Bochner编码集成
  scripts/train_hgt.py              # TGAT模型集成

需要新增的文件:
  scripts/models/bochner_time_encoder.py     # Bochner编码器
  scripts/models/tgat_model.py               # TGAT模型
  scripts/models/hgt_tgat_model.py           # HGT-TGAT融合
  scripts/parse_cnipa_pdf_tables.py          # PDF解析
  scripts/fetch_cnipa_reports.py             # PDF下载
  scripts/prep_dapt_corpus.py                # DAPT语料
  scripts/run_dapt.py                        # DAPT训练
  scripts/prep_tapt_task.py                  # TAPT任务
  scripts/run_tapt.py                        # TAPT训练

需要新增的目录:
  models/dapt_checkpoint/                    # DAPT模型
  models/tapt_checkpoint/                    # TAPT模型
  data/cnipa_raw/                            # CNIPA PDF
```

---

## 七、总结与建议

### 7.1 核心问题

PSC-Graph项目存在**"设计-实现断层"**问题：
- ✓ 技术方案文档完整详细
- ✗ 实际代码大量简化实现
- ✗ 未按CLAUDE.md规范完成全量功能

### 7.2 建议行动

**立即执行**（优先级1）：
1. Week 1完成P3（PDF解析）和P4（Bochner编码）
2. 验证数据完整性和时间编码质量

**第2周执行**（优先级2）：
3. Week 2完成P1（TGAT模型）
4. 进行消融实验验证性能提升

**第3周执行**（优先级3）：
5. Week 3完成P2（DAPT/TAPT）
6. 如GPU资源不足，使用LoRA或云GPU

### 7.3 长期建议

1. **强化CI/CD验证**：
   - 自动化测试覆盖核心模块
   - 每次提交检查实现完整性

2. **定期代码审查**：
   - 对比技术方案文档与实际代码
   - 发现简化实现立即标记

3. **技术债务管理**：
   - 维护技术债务清单
   - 每周复盘并安排修复计划

---

**报告生成时间**：2025-12-01
**分析人员**：Claude Code
**下一步行动**：提交改进计划，申请资源，启动Week 1开发
