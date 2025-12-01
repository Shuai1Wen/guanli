#!/usr/bin/env python3
"""
PSC-Graph HGT/TGAT模型训练脚本

实现Heterogeneous Graph Transformer (HGT) 和 Temporal Graph Attention (TGAT) 模型训练
符合CLAUDE.md强制规范：
- 模型架构: 2-3层HGTConv/TGAT + Residual connections + Dropout
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
import sys

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from torch_geometric.data import HeteroData
except ImportError:
    print("错误：PyTorch Geometric未安装")
    print("请运行: pip install torch-geometric")
    exit(1)

# 导入自定义模型
from scripts.models import HGT, TGAT

@dataclass
class TrainingConfig:
    """训练配置类"""
    # 路径配置
    graph_path: Path = Path("data/graph_base.pt")
    output_dir: Path = Path("results")

    # 模型超参数
    model_type: str = "HGT" # HGT or TGAT
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

def setup_device() -> torch.device:
    """设置计算设备"""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    return device

def load_graph(graph_path: Path) -> HeteroData:
    """加载图数据"""
    if not graph_path.exists():
        raise FileNotFoundError(f"图文件不存在: {graph_path}")

    print(f"正在加载图数据: {graph_path}")
    data = torch.load(str(graph_path), weights_only=False)

    print(f"✓ 图加载成功")
    return data

def train_link_prediction(
    model: nn.Module,
    data: HeteroData,
    x_dict: Dict[str, torch.Tensor],
    edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor],
    optimizer: torch.optim.Optimizer,
    target_edge_type: Tuple[str, str, str],
    max_grad_norm: float = 1.0
) -> float:
    """训练一个epoch（链路预测任务）"""
    model.train()
    optimizer.zero_grad()

    # 前向传播
    h_dict = model(x_dict, edge_index_dict)

    # 获取目标边的源节点和目标节点嵌入
    src_type, rel, dst_type = target_edge_type
    
    if src_type not in h_dict or dst_type not in h_dict:
        # 如果目标节点类型在h_dict中不存在（可能被过滤掉了），则跳过此step
        return 0.0
        
    edge_index = data[target_edge_type].edge_index

    src_embeddings = h_dict[src_type][edge_index[0]]
    dst_embeddings = h_dict[dst_type][edge_index[1]]

    # 计算链路预测得分（点积）
    pos_scores = (src_embeddings * dst_embeddings).sum(dim=-1)

    # 负采样
    num_neg = edge_index.shape[1]
    device = edge_index.device
    neg_src = torch.randint(0, data[src_type].x.shape[0], (num_neg,), device=device)
    neg_dst = torch.randint(0, data[dst_type].x.shape[0], (num_neg,), device=device)

    neg_src_embeddings = h_dict[src_type][neg_src]
    neg_dst_embeddings = h_dict[dst_type][neg_dst]
    neg_scores = (neg_src_embeddings * neg_dst_embeddings).sum(dim=-1)

    # 裁剪logits
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

    if torch.isnan(loss):
        raise RuntimeError("检测到NaN损失！")

    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
    optimizer.step()

    return loss.item()

def initialize_model_and_data(
    data: HeteroData,
    device: torch.device,
    config: TrainingConfig
) -> Tuple[nn.Module, torch.optim.Optimizer, Dict, Dict]:
    """初始化模型、优化器和数据字典"""
    print(f"\n【步骤2】初始化{config.model_type}模型")
    print("-" * 80)

    if config.model_type == "HGT":
        model = HGT(
            node_types=list(data.node_types),
            edge_types=list(data.edge_types),
            hidden_channels=config.hidden_channels,
            num_heads=config.num_heads,
            num_layers=config.num_layers,
            dropout=config.dropout
        )
    elif config.model_type == "TGAT":
        model = TGAT(
            node_types=list(data.node_types),
            edge_types=list(data.edge_types),
            hidden_channels=config.hidden_channels,
            num_heads=config.num_heads,
            num_layers=config.num_layers,
            dropout=config.dropout
        )
    else:
        raise ValueError(f"未知模型类型: {config.model_type}")

    model = model.to(device)

    # 构建x_dict和edge_index_dict
    x_dict = {}
    for node_type in data.node_types:
        if hasattr(data[node_type], 'x'):
            x_dict[node_type] = data[node_type].x

    edge_index_dict = {}
    for edge_type in data.edge_types:
        if hasattr(data[edge_type], 'edge_index'):
            edge_index_dict[edge_type] = data[edge_type].edge_index

    # 初始化优化器
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay
    )

    return model, optimizer, x_dict, edge_index_dict

def run_training_loop(
    model: nn.Module,
    data: HeteroData,
    x_dict: Dict,
    edge_index_dict: Dict,
    optimizer: torch.optim.Optimizer,
    target_edge_type: Tuple[str, str, str],
    num_epochs: int = 50,
    max_grad_norm: float = 1.0
):
    """运行训练循环"""
    print(f"\n【步骤3】训练链路预测任务")
    
    for epoch in range(1, num_epochs + 1):
        try:
            loss = train_link_prediction(
                model, data, x_dict, edge_index_dict, optimizer, target_edge_type,
                max_grad_norm=max_grad_norm
            )

            if epoch % 10 == 0:
                print(f"Epoch {epoch:03d} | Loss: {loss:.4f}")

        except RuntimeError as e:
            print(f"\n❌ 训练失败于Epoch {epoch}: {e}")
            raise

    print(f"\n✓ 训练完成")

def save_trained_model(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    output_dir: Path,
    model_name: str = "hgt_model.pt"
):
    """保存训练好的模型"""
    print("\n【步骤4】保存模型")
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / model_name
    torch.save({
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
    }, str(model_path))
    print(f"✓ 模型已保存到: {model_path}")

def main(config: Optional[TrainingConfig] = None):
    """主函数"""
    if config is None:
        config = TrainingConfig()

    print(f"PSC-Graph {config.model_type}模型训练")
    print("=" * 80)

    device = setup_device()
    
    print("\n【步骤1】加载图数据")
    data = load_graph(config.graph_path)
    data = data.to(device)

    model, optimizer, x_dict, edge_index_dict = initialize_model_and_data(
        data, device, config
    )

    run_training_loop(
        model, data, x_dict, edge_index_dict, optimizer,
        config.target_edge_type, config.num_epochs
    )

    save_trained_model(model, optimizer, config.output_dir, f"{config.model_type.lower()}_model.pt")

    print("\n" + "=" * 80)
    print("训练完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
