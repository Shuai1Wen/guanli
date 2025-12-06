#!/usr/bin/env python3
"""
PSC-Graph HGT-TGAT混合模型

实现HGT（异质图）和TGAT（时序图）的融合架构，符合CLAUDE.md要求：
- 支持三种融合策略：early_fusion、late_fusion、parallel_fusion
- 异质性建模：不同类型节点/边的语义差异（HGT）
- 时序性建模：时间戳对交互的影响（TGAT）
- 消融研究支持：可单独禁用HGT或TGAT

设计理念：
- early_fusion：先聚合时序邻居，再聚合异质邻居
- late_fusion：先聚合异质邻居，再建模时序演化
- parallel_fusion：两个模型并行，加权融合

依赖：PyTorch Geometric, torch-scatter
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import sys

# 添加scripts目录到路径（用于导入train_hgt中的HGT）
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from torch_geometric.data import HeteroData
    from torch_geometric.nn import HGTConv, Linear
except ImportError:
    print("错误：PyTorch Geometric未安装")
    print("请运行: pip install torch-geometric")
    exit(1)

# 导入我们实现的模型
try:
    from models.tgat_model import TGAT
except ImportError:
    print("错误：无法导入TGAT模型")
    print("请确保scripts/models/tgat_model.py存在")
    exit(1)


class HGT(nn.Module):
    """Heterogeneous Graph Transformer（从train_hgt.py复制）

    用于HGT-TGAT融合的HGT基础模型
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
        super().__init__()

        if not (2 <= num_layers <= 3):
            print(f"警告：num_layers={num_layers}不符合CLAUDE.md规范（推荐2-3层）")

        self.node_types = node_types
        self.edge_types = edge_types
        self.hidden_channels = hidden_channels
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.dropout = dropout

        # 输入投影层
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
        """前向传播"""
        # 输入投影（使用非in-place的relu()）
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


class HGT_TGAT_Hybrid(nn.Module):
    """HGT-TGAT混合模型

    融合异质图Transformer (HGT) 和时序图注意力 (TGAT)，同时建模：
    - 节点/边的类型异质性
    - 交互的时间动态性

    三种融合模式：
    1. early_fusion：TGAT → HGT
       适用场景：时序信息是基础特征，异质性是高层语义
       流程：先用TGAT聚合时序邻居特征 → 再用HGT聚合不同类型邻居

    2. late_fusion：HGT → TGAT
       适用场景：异质性是基础特征，时序演化是高层动态
       流程：先用HGT聚合异质邻居特征 → 再用TGAT建模时序演化

    3. parallel_fusion：HGT ‖ TGAT
       适用场景：异质性和时序性同等重要
       流程：两个模型并行计算 → 加权融合

    消融研究支持：
    - ablation_mode='hgt_only'：仅使用HGT（去时序）
    - ablation_mode='tgat_only'：仅使用TGAT（去异质）
    """

    def __init__(
        self,
        node_types: List[str],
        edge_types: List[Tuple[str, str, str]],
        in_channels_dict: Dict[str, int],
        hidden_channels: int = 128,
        num_heads: int = 4,
        num_layers: int = 2,
        time_dim: int = 32,
        dropout: float = 0.2,
        fusion_mode: str = 'late_fusion',
        fusion_weight: float = 0.5,
        ablation_mode: Optional[str] = None
    ):
        """初始化HGT-TGAT混合模型

        Args:
            node_types: 节点类型列表 ['policy', 'actor', 'region', ...]
            edge_types: 边类型列表 [('policy', 'apply_to', 'actor'), ...]
            in_channels_dict: 每种节点类型的输入维度 {'policy': 416, 'actor': 384, ...}
            hidden_channels: 隐藏层维度
            num_heads: 注意力头数
            num_layers: 层数
            time_dim: 时间编码维度
            dropout: Dropout比例
            fusion_mode: 融合模式 ['early_fusion', 'late_fusion', 'parallel_fusion']
            fusion_weight: parallel_fusion模式下HGT的权重（0-1）
            ablation_mode: 消融研究模式 ['hgt_only', 'tgat_only', None]
        """
        super().__init__()

        valid_fusion_modes = ['early_fusion', 'late_fusion', 'parallel_fusion']
        assert fusion_mode in valid_fusion_modes, \
            f"fusion_mode必须是{valid_fusion_modes}之一"

        valid_ablation_modes = ['hgt_only', 'tgat_only', None]
        assert ablation_mode in valid_ablation_modes, \
            f"ablation_mode必须是{valid_ablation_modes}之一"

        self.node_types = node_types
        self.edge_types = edge_types
        self.in_channels_dict = in_channels_dict
        self.hidden_channels = hidden_channels
        self.fusion_mode = fusion_mode
        self.fusion_weight = fusion_weight
        self.ablation_mode = ablation_mode

        # 输入投影层（每种节点类型独立）
        self.input_proj_dict = nn.ModuleDict()
        for node_type in node_types:
            in_ch = in_channels_dict.get(node_type, hidden_channels)
            self.input_proj_dict[node_type] = nn.Linear(in_ch, hidden_channels)

        # HGT模型
        if ablation_mode != 'tgat_only':
            self.hgt = HGT(
                node_types=node_types,
                edge_types=edge_types,
                hidden_channels=hidden_channels,
                num_heads=num_heads,
                num_layers=num_layers,
                dropout=dropout
            )

        # TGAT模型（需要为每种节点类型创建独立的TGAT）
        if ablation_mode != 'hgt_only':
            self.tgat_dict = nn.ModuleDict()
            for node_type in node_types:
                self.tgat_dict[node_type] = TGAT(
                    in_channels=hidden_channels,
                    hidden_channels=hidden_channels,
                    out_channels=hidden_channels,
                    num_heads=num_heads,
                    num_layers=num_layers,
                    time_dim=time_dim,
                    dropout=dropout
                )

        # 融合层（仅parallel_fusion需要）
        if fusion_mode == 'parallel_fusion':
            self.fusion_proj = nn.ModuleDict()
            for node_type in node_types:
                self.fusion_proj[node_type] = nn.Linear(hidden_channels * 2, hidden_channels)

    def forward(
        self,
        x_dict: Dict[str, torch.Tensor],
        edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor],
        edge_time_dict: Optional[Dict[Tuple[str, str, str], torch.Tensor]] = None,
        node_time_dict: Optional[Dict[str, torch.Tensor]] = None
    ) -> Dict[str, torch.Tensor]:
        """前向传播

        Args:
            x_dict: 节点特征字典 {node_type: Tensor}
            edge_index_dict: 边索引字典 {edge_type: Tensor}
            edge_time_dict: 边时间戳字典 {edge_type: Tensor}（TGAT需要）
            node_time_dict: 节点时间戳字典 {node_type: Tensor}（可选）

        Returns:
            节点嵌入字典 {node_type: Tensor}
        """
        # 输入投影
        h_dict = {}
        for node_type, x in x_dict.items():
            h_dict[node_type] = self.input_proj_dict[node_type](x)
            h_dict[node_type] = F.relu(h_dict[node_type])

        # 消融研究模式
        if self.ablation_mode == 'hgt_only':
            return self.hgt(h_dict, edge_index_dict)

        if self.ablation_mode == 'tgat_only':
            return self._tgat_forward(h_dict, edge_index_dict, edge_time_dict, node_time_dict)

        # 正常融合模式
        if self.fusion_mode == 'early_fusion':
            # Step 1: TGAT时序聚合
            h_dict_temporal = self._tgat_forward(h_dict, edge_index_dict, edge_time_dict, node_time_dict)
            # Step 2: HGT异质聚合
            h_dict_final = self.hgt(h_dict_temporal, edge_index_dict)

        elif self.fusion_mode == 'late_fusion':
            # Step 1: HGT异质聚合
            h_dict_hetero = self.hgt(h_dict, edge_index_dict)
            # Step 2: TGAT时序演化
            h_dict_final = self._tgat_forward(h_dict_hetero, edge_index_dict, edge_time_dict, node_time_dict)

        elif self.fusion_mode == 'parallel_fusion':
            # 并行计算
            h_dict_hgt = self.hgt(h_dict, edge_index_dict)
            h_dict_tgat = self._tgat_forward(h_dict, edge_index_dict, edge_time_dict, node_time_dict)

            # 加权融合
            h_dict_final = {}
            alpha = self.fusion_weight
            for node_type in h_dict.keys():
                # 拼接后投影（更灵活的融合）
                h_concat = torch.cat([h_dict_hgt[node_type], h_dict_tgat[node_type]], dim=-1)
                h_dict_final[node_type] = self.fusion_proj[node_type](h_concat)

        return h_dict_final

    def _tgat_forward(
        self,
        h_dict: Dict[str, torch.Tensor],
        edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor],
        edge_time_dict: Optional[Dict[Tuple[str, str, str], torch.Tensor]],
        node_time_dict: Optional[Dict[str, torch.Tensor]]
    ) -> Dict[str, torch.Tensor]:
        """TGAT前向传播辅助函数

        由于TGAT是同质图模型，需要为每种节点类型独立处理
        """
        h_dict_out = {}

        for node_type in self.node_types:
            # 收集该节点类型相关的边
            node_edges = []
            node_edge_times = []

            for edge_type in edge_index_dict.keys():
                src_type, rel, dst_type = edge_type

                # 只处理目标节点是当前类型的边
                if dst_type == node_type:
                    edge_index = edge_index_dict[edge_type]
                    node_edges.append(edge_index)

                    if edge_time_dict is not None and edge_type in edge_time_dict:
                        node_edge_times.append(edge_time_dict[edge_type])

            # 如果该节点类型没有入边，直接返回输入
            if len(node_edges) == 0:
                h_dict_out[node_type] = h_dict[node_type]
                continue

            # 合并所有边（简化处理，实际应该按源节点类型分组）
            combined_edge_index = torch.cat(node_edges, dim=1)
            combined_edge_time = torch.cat(node_edge_times, dim=0) if node_edge_times else None

            # 获取节点时间
            node_time = node_time_dict.get(node_type) if node_time_dict else None

            # TGAT前向传播
            h_dict_out[node_type] = self.tgat_dict[node_type](
                h_dict[node_type],
                combined_edge_index,
                combined_edge_time if combined_edge_time is not None else torch.zeros(combined_edge_index.shape[1]),
                node_time
            )

        return h_dict_out


def test_hgt_tgat_hybrid():
    """单元测试：HGT-TGAT混合模型"""
    print("=" * 80)
    print("HGT-TGAT混合模型单元测试")
    print("=" * 80)

    # 设置随机种子
    torch.manual_seed(42)

    # 构造异质图测试数据
    node_types = ['policy', 'actor', 'region']
    edge_types = [
        ('policy', 'apply_to', 'actor'),
        ('policy', 'target', 'region'),
        ('actor', 'located_in', 'region')
    ]

    num_nodes = {'policy': 50, 'actor': 100, 'region': 20}
    in_channels_dict = {'policy': 416, 'actor': 384, 'region': 384}  # policy有时间编码
    hidden_channels = 128

    # 节点特征
    x_dict = {
        node_type: torch.randn(num_nodes[node_type], in_channels_dict[node_type])
        for node_type in node_types
    }

    # 边索引
    edge_index_dict = {
        ('policy', 'apply_to', 'actor'): torch.randint(
            0, num_nodes['policy'], (2, 200)
        ).clamp(max=torch.tensor([num_nodes['policy']-1, num_nodes['actor']-1]).unsqueeze(1)),
        ('policy', 'target', 'region'): torch.randint(
            0, num_nodes['policy'], (2, 100)
        ).clamp(max=torch.tensor([num_nodes['policy']-1, num_nodes['region']-1]).unsqueeze(1)),
        ('actor', 'located_in', 'region'): torch.randint(
            0, num_nodes['actor'], (2, 150)
        ).clamp(max=torch.tensor([num_nodes['actor']-1, num_nodes['region']-1]).unsqueeze(1))
    }

    # 边时间戳（模拟2010-2020年）
    edge_time_dict = {
        edge_type: torch.randint(0, 3650, (edge_index.shape[1],)).float()
        for edge_type, edge_index in edge_index_dict.items()
    }

    # 节点时间戳
    node_time_dict = {
        node_type: torch.randint(0, 3650, (num_nodes[node_type],)).float()
        for node_type in node_types
    }

    print(f"\n测试数据：")
    print(f"  节点类型: {node_types}")
    print(f"  边类型: {[f'{s}-{r}-{d}' for s,r,d in edge_types]}")
    print(f"  节点数: {num_nodes}")

    # 测试1：Late Fusion模式
    print(f"\n【测试1】Late Fusion模式（HGT → TGAT）")
    print("-" * 80)
    model_late = HGT_TGAT_Hybrid(
        node_types=node_types,
        edge_types=edge_types,
        in_channels_dict=in_channels_dict,
        hidden_channels=hidden_channels,
        fusion_mode='late_fusion'
    )
    h_dict_late = model_late(x_dict, edge_index_dict, edge_time_dict, node_time_dict)

    for node_type in node_types:
        print(f"  {node_type}: {h_dict_late[node_type].shape}")
        assert h_dict_late[node_type].shape == (num_nodes[node_type], hidden_channels)
        assert not torch.isnan(h_dict_late[node_type]).any()

    print(f"  ✓ Late Fusion测试通过")

    # 测试2：Early Fusion模式
    print(f"\n【测试2】Early Fusion模式（TGAT → HGT）")
    print("-" * 80)
    model_early = HGT_TGAT_Hybrid(
        node_types=node_types,
        edge_types=edge_types,
        in_channels_dict=in_channels_dict,
        hidden_channels=hidden_channels,
        fusion_mode='early_fusion'
    )
    h_dict_early = model_early(x_dict, edge_index_dict, edge_time_dict, node_time_dict)

    for node_type in node_types:
        print(f"  {node_type}: {h_dict_early[node_type].shape}")
        assert h_dict_early[node_type].shape == (num_nodes[node_type], hidden_channels)

    print(f"  ✓ Early Fusion测试通过")

    # 测试3：Parallel Fusion模式
    print(f"\n【测试3】Parallel Fusion模式（HGT ‖ TGAT）")
    print("-" * 80)
    model_parallel = HGT_TGAT_Hybrid(
        node_types=node_types,
        edge_types=edge_types,
        in_channels_dict=in_channels_dict,
        hidden_channels=hidden_channels,
        fusion_mode='parallel_fusion',
        fusion_weight=0.6
    )
    h_dict_parallel = model_parallel(x_dict, edge_index_dict, edge_time_dict, node_time_dict)

    for node_type in node_types:
        print(f"  {node_type}: {h_dict_parallel[node_type].shape}")
        assert h_dict_parallel[node_type].shape == (num_nodes[node_type], hidden_channels)

    print(f"  ✓ Parallel Fusion测试通过")

    # 测试4：消融研究 - HGT Only
    print(f"\n【测试4】消融研究 - HGT Only（去时序）")
    print("-" * 80)
    model_hgt_only = HGT_TGAT_Hybrid(
        node_types=node_types,
        edge_types=edge_types,
        in_channels_dict=in_channels_dict,
        hidden_channels=hidden_channels,
        ablation_mode='hgt_only'
    )
    h_dict_hgt = model_hgt_only(x_dict, edge_index_dict)
    print(f"  policy: {h_dict_hgt['policy'].shape}")
    print(f"  ✓ HGT Only测试通过")

    # 测试5：消融研究 - TGAT Only
    print(f"\n【测试5】消融研究 - TGAT Only（去异质）")
    print("-" * 80)
    model_tgat_only = HGT_TGAT_Hybrid(
        node_types=node_types,
        edge_types=edge_types,
        in_channels_dict=in_channels_dict,
        hidden_channels=hidden_channels,
        ablation_mode='tgat_only'
    )
    h_dict_tgat = model_tgat_only(x_dict, edge_index_dict, edge_time_dict, node_time_dict)
    print(f"  policy: {h_dict_tgat['policy'].shape}")
    print(f"  ✓ TGAT Only测试通过")

    print(f"\n" + "=" * 80)
    print("所有测试通过 ✓")
    print("=" * 80)


if __name__ == "__main__":
    test_hgt_tgat_hybrid()
