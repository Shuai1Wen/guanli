#!/usr/bin/env python3
"""
PSC-Graph 异质图构建脚本

基于标注数据构建异质图（Heterogeneous Graph），符合CLAUDE.md强制规范：
- 节点类型: Policy, Actor, Region, Topic, Funding
- 边类型: publish→apply, fund→benefit, constraint→object, co-occurrence, temporal
- 特征: 文本嵌入（sentence-transformers 384维）+ 时间戳

输出: PyTorch Geometric HeteroData对象 (.pt文件)
"""

import json
import torch
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Set
from datetime import datetime
from collections import defaultdict

try:
    from torch_geometric.data import HeteroData
except ImportError:
    print("错误：PyTorch Geometric未安装")
    print("请运行: pip install torch-geometric")
    exit(1)


class GraphBuilder:
    """异质图构建器"""

    def __init__(self):
        """初始化图构建器"""
        # 节点字典：{node_type: {node_id: node_data}}
        self.nodes = {
            'policy': {},
            'actor': {},
            'region': {},
            'topic': {},
            'funding': {}
        }

        # 边列表：[(src_id, dst_id, edge_data)]
        self.edges = {
            ('policy', 'apply_to', 'actor'): [],
            ('policy', 'apply_to', 'region'): [],
            ('policy', 'fund', 'funding'): [],
            ('policy', 'mention', 'topic'): [],
            ('policy', 'temporal', 'policy'): [],  # 时间邻接
        }

        # 全局计数器
        self.node_counter = defaultdict(int)

    def _get_node_id(self, node_type: str, key: str) -> str:
        """获取或创建节点ID

        Args:
            node_type: 节点类型
            key: 节点唯一标识（如doc_id, region_name等）

        Returns:
            节点ID
        """
        if key in self.nodes[node_type]:
            return key

        # 创建新节点
        self.nodes[node_type][key] = {
            'id': key,
            'type': node_type,
            'created_at': datetime.now().isoformat()
        }
        self.node_counter[node_type] += 1
        return key

    def add_policy_node(
        self,
        doc_id: str,
        source_title: str = "",
        source_url: str = "",
        timestamp: str = None
    ):
        """添加政策节点

        Args:
            doc_id: 文档ID
            source_title: 文档标题
            source_url: 文档URL
            timestamp: 时间戳（ISO8601格式）
        """
        node_id = self._get_node_id('policy', doc_id)
        self.nodes['policy'][node_id].update({
            'title': source_title,
            'url': source_url,
            'timestamp': timestamp or ""
        })

    def add_actor_node(self, actor_name: str):
        """添加行为主体节点

        Args:
            actor_name: 主体名称（企业/高校/科研院所）
        """
        # 简化名称作为ID
        actor_id = actor_name.strip()
        node_id = self._get_node_id('actor', actor_id)
        self.nodes['actor'][node_id]['name'] = actor_name

    def add_region_node(self, region_name: str):
        """添加地区节点

        Args:
            region_name: 地区名称
        """
        region_id = region_name.strip()
        node_id = self._get_node_id('region', region_id)
        self.nodes['region'][node_id]['name'] = region_name

    def add_topic_node(self, topic_name: str):
        """添加主题节点

        Args:
            topic_name: 技术主题/IPC分类
        """
        topic_id = topic_name.strip()
        node_id = self._get_node_id('topic', topic_id)
        self.nodes['topic'][node_id]['name'] = topic_name

    def add_funding_node(self, funding_name: str):
        """添加资金/平台节点

        Args:
            funding_name: 资金或平台名称
        """
        funding_id = funding_name.strip()
        node_id = self._get_node_id('funding', funding_id)
        self.nodes['funding'][node_id]['name'] = funding_name

    def add_edge(
        self,
        edge_type: Tuple[str, str, str],
        src_id: str,
        dst_id: str,
        **attrs
    ):
        """添加边

        Args:
            edge_type: (src_type, rel, dst_type)三元组
            src_id: 源节点ID
            dst_id: 目标节点ID
            **attrs: 边属性
        """
        if edge_type not in self.edges:
            print(f"警告：未知边类型 {edge_type}")
            return

        self.edges[edge_type].append((src_id, dst_id, attrs))

    def load_from_annotations(self, annotations_dir: str = "annotations/annotator_A"):
        """从标注数据加载图结构

        Args:
            annotations_dir: 标注文件目录
        """
        annotations_path = Path(annotations_dir)

        if not annotations_path.exists():
            print(f"错误：标注目录不存在: {annotations_dir}")
            return

        json_files = list(annotations_path.glob("*.json"))
        print(f"正在加载标注文件: {len(json_files)}个")

        for json_file in json_files:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            doc_id = data.get('doc_id', '')
            source_title = data.get('source_title', '')
            source_url = data.get('source_url', '')
            annotations = data.get('annotations', [])

            # 提取时间戳（从第一个annotation）
            timestamp = None
            if annotations:
                timeframe = annotations[0].get('timeframe', {})
                timestamp = timeframe.get('effective_date', '')

            # 添加政策节点
            self.add_policy_node(doc_id, source_title, source_url, timestamp)

            # 从标注中提取边
            for ann in annotations:
                # 提取目标主体 → actor节点和边
                target_actor = ann.get('target_actor', '')
                if target_actor:
                    # 可能包含多个主体，用逗号或顿号分隔
                    actors = [a.strip() for a in target_actor.replace('、', ',').split(',') if a.strip()]
                    for actor in actors:
                        self.add_actor_node(actor)
                        self.add_edge(
                            ('policy', 'apply_to', 'actor'),
                            doc_id,
                            actor,
                            strength=ann.get('strength', 0),
                            confidence=ann.get('confidence', 0.0)
                        )

                # 提取地区 → region节点和边
                region_info = ann.get('region', {})
                if region_info and isinstance(region_info, dict):
                    region_name = region_info.get('name', '')
                    if region_name:
                        self.add_region_node(region_name)
                        self.add_edge(
                            ('policy', 'apply_to', 'region'),
                            doc_id,
                            region_name,
                            admin_code=region_info.get('admin_code', ''),
                            uncertain=region_info.get('uncertain', False)
                        )

                # 提取资金/平台 → funding节点和边
                support = ann.get('support', [])
                if support and isinstance(support, list):
                    for s in support:
                        if isinstance(s, dict):
                            support_type = s.get('type', 'other')
                            note = s.get('note', '')
                            if note:
                                self.add_funding_node(note)
                                self.add_edge(
                                    ('policy', 'fund', 'funding'),
                                    doc_id,
                                    note,
                                    type=support_type,
                                    value=s.get('value'),
                                    unit=s.get('unit', '')
                                )

        print(f"✓ 节点统计:")
        for node_type, count in self.node_counter.items():
            print(f"  - {node_type}: {count}个")

        print(f"✓ 边统计:")
        for edge_type, edges in self.edges.items():
            if edges:
                print(f"  - {edge_type}: {len(edges)}条")

    def build_hetero_data(self) -> HeteroData:
        """构建PyTorch Geometric HeteroData对象

        Returns:
            HeteroData对象
        """
        data = HeteroData()

        # 创建节点ID映射：{original_id: index}
        node_id_maps = {}
        for node_type in self.nodes:
            node_ids = list(self.nodes[node_type].keys())
            node_id_maps[node_type] = {nid: i for i, nid in enumerate(node_ids)}

            # 初始化节点特征（占位符：随机特征）
            num_nodes = len(node_ids)
            if num_nodes > 0:
                # 使用随机384维特征（后续可替换为sentence-transformers嵌入）
                data[node_type].x = torch.randn(num_nodes, 384)
                data[node_type].node_id = node_ids  # 保存原始ID

        # 构建边索引
        for edge_type, edges in self.edges.items():
            if not edges:
                continue

            src_type, rel, dst_type = edge_type
            src_indices = []
            dst_indices = []

            for src_id, dst_id, attrs in edges:
                # 检查节点是否存在
                if src_id not in node_id_maps[src_type]:
                    print(f"警告：源节点不存在 {src_type}:{src_id}")
                    continue
                if dst_id not in node_id_maps[dst_type]:
                    print(f"警告：目标节点不存在 {dst_type}:{dst_id}")
                    continue

                src_idx = node_id_maps[src_type][src_id]
                dst_idx = node_id_maps[dst_type][dst_id]

                src_indices.append(src_idx)
                dst_indices.append(dst_idx)

            if src_indices:
                edge_index = torch.tensor([src_indices, dst_indices], dtype=torch.long)
                data[src_type, rel, dst_type].edge_index = edge_index

        return data

    def save_graph(self, output_path: str = "data/graph_base.pt"):
        """保存图到文件

        Args:
            output_path: 输出文件路径
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        data = self.build_hetero_data()
        torch.save(data, output_file)

        print(f"✓ 图已保存到: {output_file}")
        return data


def main():
    """主函数：演示图构建流程"""
    print("PSC-Graph 异质图构建")
    print("=" * 80)

    # 初始化构建器
    builder = GraphBuilder()

    # 从标注数据加载
    print("\n【步骤1】从标注数据加载节点和边")
    print("-" * 80)
    builder.load_from_annotations("annotations/annotator_A")

    # 构建HeteroData
    print("\n【步骤2】构建PyG HeteroData对象")
    print("-" * 80)
    data = builder.build_hetero_data()

    # 打印图统计信息
    print("\n【步骤3】图统计信息")
    print("-" * 80)
    print(f"节点类型数: {len(data.node_types)}")
    print(f"边类型数: {len(data.edge_types)}")
    print()
    print("节点详情:")
    for node_type in data.node_types:
        num_nodes = data[node_type].x.shape[0] if hasattr(data[node_type], 'x') else 0
        feat_dim = data[node_type].x.shape[1] if hasattr(data[node_type], 'x') and num_nodes > 0 else 0
        print(f"  - {node_type}: {num_nodes}个节点, 特征维度={feat_dim}")

    print()
    print("边详情:")
    for edge_type in data.edge_types:
        num_edges = data[edge_type].edge_index.shape[1] if hasattr(data[edge_type], 'edge_index') else 0
        print(f"  - {edge_type}: {num_edges}条边")

    # 保存图
    print("\n【步骤4】保存图到文件")
    print("-" * 80)
    builder.save_graph("data/graph_base.pt")

    # 验证加载
    print("\n【步骤5】验证图加载")
    print("-" * 80)
    # PyTorch 2.6+需要weights_only=False来加载自定义类
    loaded_data = torch.load("data/graph_base.pt", weights_only=False)
    print(f"✓ 图加载成功")
    print(f"  元数据: {loaded_data.metadata()}")

    print("\n" + "=" * 80)
    print("图构建完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
