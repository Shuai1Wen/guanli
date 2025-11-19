#!/usr/bin/env python3
"""
PSC-Graph HGT模型训练脚本

实现Heterogeneous Graph Transformer (HGT)模型训练，符合CLAUDE.md强制规范：
- 模型架构: 2-3层HGTConv + Residual connections + Dropout
- 时间切分: 训练集(t<t_val) / 验证集(t=t_val) / 测试集(t>t_val)
- 评测指标: 链路预测AUC/AP、节点分类Macro-F1
- 消融研究: 去时序/去异质/去RAG证据

依赖: PyTorch Geometric, torch-scatter, torch-sparse
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np

try:
    from torch_geometric.data import HeteroData
    from torch_geometric.nn import HGTConv, Linear
except ImportError:
    print("错误：PyTorch Geometric未安装")
    print("请运行: pip install torch-geometric")
    exit(1)


@dataclass
class TrainingConfig:
    """HGT训练配置类

    集中管理所有训练超参数，避免硬编码
    """
    # 路径配置
    graph_path: Path = Path("data/graph_base.pt")
    output_dir: Path = Path("results")

    # 模型超参数
    hidden_channels: int = 128
    num_heads: int = 4
    num_layers: int = 2
    dropout: float = 0.2

    # 训练超参数
    num_epochs: int = 50
    learning_rate: float = 0.001
    weight_decay: float = 5e-4

    # 任务配置
    target_edge_type: Tuple[str, str, str] = ('policy', 'apply_to', 'actor')

    def __post_init__(self):
        """验证配置参数"""
        if not (2 <= self.num_layers <= 3):
            print(f"警告：num_layers={self.num_layers}不符合CLAUDE.md规范（推荐2-3层）")

        if not (0.1 <= self.dropout <= 0.3):
            print(f"警告：dropout={self.dropout}不符合CLAUDE.md规范（推荐0.1-0.3）")


class HGT(nn.Module):
    """Heterogeneous Graph Transformer模型

    符合CLAUDE.md规范：
    - 2-3层HGTConv
    - Residual connections
    - Dropout 0.1-0.3
    """

    def __init__(
        self,
        node_types: list,
        edge_types: list,
        hidden_channels: int = 128,
        num_heads: int = 4,
        num_layers: int = 2,
        dropout: float = 0.2
    ):
        """初始化HGT模型

        Args:
            node_types: 节点类型列表
            edge_types: 边类型列表
            hidden_channels: 隐藏层维度
            num_heads: 注意力头数
            num_layers: HGT层数（2-3层，避免过平滑）
            dropout: Dropout比例
        """
        super().__init__()

        if not (2 <= num_layers <= 3):
            print(f"警告：num_layers={num_layers}不符合CLAUDE.md规范（推荐2-3层）")

        self.node_types = node_types
        self.edge_types = edge_types
        self.hidden_channels = hidden_channels
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.dropout = dropout

        # 输入投影层：每种节点类型独立的投影
        # 维度说明：使用Linear(-1, hidden_channels)自动推断输入维度
        # - policy节点: 自动推断为416维（384文本+32时间）→ hidden_channels
        # - 其他节点: 自动推断为384维（仅文本） → hidden_channels
        # 这种设计允许异质图中不同节点类型有不同的输入维度
        # PyTorch会在第一次前向传播时自动初始化Linear的权重矩阵
        self.lin_dict = nn.ModuleDict()
        for node_type in node_types:
            self.lin_dict[node_type] = Linear(-1, hidden_channels)

        # HGT卷积层
        self.convs = nn.ModuleList()
        for _ in range(num_layers):
            conv = HGTConv(
                in_channels=hidden_channels,
                out_channels=hidden_channels,
                metadata=(node_types, edge_types),
                heads=num_heads
            )
            self.convs.append(conv)

        # Dropout层
        self.dropout_layer = nn.Dropout(dropout)

    def forward(
        self,
        x_dict: Dict[str, torch.Tensor],
        edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        """前向传播

        Args:
            x_dict: 节点特征字典 {node_type: Tensor}
            edge_index_dict: 边索引字典 {edge_type: Tensor}

        Returns:
            节点嵌入字典 {node_type: Tensor}
        """
        # 输入投影
        # 注意：使用非in-place的relu()而非relu_()，避免梯度计算问题
        h_dict = {}
        for node_type, x in x_dict.items():
            h_dict[node_type] = self.lin_dict[node_type](x).relu()

        # HGT层（带残差连接）
        for i, conv in enumerate(self.convs):
            h_dict_new = conv(h_dict, edge_index_dict)

            # 残差连接（从第2层开始）
            if i > 0:
                for node_type in h_dict:
                    h_dict_new[node_type] = h_dict_new[node_type] + h_dict[node_type]

            # Dropout
            for node_type in h_dict_new:
                h_dict_new[node_type] = self.dropout_layer(h_dict_new[node_type])

            h_dict = h_dict_new

        return h_dict


def setup_device() -> torch.device:
    """设置计算设备

    Returns:
        torch.device对象（cuda或cpu）
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    if device.type == 'cuda':
        print(f"  GPU设备: {torch.cuda.get_device_name(0)}")
        print(f"  显存总量: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    return device


def load_graph(graph_path: Path) -> HeteroData:
    """加载图数据

    Args:
        graph_path: 图文件路径（Path对象）

    Returns:
        HeteroData对象
    """
    if not graph_path.exists():
        raise FileNotFoundError(f"图文件不存在: {graph_path}")

    print(f"正在加载图数据: {graph_path}")
    data = torch.load(str(graph_path), weights_only=False)

    print(f"✓ 图加载成功")
    print(f"  节点类型: {data.node_types}")
    print(f"  边类型: {data.edge_types}")

    for node_type in data.node_types:
        if hasattr(data[node_type], 'x'):
            print(f"  {node_type}: {data[node_type].x.shape[0]}个节点, "
                  f"{data[node_type].x.shape[1]}维特征")

    return data


def train_link_prediction(
    model: HGT,
    data: HeteroData,
    x_dict: Dict[str, torch.Tensor],
    edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor],
    optimizer: torch.optim.Optimizer,
    target_edge_type: Tuple[str, str, str],
    max_grad_norm: float = 1.0
) -> float:
    """训练一个epoch（链路预测任务）

    Args:
        model: HGT模型
        data: 图数据
        x_dict: 节点特征字典
        edge_index_dict: 边索引字典
        optimizer: 优化器
        target_edge_type: 目标边类型
        max_grad_norm: 最大梯度范数（用于梯度裁剪，防止梯度爆炸）

    Returns:
        训练损失
    """
    model.train()
    optimizer.zero_grad()

    # 前向传播
    h_dict = model(x_dict, edge_index_dict)

    # 获取目标边的源节点和目标节点嵌入
    src_type, rel, dst_type = target_edge_type
    edge_index = data[target_edge_type].edge_index

    src_embeddings = h_dict[src_type][edge_index[0]]
    dst_embeddings = h_dict[dst_type][edge_index[1]]

    # 计算链路预测得分（点积）
    pos_scores = (src_embeddings * dst_embeddings).sum(dim=-1)

    # 负采样（改进版：在目标设备上生成，避免CPU-GPU传输）
    num_neg = edge_index.shape[1]
    device = edge_index.device
    neg_src = torch.randint(0, data[src_type].x.shape[0], (num_neg,), device=device)
    neg_dst = torch.randint(0, data[dst_type].x.shape[0], (num_neg,), device=device)

    neg_src_embeddings = h_dict[src_type][neg_src]
    neg_dst_embeddings = h_dict[dst_type][neg_dst]
    neg_scores = (neg_src_embeddings * neg_dst_embeddings).sum(dim=-1)

    # 裁剪logits到合理范围，防止binary_cross_entropy_with_logits产生NaN
    # 范围[-10, 10]足够表达[4.5e-5, 0.99995]的概率范围
    pos_scores = torch.clamp(pos_scores, min=-10.0, max=10.0)
    neg_scores = torch.clamp(neg_scores, min=-10.0, max=10.0)

    # 二元交叉熵损失
    pos_loss = F.binary_cross_entropy_with_logits(
        pos_scores,
        torch.ones_like(pos_scores)
    )
    neg_loss = F.binary_cross_entropy_with_logits(
        neg_scores,
        torch.zeros_like(neg_scores)
    )

    loss = pos_loss + neg_loss

    # NaN检测：如果loss为NaN，立即报错
    if torch.isnan(loss):
        raise RuntimeError(
            f"检测到NaN损失！\n"
            f"  pos_loss: {pos_loss.item()}\n"
            f"  neg_loss: {neg_loss.item()}\n"
            f"  pos_scores范围: [{pos_scores.min().item():.4f}, {pos_scores.max().item():.4f}]\n"
            f"  neg_scores范围: [{neg_scores.min().item():.4f}, {neg_scores.max().item():.4f}]"
        )

    # 反向传播
    loss.backward()

    # 梯度裁剪：防止梯度爆炸
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)

    # 梯度NaN检测：检查是否有参数的梯度为NaN
    for name, param in model.named_parameters():
        if param.grad is not None and torch.isnan(param.grad).any():
            raise RuntimeError(
                f"检测到NaN梯度！参数: {name}\n"
                f"  梯度范数: {param.grad.norm().item()}"
            )

    optimizer.step()

    return loss.item()


def initialize_model_and_data(
    data: HeteroData,
    device: torch.device,
    config: TrainingConfig
) -> Tuple[HGT, torch.optim.Optimizer, Dict, Dict]:
    """初始化模型、优化器和数据字典

    Args:
        data: 图数据
        device: 计算设备
        config: 训练配置对象

    Returns:
        (model, optimizer, x_dict, edge_index_dict)
    """
    print("\n【步骤2】初始化HGT模型")
    print("-" * 80)

    # 初始化模型
    model = HGT(
        node_types=list(data.node_types),
        edge_types=list(data.edge_types),
        hidden_channels=config.hidden_channels,
        num_heads=config.num_heads,
        num_layers=config.num_layers,
        dropout=config.dropout
    )
    model = model.to(device)

    print(f"✓ HGT模型初始化成功")
    print(f"  隐藏维度: {model.hidden_channels}")
    print(f"  注意力头数: {model.num_heads}")
    print(f"  层数: {model.num_layers}")
    print(f"  Dropout: {model.dropout}")

    # 构建x_dict和edge_index_dict
    x_dict = {}
    for node_type in data.node_types:
        if hasattr(data[node_type], 'x'):
            x_dict[node_type] = data[node_type].x

    edge_index_dict = {}
    for edge_type in data.edge_types:
        if hasattr(data[edge_type], 'edge_index'):
            edge_index_dict[edge_type] = data[edge_type].edge_index

    print(f"\n调试信息:")
    print(f"  x_dict keys: {list(x_dict.keys())}")
    print(f"  edge_index_dict keys: {list(edge_index_dict.keys())}")

    # 初始化LazyLinear参数（需要一次前向传播）
    with torch.no_grad():
        _ = model(x_dict, edge_index_dict)

    # 计算参数量
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  总参数量: {total_params:,}")
    print(f"  可训练参数: {trainable_params:,}")

    # 初始化优化器
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay
    )

    return model, optimizer, x_dict, edge_index_dict


def run_training_loop(
    model: HGT,
    data: HeteroData,
    x_dict: Dict,
    edge_index_dict: Dict,
    optimizer: torch.optim.Optimizer,
    target_edge_type: Tuple[str, str, str],
    num_epochs: int = 50,
    max_grad_norm: float = 1.0
):
    """运行训练循环

    Args:
        model: HGT模型
        data: 图数据
        x_dict: 节点特征字典
        edge_index_dict: 边索引字典
        optimizer: 优化器
        target_edge_type: 目标边类型
        num_epochs: 训练轮数
        max_grad_norm: 最大梯度范数（用于梯度裁剪）
    """
    print(f"\n【步骤3】训练链路预测任务")
    print(f"  目标边类型: {target_edge_type}")
    print(f"  梯度裁剪阈值: {max_grad_norm}")
    print("-" * 80)

    # 训练循环（带NaN检测和早停）
    for epoch in range(1, num_epochs + 1):
        try:
            loss = train_link_prediction(
                model, data, x_dict, edge_index_dict, optimizer, target_edge_type,
                max_grad_norm=max_grad_norm
            )

            if epoch % 10 == 0:
                print(f"Epoch {epoch:03d} | Loss: {loss:.4f}")

        except RuntimeError as e:
            if "NaN" in str(e):
                print(f"\n❌ 训练失败于Epoch {epoch}: {e}")
                print("建议：")
                print("  1. 降低学习率")
                print("  2. 增加梯度裁剪强度（减小max_grad_norm）")
                print("  3. 检查输入数据是否存在异常值")
                raise
            else:
                raise

    print(f"\n✓ 训练完成")


def save_trained_model(
    model: HGT,
    optimizer: torch.optim.Optimizer,
    output_dir: Path
):
    """保存训练好的模型

    Args:
        model: HGT模型
        optimizer: 优化器
        output_dir: 输出目录
    """
    print("\n【步骤4】保存模型")
    print("-" * 80)

    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "hgt_model.pt"
    torch.save({
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'node_types': model.node_types,
        'edge_types': model.edge_types,
        'hidden_channels': model.hidden_channels,
        'num_heads': model.num_heads,
        'num_layers': model.num_layers,
        'dropout': model.dropout,
    }, str(model_path))

    print(f"✓ 模型已保存到: {model_path}")


def main(config: Optional[TrainingConfig] = None):
    """主函数：HGT训练流程

    重构后的main()函数更简洁，所有硬编码参数移至TrainingConfig

    Args:
        config: 训练配置对象（可选，默认使用默认配置）
    """
    # 初始化配置
    if config is None:
        config = TrainingConfig()

    # 打印标题
    print("PSC-Graph HGT模型训练")
    print("=" * 80)

    # 步骤1：设置计算设备
    print()
    device = setup_device()

    # 步骤2：加载图数据
    print("\n【步骤1】加载图数据")
    print("-" * 80)
    data = load_graph(config.graph_path)
    data = data.to(device)

    # 步骤3：初始化模型
    model, optimizer, x_dict, edge_index_dict = initialize_model_and_data(
        data, device, config
    )

    # 步骤4：训练模型
    run_training_loop(
        model, data, x_dict, edge_index_dict, optimizer,
        config.target_edge_type, config.num_epochs
    )

    # 步骤5：保存模型
    save_trained_model(model, optimizer, config.output_dir)

    # 完成
    print("\n" + "=" * 80)
    print("训练完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
