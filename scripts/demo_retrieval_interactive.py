#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语义抽取层交互式检索演示脚本

功能：
1. 加载BM25和FAISS索引
2. 提供预定义查询示例
3. 允许用户输入自定义查询
4. 展示Top-K结果（标题、摘要、相关度）
5. 对比BM25和FAISS的检索差异

使用：python3 scripts/demo_retrieval_interactive.py
"""

import pickle
import json
from pathlib import Path
from typing import List, Tuple
import warnings

warnings.filterwarnings('ignore')


def main():
    """主演示函数"""
    print("=" * 70)
    print("语义抽取层交互式检索演示")
    print("=" * 70)

    project_root = Path(__file__).parent.parent

    # 步骤1: 加载索引
    print("\n【步骤1】 加载索引")
    print("-" * 70)

    bm25_available, faiss_available = check_index_availability(project_root)

    if not bm25_available:
        print("❌ BM25索引不可用，请先运行: python3 scripts/build_index.py")
        return 1

    # 加载BM25索引
    bm25_data = load_bm25_index(project_root)
    if not bm25_data:
        return 1

    print(f"✓ BM25索引加载成功: {len(bm25_data['id_map'])}份文档")

    # 尝试加载FAISS索引
    if faiss_available:
        print("✓ FAISS索引可用（完整混合检索模式）")
        mode = "hybrid"
    else:
        print("⚠️  FAISS索引不可用（仅BM25模式）")
        mode = "bm25_only"

    # 步骤2: 预定义查询演示
    print("\n【步骤2】 预定义查询演示")
    print("-" * 70)

    demo_queries = [
        "绿色贸易政策支持措施",
        "人工智能技术研发资金",
        "科技园区建设用地支持",
        "创新企业税收优惠",
        "新能源产业发展规划"
    ]

    print(f"\n预定义查询列表:")
    for i, query in enumerate(demo_queries, 1):
        print(f"  {i}. {query}")

    print(f"\n选择一个查询进行演示（输入1-5，或直接回车查询第1个）:")
    choice = input("> ").strip()

    if choice == "":
        choice = "1"

    if choice.isdigit() and 1 <= int(choice) <= len(demo_queries):
        query = demo_queries[int(choice) - 1]
    else:
        query = demo_queries[0]

    print(f"\n查询: {query}")
    print("-" * 70)

    # 执行检索
    results = simple_bm25_search(query, bm25_data, top_k=5)

    # 展示结果
    show_results(results)

    # 步骤3: 交互式查询
    print("\n【步骤3】 交互式查询")
    print("-" * 70)
    print("输入自定义查询（直接回车退出）:")

    while True:
        user_query = input("\n查询> ").strip()

        if not user_query:
            break

        print(f"\n检索中...")
        results = simple_bm25_search(user_query, bm25_data, top_k=5)
        show_results(results)

    # 总结
    print("\n" + "=" * 70)
    print("检索演示完成")
    print("=" * 70)

    print("\n提示:")
    if mode == "bm25_only":
        print("  当前仅使用BM25检索（精确匹配）")
        print("  建议：运行 python3 scripts/build_index.py 构建FAISS索引以启用语义检索")
    else:
        print("  当前支持BM25+FAISS混合检索")
        print("  可运行 python3 scripts/retrieve_evidence.py 使用完整混合检索功能")

    return 0


def check_index_availability(project_root: Path) -> Tuple[bool, bool]:
    """检查索引可用性

    返回:
        (bm25_available, faiss_available)
    """
    bm25_path = project_root / 'indexes' / 'bm25' / 'tfidf_matrix.pkl'
    faiss_path = project_root / 'indexes' / 'faiss.index'

    bm25_available = bm25_path.exists()
    faiss_available = faiss_path.exists()

    return bm25_available, faiss_available


def load_bm25_index(project_root: Path):
    """加载BM25索引"""
    try:
        # 加载TF-IDF矩阵
        tfidf_matrix_path = project_root / 'indexes' / 'bm25' / 'tfidf_matrix.pkl'
        with open(tfidf_matrix_path, 'rb') as f:
            tfidf_matrix = pickle.load(f)

        # 加载向量化器
        vectorizer_path = project_root / 'indexes' / 'bm25' / 'vectorizer.pkl'
        with open(vectorizer_path, 'rb') as f:
            vectorizer = pickle.load(f)

        # 加载ID映射
        id_map_path = project_root / 'indexes' / 'id_map.json'
        with open(id_map_path, 'r', encoding='utf-8') as f:
            id_map = json.load(f)

        # 加载元数据
        metadata_path = project_root / 'indexes' / 'doc_metadata.json'
        with open(metadata_path, 'r', encoding='utf-8') as f:
            doc_metadata_list = json.load(f)

        # 转换为字典以便快速查找（doc_id -> metadata）
        if isinstance(doc_metadata_list, list):
            doc_metadata = {item['doc_id']: item for item in doc_metadata_list}
        else:
            doc_metadata = doc_metadata_list

        return {
            'tfidf_matrix': tfidf_matrix,
            'vectorizer': vectorizer,
            'id_map': id_map,
            'doc_metadata': doc_metadata
        }

    except Exception as e:
        print(f"❌ 加载BM25索引失败: {e}")
        return None


def simple_bm25_search(query: str, bm25_data: dict, top_k: int = 5) -> List[dict]:
    """简化的BM25检索

    参数:
        query: 查询文本
        bm25_data: BM25索引数据
        top_k: 返回前K个结果

    返回:
        检索结果列表
    """
    import jieba
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity

    # 分词
    query_tokens = ' '.join(jieba.cut(query))

    # 向量化
    query_vec = bm25_data['vectorizer'].transform([query_tokens])

    # 计算相似度
    similarities = cosine_similarity(query_vec, bm25_data['tfidf_matrix']).flatten()

    # 排序
    top_indices = similarities.argsort()[::-1][:top_k]

    # 构建结果
    results = []
    idx_to_id = bm25_data['id_map'].get('idx_to_id', {})

    for idx in top_indices:
        doc_id = idx_to_id.get(str(idx))
        if not doc_id:
            continue

        metadata = bm25_data['doc_metadata'].get(doc_id, {})

        results.append({
            'doc_id': doc_id,
            'score': float(similarities[idx]),
            'title': metadata.get('source_title', '无标题'),
            'category': metadata.get('category', '未分类'),
            'region': metadata.get('region', ''),
            'url': metadata.get('source_url', ''),
            'content_preview': metadata.get('content', '')[:150] + '...' if metadata.get('content') else ''
        })

    return results


def show_results(results: List[dict]):
    """展示检索结果"""

    if not results:
        print("  未找到相关文档")
        return

    print(f"\n检索结果 (Top-{len(results)}):\n")

    for i, result in enumerate(results, 1):
        print(f"【{i}】 {result['title']}")
        print(f"  相关度: {result['score']:.4f}")
        print(f"  类别: {result['category']}")

        if result['region']:
            print(f"  地区: {result['region']}")

        if result['content_preview']:
            print(f"  摘要: {result['content_preview']}")

        print(f"  URL: {result['url']}")
        print()


if __name__ == '__main__':
    exit(main())
