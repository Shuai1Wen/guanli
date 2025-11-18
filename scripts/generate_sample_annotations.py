#!/usr/bin/env python3
"""
PSC-Graph 示例标注生成脚本

基于已爬取的政策文档自动生成示例标注
注意：这是LLM辅助生成的示例，实际项目中需要人工复核
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple


class SampleAnnotationGenerator:
    """示例标注生成器"""

    def __init__(self):
        self.base_dir = Path('.')
        self.corpus_dir = self.base_dir / 'corpus/raw'
        self.output_dir = self.base_dir / 'annotations/annotator_A'
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_document(self, doc_path: Path) -> Dict:
        """加载文档"""
        with open(doc_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def extract_policy_tuples_from_content(self, content_text: str, doc_type: str) -> List[Dict]:
        """
        从文档内容中提取政策五元组（简化版）
        实际项目中应使用DAPT/TAPT微调的模型+RAG
        """
        tuples = []

        # 简单的关键词匹配和模式识别
        funding_keywords = ['资金', '补贴', '奖励', '经费', '支持']
        platform_keywords = ['平台', '载体', '空间', '基地', '中心']
        talent_keywords = ['人才', '引进', '团队']

        # 分段处理
        paragraphs = [p.strip() for p in content_text.split('\n') if len(p.strip()) > 20]

        for i, para in enumerate(paragraphs[:10]):  # 只处理前10段
            # 检测是否包含政策要素
            has_funding = any(kw in para for kw in funding_keywords)
            has_platform = any(kw in para for kw in platform_keywords)
            has_talent = any(kw in para for kw in talent_keywords)

            if has_funding or has_platform or has_talent:
                # 提取目标（简化处理）
                goal_match = re.search(r'(支持|鼓励|推动|促进|加强|提升|建设|完善)([^，。！]{5,50})', para)
                if goal_match:
                    goal = goal_match.group(0)

                    # 确定工具类型
                    instruments = []
                    if has_funding:
                        instruments.append("funding")
                    if has_platform:
                        instruments.append("platform")
                    if has_talent:
                        instruments.append("talent")

                    # 提取对象
                    actor_keywords = ['企业', '高校', '科研院所', '机构', '单位', '园区']
                    target_actor = "相关单位"
                    for keyword in actor_keywords:
                        if keyword in para:
                            target_actor = keyword
                            break

                    # 确定强度
                    strength = 1
                    if '要求' in para or '必须' in para or '应当' in para:
                        strength = 2
                    if '考核' in para or '问责' in para:
                        strength = 3

                    # 创建五元组
                    tuple_item = {
                        "goal": goal[:100],  # 限制长度
                        "instrument": instruments if instruments else ["other"],
                        "target_actor": target_actor,
                        "strength": strength,
                        "evidence_spans": [
                            {
                                "start": content_text.find(para),
                                "end": content_text.find(para) + len(para[:150]),
                                "from_doc": "policy" if doc_type == "省级政策" else "interpretation",
                                "text": para[:150] + "..." if len(para) > 150 else para
                            }
                        ],
                        "confidence": 0.75  # LLM辅助生成，置信度中等
                    }

                    tuples.append(tuple_item)

                    if len(tuples) >= 3:  # 每个文档最多提取3个五元组
                        break

        return tuples

    def generate_annotation(self, doc_path: Path) -> Dict:
        """生成单个文档的标注"""
        doc_data = self.load_document(doc_path)

        content = doc_data.get('content_text', '')
        doc_id = doc_data.get('doc_id')
        title = doc_data.get('title', '')
        url = doc_data.get('source_url', '')
        doc_type = doc_data.get('category', 'policy')

        # 提取五元组
        tuples = self.extract_policy_tuples_from_content(content, doc_type)

        if not tuples:
            return None

        # 构建标注对象
        annotation = {
            "doc_id": doc_id,
            "source_title": title,
            "source_url": url,
            "annotations": tuples,
            "annotator": "annotator_A",
            "annotated_at": datetime.now().isoformat() + "Z",
            "notes": "LLM辅助生成的示例标注（自动化脚本），需人工复核"
        }

        return annotation

    def generate_batch(self, doc_paths: List[Path], max_count: int = 10) -> int:
        """批量生成标注"""
        generated = 0

        for doc_path in doc_paths:
            if generated >= max_count:
                break

            print(f"正在处理: {doc_path.name}")

            try:
                annotation = self.generate_annotation(doc_path)

                if annotation:
                    output_file = self.output_dir / f"{annotation['doc_id']}_auto.json"

                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(annotation, f, ensure_ascii=False, indent=2)

                    print(f"  ✓ 已生成: {output_file.name}")
                    generated += 1
                else:
                    print(f"  ✗ 跳过（无有效标注）")

            except Exception as e:
                print(f"  ✗ 错误: {e}")
                continue

        return generated


def main():
    """主函数"""
    generator = SampleAnnotationGenerator()

    # 读取选中的文件列表
    selected_file = Path('corpus/samples/selected_for_annotation.txt')

    if not selected_file.exists():
        print("错误：未找到选中文件列表")
        return

    with open(selected_file, 'r', encoding='utf-8') as f:
        doc_paths = [Path(line.strip()) for line in f if line.strip()]

    print(f"找到 {len(doc_paths)} 个待标注文档")
    print("=" * 60)

    # 批量生成（跳过已标注的）
    count = generator.generate_batch(doc_paths[1:], max_count=8)  # 跳过第一个（已手动标注）

    print("=" * 60)
    print(f"完成！共生成 {count} 个标注文件")

    # 运行验证
    print("\n运行验证...")
    import subprocess
    result = subprocess.run(
        ['python3', 'scripts/validate_annotations.py', '--annotator', 'A'],
        capture_output=True,
        text=True
    )
    print(result.stdout)


if __name__ == "__main__":
    main()
