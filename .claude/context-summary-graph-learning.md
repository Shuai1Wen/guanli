## 项目上下文摘要（图学习层）
生成时间: 2025-11-17 15:15

### 1. 相似实现分析
项目中**未找到**现有的图构建代码，这是全新的模块。

**项目现有脚本模式**（参考已有实现）:
- `scripts/build_index.py`: RAG索引构建（287行）
  - 模式：数据加载 → 处理 → 索引构建 → 保存到indexes/
  - 可复用：文档加载逻辑、路径管理模式
  - 需注意：使用pickle保存索引，需确保序列化安全

- `scripts/calibrate_and_conformal.py`: 校准脚本（323行）
  - 模式：类封装 + 演示函数
  - 可复用：demo函数模式、numpy数组处理
  - 需注意：scipy优化器使用模式

- `scripts/evaluate_retrieval.py`: 评估脚本（323行）
  - 模式：评估器类 + 指标计算静态方法
  - 可复用：评估流程、结果表格输出
  - 需注意：从annotations/自动生成测试数据

### 2. 项目约定
- **命名约定**:
  - 文件名: `snake_case.py`（如`build_index.py`）
  - 类名: `PascalCase`（如`HybridRetriever`）
  - 函数名: `snake_case`（如`hybrid_search`）
  - 私有方法: 无特殊标识，依赖文档说明

- **文件组织**:
  - 脚本位于`scripts/`目录
  - 数据输出到对应目录（`indexes/`, `data/`, `results/`）
  - 中间文件使用pickle或JSON格式

- **导入顺序**:
  1. 标准库（json, pathlib等）
  2. 第三方库（numpy, torch等）
  3. 项目内部模块（相对导入）

- **代码风格**:
  - UTF-8编码，简体中文注释
  - 类和函数都有文档字符串
  - 主函数模式：`if __name__ == "__main__": main()`

### 3. 可复用组件清单
**无直接可复用的图构建组件**，但可参考以下工具：
- `scripts/crawler_common.py`: 文件路径管理、SHA256计算
- `scripts/build_index.py`: 文档加载和批处理逻辑
- `sentence_transformers` (已安装): 文本嵌入生成（384维向量）

### 4. 测试策略
- **测试框架**: 项目暂无正式测试框架，使用演示函数验证
- **测试模式**: 每个脚本包含`main()`函数进行功能演示
- **参考文件**: `scripts/calibrate_and_conformal.py`的`demo_calibration()`
- **覆盖要求**:
  - 正常流程：图构建成功，保存到文件
  - 边界条件：空节点、孤立节点、无边情况
  - 错误处理：数据缺失、格式错误

### 5. 依赖和集成点
**外部依赖**（需新增）:
- `torch-geometric`: HGT模型核心库（**尚未安装**）
- `torch-scatter`, `torch-sparse`: PyG依赖（**尚未安装**）

**内部依赖**:
- `annotations/`: 标注数据（提取policy节点）
- `corpus/`: 政策文档（提取文本特征）
- `indexes/`: 句子嵌入模型（生成节点特征）
- `data/`: 统计数据（提取region/actor节点特征）

**集成方式**:
- 从标注数据提取图结构（五元组 → 节点和边）
- 使用sentence-transformers生成节点文本特征
- 输出PyG Data对象，保存为`.pt`文件

**配置来源**:
- `schemas/policy_schema.json`: 标注结构定义
- `data/province_codes.csv`: 地区编码映射

### 6. 技术选型理由（基于CLAUDE.md强制要求）
**为什么用PyTorch Geometric + HGT**:
- PyG是图学习标准库，生态成熟
- HGT专为异质图设计，支持多类型节点和边
- 内置时间编码，满足时序图需求
- 官方示例完整（OGB-MAG数据集示例）

**优势**:
- 高效的消息传递机制
- 支持mini-batch训练（节约显存）
- 可解释性好（注意力权重可视化）
- 与PyTorch生态无缝集成

**劣势和风险**:
- 安装依赖复杂（torch-scatter, torch-sparse需编译）
- GPU显存需求较高（建议≥24GB）
- 过平滑问题（需限制2-3层）

### 7. 关键风险点
**并发问题**:
- 图构建为单线程处理，无并发风险
- 保存时需确保原子性操作

**边界条件**:
- 孤立节点处理：保留但标记
- 空标注文件：跳过并记录警告
- 时间戳缺失：使用文档发布日期

**性能瓶颈**:
- 大规模图构建：考虑分批处理
- 特征生成：sentence-transformers在CPU上较慢
- 内存占用：533文档×384维≈0.8MB（可接受）

**安全考虑**:
- pickle反序列化风险：仅加载可信文件
- 路径遍历：验证文件路径合法性

---

## PyTorch Geometric HGT 核心API

### HGTConv层
```python
from torch_geometric.nn import HGTConv

# 初始化
conv = HGTConv(
    in_channels,      # 输入特征维度（或-1自动推断）
    out_channels,     # 输出特征维度
    metadata,         # (node_types, edge_types)元组
    num_heads,        # 注意力头数（建议4-8）
    group='sum'       # 聚合方式：'sum', 'mean', 'min', 'max'
)

# 前向传播
x_dict = conv(x_dict, edge_index_dict)
# x_dict: {node_type: Tensor}
# edge_index_dict: {edge_type: Tensor}
```

### 异质图数据结构
```python
from torch_geometric.data import HeteroData

data = HeteroData()

# 添加节点
data['policy'].x = torch.randn(num_policies, 384)
data['region'].x = torch.randn(num_regions, 128)

# 添加边
data['policy', 'apply_to', 'region'].edge_index = edge_index
data['policy', 'apply_to', 'region'].edge_attr = edge_features

# 元数据
metadata = (
    ['policy', 'region', 'actor', 'topic', 'funding'],  # 节点类型
    [('policy', 'apply_to', 'region'), ...]             # 边类型
)
```

### 官方示例模式
```python
class HGT(torch.nn.Module):
    def __init__(self, hidden_channels, out_channels, num_heads, num_layers):
        super().__init__()
        # 1. 每种节点类型独立的输入投影层
        self.lin_dict = torch.nn.ModuleDict()
        for node_type in node_types:
            self.lin_dict[node_type] = Linear(-1, hidden_channels)

        # 2. HGT卷积层（2-3层）
        self.convs = torch.nn.ModuleList()
        for _ in range(num_layers):
            conv = HGTConv(hidden_channels, hidden_channels,
                          metadata, num_heads)
            self.convs.append(conv)

        # 3. 输出层
        self.lin = Linear(hidden_channels, out_channels)

    def forward(self, x_dict, edge_index_dict):
        # 输入投影
        for node_type, x in x_dict.items():
            x_dict[node_type] = self.lin_dict[node_type](x).relu_()

        # HGT层
        for conv in self.convs:
            x_dict = conv(x_dict, edge_index_dict)

        # 输出（示例：仅取目标节点）
        return self.lin(x_dict['target_node_type'])
```

---

## CLAUDE.md强制要求摘要

### 节点类型（必须实现）
- **Policy**: 政策文档节点
- **Actor**: 企业/高校/科研院所
- **Region**: 地区（省/市/区）
- **Topic**: 技术主题/IPC分类
- **Funding**: 资金/平台

### 边类型（必须实现）
- `publish→apply`: 政策发布→适用对象
- `fund→benefit`: 资金→受益主体
- `constraint→object`: 约束→对象
- `co-occurrence`: 共现关系
- `temporal`: 时间邻接

### 特征要求（必须）
- 文本嵌入: sentence-transformers 384维
- 统计特征: GDP/R&D/专利等
- 时间戳: Unix时间或ISO8601

### 模型架构（强制）
- 层数: 2-3层（避免过平滑）
- 跳连: Residual connections
- 正则: Dropout 0.1-0.3
- 负采样: 1:5比例

### 时间切分（强制）
- 训练集: t < t_val
- 验证集: t = t_val
- 测试集: t > t_val
- **禁止时间泄露**

### 评测指标（必须报告）
- 链路预测: AUC, AP
- 节点分类: Macro-F1
- 可解释性: 高权重路径回查

### 消融研究（必须进行）
- 去时序（HGT only）
- 去异质（GAT/GCN）
- 去RAG证据（随机初始化）

---

## 实施计划关键决策

### 分阶段实施策略
**阶段1：基础图构建**（当前任务）
- 从标注数据提取节点和边
- 生成基础异质图结构
- 输出PyG HeteroData对象

**阶段2：特征工程**
- 文本嵌入（sentence-transformers）
- 统计特征集成
- 时间戳编码

**阶段3：模型训练**（后续任务）
- HGT模型实现
- 训练/验证/测试切分
- 评测指标计算

### 数据流设计
```
annotations/
    ↓ (提取五元组)
节点提取
    ↓ (去重+编码)
节点ID映射
    ↓
边提取
    ↓ (类型分类)
HeteroData对象
    ↓ (添加特征)
完整图数据
    ↓ (保存)
data/graph_base.pt
```

### 依赖安装顺序
1. 检查torch版本（已安装2.9.1）
2. 安装torch-geometric（需匹配torch版本）
3. 安装torch-scatter, torch-sparse（可能需要编译）
4. 验证导入成功

---

*本摘要遵循CLAUDE.md强制规范，确保充分性检查通过后再进入实施阶段。*
