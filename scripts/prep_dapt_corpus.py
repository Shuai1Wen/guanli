#!/usr/bin/env python3
"""
PSC-Graph DAPT语料准备脚本

构建Domain-Adaptive Pre-Training (DAPT) 的训练语料，符合CLAUDE.md要求：
- 语料来源：中央政策 + 省级政策（corpus/raw/）
- 处理流程：提取正文 → 句子切分 → 过滤清洗 → 去重
- 输出格式：纯文本，每行一个句子，空行分隔文档
- 质量要求：≥50k句子，覆盖政策领域核心词汇

目标：为通用预训练模型（如chinese-roberta-wwm-ext）注入政策领域知识

依赖：无特殊依赖，仅使用标准库
"""

import json
import re
from pathlib import Path
from typing import List, Set
from collections import Counter


class DAPTCorpusBuilder:
    """DAPT语料构建器"""

    def __init__(
        self,
        central_dir: str = "corpus/raw/policy_central",
        prov_dir: str = "corpus/raw/policy_prov",
        output_path: str = "data/dapt_corpus.txt",
        min_sent_length: int = 10,
        max_sent_length: int = 512
    ):
        """初始化语料构建器

        Args:
            central_dir: 中央政策目录
            prov_dir: 省级政策目录
            output_path: 输出文件路径
            min_sent_length: 最小句子长度（字符数）
            max_sent_length: 最大句子长度（防止异常长句）
        """
        self.central_dir = Path(central_dir)
        self.prov_dir = Path(prov_dir)
        self.output_path = Path(output_path)
        self.min_sent_length = min_sent_length
        self.max_sent_length = max_sent_length

        # 统计信息
        self.stats = {
            'total_files': 0,
            'total_docs': 0,
            'total_sentences_raw': 0,
            'total_sentences_filtered': 0,
            'total_sentences_unique': 0,
            'total_chars': 0
        }

    def split_sentences(self, text: str) -> List[str]:
        """中文句子切分

        使用规则方法：根据中文标点符号切分
        句末标点：。！？；

        Args:
            text: 输入文本

        Returns:
            句子列表
        """
        # 替换英文句号为中文句号（统一处理）
        text = text.replace('.', '。')

        # 按句末标点切分
        # 注意：保留标点符号
        sentences = re.split(r'([。！？；])', text)

        # 重新组合（标点符号附加到前一个句子）
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sent = sentences[i]
            if i + 1 < len(sentences):
                sent += sentences[i + 1]  # 添加标点
            if sent.strip():
                result.append(sent.strip())

        return result

    def clean_sentence(self, sent: str) -> str:
        """清洗句子

        处理：
        1. 去除多余空白字符
        2. 去除特殊控制字符
        3. 标准化标点符号

        Args:
            sent: 输入句子

        Returns:
            清洗后的句子
        """
        # 去除控制字符（\x00-\x1f）
        sent = re.sub(r'[\x00-\x1f]', '', sent)

        # 统一多个空格为一个
        sent = re.sub(r'\s+', ' ', sent)

        # 去除首尾空格
        sent = sent.strip()

        # 标准化引号
        sent = sent.replace('"', '"').replace('"', '"')
        sent = sent.replace(''', "'").replace(''', "'")

        return sent

    def is_valid_sentence(self, sent: str) -> bool:
        """判断句子是否有效

        过滤规则：
        1. 长度在[min_sent_length, max_sent_length]范围内
        2. 包含至少3个中文字符
        3. 不是纯数字或纯标点
        4. 不包含HTML标签

        Args:
            sent: 句子

        Returns:
            是否有效
        """
        # 长度检查
        if not (self.min_sent_length <= len(sent) <= self.max_sent_length):
            return False

        # 中文字符数量检查
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', sent)
        if len(chinese_chars) < 3:
            return False

        # 纯数字或纯标点检查
        if re.match(r'^[\d\s\.\-\,，。；：、]+$', sent):
            return False

        # HTML标签检查
        if re.search(r'<[^>]+>', sent):
            return False

        return True

    def extract_policy_content(self, policy_json: dict) -> str:
        """从政策JSON提取正文内容

        支持多种字段名：content, text, full_text, body

        Args:
            policy_json: 政策JSON对象

        Returns:
            政策正文（可能为空）
        """
        # 尝试多种可能的字段名
        content_fields = ['content', 'text', 'full_text', 'body', 'description']

        for field in content_fields:
            if field in policy_json and policy_json[field]:
                return str(policy_json[field])

        return ""

    def process_policy_file(self, file_path: Path) -> List[str]:
        """处理单个政策文件

        Args:
            file_path: 政策JSON文件路径

        Returns:
            句子列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                policy = json.load(f)

            # 提取正文
            content = self.extract_policy_content(policy)

            if not content:
                return []

            # 句子切分
            sentences = self.split_sentences(content)

            # 清洗和过滤
            sentences_cleaned = []
            for sent in sentences:
                sent_clean = self.clean_sentence(sent)
                if self.is_valid_sentence(sent_clean):
                    sentences_cleaned.append(sent_clean)

            return sentences_cleaned

        except Exception as e:
            print(f"  警告：处理文件失败 {file_path.name}: {e}")
            return []

    def build_corpus(self):
        """构建DAPT语料

        主流程：
        1. 收集所有政策JSON文件
        2. 逐文件提取和处理
        3. 去重
        4. 保存到输出文件
        """
        print("=" * 80)
        print("PSC-Graph DAPT语料构建")
        print("=" * 80)

        # 收集文件
        print("\n【步骤1】收集政策文件")
        print("-" * 80)

        corpus_files = []

        # 中央政策
        if self.central_dir.exists():
            central_files = list(self.central_dir.glob("*.json"))
            corpus_files.extend(central_files)
            print(f"  中央政策文件: {len(central_files)}个")
        else:
            print(f"  警告：中央政策目录不存在: {self.central_dir}")

        # 省级政策
        if self.prov_dir.exists():
            # 遍历所有省份子目录
            prov_files = []
            for prov_subdir in self.prov_dir.iterdir():
                if prov_subdir.is_dir():
                    prov_json_files = list(prov_subdir.glob("*.json"))
                    prov_files.extend(prov_json_files)

            corpus_files.extend(prov_files)
            print(f"  省级政策文件: {len(prov_files)}个")
        else:
            print(f"  警告：省级政策目录不存在: {self.prov_dir}")

        if not corpus_files:
            print("\n❌ 错误：未找到任何政策文件")
            print(f"  请确保以下目录存在并包含JSON文件：")
            print(f"    - {self.central_dir}")
            print(f"    - {self.prov_dir}")
            return

        self.stats['total_files'] = len(corpus_files)
        print(f"\n  总计：{len(corpus_files)}个政策文件")

        # 处理文件
        print("\n【步骤2】提取和处理句子")
        print("-" * 80)

        all_sentences = []
        processed_count = 0

        for i, file_path in enumerate(corpus_files):
            sentences = self.process_policy_file(file_path)

            if sentences:
                all_sentences.extend(sentences)
                processed_count += 1

            # 进度显示
            if (i + 1) % 100 == 0:
                print(f"  已处理: {i+1}/{len(corpus_files)} 文件 "
                      f"(累计 {len(all_sentences)} 句子)")

        self.stats['total_docs'] = processed_count
        self.stats['total_sentences_raw'] = len(all_sentences)

        print(f"\n  ✓ 处理完成")
        print(f"    有效文档数: {processed_count}")
        print(f"    原始句子数: {len(all_sentences):,}")

        # 去重
        print("\n【步骤3】去重")
        print("-" * 80)

        # 使用set去重（保持插入顺序用dict）
        unique_sentences = list(dict.fromkeys(all_sentences))
        self.stats['total_sentences_filtered'] = len(all_sentences)
        self.stats['total_sentences_unique'] = len(unique_sentences)

        print(f"  去重前: {len(all_sentences):,} 句子")
        print(f"  去重后: {len(unique_sentences):,} 句子")
        print(f"  去重率: {(1 - len(unique_sentences)/len(all_sentences))*100:.1f}%")

        # 统计字符数
        total_chars = sum(len(s) for s in unique_sentences)
        self.stats['total_chars'] = total_chars

        # 保存
        print("\n【步骤4】保存语料")
        print("-" * 80)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_path, 'w', encoding='utf-8') as f:
            for sent in unique_sentences:
                f.write(sent + '\n')

        print(f"  ✓ 语料已保存到: {self.output_path}")
        print(f"    文件大小: {self.output_path.stat().st_size / 1024 / 1024:.2f} MB")

        # 词频统计（前50个高频词）
        print("\n【步骤5】语料统计")
        print("-" * 80)

        self._print_statistics(unique_sentences)

        # 最终报告
        print("\n" + "=" * 80)
        print("DAPT语料构建完成 ✓")
        print("=" * 80)
        print(f"\n统计摘要：")
        print(f"  政策文件数: {self.stats['total_files']:,}")
        print(f"  有效文档数: {self.stats['total_docs']:,}")
        print(f"  唯一句子数: {self.stats['total_sentences_unique']:,}")
        print(f"  总字符数: {self.stats['total_chars']:,}")
        print(f"  平均句长: {self.stats['total_chars'] / self.stats['total_sentences_unique']:.1f} 字符")

        # 质量检查
        if self.stats['total_sentences_unique'] < 50000:
            print(f"\n⚠️  警告：句子数（{self.stats['total_sentences_unique']:,}）少于推荐值（50,000）")
            print(f"  建议：收集更多政策数据或降低min_sent_length参数")
        else:
            print(f"\n✓ 语料规模符合要求（≥50k句子）")

    def _print_statistics(self, sentences: List[str], top_n: int = 50):
        """打印语料统计信息

        Args:
            sentences: 句子列表
            top_n: 显示前N个高频词
        """
        # 简单的词频统计（按字符）
        char_counter = Counter()
        for sent in sentences:
            # 只统计中文字符
            chinese_chars = re.findall(r'[\u4e00-\u9fff]', sent)
            char_counter.update(chinese_chars)

        print(f"  唯一中文字符数: {len(char_counter)}")
        print(f"\n  高频字符Top {top_n}:")

        for i, (char, count) in enumerate(char_counter.most_common(top_n)):
            if i % 10 == 0:
                print("  ", end='')
            print(f"{char}({count:,})", end='  ')
            if (i + 1) % 10 == 0:
                print()

        print()

        # 政策领域关键词检查
        policy_keywords = [
            '发展', '创新', '支持', '推进', '建设', '完善', '加强', '促进', '鼓励',
            '企业', '产业', '科技', '技术', '研发', '人才', '资金', '政策', '规划',
            '战略', '新兴', '高新', '智能', '数字', '绿色', '可持续'
        ]

        print(f"\n  政策领域关键词覆盖检查:")
        for keyword in policy_keywords:
            count = sum(1 for sent in sentences if keyword in sent)
            coverage = count / len(sentences) * 100
            print(f"    '{keyword}': {count:,}句 ({coverage:.1f}%)")


def main():
    """主函数"""
    builder = DAPTCorpusBuilder(
        central_dir="corpus/raw/policy_central",
        prov_dir="corpus/raw/policy_prov",
        output_path="data/dapt_corpus.txt",
        min_sent_length=10,
        max_sent_length=512
    )

    builder.build_corpus()


if __name__ == "__main__":
    main()
