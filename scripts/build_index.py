#!/usr/bin/env python3
"""
PSC-Graph RAG索引构建脚本

功能:
1. 构建BM25索引（Pyserini/Lucene）- 精确检索
2. 构建FAISS向量索引 - 语义检索
3. 支持混合检索（α=0.5融合）

依赖:
- sentence-transformers (向量编码)
- faiss-cpu (向量索引)
- jieba (中文分词)
- pyserini (BM25索引，需要Java环境)
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
import pickle
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    import jieba
except ImportError as e:
    print(f"错误：缺少依赖库 - {e}")
    print("请运行: pip install sentence-transformers faiss-cpu jieba")
    sys.exit(1)


class RAGIndexBuilder:
    """RAG索引构建器"""

    def __init__(
        self,
        corpus_dir: str = "corpus/raw",
        index_dir: str = "indexes",
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    ):
        self.corpus_dir = Path(corpus_dir)
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # 向量模型（384维）
        print(f"正在加载向量模型: {model_name}")
        self.model = SentenceTransformer(model_name)

        # 文档集合
        self.documents = []
        self.doc_ids = []

    def load_documents(self) -> int:
        """加载所有政策文档"""
        print("\n正在加载政策文档...")

        # 加载中央政策
        central_files = list(self.corpus_dir.glob("policy_central/**/*.json"))
        print(f"  找到 {len(central_files)} 份中央政策")

        # 加载省级政策
        prov_files = list(self.corpus_dir.glob("policy_provinces/**/*.json"))
        print(f"  找到 {len(prov_files)} 份省级政策")

        all_files = central_files + prov_files

        for i, file_path in enumerate(all_files):
            if (i + 1) % 100 == 0:
                print(f"  进度: {i+1}/{len(all_files)}")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                doc_id = data.get('doc_id')
                title = data.get('title', '')
                content = data.get('content_text', '')

                if not content or len(content) < 50:
                    continue

                # 合并标题和内容（标题权重更高）
                full_text = f"{title}\n{title}\n{content}"  # 标题重复2次提升权重

                self.documents.append({
                    'doc_id': doc_id,
                    'title': title,
                    'content': content,
                    'full_text': full_text,
                    'source_url': data.get('source_url', ''),
                    'category': data.get('category', ''),
                    'region': data.get('region', '')
                })
                self.doc_ids.append(doc_id)

            except Exception as e:
                print(f"  警告：跳过文件 {file_path.name} - {e}")
                continue

        print(f"\n✓ 成功加载 {len(self.documents)} 份有效文档")
        return len(self.documents)

    def build_bm25_index(self):
        """构建BM25索引（使用简化的TF-IDF方法替代Pyserini）"""
        print("\n正在构建BM25索引...")
        print("  注意：使用jieba分词+TF-IDF（简化版BM25）")

        from sklearn.feature_extraction.text import TfidfVectorizer

        # 中文分词
        def tokenize_chinese(text):
            return ' '.join(jieba.cut(text))

        texts = [doc['full_text'] for doc in self.documents]
        tokenized_texts = [tokenize_chinese(text) for text in texts]

        # 构建TF-IDF向量（BM25的简化版本）
        vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            min_df=2
        )

        tfidf_matrix = vectorizer.fit_transform(tokenized_texts)

        # 保存索引
        bm25_path = self.index_dir / 'bm25'
        bm25_path.mkdir(parents=True, exist_ok=True)

        with open(bm25_path / 'vectorizer.pkl', 'wb') as f:
            pickle.dump(vectorizer, f)

        with open(bm25_path / 'tfidf_matrix.pkl', 'wb') as f:
            pickle.dump(tfidf_matrix, f)

        print(f"✓ BM25索引已保存到: {bm25_path}")
        print(f"  词汇表大小: {len(vectorizer.vocabulary_)}")
        print(f"  文档数: {tfidf_matrix.shape[0]}")

    def build_faiss_index(self):
        """构建FAISS向量索引"""
        print("\n正在构建FAISS向量索引...")

        # 提取文本列表
        texts = [doc['full_text'] for doc in self.documents]

        # 批量编码（避免内存溢出）
        print("  正在生成文档向量...")
        batch_size = 32
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_emb = self.model.encode(batch, show_progress_bar=True)
            embeddings.append(batch_emb)

            if (i + batch_size) % 100 == 0:
                print(f"    进度: {min(i+batch_size, len(texts))}/{len(texts)}")

        embeddings = np.vstack(embeddings).astype('float32')

        # 构建FAISS索引
        print("  正在构建FAISS索引...")
        dimension = embeddings.shape[1]  # 384
        index = faiss.IndexFlatL2(dimension)  # L2距离
        index.add(embeddings)

        # 保存索引
        faiss_path = self.index_dir / 'faiss.index'
        faiss.write_index(index, str(faiss_path))

        print(f"✓ FAISS索引已保存到: {faiss_path}")
        print(f"  向量维度: {dimension}")
        print(f"  文档数: {index.ntotal}")

    def build_id_mapping(self):
        """构建doc_id到索引位置的映射"""
        print("\n正在构建ID映射...")

        mapping = {
            'id_to_idx': {doc_id: idx for idx, doc_id in enumerate(self.doc_ids)},
            'idx_to_id': {idx: doc_id for idx, doc_id in enumerate(self.doc_ids)},
            'idx_to_doc': {idx: doc for idx, doc in enumerate(self.documents)}
        }

        map_path = self.index_dir / 'id_map.json'
        with open(map_path, 'w', encoding='utf-8') as f:
            json.dump({
                'id_to_idx': mapping['id_to_idx'],
                'idx_to_id': mapping['idx_to_id']
            }, f, ensure_ascii=False, indent=2)

        # 保存完整文档元数据
        meta_path = self.index_dir / 'doc_metadata.json'
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)

        print(f"✓ ID映射已保存到: {map_path}")
        print(f"✓ 文档元数据已保存到: {meta_path}")

    def generate_report(self):
        """生成索引构建报告"""
        report = []
        report.append("=" * 60)
        report.append("PSC-Graph RAG索引构建报告")
        report.append("=" * 60)
        report.append(f"构建时间: {datetime.now().isoformat()}")
        report.append("")

        # 统计信息
        report.append("### 文档统计")
        report.append("-" * 60)
        report.append(f"总文档数: {len(self.documents)}")

        # 按类别统计
        categories = {}
        for doc in self.documents:
            cat = doc['category']
            categories[cat] = categories.get(cat, 0) + 1

        for cat, count in sorted(categories.items()):
            report.append(f"  - {cat}: {count}份")

        # 索引信息
        report.append("")
        report.append("### 索引信息")
        report.append("-" * 60)
        report.append(f"BM25索引: {self.index_dir / 'bm25'}")
        report.append(f"FAISS索引: {self.index_dir / 'faiss.index'}")
        report.append(f"ID映射: {self.index_dir / 'id_map.json'}")
        report.append(f"文档元数据: {self.index_dir / 'doc_metadata.json'}")

        report.append("")
        report.append("### 模型信息")
        report.append("-" * 60)
        report.append(f"向量模型: paraphrase-multilingual-MiniLM-L12-v2")
        report.append(f"向量维度: 384")
        report.append(f"分词工具: jieba")

        report.append("=" * 60)

        report_text = "\n".join(report)
        print("\n" + report_text)

        # 保存报告
        report_path = self.index_dir / 'build_report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(f"\n✓ 构建报告已保存到: {report_path}")


def main():
    """主函数"""
    print("PSC-Graph RAG索引构建工具")
    print("=" * 60)

    # 初始化构建器
    builder = RAGIndexBuilder()

    # 加载文档
    doc_count = builder.load_documents()
    if doc_count == 0:
        print("错误：未找到有效文档")
        return

    # 构建BM25索引
    builder.build_bm25_index()

    # 构建FAISS索引
    builder.build_faiss_index()

    # 构建ID映射
    builder.build_id_mapping()

    # 生成报告
    builder.generate_report()

    print("\n✓ 索引构建完成！")
    print("\n下一步：运行 python3 scripts/retrieve_evidence.py 进行检索测试")


if __name__ == "__main__":
    main()
