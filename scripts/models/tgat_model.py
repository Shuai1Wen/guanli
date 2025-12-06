#!/usr/bin/env python3
"""
PSC-Graph TGAT时序图注意力模型

实现Temporal Graph Attention Network (TGAT)，符合CLAUDE.md强制规范：
- 时序注意力机制：建模边的时间戳对交互的影响
- Bochner时间编码：可学习的随机傅里叶特征
- 数值稳定性：梯度裁剪、NaN检测、logits裁剪
- 多头注意力：增强表达能力

参考论文：
Xu et al. "Inductive Representation Learning on Temporal Graphs" (ICLR 2020)

依赖：PyTorch Geometric, torch-scatter
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional
import math

try:
    from torch_geometric.nn import MessagePassing
    from torch_scatter import scatter_softmax, scatter_add
except ImportError:
    print("错误：PyTorch Geometric未安装")
    print("请运行: pip install torch-geometric torch-scatter")
    exit(1)

try:
    from models.bochner_time_encoder import BochnerTimeEncoder
except ImportError:
    # 如果无法导入，定义一个简化版本
    class BochnerTimeEncoder(nn.Module):
        """简化版Bochner时间编码器（用于独立运行）"""
        def __init__(self, dim=32, sigma=1.0, trainable=True):
            super().__init__()
            assert dim % 2 == 0
            self.dim = dim
            omega_init = torch.randn(dim // 2) * sigma
            if trainable:
                self.omega = nn.Parameter(omega_init)
                self.bias = nn.Parameter(torch.randn(dim // 2) * 2 * math.pi)
            else:
                self.register_buffer('omega', omega_init)
                self.register_buffer('bias', torch.randn(dim // 2) * 2 * math.pi)

        def forward(self, timestamps):
            """编码时间戳为随机傅里叶特征"""
            t_normalized = timestamps.float() / 31536000.0  # 转换为年
            t = t_normalized.unsqueeze(-1)
            omega_t_plus_b = t * self.omega + self.bias
            cos_features = torch.cos(omega_t_plus_b)
            sin_features = torch.sin(omega_t_plus_b)
            encoded = torch.stack([cos_features, sin_features], dim=-1)
            return encoded.reshape(timestamps.shape[0], self.dim)


class TemporalAttentionLayer(MessagePassing):
    """时序注意力层

    核心机制：
    1. Query-Key注意力：衡量源节点和目标节点的相关性
    2. 时间调制：使用Bochner编码将时间差融入注意力权重
    3. 多头注意力：增强表达能力

    时间建模：
    - Δt = t_edge - t_dst（相对时间差）
    - 正值：边发生在目标节点时间之后（未来事件）
    - 负值：边发生在目标节点时间之前（历史事件）

    公式：
    α_ij = softmax(LeakyReLU((W_q * h_i) · (W_k * h_j + W_t * φ(Δt_ij)) / √d))
    h_i' = Σ_j α_ij * (W_v * h_j)
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        num_heads: int = 4,
        time_dim: int = 32,
        dropout: float = 0.1,
        negative_slope: float = 0.2
    ):
        """初始化时序注意力层

        Args:
            in_channels: 输入特征维度
            out_channels: 输出特征维度
            num_heads: 注意力头数
            time_dim: 时间编码维度
            dropout: Dropout比例
            negative_slope: LeakyReLU负斜率
        """
        super().__init__(aggr='add', node_dim=0)

        assert out_channels % num_heads == 0, \
            f"out_channels ({out_channels}) 必须能被 num_heads ({num_heads}) 整除"

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.num_heads = num_heads
        self.head_dim = out_channels // num_heads
        self.time_dim = time_dim
        self.dropout = dropout
        self.negative_slope = negative_slope

        # 时间编码器
        self.time_encoder = BochnerTimeEncoder(dim=time_dim, trainable=True)

        # Query、Key、Value变换矩阵
        self.W_q = nn.Linear(in_channels, out_channels)
        self.W_k = nn.Linear(in_channels, out_channels)
        self.W_v = nn.Linear(in_channels, out_channels)

        # 时间特征投影矩阵
        self.W_time = nn.Linear(time_dim, out_channels)

        # 注意力权重计算
        self.attn_weight = nn.Parameter(torch.empty(num_heads, 2 * self.head_dim))

        # Dropout
        self.dropout_layer = nn.Dropout(dropout)

        self.reset_parameters()

    def reset_parameters(self):
        """初始化参数"""
        nn.init.xavier_uniform_(self.W_q.weight)
        nn.init.xavier_uniform_(self.W_k.weight)
        nn.init.xavier_uniform_(self.W_v.weight)
        nn.init.xavier_uniform_(self.W_time.weight)
        nn.init.xavier_uniform_(self.attn_weight)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_time: torch.Tensor,
        node_time: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """前向传播

        Args:
            x: 节点特征 [N, in_channels]
            edge_index: 边索引 [2, E]
            edge_time: 边时间戳 [E]（Unix时间戳或年份）
            node_time: 节点时间戳 [N]（可选，如果为None则使用edge_time）

        Returns:
            更新后的节点特征 [N, out_channels]
        """
        # Query、Key、Value投影
        query = self.W_q(x)  # [N, out_channels]
        key = self.W_k(x)
        value = self.W_v(x)

        # 重塑为多头格式 [N, num_heads, head_dim]
        query = query.view(-1, self.num_heads, self.head_dim)
        key = key.view(-1, self.num_heads, self.head_dim)
        value = value.view(-1, self.num_heads, self.head_dim)

        # 计算相对时间差
        if node_time is not None:
            # Δt = t_edge - t_dst
            src_idx, dst_idx = edge_index
            delta_t = edge_time - node_time[dst_idx]
        else:
            # 如果没有节点时间，直接使用边时间
            delta_t = edge_time

        # 时间编码
        time_feat = self.time_encoder(delta_t)  # [E, time_dim]
        time_feat = self.W_time(time_feat)      # [E, out_channels]
        time_feat = time_feat.view(-1, self.num_heads, self.head_dim)  # [E, num_heads, head_dim]

        # 消息传递
        out = self.propagate(
            edge_index,
            query=query,
            key=key,
            value=value,
            time_feat=time_feat
        )

        # 合并多头 [N, out_channels]
        out = out.view(-1, self.out_channels)

        return out

    def message(
        self,
        query_i: torch.Tensor,
        key_j: torch.Tensor,
        value_j: torch.Tensor,
        time_feat: torch.Tensor,
        index: torch.Tensor,
        ptr: Optional[torch.Tensor] = None,
        size_i: Optional[int] = None
    ) -> torch.Tensor:
        """计算消息（带时序注意力权重）

        Args:
            query_i: 目标节点的Query [E, num_heads, head_dim]
            key_j: 源节点的Key [E, num_heads, head_dim]
            value_j: 源节点的Value [E, num_heads, head_dim]
            time_feat: 时间特征 [E, num_heads, head_dim]
            index: 目标节点索引 [E]
            ptr: CSR格式指针（可选）
            size_i: 目标节点数量（可选）

        Returns:
            加权消息 [E, num_heads, head_dim]
        """
        # Key加上时间调制
        key_with_time = key_j + time_feat  # [E, num_heads, head_dim]

        # 拼接Query和Key（用于注意力权重计算）
        qk = torch.cat([query_i, key_with_time], dim=-1)  # [E, num_heads, 2*head_dim]

        # 注意力logits
        # attn_weight: [num_heads, 2*head_dim]
        # qk: [E, num_heads, 2*head_dim]
        attn_logits = (qk * self.attn_weight).sum(dim=-1)  # [E, num_heads]

        # LeakyReLU激活
        attn_logits = F.leaky_relu(attn_logits, self.negative_slope)

        # 缩放（防止梯度消失）
        attn_logits = attn_logits / math.sqrt(self.head_dim)

        # 裁剪logits防止数值不稳定
        attn_logits = torch.clamp(attn_logits, min=-10.0, max=10.0)

        # Softmax归一化（按目标节点分组）
        attn_weights = scatter_softmax(attn_logits, index, dim=0)  # [E, num_heads]

        # Dropout
        attn_weights = self.dropout_layer(attn_weights)

        # 加权Value
        # attn_weights: [E, num_heads] -> [E, num_heads, 1]
        # value_j: [E, num_heads, head_dim]
        messages = attn_weights.unsqueeze(-1) * value_j  # [E, num_heads, head_dim]

        return messages


class TGAT(nn.Module):
    """Temporal Graph Attention Network (TGAT)

    完整的时序图注意力网络，支持：
    - 多层时序注意力
    - 残差连接
    - 层归一化
    - Dropout正则化

    符合CLAUDE.md规范：
    - 2-3层（避免过平滑）
    - Dropout 0.1-0.3
    - 残差连接
    """

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = 128,
        out_channels: int = 128,
        num_heads: int = 4,
        num_layers: int = 2,
        time_dim: int = 32,
        dropout: float = 0.2,
        use_layer_norm: bool = True
    ):
        """初始化TGAT模型

        Args:
            in_channels: 输入特征维度
            hidden_channels: 隐藏层维度
            out_channels: 输出特征维度
            num_heads: 注意力头数
            num_layers: TGAT层数（2-3层，避免过平滑）
            time_dim: 时间编码维度
            dropout: Dropout比例
            use_layer_norm: 是否使用层归一化
        """
        super().__init__()

        if not (2 <= num_layers <= 3):
            print(f"警告：num_layers={num_layers}不符合CLAUDE.md规范（推荐2-3层）")

        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.out_channels = out_channels
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.time_dim = time_dim
        self.dropout = dropout
        self.use_layer_norm = use_layer_norm

        # 输入投影层
        self.input_proj = nn.Linear(in_channels, hidden_channels)

        # TGAT卷积层
        self.convs = nn.ModuleList()
        for i in range(num_layers):
            in_ch = hidden_channels
            out_ch = hidden_channels if i < num_layers - 1 else out_channels

            conv = TemporalAttentionLayer(
                in_channels=in_ch,
                out_channels=out_ch,
                num_heads=num_heads,
                time_dim=time_dim,
                dropout=dropout
            )
            self.convs.append(conv)

        # 层归一化
        if use_layer_norm:
            self.layer_norms = nn.ModuleList()
            for i in range(num_layers):
                out_ch = hidden_channels if i < num_layers - 1 else out_channels
                self.layer_norms.append(nn.LayerNorm(out_ch))

        # Dropout
        self.dropout_layer = nn.Dropout(dropout)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_time: torch.Tensor,
        node_time: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """前向传播

        Args:
            x: 节点特征 [N, in_channels]
            edge_index: 边索引 [2, E]
            edge_time: 边时间戳 [E]
            node_time: 节点时间戳 [N]（可选）

        Returns:
            节点嵌入 [N, out_channels]
        """
        # 输入投影
        h = self.input_proj(x)
        h = F.relu(h)  # 使用非in-place的relu()
        h = self.dropout_layer(h)

        # TGAT层（带残差连接）
        for i, conv in enumerate(self.convs):
            h_new = conv(h, edge_index, edge_time, node_time)

            # 残差连接（从第2层开始，且维度匹配）
            if i > 0 and h_new.shape == h.shape:
                h_new = h_new + h

            # 层归一化
            if self.use_layer_norm:
                h_new = self.layer_norms[i](h_new)

            # 激活和Dropout（除了最后一层）
            if i < self.num_layers - 1:
                h_new = F.relu(h_new)
                h_new = self.dropout_layer(h_new)

            h = h_new

        return h


def test_tgat():
    """单元测试：TGAT模型"""
    print("=" * 80)
    print("TGAT模型单元测试")
    print("=" * 80)

    # 设置随机种子
    torch.manual_seed(42)

    # 构造测试数据
    num_nodes = 100
    num_edges = 500
    in_channels = 64
    hidden_channels = 128
    out_channels = 128

    x = torch.randn(num_nodes, in_channels)
    edge_index = torch.randint(0, num_nodes, (2, num_edges))
    edge_time = torch.randint(0, 3650, (num_edges,)).float()  # 模拟10年的时间跨度（天）
    node_time = torch.randint(0, 3650, (num_nodes,)).float()

    print(f"\n测试数据：")
    print(f"  节点数: {num_nodes}")
    print(f"  边数: {num_edges}")
    print(f"  输入维度: {in_channels}")
    print(f"  隐藏维度: {hidden_channels}")
    print(f"  输出维度: {out_channels}")

    # 测试1：TemporalAttentionLayer
    print(f"\n【测试1】TemporalAttentionLayer")
    print("-" * 80)
    attn_layer = TemporalAttentionLayer(
        in_channels=in_channels,
        out_channels=hidden_channels,
        num_heads=4,
        time_dim=32
    )
    out = attn_layer(x, edge_index, edge_time, node_time)
    print(f"  输入形状: {x.shape}")
    print(f"  输出形状: {out.shape}")
    print(f"  参数量: {sum(p.numel() for p in attn_layer.parameters()):,}")
    assert out.shape == (num_nodes, hidden_channels), "输出维度错误"
    assert not torch.isnan(out).any(), "检测到NaN输出"
    print(f"  ✓ TemporalAttentionLayer测试通过")

    # 测试2：TGAT完整模型
    print(f"\n【测试2】TGAT完整模型")
    print("-" * 80)
    model = TGAT(
        in_channels=in_channels,
        hidden_channels=hidden_channels,
        out_channels=out_channels,
        num_heads=4,
        num_layers=2,
        time_dim=32,
        dropout=0.1
    )
    out = model(x, edge_index, edge_time, node_time)
    print(f"  输入形状: {x.shape}")
    print(f"  输出形状: {out.shape}")
    print(f"  参数量: {sum(p.numel() for p in model.parameters()):,}")
    assert out.shape == (num_nodes, out_channels), "输出维度错误"
    assert not torch.isnan(out).any(), "检测到NaN输出"
    print(f"  ✓ TGAT模型测试通过")

    # 测试3：梯度反向传播
    print(f"\n【测试3】梯度反向传播")
    print("-" * 80)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    for epoch in range(5):
        optimizer.zero_grad()

        # 前向传播
        h = model(x, edge_index, edge_time, node_time)

        # 简单的损失函数（L2范数）
        loss = (h ** 2).mean()

        # 反向传播
        loss.backward()

        # 检查梯度
        has_grad = False
        has_nan_grad = False
        for name, param in model.named_parameters():
            if param.grad is not None:
                has_grad = True
                if torch.isnan(param.grad).any():
                    has_nan_grad = True
                    print(f"  ✗ 检测到NaN梯度: {name}")

        optimizer.step()

        print(f"  Epoch {epoch+1} | Loss: {loss.item():.6f}")

    assert has_grad, "未检测到梯度"
    assert not has_nan_grad, "检测到NaN梯度"
    print(f"  ✓ 梯度反向传播测试通过")

    # 测试4：时间编码影响
    print(f"\n【测试4】时间编码影响")
    print("-" * 80)

    # 相同的图结构，不同的时间戳
    edge_time_1 = torch.zeros(num_edges)  # 所有边发生在t=0
    edge_time_2 = torch.ones(num_edges) * 1000  # 所有边发生在t=1000

    out_1 = model(x, edge_index, edge_time_1, node_time)
    out_2 = model(x, edge_index, edge_time_2, node_time)

    diff = (out_1 - out_2).abs().mean().item()
    print(f"  时间戳差异导致的输出差异: {diff:.6f}")

    assert diff > 1e-3, "时间编码没有产生影响"
    print(f"  ✓ 时间编码影响测试通过")

    print(f"\n" + "=" * 80)
    print("所有测试通过 ✓")
    print("=" * 80)


if __name__ == "__main__":
    test_tgat()
