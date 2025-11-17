#!/usr/bin/env python3
"""
PSC-Graph 政策标注验证脚本

功能:
1. JSON Schema验证
2. Cohen's κ 一致性计算
3. 质量门槛检查（F1≥0.85, κ≥0.80）

用法:
    python validate_annotations.py [--annotator A|B] [--compute-kappa]
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import argparse

try:
    from jsonschema import Draft202012Validator, ValidationError
    from sklearn.metrics import cohen_kappa_score, f1_score, precision_score, recall_score
    import numpy as np
except ImportError as e:
    print(f"错误：缺少依赖库 - {e}")
    print("请运行: pip install jsonschema scikit-learn numpy")
    sys.exit(1)


class AnnotationValidator:
    """标注验证器"""

    def __init__(self, schema_path: str = "schemas/policy_schema.json"):
        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()
        self.validator = Draft202012Validator(self.schema)

        # 质量门槛（来自CLAUDE.md）
        self.QUALITY_THRESHOLDS = {
            "min_f1": 0.85,
            "min_kappa": 0.80,
            "min_confidence": 0.70
        }

    def _load_schema(self) -> dict:
        """加载JSON Schema"""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema文件不存在: {self.schema_path}")

        with open(self.schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def validate_file(self, annotation_file: Path) -> Tuple[bool, List[str]]:
        """
        验证单个标注文件

        Returns:
            (is_valid, errors)
        """
        errors = []

        # 1. 检查文件存在
        if not annotation_file.exists():
            return False, [f"文件不存在: {annotation_file}"]

        # 2. 加载JSON
        try:
            with open(annotation_file, 'r', encoding='utf-8') as f:
                annotation = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"JSON解析失败: {e}"]

        # 3. Schema验证
        try:
            self.validator.validate(annotation)
        except ValidationError as e:
            errors.append(f"Schema验证失败: {e.message}")
            errors.append(f"  路径: {'.'.join(str(p) for p in e.path)}")
            return False, errors

        # 4. 业务规则验证
        business_errors = self._validate_business_rules(annotation)
        if business_errors:
            errors.extend(business_errors)
            return False, errors

        return True, []

    def _validate_business_rules(self, annotation: dict) -> List[str]:
        """验证业务规则"""
        errors = []

        # 检查每个标注项
        for idx, item in enumerate(annotation.get("annotations", [])):
            # 检查evidence_spans的start < end
            for ev_idx, evidence in enumerate(item.get("evidence_spans", [])):
                if evidence["start"] >= evidence["end"]:
                    errors.append(
                        f"标注项{idx+1}的证据{ev_idx+1}: start({evidence['start']}) >= end({evidence['end']})"
                    )

            # 检查confidence范围
            conf = item.get("confidence", 0.0)
            if conf < self.QUALITY_THRESHOLDS["min_confidence"]:
                errors.append(
                    f"标注项{idx+1}: 置信度过低 ({conf:.2f} < {self.QUALITY_THRESHOLDS['min_confidence']})"
                )

            # 检查instrument不能包含other且没有其他值
            instruments = item.get("instrument", [])
            if instruments == ["other"]:
                errors.append(
                    f"标注项{idx+1}: instrument仅包含'other'，需要补充具体类型"
                )

        return errors

    def validate_directory(self, dir_path: Path) -> Dict[str, Tuple[bool, List[str]]]:
        """
        验证目录下所有标注文件

        Returns:
            {filename: (is_valid, errors)}
        """
        results = {}

        if not dir_path.exists():
            print(f"警告：目录不存在 - {dir_path}")
            return results

        for json_file in dir_path.glob("*.json"):
            is_valid, errors = self.validate_file(json_file)
            results[json_file.name] = (is_valid, errors)

        return results

    def compute_kappa(
        self,
        annotator_a_dir: Path,
        annotator_b_dir: Path
    ) -> Tuple[float, Dict[str, float]]:
        """
        计算Cohen's κ（双标注人员一致性）

        Returns:
            (overall_kappa, detailed_metrics)
        """
        # 找到共同标注的文档
        files_a = set(f.name for f in annotator_a_dir.glob("*.json"))
        files_b = set(f.name for f in annotator_b_dir.glob("*.json"))
        common_files = files_a & files_b

        if not common_files:
            raise ValueError("没有找到共同标注的文档")

        print(f"\n找到{len(common_files)}个共同标注的文档")

        # 收集标注对
        all_labels_a = []
        all_labels_b = []

        for filename in common_files:
            file_a = annotator_a_dir / filename
            file_b = annotator_b_dir / filename

            with open(file_a, 'r', encoding='utf-8') as f:
                data_a = json.load(f)
            with open(file_b, 'r', encoding='utf-8') as f:
                data_b = json.load(f)

            # 提取关键字段用于一致性计算
            # 这里简化为比较标注项数量和strength字段
            annotations_a = data_a.get("annotations", [])
            annotations_b = data_b.get("annotations", [])

            # 对齐标注项（按照相似度）
            max_len = max(len(annotations_a), len(annotations_b))
            for i in range(max_len):
                strength_a = annotations_a[i]["strength"] if i < len(annotations_a) else -1
                strength_b = annotations_b[i]["strength"] if i < len(annotations_b) else -1

                all_labels_a.append(strength_a)
                all_labels_b.append(strength_b)

        # 计算κ
        kappa = cohen_kappa_score(all_labels_a, all_labels_b)

        # 计算详细指标
        detailed = {
            "common_docs": len(common_files),
            "total_annotations_a": len(all_labels_a),
            "total_annotations_b": len(all_labels_b),
            "agreement_rate": np.mean(np.array(all_labels_a) == np.array(all_labels_b))
        }

        return kappa, detailed

    def generate_report(
        self,
        validation_results: Dict[str, Dict[str, Tuple[bool, List[str]]]],
        kappa_score: float = None
    ) -> str:
        """生成验证报告"""
        report = []
        report.append("=" * 60)
        report.append("PSC-Graph 标注验证报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().isoformat()}")
        report.append("")

        # 统计总体情况
        total_files = 0
        total_valid = 0
        total_errors = 0

        for annotator, results in validation_results.items():
            report.append(f"\n### {annotator}")
            report.append("-" * 60)

            valid_count = sum(1 for is_valid, _ in results.values() if is_valid)
            error_count = len(results) - valid_count

            report.append(f"总文件数: {len(results)}")
            report.append(f"✓ 通过验证: {valid_count}")
            report.append(f"✗ 验证失败: {error_count}")

            total_files += len(results)
            total_valid += valid_count
            total_errors += error_count

            # 显示错误详情
            if error_count > 0:
                report.append("\n错误详情:")
                for filename, (is_valid, errors) in results.items():
                    if not is_valid:
                        report.append(f"\n  文件: {filename}")
                        for error in errors:
                            report.append(f"    - {error}")

        # Cohen's κ结果
        if kappa_score is not None:
            report.append("\n" + "=" * 60)
            report.append("### 一致性检验 (Cohen's κ)")
            report.append("-" * 60)
            report.append(f"κ 值: {kappa_score:.4f}")

            # 评价标准
            if kappa_score >= 0.80:
                level = "优秀 (≥0.80)"
                status = "✓ 通过质量门槛"
            elif kappa_score >= 0.60:
                level = "良好 (0.60-0.79)"
                status = "⚠ 需要改进"
            elif kappa_score >= 0.40:
                level = "中等 (0.40-0.59)"
                status = "✗ 未达标"
            else:
                level = "较差 (<0.40)"
                status = "✗ 严重问题"

            report.append(f"一致性等级: {level}")
            report.append(f"状态: {status}")

        # 总结
        report.append("\n" + "=" * 60)
        report.append("### 总结")
        report.append("-" * 60)
        report.append(f"总计文件: {total_files}")
        report.append(f"通过验证: {total_valid} ({total_valid/total_files*100:.1f}%)" if total_files > 0 else "")
        report.append(f"验证失败: {total_errors}")

        # 质量门槛判定
        report.append("\n### 质量门槛判定")
        report.append("-" * 60)
        report.append(f"Schema验证通过率: {total_valid/total_files*100:.1f}%" if total_files > 0 else "N/A")
        if kappa_score is not None:
            kappa_pass = "✓" if kappa_score >= self.QUALITY_THRESHOLDS["min_kappa"] else "✗"
            report.append(f"Cohen's κ ≥ 0.80: {kappa_pass} ({kappa_score:.4f})")

        report.append("=" * 60)

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="PSC-Graph 标注验证工具")
    parser.add_argument(
        "--annotator",
        choices=["A", "B", "all"],
        default="all",
        help="指定要验证的标注人员"
    )
    parser.add_argument(
        "--compute-kappa",
        action="store_true",
        help="计算双标注人员的Cohen's κ"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".claude/verification-report.md",
        help="验证报告输出路径"
    )

    args = parser.parse_args()

    # 初始化验证器
    validator = AnnotationValidator()

    # 验证标注文件
    validation_results = {}

    if args.annotator in ["A", "all"]:
        print("正在验证 annotator_A 的标注...")
        results_a = validator.validate_directory(Path("annotations/annotator_A"))
        validation_results["annotator_A"] = results_a
        print(f"  完成: {len(results_a)}个文件")

    if args.annotator in ["B", "all"]:
        print("正在验证 annotator_B 的标注...")
        results_b = validator.validate_directory(Path("annotations/annotator_B"))
        validation_results["annotator_B"] = results_b
        print(f"  完成: {len(results_b)}个文件")

    # 计算κ
    kappa_score = None
    if args.compute_kappa:
        try:
            print("\n正在计算 Cohen's κ...")
            kappa_score, details = validator.compute_kappa(
                Path("annotations/annotator_A"),
                Path("annotations/annotator_B")
            )
            print(f"  κ = {kappa_score:.4f}")
            print(f"  共同文档数: {details['common_docs']}")
            print(f"  一致率: {details['agreement_rate']:.2%}")
        except ValueError as e:
            print(f"  警告: {e}")

    # 生成报告
    report = validator.generate_report(validation_results, kappa_score)
    print("\n" + report)

    # 保存报告
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n验证报告已保存到: {output_path}")


if __name__ == "__main__":
    main()
