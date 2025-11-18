#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图学习工作流演示脚本

功能：
1. 加载异质图数据
2. 展示图统计信息
3. 可视化节点和边分布
4. 展示特征维度信息
5. 验证维度匹配

使用：python3 scripts/demo_graph_workflow.py

注意：如果torch未安装，将以只读模式运行（读取文件元数据）
"""

from pathlib import Path
from collections import defaultdict
import warnings
import json

warnings.filterwarnings('ignore')

# 尝试导入torch
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️  torch未安装，将以只读模式运行\n")


def main():
    """主演示函数"""
    print("=" * 70)
    print("图学习工作流演示")
    print("=" * 70)

    project_root = Path(__file__).parent.parent
    graph_path = project_root / 'data' / 'graph_base.pt'

    # 步骤1: 加载图数据
    print("\n【步骤1】 加载异质图数据")
    print("-" * 70)

    if not graph_path.exists():
        print(f"❌ 图数据不存在: {graph_path}")
        print("请先运行: python3 scripts/build_graph_pyg.py")
        return 1

    if TORCH_AVAILABLE:
        try:
            data = torch.load(graph_path)
            print(f"✓ 成功加载图数据: {graph_path}")
            print(f"  数据类型: {type(data).__name__}")

            # 完整分析
            show_graph_statistics(data)
            show_node_type_distribution(data)
            show_edge_type_distribution(data)
            verify_feature_dimensions(data)
            show_pyg_metadata(data)

        except Exception as e:
            print(f"❌ 加载图数据失败: {e}")
            return 1
    else:
        # torch不可用，使用只读模式
        show_graph_metadata_readonly(graph_path)

    # 总结
    print("\n" + "=" * 70)
    print("图学习工作流演示完成")
    print("=" * 70)

    if not TORCH_AVAILABLE:
        print("\n提示:")
        print("  torch未安装，无法加载完整图数据")
        print("  建议：安装torch后重新运行此脚本")

    print("\n下一步:")
    print("1. 解决torch-scatter/torch-sparse依赖问题")
    print("2. 运行HGT模型训练: python3 scripts/train_hgt.py")
    print("3. 评估链路预测性能")

    return 0


def show_graph_metadata_readonly(graph_path: Path):
    """只读模式：展示图元数据（不加载torch对象）"""

    print("\n【只读模式】 图元数据信息")
    print("-" * 70)

    # 读取图文件的统计信息
    file_size = graph_path.stat().st_size / 1024  # KB

    print(f"\n文件信息:")
    print(f"  路径: {graph_path}")
    print(f"  大小: {file_size:.2f} KB")

    # 从构建脚本的日志推断图结构
    print(f"\n预期图结构（基于CLAUDE.md规范）:")
    print(f"  节点类型: policy, actor, region, topic, funding")
    print(f"  边类型:")
    print(f"    (policy) --[apply_to]--> (actor)")
    print(f"    (policy) --[apply_to]--> (region)")
    print(f"    (policy) --[fund]--> (funding)")

    print(f"\n预期特征维度:")
    print(f"  policy节点: 416维 (384文本嵌入 + 32时间编码)")
    print(f"  其他节点: 384维 (仅文本嵌入)")

    print(f"\n⚠️  无法验证实际图结构（需要torch）")
    print(f"  建议：安装torch后使用完整模式运行")


def show_graph_statistics(data):
    """展示图的基本统计信息"""

    # 节点总数
    total_nodes = 0
    for node_type in data.node_types:
        num_nodes = data[node_type].num_nodes
        total_nodes += num_nodes

    # 边总数
    total_edges = 0
    for edge_type in data.edge_types:
        num_edges = data[edge_type].num_edges
        total_edges += num_edges

    print(f"\n【步骤2】 图统计信息")
    print("-" * 70)
    print(f"  节点类型数: {len(data.node_types)}")
    print(f"  边类型数: {len(data.edge_types)}")
    print(f"  总节点数: {total_nodes}")
    print(f"  总边数: {total_edges}")


def show_node_type_distribution(data):
    """展示节点类型分布"""

    print(f"\n【步骤3】 节点类型分布")
    print("-" * 70)

    for node_type in data.node_types:
        num_nodes = data[node_type].num_nodes
        has_features = hasattr(data[node_type], 'x') and data[node_type].x is not None

        if has_features:
            feat_dim = data[node_type].x.shape[1]
            feat_info = f"{feat_dim}维"
        else:
            feat_info = "无特征"

        print(f"  {node_type}: {num_nodes}个节点, 特征={feat_info}")


def show_edge_type_distribution(data):
    """展示边类型分布"""

    print(f"\n【步骤4】 边类型分布")
    print("-" * 70)

    for edge_type in data.edge_types:
        src_type, rel, dst_type = edge_type
        num_edges = data[edge_type].num_edges

        print(f"  ({src_type}) --[{rel}]--> ({dst_type}): {num_edges}条边")


def verify_feature_dimensions(data):
    """验证特征维度匹配"""

    print(f"\n【步骤5】 特征维度验证")
    print("-" * 70)

    issues = []

    for node_type in data.node_types:
        if not hasattr(data[node_type], 'x') or data[node_type].x is None:
            print(f"  ⚠️  {node_type}: 无特征向量")
            continue

        feat_dim = data[node_type].x.shape[1]

        # 检查policy节点应该是416维（384文本+32时间）
        if node_type == 'policy':
            expected_dim = 416
            if feat_dim == expected_dim:
                print(f"  ✓ {node_type}: {feat_dim}维 (384文本 + 32时间) ✓ 正确")
            else:
                print(f"  ❌ {node_type}: {feat_dim}维 (期望{expected_dim}维) ❌ 错误")
                issues.append(f"{node_type}节点维度不匹配")
        else:
            # 其他节点应该是384维（仅文本嵌入）
            expected_dim = 384
            if feat_dim == expected_dim:
                print(f"  ✓ {node_type}: {feat_dim}维 (文本嵌入) ✓ 正确")
            else:
                print(f"  ❌ {node_type}: {feat_dim}维 (期望{expected_dim}维) ❌ 错误")
                issues.append(f"{node_type}节点维度不匹配")

    if issues:
        print(f"\n❌ 维度验证失败")
        return False
    else:
        print(f"\n✅ 所有节点类型的特征维度正确")
        return True


def show_pyg_metadata(data):
    """展示PyG元数据"""

    print(f"\n【步骤6】 PyTorch Geometric元数据")
    print("-" * 70)

    if hasattr(data, 'metadata'):
        node_types, edge_types = data.metadata()

        print(f"\n节点类型列表: {node_types}")
        print(f"\n边类型列表:")
        for edge_type in edge_types:
            print(f"  {edge_type}")
    else:
        print(f"⚠️  无元数据")

    # 检查edge_index
    print(f"\n边索引 (edge_index):")
    for edge_type in data.edge_types:
        edge_index = data[edge_type].edge_index
        print(f"  {edge_type}: shape={edge_index.shape}")


if __name__ == '__main__':
    exit(main())
