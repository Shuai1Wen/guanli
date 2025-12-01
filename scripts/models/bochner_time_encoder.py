#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bochner时间编码器
----------------
基于随机傅里叶特征（RFF）的可学习时间编码

理论基础：
Bochner定理表明，任何平移不变的核函数k(t1, t2) = k(t1 - t2)都可以表示为：
k(Δt) = ∫ e^(iωΔt) p(ω) dω

使用随机傅里叶特征近似：
φ(t) = [cos(ω₁t+b₁), sin(ω₁t+b₁), ..., cos(ωₖt+bₖ), sin(ωₖt+bₖ)]

其中ω是可学习的频率参数，从高斯分布初始化。

用法示例：
    encoder = BochnerTimeEncoder(dim=32)
    timestamps = torch.tensor([1609459200, 1612137600, ...])  # Unix时间戳
    encoded = encoder(timestamps)  # [num_timestamps, 32]
"""

import torch
import torch.nn as nn
import math


class BochnerTimeEncoder(nn.Module):
    """
    Bochner时间编码器

    基于随机傅里叶特征（Random Fourier Features）的可学习时间编码。
    相比固定频率的正弦-余弦编码，Bochner编码的频率是可学习的，
    能够更好地捕捉数据的时间模式。

    参数：
        dim (int): 编码维度（必须是偶数），默认32
        sigma (float): 频率分布的标准差，默认1.0
        trainable (bool): 频率是否可训练，默认True

    属性：
        omega: [dim//2] 可学习的频率参数
        bias: [dim//2] 可学习的相位偏移

    输入：
        timestamps: [batch_size] 或 [batch_size, 1] Unix时间戳（秒）

    输出：
        encoded: [batch_size, dim] 时间编码向量
    """

    def __init__(self, dim=32, sigma=1.0, trainable=True):
        super().__init__()

        assert dim % 2 == 0, f"编码维度必须是偶数，当前为 {dim}"

        self.dim = dim
        self.sigma = sigma
        self.trainable = trainable

        # 初始化频率：从N(0, σ²)采样
        omega_init = torch.randn(dim // 2) * sigma

        if trainable:
            self.omega = nn.Parameter(omega_init)
            self.bias = nn.Parameter(torch.randn(dim // 2) * 2 * math.pi)
        else:
            self.register_buffer('omega', omega_init)
            self.register_buffer('bias', torch.randn(dim // 2) * 2 * math.pi)

    def forward(self, timestamps):
        """
        前向传播

        参数：
            timestamps: [batch_size] 或 [batch_size, 1] 时间戳（Unix秒）

        返回：
            encoded: [batch_size, dim] 编码向量
        """
        # 确保timestamps是1D张量
        if timestamps.dim() == 2:
            timestamps = timestamps.squeeze(-1)

        # 归一化时间戳（转换为年份单位，便于学习）
        # Unix时间戳0对应1970年，每年约31,536,000秒
        t_normalized = timestamps.float() / 31536000.0  # 转换为年份单位

        # 扩展维度：[batch_size] -> [batch_size, 1]
        t = t_normalized.unsqueeze(-1)

        # 计算ω*t + b：[batch_size, dim//2]
        omega_t_plus_b = t * self.omega + self.bias

        # 计算cos和sin：[batch_size, dim//2] -> [batch_size, dim]
        cos_features = torch.cos(omega_t_plus_b)
        sin_features = torch.sin(omega_t_plus_b)

        # 交错拼接：[cos(ω₁t+b₁), sin(ω₁t+b₁), cos(ω₂t+b₂), sin(ω₂t+b₂), ...]
        encoded = torch.stack([cos_features, sin_features], dim=-1)  # [batch_size, dim//2, 2]
        encoded = encoded.reshape(timestamps.shape[0], self.dim)      # [batch_size, dim]

        return encoded

    def extra_repr(self):
        """打印额外的模块信息"""
        return f'dim={self.dim}, sigma={self.sigma}, trainable={self.trainable}'


class BochnerTimeEncoderV2(nn.Module):
    """
    Bochner时间编码器（增强版）

    增加了以下特性：
    1. 支持多尺度频率（低频捕捉年度周期，高频捕捉月度周期）
    2. 支持非线性变换（可选MLP投影）
    3. 支持Dropout正则化

    参数：
        dim (int): 编码维度（必须是偶数）
        num_scales (int): 频率尺度数量，默认1
        sigma_base (float): 基础标准差，默认1.0
        sigma_scale (float): 尺度缩放因子，默认2.0
        use_mlp (bool): 是否使用MLP投影，默认False
        dropout (float): Dropout概率，默认0.0
    """

    def __init__(self, dim=32, num_scales=1, sigma_base=1.0, sigma_scale=2.0,
                 use_mlp=False, dropout=0.0):
        super().__init__()

        assert dim % (2 * num_scales) == 0, \
            f"dim必须能被2*num_scales整除：dim={dim}, num_scales={num_scales}"

        self.dim = dim
        self.num_scales = num_scales
        self.use_mlp = use_mlp

        # 每个尺度的频率数量
        freqs_per_scale = dim // (2 * num_scales)

        # 初始化多尺度频率
        self.omega_list = nn.ParameterList()
        self.bias_list = nn.ParameterList()

        for i in range(num_scales):
            # 每个尺度使用不同的σ：σᵢ = σ_base * σ_scale^i
            sigma = sigma_base * (sigma_scale ** i)
            omega_init = torch.randn(freqs_per_scale) * sigma
            bias_init = torch.randn(freqs_per_scale) * 2 * math.pi

            self.omega_list.append(nn.Parameter(omega_init))
            self.bias_list.append(nn.Parameter(bias_init))

        # 可选：MLP投影层
        if use_mlp:
            self.mlp = nn.Sequential(
                nn.Linear(dim, dim * 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(dim * 2, dim)
            )

        self.dropout = nn.Dropout(dropout) if dropout > 0 else None

    def forward(self, timestamps):
        """
        前向传播（多尺度版本）

        参数：
            timestamps: [batch_size] 时间戳

        返回：
            encoded: [batch_size, dim] 编码向量
        """
        if timestamps.dim() == 2:
            timestamps = timestamps.squeeze(-1)

        # 归一化
        t_normalized = timestamps.float() / 31536000.0
        t = t_normalized.unsqueeze(-1)

        # 计算所有尺度的编码
        encoded_list = []

        for omega, bias in zip(self.omega_list, self.bias_list):
            omega_t_plus_b = t * omega + bias
            cos_features = torch.cos(omega_t_plus_b)
            sin_features = torch.sin(omega_t_plus_b)

            # 交错拼接
            scale_encoded = torch.stack([cos_features, sin_features], dim=-1)
            scale_encoded = scale_encoded.reshape(timestamps.shape[0], -1)
            encoded_list.append(scale_encoded)

        # 拼接所有尺度
        encoded = torch.cat(encoded_list, dim=-1)  # [batch_size, dim]

        # 可选：通过MLP投影
        if self.use_mlp:
            encoded = self.mlp(encoded)

        # 可选：Dropout
        if self.dropout is not None:
            encoded = self.dropout(encoded)

        return encoded

    def extra_repr(self):
        return (f'dim={self.dim}, num_scales={self.num_scales}, '
                f'use_mlp={self.use_mlp}')


# ==================== 辅助函数 ====================

def test_bochner_encoder():
    """
    测试Bochner时间编码器

    测试内容：
    1. 基本功能测试
    2. 维度检查
    3. 梯度反向传播测试
    4. 数值稳定性测试
    """
    print("=" * 80)
    print("测试Bochner时间编码器")
    print("=" * 80)

    # 测试1：基本功能
    print("\n[测试1] 基本功能测试")
    encoder = BochnerTimeEncoder(dim=32)
    timestamps = torch.tensor([
        1609459200,  # 2021-01-01 00:00:00 UTC
        1612137600,  # 2021-02-01 00:00:00 UTC
        1614556800,  # 2021-03-01 00:00:00 UTC
    ])
    encoded = encoder(timestamps)

    print(f"  输入时间戳shape: {timestamps.shape}")
    print(f"  输出编码shape: {encoded.shape}")
    print(f"  编码范围: [{encoded.min().item():.4f}, {encoded.max().item():.4f}]")
    assert encoded.shape == (3, 32), "输出维度错误"
    print("  ✅ 基本功能测试通过")

    # 测试2：梯度反向传播
    print("\n[测试2] 梯度反向传播测试")
    loss = encoded.sum()
    loss.backward()

    omega_grad_norm = encoder.omega.grad.norm().item()
    bias_grad_norm = encoder.bias.grad.norm().item()
    print(f"  omega梯度范数: {omega_grad_norm:.6f}")
    print(f"  bias梯度范数: {bias_grad_norm:.6f}")
    assert omega_grad_norm > 0, "omega梯度为零"
    assert bias_grad_norm > 0, "bias梯度为零"
    print("  ✅ 梯度反向传播测试通过")

    # 测试3：数值稳定性（大时间戳）
    print("\n[测试3] 数值稳定性测试")
    large_timestamps = torch.tensor([
        1609459200,      # 2021年
        1893456000,      # 2030年
        2177452800,      # 2039年
    ])
    encoded_large = encoder(large_timestamps)

    has_nan = torch.isnan(encoded_large).any()
    has_inf = torch.isinf(encoded_large).any()
    print(f"  是否存在NaN: {has_nan.item()}")
    print(f"  是否存在Inf: {has_inf.item()}")
    assert not has_nan, "编码包含NaN"
    assert not has_inf, "编码包含Inf"
    print("  ✅ 数值稳定性测试通过")

    # 测试4：增强版编码器（多尺度）
    print("\n[测试4] 增强版编码器测试（多尺度）")
    encoder_v2 = BochnerTimeEncoderV2(dim=32, num_scales=2, use_mlp=True, dropout=0.1)
    encoded_v2 = encoder_v2(timestamps)

    print(f"  增强版编码shape: {encoded_v2.shape}")
    print(f"  编码范围: [{encoded_v2.min().item():.4f}, {encoded_v2.max().item():.4f}]")
    assert encoded_v2.shape == (3, 32), "增强版输出维度错误"
    print("  ✅ 增强版编码器测试通过")

    print("\n" + "=" * 80)
    print("所有测试通过！✅")
    print("=" * 80)


if __name__ == '__main__':
    test_bochner_encoder()
