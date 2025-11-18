#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PSC-Graph 完整端到端演示脚本

功能：依次演示所有核心模块的完整工作流程
- 标注验证（Annotation Validation）
- 索引构建（Index Building）
- 证据检索（Evidence Retrieval）
- 异质图构建（Graph Building）
- HGT模型训练（Model Training）
- 校准与不确定性量化（Calibration）
- DID因果推断（Causal Inference）- 面板数据准备（Panel Preparation）

使用方法：
    python scripts/run_all_demos.py

作者：Claude Code
日期：2025-11-18
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime


class DemoRunner:
    """演示运行器：依次执行所有核心模块的演示"""

    def __init__(self, project_root: Path = None):
        """初始化

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = project_root or Path(__file__).parent.parent
        self.scripts_dir = self.project_root / 'scripts'

        # 演示脚本列表（按执行顺序）
        self.demos = [
            {
                'name': '标注验证',
                'script': 'validate_annotations.py',
                'description': '验证标注数据的完整性、一致性和质量',
                'required': False  # 可选
            },
            {
                'name': '索引构建',
                'script': 'build_index.py',
                'description': '构建BM25和FAISS混合检索索引',
                'required': True  # 必需
            },
            {
                'name': '证据检索演示',
                'script': 'retrieve_evidence.py',
                'description': '演示混合检索功能',
                'required': False
            },
            {
                'name': '异质图构建',
                'script': 'build_graph_pyg.py',
                'description': '从标注数据构建PyG异质图',
                'required': True
            },
            {
                'name': 'HGT模型训练',
                'script': 'train_hgt.py',
                'description': '训练Heterogeneous Graph Transformer模型',
                'required': False
            },
            {
                'name': '校准与不确定性量化',
                'script': 'calibrate_and_conformal.py',
                'description': '温度缩放校准和共形预测',
                'required': False
            },
            {
                'name': '面板数据准备',
                'script': 'prep_panel.py',
                'description': '准备DID因果推断所需的面板数据',
                'required': False
            },
            {
                'name': 'DID因果推断（需R环境）',
                'script': 'demo_did_workflow.py',
                'description': 'DID因果推断完整流程演示（Python模拟版）',
                'required': False
            }
        ]

    def print_header(self):
        """打印欢迎信息"""
        print("=" * 80)
        print(" " * 20 + "PSC-Graph 完整端到端演示")
        print("=" * 80)
        print(f"项目根目录: {self.project_root}")
        print(f"脚本目录: {self.scripts_dir}")
        print(f"演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()

    def run_demo(self, demo: dict) -> bool:
        """运行单个演示脚本

        Args:
            demo: 演示配置字典

        Returns:
            是否成功
        """
        print("\n" + "=" * 80)
        print(f"【{demo['name']}】")
        print("=" * 80)
        print(f"描述: {demo['description']}")
        print(f"脚本: {demo['script']}")
        print(f"必需: {'是' if demo['required'] else '否'}")
        print("-" * 80)

        script_path = self.scripts_dir / demo['script']

        if not script_path.exists():
            print(f"❌ 脚本不存在: {script_path}")
            if demo['required']:
                print("⚠️  这是必需的演示，流程将终止")
                return False
            else:
                print("⚠️  这是可选的演示，跳过并继续")
                return True

        try:
            # 执行脚本
            print(f"\n正在执行: python {script_path.relative_to(self.project_root)}")
            print("-" * 80)

            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self.project_root),
                capture_output=False,  # 直接输出到终端
                text=True,
                timeout=300  # 5分钟超时
            )

            print("-" * 80)

            if result.returncode == 0:
                print(f"✓ {demo['name']} 完成")
                return True
            else:
                print(f"❌ {demo['name']} 失败（返回码: {result.returncode}）")

                if demo['required']:
                    print("⚠️  这是必需的演示，流程将终止")
                    return False
                else:
                    print("⚠️  这是可选的演示，继续执行下一个")
                    return True

        except subprocess.TimeoutExpired:
            print(f"❌ {demo['name']} 执行超时（5分钟）")

            if demo['required']:
                print("⚠️  这是必需的演示，流程将终止")
                return False
            else:
                print("⚠️  这是可选的演示，继续执行下一个")
                return True

        except Exception as e:
            print(f"❌ 执行 {demo['name']} 时出错: {e}")

            if demo['required']:
                print("⚠️  这是必需的演示，流程将终止")
                return False
            else:
                print("⚠️  这是可选的演示，继续执行下一个")
                return True

    def run_all(self, skip_optional: bool = False):
        """运行所有演示

        Args:
            skip_optional: 是否跳过可选演示
        """
        self.print_header()

        # 统计信息
        total = len(self.demos)
        completed = 0
        failed = 0
        skipped = 0

        # 依次执行演示
        for i, demo in enumerate(self.demos, 1):
            print(f"\n[进度: {i}/{total}]")

            # 如果设置了跳过可选演示，且当前演示是可选的
            if skip_optional and not demo['required']:
                print(f"⏭️  跳过可选演示: {demo['name']}")
                skipped += 1
                continue

            # 运行演示
            success = self.run_demo(demo)

            if success:
                completed += 1
            else:
                failed += 1
                # 如果必需演示失败，终止流程
                if demo['required']:
                    print("\n" + "=" * 80)
                    print("⚠️  必需演示失败，终止流程")
                    print("=" * 80)
                    break

        # 打印总结
        self.print_summary(total, completed, failed, skipped)

    def print_summary(self, total: int, completed: int, failed: int, skipped: int):
        """打印总结信息

        Args:
            total: 总演示数
            completed: 完成数
            failed: 失败数
            skipped: 跳过数
        """
        print("\n" + "=" * 80)
        print(" " * 30 + "演示总结")
        print("=" * 80)
        print(f"总演示数: {total}")
        print(f"✓ 完成: {completed}")
        print(f"❌ 失败: {failed}")
        print(f"⏭️  跳过: {skipped}")
        print("-" * 80)

        if failed == 0 and completed > 0:
            print("🎉 所有执行的演示均已成功完成！")
        elif failed > 0:
            print("⚠️  部分演示失败，请查看上方日志排查问题")
        else:
            print("⚠️  没有执行任何演示")

        print("=" * 80)


def print_usage():
    """打印使用说明"""
    print("使用方法：")
    print("  python scripts/run_all_demos.py [选项]")
    print()
    print("选项：")
    print("  --skip-optional    仅运行必需的演示，跳过可选演示")
    print("  --help, -h         显示此帮助信息")
    print()
    print("示例：")
    print("  python scripts/run_all_demos.py")
    print("  python scripts/run_all_demos.py --skip-optional")


def main():
    """主函数"""
    # 解析命令行参数
    skip_optional = False

    if len(sys.argv) > 1:
        if '--help' in sys.argv or '-h' in sys.argv:
            print_usage()
            return 0
        if '--skip-optional' in sys.argv:
            skip_optional = True

    # 运行演示
    runner = DemoRunner()
    runner.run_all(skip_optional=skip_optional)

    return 0


if __name__ == '__main__':
    exit(main())
