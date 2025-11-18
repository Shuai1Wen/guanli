#!/usr/bin/env python3
"""
PSC-Graph 检索系统评估

实现检索指标计算：
- Recall@K: Top-K召回率
- MRR (Mean Reciprocal Rank): 平均倒数排名
- NDCG@K (Normalized Discounted Cumulative Gain): 归一化折损累积增益

基于标注数据生成评估数据集：
- 从annotations/中提取goal作为查询
- doc_id作为相关文档ground truth
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Set
import sys

try:
    from retrieve_evidence import HybridRetriever
except ImportError:
    print("错误：无法导入HybridRetriever")
    print("请确保retrieve_evidence.py在同一目录下")
    sys.exit(1)


class RetrievalEvaluator:
    """检索系统评估器"""

    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever

    @staticmethod
    def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
        """计算Recall@K

        Args:
            retrieved: 检索结果列表（doc_id）
            relevant: 相关文档集合（doc_id）
            k: Top-K阈值

        Returns:
            召回率（0-1之间）
        """
        if not relevant:
            return 0.0

        top_k = set(retrieved[:k])
        hits = len(top_k & relevant)
        return hits / len(relevant)

    @staticmethod
    def mean_reciprocal_rank(retrieved: List[str], relevant: Set[str]) -> float:
        """计算MRR (Mean Reciprocal Rank)

        Args:
            retrieved: 检索结果列表（doc_id）
            relevant: 相关文档集合（doc_id）

        Returns:
            倒数排名（0-1之间）
        """
        for i, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant:
                return 1.0 / i
        return 0.0

    @staticmethod
    def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
        """计算NDCG@K (Normalized Discounted Cumulative Gain)

        Args:
            retrieved: 检索结果列表（doc_id）
            relevant: 相关文档集合（doc_id）
            k: Top-K阈值

        Returns:
            NDCG值（0-1之间）
        """
        # DCG: sum(rel_i / log2(i+1))
        dcg = 0.0
        for i, doc_id in enumerate(retrieved[:k], 1):
            rel = 1.0 if doc_id in relevant else 0.0
            dcg += rel / np.log2(i + 1)

        # IDCG: 理想排序的DCG
        idcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def evaluate_query(
        self,
        query: str,
        relevant_docs: Set[str],
        top_k: int = 10,
        alpha: float = 0.5
    ) -> Dict[str, float]:
        """评估单个查询

        Args:
            query: 查询字符串
            relevant_docs: 相关文档ID集合
            top_k: Top-K阈值
            alpha: 混合检索权重

        Returns:
            指标字典
        """
        # 检索
        results = self.retriever.hybrid_search(query, top_k=top_k, alpha=alpha)
        retrieved_ids = [doc_id for doc_id, _, _ in results]

        # 计算指标
        metrics = {
            'recall@5': self.recall_at_k(retrieved_ids, relevant_docs, 5),
            'recall@10': self.recall_at_k(retrieved_ids, relevant_docs, 10),
            'mrr': self.mean_reciprocal_rank(retrieved_ids, relevant_docs),
            'ndcg@5': self.ndcg_at_k(retrieved_ids, relevant_docs, 5),
            'ndcg@10': self.ndcg_at_k(retrieved_ids, relevant_docs, 10),
        }

        return metrics

    def evaluate_dataset(
        self,
        test_queries: List[Dict],
        top_k: int = 10,
        alpha: float = 0.5
    ) -> Dict[str, float]:
        """评估整个数据集

        Args:
            test_queries: 测试查询列表
                [{'query': str, 'relevant_docs': Set[str]}, ...]
            top_k: Top-K阈值
            alpha: 混合检索权重

        Returns:
            平均指标字典
        """
        all_metrics = []

        for item in test_queries:
            query = item['query']
            relevant = item['relevant_docs']

            metrics = self.evaluate_query(query, relevant, top_k, alpha)
            all_metrics.append(metrics)

        # 计算平均值
        avg_metrics = {}
        for key in all_metrics[0].keys():
            avg_metrics[key] = np.mean([m[key] for m in all_metrics])

        return avg_metrics


def load_test_queries_from_annotations(
    annotations_dir: str = "annotations/annotator_A"
) -> List[Dict]:
    """从标注数据中生成测试查询

    Args:
        annotations_dir: 标注文件目录

    Returns:
        测试查询列表
            [{'query': str, 'relevant_docs': Set[str], 'metadata': dict}, ...]
    """
    annotations_path = Path(annotations_dir)
    test_queries = []

    # 遍历所有标注文件
    for json_file in annotations_path.glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        doc_id = data['doc_id']
        annotations = data.get('annotations', [])

        # 从每个标注中提取goal作为查询
        for ann in annotations:
            goal = ann.get('goal', '')
            if not goal:
                continue

            # 每个goal对应的相关文档就是该doc_id
            test_queries.append({
                'query': goal,
                'relevant_docs': {doc_id},
                'metadata': {
                    'doc_id': doc_id,
                    'source_title': data.get('source_title', ''),
                    'instrument': ann.get('instrument', []),
                    'strength': ann.get('strength', 0),
                }
            })

    return test_queries


def main():
    """主函数：运行检索评估"""
    print("PSC-Graph 检索系统评估")
    print("=" * 80)

    # 初始化检索器（纯BM25模式）
    print("\n正在加载检索器...")
    retriever = HybridRetriever(index_dir="indexes", use_faiss=False)

    # 加载测试查询
    print("\n正在从标注数据生成测试查询...")
    test_queries = load_test_queries_from_annotations("annotations/annotator_A")

    if not test_queries:
        print("错误：未找到测试查询")
        print("请确保annotations/annotator_A/目录下有标注文件")
        sys.exit(1)

    print(f"✓ 生成测试查询: {len(test_queries)}个")

    # 显示示例查询
    print("\n示例查询（前3个）:")
    for i, item in enumerate(test_queries[:3], 1):
        print(f"  {i}. {item['query'][:50]}...")
        print(f"     相关文档: {list(item['relevant_docs'])[0]}")

    # 创建评估器
    evaluator = RetrievalEvaluator(retriever)

    # 评估不同的α参数
    print("\n" + "=" * 80)
    print("评估不同检索策略")
    print("=" * 80)

    strategies = [
        ("纯BM25检索", 1.0),
        ("混合检索（α=0.7）", 0.7),
        ("混合检索（α=0.5）", 0.5),
        ("混合检索（α=0.3）", 0.3),
    ]

    # 如果FAISS可用，添加纯FAISS评估
    if retriever.use_faiss:
        strategies.append(("纯FAISS检索", 0.0))

    results_table = []

    for strategy_name, alpha in strategies:
        print(f"\n正在评估: {strategy_name} (α={alpha})")

        # 评估
        avg_metrics = evaluator.evaluate_dataset(
            test_queries,
            top_k=10,
            alpha=alpha
        )

        results_table.append({
            'strategy': strategy_name,
            'alpha': alpha,
            **avg_metrics
        })

        # 显示结果
        print(f"  Recall@5:  {avg_metrics['recall@5']:.4f}")
        print(f"  Recall@10: {avg_metrics['recall@10']:.4f}")
        print(f"  MRR:       {avg_metrics['mrr']:.4f}")
        print(f"  NDCG@5:    {avg_metrics['ndcg@5']:.4f}")
        print(f"  NDCG@10:   {avg_metrics['ndcg@10']:.4f}")

    # 汇总表格
    print("\n" + "=" * 80)
    print("检索指标对比表")
    print("=" * 80)
    print(f"{'策略':<20} {'Recall@5':<12} {'Recall@10':<12} {'MRR':<12} {'NDCG@10':<12}")
    print("-" * 80)

    for row in results_table:
        print(
            f"{row['strategy']:<20} "
            f"{row['recall@5']:<12.4f} "
            f"{row['recall@10']:<12.4f} "
            f"{row['mrr']:<12.4f} "
            f"{row['ndcg@10']:<12.4f}"
        )

    # 找出最佳策略
    print("\n" + "=" * 80)
    print("最佳策略分析")
    print("=" * 80)

    best_recall = max(results_table, key=lambda x: x['recall@10'])
    best_mrr = max(results_table, key=lambda x: x['mrr'])
    best_ndcg = max(results_table, key=lambda x: x['ndcg@10'])

    print(f"最佳Recall@10: {best_recall['strategy']} ({best_recall['recall@10']:.4f})")
    print(f"最佳MRR:       {best_mrr['strategy']} ({best_mrr['mrr']:.4f})")
    print(f"最佳NDCG@10:   {best_ndcg['strategy']} ({best_ndcg['ndcg@10']:.4f})")

    print("\n" + "=" * 80)
    print("评估完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
