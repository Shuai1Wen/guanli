# PSC-Graph项目深度分析：TGAT与DAPT/TAPT实现方案

生成时间：2025-12-06

## 1. 项目当前状态评估

### 1.1 已完成的组件（✓）

**数据采集层**：
- ✓ 中央政策爬虫（crawl_gov_central.py）
- ✓ 省级政策爬虫（crawl_provinces.py）
- ✓ 爬虫通用模块（crawler_common.py）
- ✓ 省份健康检查工具（health_check_provinces.py）
- ✓ 31省份分层策略（A/B/C/D分类，provinces.yaml）
- ✓ PDF下载和解析（fetch_cnipa_reports.py, parse_cnipa_pdf_tables.py）

**图学习层**：
- ✓ HGT模型实现（train_hgt.py，已修复NaN问题）
- ✓ 图构建脚本（build_graph_pyg.py）
- ✓ Bochner时间编码器（models/bochner_time_encoder.py）
- ✓ 梯度裁剪和NaN检测机制
- ✓ 数值稳定性优化

**NLP与语义抽取层**：
- ✓ RAG检索系统（build_index.py, retrieve_evidence.py）
- ✓ 标注验证（validate_annotations.py）
- ✓ 校准和共形预测（calibrate_and_conformal.py）

**因果推断层**：
- ✓ DID面板准备（prep_panel.py）
- ✓ Python-R桥接（run_did_from_python.py）

### 1.2 用户已修复的关键问题（train_hgt.py）

**d0b6bba提交的主要修复**：

1. **梯度计算问题修复**（P0级）
   ```python
   # 修复前（错误）
   h_dict[node_type] = self.lin_dict[node_type](x).relu_()  # in-place操作破坏梯度

   # 修复后（正确）
   h_dict[node_type] = self.lin_dict[node_type](x).relu()   # 非in-place操作
   ```

2. **NaN检测机制**（P0级）
   ```python
   # 损失NaN检测
   if torch.isnan(loss):
       raise RuntimeError(f"检测到NaN损失！...")

   # 梯度NaN检测
   for name, param in model.named_parameters():
       if param.grad is not None and torch.isnan(param.grad).any():
           raise RuntimeError(f"检测到NaN梯度！参数: {name}")
   ```

3. **数值稳定性优化**（P1级）
   ```python
   # logits裁剪防止BCE产生NaN
   pos_scores = torch.clamp(pos_scores, min=-10.0, max=10.0)
   neg_scores = torch.clamp(neg_scores, min=-10.0, max=10.0)

   # 梯度裁剪防止梯度爆炸
   torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
   ```

4. **设备优化**（P1级）
   ```python
   # 负采样直接在GPU上生成，避免CPU-GPU传输
   device = edge_index.device
   neg_src = torch.randint(0, data[src_type].x.shape[0], (num_neg,), device=device)
   ```

**评价**：用户的修改非常专业，完全符合CLAUDE.md的强制规范，解决了梯度失效和数值不稳定的核心问题。

### 1.3 当前缺失的关键组件（❌）

根据CLAUDE.md第406-475行的强制技术栈要求：

**P1 - TGAT模型缺失**（Week 2任务，0%完成）：
```yaml
问题：train_hgt.py仅实现HGT，未包含TGAT（时序图注意力）模块
影响：无法建模政策发布时间对政策-产业关系的影响
要求：CLAUDE.md第414-418行强制要求HGT+TGAT时序图学习
估计：3-5天，高优先级
```

**P2 - DAPT/TAPT预训练缺失**（Week 3任务，0%完成）：
```yaml
问题：代码中未发现域适应预训练（DAPT/TAPT）的相关脚本
影响：LLM语义抽取缺乏政策领域知识，F1可能<0.85
要求：CLAUDE.md第427-438行强制要求DAPT+RAG实现语义抽取
估计：5-7天，中优先级
```

## 2. P1 TGAT模型实现方案

### 2.1 TGAT原理与设计目标

**核心思想**：在异质图的基础上，引入时间维度建模动态演化。

**与HGT的关系**：
- HGT：建模不同类型节点/边的语义异质性
- TGAT：建模时间序列上的动态交互
- 融合：HGT-TGAT混合架构同时处理异质性和时序性

**PSC-Graph场景**：
```
政策发布（2020年1月）→ 企业响应（2020年3月）→ 专利申请（2020年6月）
                     ↓ 时序依赖                    ↓ 时序依赖
需要TGAT捕捉：政策生效后不同时间窗口的产业行为变化
```

### 2.2 TGAT架构设计

**2.2.1 时间注意力机制**

```python
class TemporalAttention(nn.Module):
    """时序注意力层

    输入：
    - h_src: 源节点嵌入 [N, D]
    - h_dst: 目标节点嵌入 [M, D]
    - t_src: 源节点时间戳 [N]
    - t_dst: 目标节点时间戳 [M]
    - edge_index: 边索引 [2, E]
    - edge_time: 边时间戳 [E]

    输出：
    - h_dst_new: 更新后的目标节点嵌入 [M, D]

    核心公式：
    α_ij = softmax(φ(h_i, h_j, Δt_ij))  # Δt_ij = t_edge - t_dst
    h_i' = Σ α_ij * ψ(h_j, Δt_ij)

    其中：
    - φ: 时序注意力权重函数（Query-Key机制 + 时间编码）
    - ψ: 时序消息函数（Value变换 + 时间调制）
    - Δt_ij: 相对时间差（边发生时间 - 目标节点时间）
    """
```

**2.2.2 时间编码集成**

```python
# 使用我们已实现的Bochner时间编码器
from models.bochner_time_encoder import BochnerTimeEncoder

class TGAT(nn.Module):
    def __init__(self, ...):
        self.time_encoder = BochnerTimeEncoder(dim=32, trainable=True)

    def forward(self, h_src, h_dst, edge_index, edge_time, t_dst):
        # 计算相对时间差
        delta_t = edge_time - t_dst[edge_index[1]]  # [E]

        # Bochner编码
        time_feat = self.time_encoder(delta_t)  # [E, 32]

        # 融入注意力计算
        ...
```

**2.2.3 HGT-TGAT融合策略**

提供三种融合方式（CLAUDE.md建议灵活选择）：

```python
class HGT_TGAT_Hybrid(nn.Module):
    """HGT-TGAT混合模型

    支持三种融合策略：
    1. early_fusion：先TGAT聚合时序邻居，再HGT聚合异质邻居
    2. late_fusion：先HGT聚合异质邻居，再TGAT建模时序演化
    3. parallel_fusion：HGT和TGAT并行计算，加权融合
    """

    def __init__(self, fusion_mode='late_fusion'):
        self.hgt = HGT(...)
        self.tgat = TGAT(...)
        self.fusion_mode = fusion_mode

    def forward(self, ...):
        if self.fusion_mode == 'early_fusion':
            # Step 1: TGAT时序聚合
            h_dict_temporal = self.tgat(x_dict, edge_index_dict, edge_time_dict)
            # Step 2: HGT异质聚合
            h_dict_final = self.hgt(h_dict_temporal, edge_index_dict)

        elif self.fusion_mode == 'late_fusion':
            # Step 1: HGT异质聚合
            h_dict_hetero = self.hgt(x_dict, edge_index_dict)
            # Step 2: TGAT时序演化
            h_dict_final = self.tgat(h_dict_hetero, edge_index_dict, edge_time_dict)

        elif self.fusion_mode == 'parallel_fusion':
            # 并行计算
            h_dict_hgt = self.hgt(x_dict, edge_index_dict)
            h_dict_tgat = self.tgat(x_dict, edge_index_dict, edge_time_dict)
            # 加权融合
            h_dict_final = {
                node_type: α * h_dict_hgt[node_type] + (1-α) * h_dict_tgat[node_type]
                for node_type in x_dict.keys()
            }

        return h_dict_final
```

### 2.3 实现文件清单

**需要创建的文件**：

1. **scripts/models/tgat_model.py**（核心模块）
   - `TemporalAttention`：时序注意力层
   - `TGAT`：完整TGAT模型
   - 输入：节点嵌入 + 边时间戳
   - 输出：时序更新后的节点嵌入

2. **scripts/models/hgt_tgat_model.py**（融合模块）
   - `HGT_TGAT_Hybrid`：HGT-TGAT混合模型
   - 支持三种融合模式
   - 提供消融研究接口

3. **scripts/build_graph_pyg.py修改**（数据准备）
   - 从政策JSON中提取`pub_date`或`effective_date`
   - 转换为Unix时间戳
   - 添加到`edge_attr`或单独的`edge_time`字段

4. **scripts/train_hgt_tgat.py**（训练脚本）
   - 复制train_hgt.py结构
   - 替换模型为HGT_TGAT_Hybrid
   - 添加时间戳数据加载
   - 保持NaN检测和梯度裁剪机制

### 2.4 时间戳数据准备

**从现有政策JSON提取时间**：

```python
# 示例：corpus/raw/policy_central/xxx.json
{
    "title": "关于加快培育和发展战略性新兴产业的决定",
    "pub_date": "2010-10-18",           # 发布日期
    "effective_date": "2010-10-18",     # 生效日期
    "source": "国务院",
    ...
}

# 转换为时间戳
from datetime import datetime
pub_timestamp = int(datetime.fromisoformat("2010-10-18").timestamp())
```

**边时间戳提取逻辑**：

```python
# build_graph_pyg.py中添加
for edge_type in data.edge_types:
    src_type, rel, dst_type = edge_type

    if src_type == 'policy':
        # 政策节点的边使用政策发布时间
        policy_ids = edge_index[0]
        edge_timestamps = torch.tensor([
            policy_metadata[pid]['pub_timestamp']
            for pid in policy_ids
        ])
        data[edge_type].edge_time = edge_timestamps
```

### 2.5 评测标准（CLAUDE.md第545-565行）

**必须达到**：
- 链路预测AUC ≥ 0.80
- 时间切分验证：Train<2020, Valid=2020, Test>2020
- 消融研究：去时序（HGT only）→ 性能下降

**对照实验**：
```python
# 实验1：HGT only（baseline）
model_hgt = HGT(...)
auc_hgt = evaluate(model_hgt)

# 实验2：TGAT only（仅时序）
model_tgat = TGAT(...)
auc_tgat = evaluate(model_tgat)

# 实验3：HGT-TGAT Hybrid（完整）
model_hybrid = HGT_TGAT_Hybrid(fusion_mode='late_fusion')
auc_hybrid = evaluate(model_hybrid)

# 期望：auc_hybrid > auc_hgt, auc_tgat
```

## 3. P2 DAPT/TAPT预训练实现方案

### 3.1 DAPT/TAPT原理与设计目标

**核心思想**：在通用预训练模型基础上，注入领域知识和任务知识。

**两阶段适配**：
```
通用预训练模型（BERT/RoBERTa）
    ↓ DAPT (Domain-Adaptive Pre-Training)
政策领域适配模型（在政策语料上继续MLM）
    ↓ TAPT (Task-Adaptive Pre-Training)
政策五元组抽取模型（在标注数据上继续MLM）
    ↓ Fine-tuning
最终任务模型（五元组抽取）
```

**PSC-Graph场景**：
- DAPT语料：10万+政策文档（中央+省级）
- TAPT语料：500-1000条已标注政策片段
- 目标：F1 ≥ 0.85（CLAUDE.md第540行要求）

### 3.2 DAPT实现方案

**3.2.1 语料准备**

```python
# scripts/prep_dapt_corpus.py
class DAPTCorpusBuilder:
    """DAPT语料构建器

    输入：corpus/raw/policy_central/*.json
         corpus/raw/policy_prov/*.json
    输出：data/dapt_corpus.txt（纯文本，每行一个句子）

    处理：
    1. 提取政策正文（content字段）
    2. 句子切分（使用jieba或pkuseg）
    3. 过滤短句（<10字）和重复句
    4. 输出格式：每行一个句子，空行分隔文档
    """

    def build_corpus(self):
        corpus_files = []
        corpus_files += list(Path("corpus/raw/policy_central").glob("*.json"))
        corpus_files += list(Path("corpus/raw/policy_prov").glob("*.json"))

        sentences = []
        for file in corpus_files:
            policy = json.load(open(file))
            content = policy.get('content', '')

            # 句子切分
            sents = self.split_sentences(content)

            # 过滤和清洗
            sents = [s for s in sents if len(s) >= 10]

            sentences.extend(sents)

        # 去重
        sentences = list(set(sentences))

        # 输出
        with open("data/dapt_corpus.txt", 'w') as f:
            for sent in sentences:
                f.write(sent + '\n')

        print(f"✓ DAPT语料构建完成：{len(sentences)}个句子")
```

**3.2.2 MLM训练**

```python
# scripts/run_dapt.py
from transformers import (
    AutoTokenizer, AutoModelForMaskedLM,
    DataCollatorForLanguageModeling, Trainer, TrainingArguments
)

class DAPTTrainer:
    """DAPT训练器

    基础模型：hfl/chinese-roberta-wwm-ext（哈工大RoBERTa）
    训练任务：Masked Language Modeling (MLM)
    训练轮数：3-5 epochs
    学习率：5e-5
    Batch size：16-32
    """

    def __init__(self):
        self.model_name = "hfl/chinese-roberta-wwm-ext"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForMaskedLM.from_pretrained(self.model_name)

    def train(self, corpus_path="data/dapt_corpus.txt"):
        # 加载语料
        dataset = self.load_corpus(corpus_path)

        # 数据整理器（自动mask 15%的token）
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=True,
            mlm_probability=0.15
        )

        # 训练参数
        training_args = TrainingArguments(
            output_dir="results/dapt_checkpoints",
            num_train_epochs=3,
            per_device_train_batch_size=16,
            learning_rate=5e-5,
            warmup_steps=500,
            logging_steps=100,
            save_steps=1000,
            save_total_limit=2,
        )

        # 训练器
        trainer = Trainer(
            model=self.model,
            args=training_args,
            data_collator=data_collator,
            train_dataset=dataset,
        )

        # 开始训练
        trainer.train()

        # 保存
        self.model.save_pretrained("results/dapt_model")
        self.tokenizer.save_pretrained("results/dapt_model")

        print("✓ DAPT训练完成")
```

### 3.3 TAPT实现方案

**3.3.1 任务语料准备**

```python
# scripts/prep_tapt_task.py
class TAPTTaskCorpusBuilder:
    """TAPT任务语料构建器

    输入：annotations/adjudicated/*.json（已标注的政策五元组）
    输出：data/tapt_corpus.txt

    策略：提取已标注段落的上下文，扩大训练语料
    """

    def build_task_corpus(self):
        anno_files = list(Path("annotations/adjudicated").glob("*.json"))

        sentences = []
        for file in anno_files:
            anno = json.load(open(file))

            # 提取evidence_spans对应的句子
            content = anno['content']
            for span in anno.get('evidence_spans', []):
                start, end = span['start'], span['end']
                text = content[start:end]
                sentences.append(text)

            # 提取整个段落（扩大上下文）
            paragraphs = content.split('\n')
            sentences.extend([p for p in paragraphs if len(p) >= 20])

        # 去重
        sentences = list(set(sentences))

        # 输出
        with open("data/tapt_corpus.txt", 'w') as f:
            for sent in sentences:
                f.write(sent + '\n')

        print(f"✓ TAPT语料构建完成：{len(sentences)}个句子")
```

**3.3.2 TAPT训练**

```python
# scripts/run_tapt.py
class TAPTTrainer:
    """TAPT训练器

    基础模型：results/dapt_model（DAPT输出）
    训练任务：Masked Language Modeling (MLM)
    训练轮数：5-10 epochs（任务语料较小，可多训练）
    学习率：2e-5（比DAPT更小，避免灾难性遗忘）
    """

    def __init__(self):
        # 加载DAPT模型
        self.model = AutoModelForMaskedLM.from_pretrained("results/dapt_model")
        self.tokenizer = AutoTokenizer.from_pretrained("results/dapt_model")

    def train(self, corpus_path="data/tapt_corpus.txt"):
        # 训练流程与DAPT类似，但参数调整
        training_args = TrainingArguments(
            output_dir="results/tapt_checkpoints",
            num_train_epochs=5,           # 更多轮数
            learning_rate=2e-5,            # 更小学习率
            ...
        )

        trainer.train()

        # 保存最终模型
        self.model.save_pretrained("results/tapt_model")
        print("✓ TAPT训练完成")
```

### 3.4 集成到RAG流程

**修改retrieve_evidence.py**：

```python
# 原来的实现
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 修改后的实现
from transformers import AutoModel, AutoTokenizer

class TAPTEmbedder:
    """使用TAPT模型生成嵌入

    优势：包含政策领域知识，语义表示更准确
    """

    def __init__(self):
        self.model = AutoModel.from_pretrained("results/tapt_model")
        self.tokenizer = AutoTokenizer.from_pretrained("results/tapt_model")

    def encode(self, texts):
        inputs = self.tokenizer(texts, padding=True, truncation=True,
                               return_tensors='pt')
        outputs = self.model(**inputs)

        # 使用[CLS] token的嵌入
        embeddings = outputs.last_hidden_state[:, 0, :]

        return embeddings.detach().numpy()

# 在build_index.py中使用
embedder = TAPTEmbedder()
embeddings = embedder.encode(policy_texts)
faiss_index.add(embeddings)
```

### 3.5 评测标准（CLAUDE.md第536-548行）

**必须达到**：
- F1 ≥ 0.85（实体/关系抽取）
- ARES评测：
  - 上下文相关性 ≥ 0.85
  - 忠实度 ≥ 0.90
  - 答案相关性 ≥ 0.88

**对照实验**：
```python
# 实验1：无DAPT/TAPT（零样本LLM）
model_baseline = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
f1_baseline = evaluate_f1(model_baseline)

# 实验2：仅DAPT（域适配）
model_dapt = load_model("results/dapt_model")
f1_dapt = evaluate_f1(model_dapt)

# 实验3：DAPT+TAPT（完整）
model_tapt = load_model("results/tapt_model")
f1_tapt = evaluate_f1(model_tapt)

# 期望：f1_tapt > f1_dapt > f1_baseline
```

## 4. 实现时间表

### 4.1 P1 TGAT实现（3-5天）

**Day 1-2：核心模块实现**
- [ ] 创建scripts/models/tgat_model.py
  - TemporalAttention类
  - TGAT类
  - 单元测试
- [ ] 创建scripts/models/hgt_tgat_model.py
  - HGT_TGAT_Hybrid类
  - 三种融合模式

**Day 3：数据准备**
- [ ] 修改build_graph_pyg.py
  - 提取政策时间戳
  - 添加edge_time字段
- [ ] 生成带时间戳的图数据

**Day 4-5：训练和验证**
- [ ] 创建scripts/train_hgt_tgat.py
  - 复制train_hgt.py结构
  - 集成TGAT模块
- [ ] 运行消融研究
- [ ] 生成评测报告

### 4.2 P2 DAPT/TAPT实现（5-7天）

**Day 1-2：DAPT**
- [ ] 创建scripts/prep_dapt_corpus.py
  - 语料构建
  - 清洗和去重
- [ ] 创建scripts/run_dapt.py
  - MLM训练
  - 3-5 epochs

**Day 3-4：TAPT**
- [ ] 创建scripts/prep_tapt_task.py
  - 任务语料提取
- [ ] 创建scripts/run_tapt.py
  - 基于DAPT模型继续训练
  - 5-10 epochs

**Day 5-6：集成和验证**
- [ ] 修改retrieve_evidence.py
  - 使用TAPT模型生成嵌入
- [ ] 重新构建FAISS索引
- [ ] 运行F1评测

**Day 7：对照实验和文档**
- [ ] 运行完整对照实验
- [ ] 生成评测报告
- [ ] 更新文档

## 5. 风险与应对

### 5.1 技术风险

**风险1：TGAT训练时间过长**
- 原因：时序注意力计算复杂度高
- 应对：使用邻域采样（k=10-20）+ 批处理

**风险2：DAPT/TAPT需要GPU资源**
- 原因：MLM训练需要24GB显存
- 应对：使用梯度累积（accumulation_steps=4）降低batch size

**风险3：时间戳数据缺失**
- 原因：部分政策JSON无pub_date字段
- 应对：使用爬取时间作为fallback

### 5.2 质量风险

**风险1：TGAT可能不显著提升性能**
- 原因：PSC-Graph场景中时序依赖可能较弱
- 应对：如果消融研究显示提升<2%，记录但不强制使用

**风险2：DAPT/TAPT可能F1仍<0.85**
- 原因：标注数据不足或质量问题
- 应对：增加标注数据量 or 使用数据增强

## 6. 成功标准

### 6.1 P1 TGAT

- [x] 代码通过单元测试
- [ ] HGT-TGAT模型成功训练（无NaN）
- [ ] 消融研究：去时序后AUC下降≥2%
- [ ] 生成事件研究可视化

### 6.2 P2 DAPT/TAPT

- [ ] 语料构建完成（DAPT ≥50k句，TAPT ≥1k句）
- [ ] DAPT训练收敛（loss<1.0）
- [ ] TAPT训练收敛（loss<0.5）
- [ ] F1 ≥ 0.85 或说明原因

### 6.3 整体集成

- [ ] Makefile新增tgat、dapt、tapt目标
- [ ] 所有脚本可独立运行
- [ ] 生成完整的验证报告

---

## 附录：关键代码片段

### A1. TGAT核心注意力计算

```python
def temporal_attention(self, h_src, h_dst, edge_index, delta_t):
    """时序注意力计算

    Args:
        h_src: 源节点嵌入 [N, D]
        h_dst: 目标节点嵌入 [M, D]
        edge_index: [2, E]
        delta_t: 相对时间差 [E]

    Returns:
        h_dst_new: [M, D]
    """
    # 时间编码
    time_feat = self.time_encoder(delta_t)  # [E, 32]

    # Query-Key计算
    src_idx, dst_idx = edge_index
    query = self.W_q(h_dst[dst_idx])  # [E, D]
    key = self.W_k(h_src[src_idx])    # [E, D]

    # 融入时间特征
    key_with_time = torch.cat([key, time_feat], dim=-1)  # [E, D+32]
    key_with_time = self.W_time(key_with_time)           # [E, D]

    # 注意力权重
    attn_logits = (query * key_with_time).sum(dim=-1)   # [E]
    attn_weights = softmax(attn_logits, dst_idx)         # [E]

    # Value计算
    value = self.W_v(h_src[src_idx])  # [E, D]

    # 消息聚合
    messages = attn_weights.unsqueeze(-1) * value  # [E, D]
    h_dst_new = scatter_add(messages, dst_idx, dim=0, dim_size=h_dst.size(0))

    return h_dst_new
```

### A2. DAPT语料示例

```
# data/dapt_corpus.txt示例
加快培育和发展战略性新兴产业，对于推进产业结构升级和经济发展方式转变具有重要意义。
支持企业加大研发投入，提升自主创新能力。
鼓励金融机构创新金融产品和服务，支持战略性新兴产业发展。
完善财税政策，对符合条件的企业给予税收优惠。
...
```
