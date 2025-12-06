#!/usr/bin/env python3
"""
PSC-Graph TAPT任务语料准备脚本

构建Task-Adaptive Pre-Training (TAPT) 的训练语料，符合CLAUDE.md要求：
- 语料来源：已标注的政策五元组数据（annotations/adjudicated/）
- 处理流程：提取evidence_spans → 扩展上下文 → 去重
- 输出格式：纯文本，每行一个句子
- 质量要求：≥1k句子，覆盖政策五元组相关语义

目标：为DAPT模型注入政策五元组抽取任务的特定知识

依赖：无特殊依赖，仅使用标准库
"""

import json
from pathlib import Path
from typing import List, Dict, Set


class TAPTTaskCorpusBuilder:
    """TAPT任务语料构建器"""

    def __init__(
        self,
        anno_dir: str = "annotations/adjudicated",
        output_path: str = "data/tapt_corpus.txt",
        context_window: int = 200,
        min_sent_length: int = 20
    ):
        """初始化语料构建器

        Args:
            anno_dir: 已标注数据目录
            output_path: 输出文件路径
            context_window: 上下文窗口大小（字符数）
            min_sent_length: 最小句子长度
        """
        self.anno_dir = Path(anno_dir)
        self.output_path = Path(output_path)
        self.context_window = context_window
        self.min_sent_length = min_sent_length

        # 统计信息
        self.stats = {
            'total_files': 0,
            'total_annotations': 0,
            'total_evidence_spans': 0,
            'total_sentences_raw': 0,
            'total_sentences_unique': 0
        }

    def extract_evidence_with_context(
        self,
        content: str,
        evidence_spans: List[Dict]
    ) -> List[str]:
        """提取evidence_spans及其上下文

        策略：
        1. 提取evidence_span本身
        2. 提取前后context_window字符的上下文
        3. 合并为完整句子

        Args:
            content: 政策正文
            evidence_spans: 证据段落列表
                [{'start': 100, 'end': 200, 'from_doc': 'policy'}, ...]

        Returns:
            句子列表
        """
        sentences = []

        for span in evidence_spans:
            start = span.get('start', 0)
            end = span.get('end', 0)

            if start >= end or end > len(content):
                continue

            # 提取evidence本身
            evidence_text = content[start:end].strip()
            if len(evidence_text) >= self.min_sent_length:
                sentences.append(evidence_text)

            # 提取带上下文的片段
            context_start = max(0, start - self.context_window)
            context_end = min(len(content), end + self.context_window)

            context_text = content[context_start:context_end].strip()
            if len(context_text) >= self.min_sent_length:
                sentences.append(context_text)

        return sentences

    def extract_paragraphs(self, content: str) -> List[str]:
        """提取政策正文的段落

        Args:
            content: 政策正文

        Returns:
            段落列表
        """
        # 按换行符分段
        paragraphs = content.split('\n')

        # 过滤短段落
        paragraphs = [p.strip() for p in paragraphs if len(p.strip()) >= self.min_sent_length]

        return paragraphs

    def process_annotation_file(self, file_path: Path) -> List[str]:
        """处理单个标注文件

        Args:
            file_path: 标注JSON文件路径

        Returns:
            句子列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                anno = json.load(f)

            # 提取正文
            content = anno.get('content', '')
            if not content:
                return []

            sentences = []

            # 方法1：提取evidence_spans及上下文
            evidence_spans = anno.get('evidence_spans', [])
            if evidence_spans:
                evidence_sents = self.extract_evidence_with_context(content, evidence_spans)
                sentences.extend(evidence_sents)
                self.stats['total_evidence_spans'] += len(evidence_spans)

            # 方法2：提取整个政策的段落（扩大语料）
            paragraphs = self.extract_paragraphs(content)
            sentences.extend(paragraphs)

            # 统计
            self.stats['total_annotations'] += 1

            return sentences

        except Exception as e:
            print(f"  警告：处理文件失败 {file_path.name}: {e}")
            return []

    def build_corpus(self):
        """构建TAPT语料

        主流程：
        1. 收集所有标注文件
        2. 逐文件提取句子
        3. 去重
        4. 保存
        """
        print("=" * 80)
        print("PSC-Graph TAPT任务语料构建")
        print("=" * 80)

        # 收集文件
        print("\n【步骤1】收集标注文件")
        print("-" * 80)

        if not self.anno_dir.exists():
            print(f"❌ 错误：标注目录不存在: {self.anno_dir}")
            print(f"\n解决方案：")
            print(f"  1. 如果已有标注数据，请确保路径正确")
            print(f"  2. 如果尚无标注数据，请先运行标注流程")
            print(f"  3. 可以使用generate_sample_annotations.py生成示例数据")
            return

        anno_files = list(self.anno_dir.glob("*.json"))
        self.stats['total_files'] = len(anno_files)

        if not anno_files:
            print(f"❌ 错误：未找到任何标注文件 (*.json)")
            print(f"  目录: {self.anno_dir}")
            print(f"\n提示：")
            print(f"  如果标注数据在其他目录，请修改anno_dir参数")
            return

        print(f"  ✓ 找到 {len(anno_files)} 个标注文件")

        # 处理文件
        print("\n【步骤2】提取句子和上下文")
        print("-" * 80)

        all_sentences = []

        for i, file_path in enumerate(anno_files):
            sentences = self.process_annotation_file(file_path)
            all_sentences.extend(sentences)

            # 进度显示
            if (i + 1) % 50 == 0:
                print(f"  已处理: {i+1}/{len(anno_files)} 文件 "
                      f"(累计 {len(all_sentences)} 句子)")

        self.stats['total_sentences_raw'] = len(all_sentences)

        print(f"\n  ✓ 提取完成")
        print(f"    标注文件数: {self.stats['total_files']}")
        print(f"    有效标注数: {self.stats['total_annotations']}")
        print(f"    evidence_spans数: {self.stats['total_evidence_spans']}")
        print(f"    原始句子数: {len(all_sentences):,}")

        # 去重
        print("\n【步骤3】去重")
        print("-" * 80)

        unique_sentences = list(dict.fromkeys(all_sentences))
        self.stats['total_sentences_unique'] = len(unique_sentences)

        print(f"  去重前: {len(all_sentences):,} 句子")
        print(f"  去重后: {len(unique_sentences):,} 句子")
        print(f"  去重率: {(1 - len(unique_sentences)/max(len(all_sentences), 1))*100:.1f}%")

        # 保存
        print("\n【步骤4】保存语料")
        print("-" * 80)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_path, 'w', encoding='utf-8') as f:
            for sent in unique_sentences:
                f.write(sent + '\n')

        print(f"  ✓ 语料已保存到: {self.output_path}")
        print(f"    文件大小: {self.output_path.stat().st_size / 1024:.2f} KB")

        # 最终报告
        print("\n" + "=" * 80)
        print("TAPT语料构建完成 ✓")
        print("=" * 80)
        print(f"\n统计摘要：")
        print(f"  标注文件数: {self.stats['total_files']:,}")
        print(f"  唯一句子数: {self.stats['total_sentences_unique']:,}")
        print(f"  平均每文件: {self.stats['total_sentences_unique'] / max(self.stats['total_files'], 1):.1f} 句子")

        # 质量检查
        if self.stats['total_sentences_unique'] < 1000:
            print(f"\n⚠️  警告：句子数（{self.stats['total_sentences_unique']:,}）少于推荐值（1,000）")
            print(f"  建议：")
            print(f"    1. 增加标注数据量")
            print(f"    2. 降低min_sent_length参数")
            print(f"    3. 增加context_window扩大上下文")
        else:
            print(f"\n✓ 语料规模符合要求（≥1k句子）")

        print(f"\n下一步：")
        print(f"  运行 run_tapt.py 进行TAPT训练")


def main():
    """主函数"""
    # 检查标注目录是否存在
    anno_dir = Path("annotations/adjudicated")

    if not anno_dir.exists():
        print("警告：标注目录不存在，尝试使用示例数据目录")
        anno_dir = Path("corpus/samples")

    builder = TAPTTaskCorpusBuilder(
        anno_dir=str(anno_dir),
        output_path="data/tapt_corpus.txt",
        context_window=200,
        min_sent_length=20
    )

    builder.build_corpus()


if __name__ == "__main__":
    main()
