#!/usr/bin/env python3
"""
PSC-Graph 混合检索演示

实现BM25（精确检索）+ FAISS（语义检索）混合检索
当前版本：优先使用BM25，FAISS可选（依赖sentence-transformers）
"""

import json
import pickle
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

try:
    import jieba
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError as e:
    print(f"错误：缺少依赖库 - {e}")
    print("请运行: apt-get install python3-jieba 或 pip install jieba scikit-learn")
    sys.exit(1)


class HybridRetriever:
    """混合检索器（BM25 + FAISS可选）"""

    def __init__(
        self,
        index_dir: str = "indexes",
        use_faiss: bool = False
    ):
        self.index_dir = Path(index_dir)
        self.use_faiss = use_faiss

        # 加载BM25索引
        self.load_bm25_index()

        # 加载文档元数据
        self.load_metadata()

        # 尝试加载FAISS索引
        if self.use_faiss:
            try:
                self.load_faiss_index()
            except Exception as e:
                print(f"警告：FAISS索引加载失败 - {e}")
                print("降级为纯BM25检索")
                self.use_faiss = False

    def load_bm25_index(self):
        """加载BM25索引"""
        bm25_dir = self.index_dir / 'bm25'

        with open(bm25_dir / 'vectorizer.pkl', 'rb') as f:
            self.vectorizer = pickle.load(f)

        with open(bm25_dir / 'tfidf_matrix.pkl', 'rb') as f:
            self.tfidf_matrix = pickle.load(f)

        print(f"✓ BM25索引加载成功")
        print(f"  词汇表大小: {len(self.vectorizer.vocabulary_)}")
        print(f"  文档数: {self.tfidf_matrix.shape[0]}")

    def load_metadata(self):
        """加载文档元数据"""
        with open(self.index_dir / 'doc_metadata.json', 'r', encoding='utf-8') as f:
            self.documents = json.load(f)

        with open(self.index_dir / 'id_map.json', 'r', encoding='utf-8') as f:
            id_map = json.load(f)
            self.id_to_idx = id_map['id_to_idx']
            self.idx_to_id = {int(k): v for k, v in id_map['idx_to_id'].items()}

        print(f"✓ 文档元数据加载成功（{len(self.documents)}份文档）")

    def load_faiss_index(self):
        """加载FAISS向量索引（可选）"""
        try:
            import faiss
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.faiss_index = faiss.read_index(str(self.index_dir / 'faiss.index'))

            print(f"✓ FAISS索引加载成功")
            print(f"  向量维度: {self.faiss_index.d}")
            print(f"  索引文档数: {self.faiss_index.ntotal}")
        except ImportError:
            raise ImportError("sentence-transformers或faiss-cpu未安装")

    def bm25_search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """BM25精确检索"""
        # 分词
        query_tokenized = ' '.join(jieba.cut(query))

        # 向量化
        query_vec = self.vectorizer.transform([query_tokenized])

        # 计算余弦相似度
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # 排序并获取Top-K
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            doc_id = self.idx_to_id[idx]
            score = float(scores[idx])
            results.append((doc_id, score))

        return results

    def faiss_search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """FAISS语义检索"""
        if not self.use_faiss:
            raise RuntimeError("FAISS索引未启用")

        # 编码查询
        query_emb = self.model.encode([query])

        # 检索
        distances, indices = self.faiss_index.search(query_emb.astype('float32'), top_k)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            doc_id = self.idx_to_id[idx]
            # L2距离转换为相似度分数（0-1）
            score = 1.0 / (1.0 + float(dist))
            results.append((doc_id, score))

        return results

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = 0.5
    ) -> List[Tuple[str, float, Dict]]:
        """混合检索（BM25 + FAISS融合）

        Args:
            query: 查询字符串
            top_k: 返回结果数
            alpha: BM25权重（0.0-1.0），FAISS权重为1-alpha

        Returns:
            [(doc_id, score, metadata), ...]
        """
        if not self.use_faiss:
            # 降级为纯BM25
            print("提示：使用纯BM25检索（FAISS未启用）")
            bm25_results = self.bm25_search(query, top_k * 2)

            # 附加元数据
            results_with_meta = []
            for doc_id, score in bm25_results[:top_k]:
                doc = next((d for d in self.documents if d['doc_id'] == doc_id), None)
                if doc:
                    results_with_meta.append((doc_id, score, doc))

            return results_with_meta

        # 获取BM25和FAISS结果
        bm25_results = self.bm25_search(query, top_k * 2)
        faiss_results = self.faiss_search(query, top_k * 2)

        # 归一化分数
        def normalize_scores(results):
            if not results:
                return {}
            max_score = max(s for _, s in results)
            min_score = min(s for _, s in results)
            if max_score == min_score:
                return {doc_id: 1.0 for doc_id, _ in results}
            return {
                doc_id: (score - min_score) / (max_score - min_score)
                for doc_id, score in results
            }

        bm25_norm = normalize_scores(bm25_results)
        faiss_norm = normalize_scores(faiss_results)

        # 融合分数
        all_doc_ids = set(bm25_norm.keys()) | set(faiss_norm.keys())
        fused_scores = {}
        for doc_id in all_doc_ids:
            bm25_score = bm25_norm.get(doc_id, 0.0)
            faiss_score = faiss_norm.get(doc_id, 0.0)
            fused_scores[doc_id] = alpha * bm25_score + (1 - alpha) * faiss_score

        # 排序并获取Top-K
        sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 附加元数据
        results_with_meta = []
        for doc_id, score in sorted_results:
            doc = next((d for d in self.documents if d['doc_id'] == doc_id), None)
            if doc:
                results_with_meta.append((doc_id, score, doc))

        return results_with_meta


def format_results(results: List[Tuple[str, float, Dict]]):
    """格式化输出检索结果"""
    print("\n" + "="*80)
    print(f"检索结果（共 {len(results)} 条）")
    print("="*80)

    for i, (doc_id, score, doc) in enumerate(results, 1):
        print(f"\n【{i}】文档ID: {doc_id} | 相关度: {score:.4f}")
        print(f"标题: {doc['title']}")
        print(f"类别: {doc.get('category', 'N/A')}")
        print(f"地区: {doc.get('region', 'N/A')}")
        print(f"URL: {doc.get('source_url', 'N/A')}")

        # 显示内容摘要（前200字）
        content = doc.get('content', doc.get('full_text', ''))
        if content:
            summary = content[:200] + "..." if len(content) > 200 else content
            print(f"摘要: {summary}")

        print("-" * 80)


def main():
    """主函数：演示检索功能"""
    print("PSC-Graph 混合检索演示")
    print("=" * 80)

    # 初始化检索器
    retriever = HybridRetriever(index_dir="indexes", use_faiss=False)

    # 演示查询
    demo_queries = [
        "绿色贸易政策",
        "科技园区建设资金支持",
        "人才引进补贴",
        "研发经费加计扣除",
        "新能源汽车产业政策"
    ]

    print(f"\n演示查询（共 {len(demo_queries)} 个）：")
    for i, query in enumerate(demo_queries, 1):
        print(f"  {i}. {query}")

    # 执行第一个查询作为演示
    query = demo_queries[0]
    print(f"\n\n正在检索: 「{query}」")
    print("检索方法: BM25精确检索")

    results = retriever.hybrid_search(query, top_k=5, alpha=1.0)
    format_results(results)

    # 交互式检索
    print("\n" + "="*80)
    print("交互式检索（输入'quit'退出）")
    print("="*80)

    while True:
        try:
            user_query = input("\n请输入查询关键词: ").strip()

            if user_query.lower() in ['quit', 'exit', 'q']:
                print("退出检索")
                break

            if not user_query:
                print("查询不能为空")
                continue

            results = retriever.hybrid_search(user_query, top_k=5, alpha=1.0)
            format_results(results)

        except KeyboardInterrupt:
            print("\n\n退出检索")
            break
        except Exception as e:
            print(f"错误: {e}")
            continue


if __name__ == "__main__":
    main()
