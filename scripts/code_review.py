#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PSC-Graph代码审查脚本

功能：
1. 自动检测常见代码问题
2. 检查维度匹配
3. 检查内存优化机会
4. 生成审查报告
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Tuple
import re


class CodeReviewer:
    """代码审查器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.issues = []
        self.warnings = []
        self.suggestions = []

    def review_python_file(self, file_path: Path) -> Dict:
        """审查单个Python文件"""
        print(f"\n审查: {file_path.relative_to(self.project_root)}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        issues = {
            'file': str(file_path),
            'errors': [],
            'warnings': [],
            'suggestions': []
        }

        # 检查1: 过大的函数
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('def '):
                func_lines = self._count_function_lines(lines, i-1)
                if func_lines > 100:
                    issues['warnings'].append(
                        f"行{i}: 函数过长({func_lines}行)，建议拆分"
                    )

        # 检查2: 内存优化机会
        # 检查是否有大列表/DataFrame全量加载
        if 'pd.read_csv' in content and 'chunksize' not in content:
            issues['suggestions'].append(
                "建议对大文件使用chunksize分块读取以降低内存占用"
            )

        # 检查3: 异常处理
        try_count = content.count('try:')
        except_count = content.count('except')
        if try_count > 0 and except_count < try_count:
            issues['errors'].append(
                f"try-except不匹配: {try_count}个try, {except_count}个except"
            )

        # 检查4: 硬编码路径
        hardcoded_paths = re.findall(r'["\'][/\\][^"\']+["\']', content)
        if hardcoded_paths:
            issues['warnings'].append(
                f"发现{len(hardcoded_paths)}处可能的硬编码路径"
            )

        # 检查5: TODO/FIXME
        todos = [i+1 for i, line in enumerate(lines) if 'TODO' in line or 'FIXME' in line]
        if todos:
            issues['warnings'].append(
                f"发现{len(todos)}处TODO/FIXME标记: {todos}"
            )

        # 检查6: print调试语句（应该使用logging）
        debug_prints = [i+1 for i, line in enumerate(lines) if re.match(r'\s*print\s*\(.*#.*debug', line, re.I)]
        if debug_prints:
            issues['suggestions'].append(
                f"行{debug_prints}: 发现调试print语句，建议使用logging"
            )

        return issues

    def _count_function_lines(self, lines: List[str], start_idx: int) -> int:
        """计算函数行数"""
        count = 0
        indent_level = len(lines[start_idx]) - len(lines[start_idx].lstrip())

        for i in range(start_idx, len(lines)):
            line = lines[i]
            if line.strip() and not line.strip().startswith('#'):
                curr_indent = len(line) - len(line.lstrip())
                if i > start_idx and curr_indent <= indent_level and line.strip():
                    break
            count += 1

        return count

    def check_dimension_compatibility(self, file_path: Path) -> List[str]:
        """检查维度兼容性问题"""
        issues = []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查图学习脚本的维度
        if 'build_graph' in file_path.name or 'train_hgt' in file_path.name:
            # 检查特征维度声明
            dims = re.findall(r'(\d+)\s*维', content)
            if dims:
                unique_dims = set(dims)
                if len(unique_dims) > 2:
                    issues.append(
                        f"发现多种特征维度: {unique_dims}，请确认异质图节点维度是否正确"
                    )

        return issues

    def generate_report(self, output_path: Path):
        """生成审查报告"""
        # Python脚本
        python_files = [
            'scripts/prep_panel.py',
            'scripts/run_did_from_python.py',
            'scripts/build_graph_pyg.py',
            'scripts/train_hgt.py',
            'scripts/build_index.py',
            'scripts/retrieve_evidence.py',
            'scripts/calibrate_and_conformal.py'
        ]

        results = []
        for py_file in python_files:
            file_path = self.project_root / py_file
            if file_path.exists():
                result = self.review_python_file(file_path)
                dim_issues = self.check_dimension_compatibility(file_path)
                if dim_issues:
                    result['warnings'].extend(dim_issues)
                results.append(result)

        # 生成报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# PSC-Graph代码审查报告\n\n")
            f.write(f"**生成时间**: {pd.Timestamp.now()}\n\n")
            f.write("---\n\n")

            for result in results:
                f.write(f"## {Path(result['file']).name}\n\n")

                if result['errors']:
                    f.write("### ❌ 错误\n\n")
                    for err in result['errors']:
                        f.write(f"- {err}\n")
                    f.write("\n")

                if result['warnings']:
                    f.write("### ⚠️ 警告\n\n")
                    for warn in result['warnings']:
                        f.write(f"- {warn}\n")
                    f.write("\n")

                if result['suggestions']:
                    f.write("### 💡 建议\n\n")
                    for sug in result['suggestions']:
                        f.write(f"- {sug}\n")
                    f.write("\n")

                if not (result['errors'] or result['warnings'] or result['suggestions']):
                    f.write("✅ 无明显问题\n\n")

                f.write("---\n\n")


if __name__ == '__main__':
    import pandas as pd

    reviewer = CodeReviewer()
    output = Path('.claude/code-review-auto.md')
    reviewer.generate_report(output)
    print(f"\n✓ 审查报告已生成: {output}")
