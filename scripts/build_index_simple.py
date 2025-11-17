#!/usr/bin/env python3
"""
PSC-Graph RAG索引构建脚本（简化版）

仅构建BM25索引用于快速测试
不依赖sentence-transformers（跳过FAISS向量索引）
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
import pickle
from datetime import datetime

try:
    import jieba
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError as e:
    print(f"错误：缺少依赖库 - {e}")
    print("请运行: pip install jieba scikit-learn")
    sys.exit(1)


class SimpleBM25IndexBuilder:
    """简化版BM25索引构建器"""

    def __init__(
        self,
        corpus_dir: str = "corpus/raw",
        index_dir: str = "indexes"
    ):
        self.corpus_dir = Path(corpus_dir)
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

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

                # 合并标题和内容
                full_text = f"{title}\n{title}\n{content}"

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
        """构建BM25索引"""
        print("\n正在构建BM25索引...")
        print("  使用jieba分词 + TF-IDF")

        # 中文分词
        def tokenize_chinese(text):
            return ' '.join(jieba.cut(text))

        texts = [doc['full_text'] for doc in self.documents]

        print("  正在分词...")
        tokenized_texts = []
        for i, text in enumerate(texts):
            if (i + 1) % 100 == 0:
                print(f"    进度: {i+1}/{len(texts)}")
            tokenized_texts.append(tokenize_chinese(text))

        # 构建TF-IDF向量
        print("  正在构建TF-IDF矩阵...")
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

        print(f"\n✓ BM25索引已保存到: {bm25_path}")
        print(f"  词汇表大小: {len(vectorizer.vocabulary_)}")
        print(f"  文档数: {tfidf_matrix.shape[0]}")

    def build_id_mapping(self):
        """构建doc_id到索引位置的映射"""
        print("\n正在构建ID映射...")

        mapping = {
            'id_to_idx': {doc_id: idx for idx, doc_id in enumerate(self.doc_ids)},
            'idx_to_id': {idx: doc_id for idx, doc_id in enumerate(self.doc_ids)}
        }

        map_path = self.index_dir / 'id_map.json'
        with open(map_path, 'w', encoding='utf-8') as f:
            json.dump({
                'id_to_idx': mapping['id_to_idx'],
                'idx_to_id': mapping['idx_to_id']
            }, f, ensure_ascii=False, indent=2)

        # 保存文档元数据
        meta_path = self.index_dir / 'doc_metadata.json'
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)

        print(f"✓ ID映射已保存到: {map_path}")
        print(f"✓ 文档元数据已保存到: {meta_path}")

    def generate_report(self):
        """生成索引构建报告"""
        report = []
        report.append("=" * 60)
        report.append("PSC-Graph BM25索引构建报告（简化版）")
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
        report.append(f"ID映射: {self.index_dir / 'id_map.json'}")
        report.append(f"文档元数据: {self.index_dir / 'doc_metadata.json'}")

        report.append("")
        report.append("### 说明")
        report.append("-" * 60)
        report.append("这是简化版索引（仅BM25）")
        report.append("完整版（含FAISS）请运行: python3 scripts/build_index.py")

        report.append("=" * 60)

        report_text = "\n".join(report)
        print("\n" + report_text)

        # 保存报告
        report_path = self.index_dir / 'build_report_simple.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(f"\n✓ 构建报告已保存到: {report_path}")


def main():
    """主函数"""
    print("PSC-Graph BM25索引构建工具（简化版）")
    print("=" * 60)

    builder = SimpleBM25IndexBuilder()

    # 加载文档
    doc_count = builder.load_documents()
    if doc_count == 0:
        print("错误：未找到有效文档")
        return

    # 构建BM25索引
    builder.build_bm25_index()

    # 构建ID映射
    builder.build_id_mapping()

    # 生成报告
    builder.generate_report()

    print("\n✓ 简化版索引构建完成！")
    print("\n说明：")
    print("  - 已构建BM25索引（精确检索）")
    print("  - FAISS向量索引需要完整版脚本")
    print("  - 运行 python3 scripts/build_index.py 构建完整索引")


if __name__ == "__main__":
    main()
