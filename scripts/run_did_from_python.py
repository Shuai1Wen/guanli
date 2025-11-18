#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python-R桥接脚本：DID因果推断完整流程

功能：
1. 调用prep_panel.py准备面板数据
2. 通过subprocess调用R脚本执行DID估计
3. 加载R输出结果并进行后处理
4. 提供统一的Python接口

输出：
- results/did_csatt_event.csv：CS-ATT事件研究结果
- results/did_csatt_overall.csv：CS-ATT总体ATT
- results/did_sunab_coefs.csv：Sun-Abraham系数
- results/did_bjs_overall.csv：BJS总体ATT
- results/did_summary.json：汇总结果

依赖：
- pandas
- subprocess
- R环境（需安装did, fixest, didimputation包）
"""

import json
import subprocess
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings
import sys

warnings.filterwarnings('ignore')


class DIDRunner:
    """DID因果推断运行器（Python-R桥接）"""

    def __init__(self, project_root: Path = None):
        """初始化

        参数:
            project_root: 项目根目录路径
        """
        self.project_root = project_root or Path(__file__).parent.parent
        self.scripts_dir = self.project_root / 'scripts'
        self.data_dir = self.project_root / 'data'
        self.results_dir = self.project_root / 'results'

        # 确保results目录存在
        self.results_dir.mkdir(exist_ok=True)

        # 关键路径
        self.panel_path = self.data_dir / 'panel_for_did.csv'
        self.r_script_path = self.scripts_dir / 'did_run.R'

    def prepare_panel_data(self, force_regenerate: bool = False) -> pd.DataFrame:
        """准备DID面板数据

        参数:
            force_regenerate: 是否强制重新生成（即使文件已存在）

        返回:
            面板数据DataFrame
        """
        print("\n=== 步骤1: 准备DID面板数据 ===")

        if self.panel_path.exists() and not force_regenerate:
            print(f"✓ 面板数据已存在: {self.panel_path}")
            panel = pd.read_csv(self.panel_path, encoding='utf-8')
            print(f"  行数: {len(panel)}, 列数: {len(panel.columns)}")
            return panel

        # 调用prep_panel.py
        print("调用prep_panel.py生成面板数据...")
        prep_script = self.scripts_dir / 'prep_panel.py'

        if not prep_script.exists():
            raise FileNotFoundError(f"面板准备脚本不存在: {prep_script}")

        try:
            result = subprocess.run(
                [sys.executable, str(prep_script)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                print("❌ prep_panel.py执行失败")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                raise RuntimeError(f"prep_panel.py返回非零状态: {result.returncode}")

            print("✓ prep_panel.py执行成功")
            print(result.stdout)

            # 加载生成的面板数据
            if not self.panel_path.exists():
                raise FileNotFoundError(f"面板数据文件未生成: {self.panel_path}")

            panel = pd.read_csv(self.panel_path, encoding='utf-8')
            print(f"✓ 加载面板数据: {len(panel)}行 × {len(panel.columns)}列")

            return panel

        except subprocess.TimeoutExpired:
            raise RuntimeError("prep_panel.py执行超时（120秒）")
        except Exception as e:
            raise RuntimeError(f"执行prep_panel.py时出错: {e}")

    def check_r_environment(self) -> Dict[str, bool]:
        """检查R环境和所需包

        返回:
            环境检查结果字典
        """
        print("\n=== 步骤2: 检查R环境 ===")

        checks = {
            'r_installed': False,
            'did_package': False,
            'fixest_package': False,
            'didimputation_package': False
        }

        # 检查R是否安装
        try:
            result = subprocess.run(
                ['Rscript', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                checks['r_installed'] = True
                print("✓ R已安装")
                version_info = result.stderr.strip().split('\n')[0]
                print(f"  {version_info}")
            else:
                print("❌ R未正确安装")
                return checks
        except FileNotFoundError:
            print("❌ 找不到Rscript命令，请确保R已安装并在PATH中")
            return checks
        except Exception as e:
            print(f"❌ 检查R安装时出错: {e}")
            return checks

        # 检查必需的R包
        required_packages = ['did', 'fixest', 'didimputation']
        check_script = f"""
        packages <- c({', '.join([f'"{pkg}"' for pkg in required_packages])})
        installed <- packages %in% rownames(installed.packages())
        cat(paste(packages, installed, sep=':', collapse='\\n'))
        """

        try:
            result = subprocess.run(
                ['Rscript', '-e', check_script],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        pkg, status = line.split(':')
                        if status.strip().upper() == 'TRUE':
                            checks[f'{pkg}_package'] = True
                            print(f"✓ R包 '{pkg}' 已安装")
                        else:
                            print(f"❌ R包 '{pkg}' 未安装")
            else:
                print("❌ 检查R包时出错")
                print("STDERR:", result.stderr)

        except Exception as e:
            print(f"❌ 检查R包时出错: {e}")

        return checks

    def install_r_packages(self, packages: List[str]):
        """安装缺失的R包

        参数:
            packages: 需要安装的包列表
        """
        if not packages:
            return

        print(f"\n正在安装R包: {', '.join(packages)}")
        install_script = f"""
        install.packages(
            c({', '.join([f'"{pkg}"' for pkg in packages])}),
            repos='https://cloud.r-project.org/',
            dependencies=TRUE,
            quiet=FALSE
        )
        """

        try:
            result = subprocess.run(
                ['Rscript', '-e', install_script],
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            if result.returncode == 0:
                print("✓ R包安装成功")
            else:
                print("❌ R包安装失败")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                raise RuntimeError("R包安装失败")

        except subprocess.TimeoutExpired:
            raise RuntimeError("R包安装超时（10分钟）")
        except Exception as e:
            raise RuntimeError(f"安装R包时出错: {e}")

    def run_r_did(
        self,
        panel_path: Path,
        output_dir: Path,
        estimators: List[str] = None
    ) -> Dict[str, Path]:
        """执行R DID估计

        参数:
            panel_path: 面板数据路径
            output_dir: 输出目录
            estimators: 估计器列表（默认: ['csatt', 'sunab', 'bjs']）

        返回:
            输出文件路径字典
        """
        print("\n=== 步骤3: 执行R DID估计 ===")

        if estimators is None:
            estimators = ['csatt', 'sunab', 'bjs']

        if not self.r_script_path.exists():
            raise FileNotFoundError(f"R脚本不存在: {self.r_script_path}")

        if not panel_path.exists():
            raise FileNotFoundError(f"面板数据不存在: {panel_path}")

        # 构建R命令
        # 向R脚本传递参数：面板路径、输出目录、估计器
        r_cmd = [
            'Rscript',
            str(self.r_script_path),
            str(panel_path),
            str(output_dir),
            ','.join(estimators)
        ]

        print(f"执行命令: {' '.join(r_cmd)}")

        try:
            result = subprocess.run(
                r_cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            print("\n--- R脚本输出 ---")
            print(result.stdout)

            if result.stderr:
                print("\n--- R脚本警告/错误 ---")
                print(result.stderr)

            if result.returncode != 0:
                raise RuntimeError(f"R脚本返回非零状态: {result.returncode}")

            print("✓ R DID估计完成")

            # 收集输出文件
            output_files = {}
            for estimator in estimators:
                if estimator == 'csatt':
                    output_files['csatt_event'] = output_dir / 'did_csatt_event.csv'
                    output_files['csatt_overall'] = output_dir / 'did_csatt_overall.csv'
                elif estimator == 'sunab':
                    output_files['sunab_coefs'] = output_dir / 'did_sunab_coefs.csv'
                elif estimator == 'bjs':
                    output_files['bjs_overall'] = output_dir / 'did_bjs_overall.csv'

            # 检查文件是否生成
            missing = [name for name, path in output_files.items() if not path.exists()]
            if missing:
                print(f"警告：以下输出文件未生成: {', '.join(missing)}")

            return output_files

        except subprocess.TimeoutExpired:
            raise RuntimeError("R脚本执行超时（5分钟）")
        except Exception as e:
            raise RuntimeError(f"执行R脚本时出错: {e}")

    def load_did_results(self, output_files: Dict[str, Path]) -> Dict[str, pd.DataFrame]:
        """加载DID估计结果

        参数:
            output_files: 输出文件路径字典

        返回:
            结果DataFrame字典
        """
        print("\n=== 步骤4: 加载DID估计结果 ===")

        results = {}

        for name, path in output_files.items():
            if not path.exists():
                print(f"⚠ 文件不存在: {name} ({path})")
                continue

            try:
                df = pd.read_csv(path, encoding='utf-8')
                results[name] = df
                print(f"✓ 加载 {name}: {len(df)}行 × {len(df.columns)}列")
            except Exception as e:
                print(f"❌ 加载 {name} 失败: {e}")

        return results

    def summarize_results(self, results: Dict[str, pd.DataFrame]) -> Dict:
        """汇总DID估计结果

        参数:
            results: 结果DataFrame字典

        返回:
            汇总结果字典
        """
        print("\n=== 步骤5: 汇总结果 ===")

        summary = {
            'estimators_run': list(results.keys()),
            'csatt': {},
            'sunab': {},
            'bjs': {}
        }

        # CS-ATT汇总
        if 'csatt_event' in results:
            event_df = results['csatt_event']
            summary['csatt']['event_study'] = {
                'num_periods': len(event_df),
                'significant_periods': int((event_df['p_value'] < 0.05).sum()) if 'p_value' in event_df.columns else None,
                'avg_att': float(event_df['att'].mean()) if 'att' in event_df.columns else None
            }
            print(f"✓ CS-ATT事件研究: {len(event_df)}个时间窗口")

        if 'csatt_overall' in results:
            overall_df = results['csatt_overall']
            if len(overall_df) > 0:
                summary['csatt']['overall'] = {
                    'att': float(overall_df['att'].iloc[0]) if 'att' in overall_df.columns else None,
                    'se': float(overall_df['se'].iloc[0]) if 'se' in overall_df.columns else None,
                    'p_value': float(overall_df['p_value'].iloc[0]) if 'p_value' in overall_df.columns else None
                }
                print(f"✓ CS-ATT总体ATT: {summary['csatt']['overall'].get('att', 'N/A')}")

        # Sun-Abraham汇总
        if 'sunab_coefs' in results:
            sunab_df = results['sunab_coefs']
            summary['sunab'] = {
                'num_cohorts': len(sunab_df),
                'significant_cohorts': int((sunab_df['p_value'] < 0.05).sum()) if 'p_value' in sunab_df.columns else None
            }
            print(f"✓ Sun-Abraham: {len(sunab_df)}个队列×时间系数")

        # BJS汇总
        if 'bjs_overall' in results:
            bjs_df = results['bjs_overall']
            if len(bjs_df) > 0:
                summary['bjs'] = {
                    'att': float(bjs_df['att'].iloc[0]) if 'att' in bjs_df.columns else None,
                    'se': float(bjs_df['se'].iloc[0]) if 'se' in bjs_df.columns else None,
                    'p_value': float(bjs_df['p_value'].iloc[0]) if 'p_value' in bjs_df.columns else None
                }
                print(f"✓ BJS总体ATT: {summary['bjs'].get('att', 'N/A')}")

        return summary

    def save_summary(self, summary: Dict, output_path: Path):
        """保存汇总结果为JSON

        参数:
            summary: 汇总结果字典
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n✓ 保存汇总结果: {output_path}")

    def validate_consistency(self, results: Dict[str, pd.DataFrame]) -> Dict:
        """验证三个估计器的一致性

        参数:
            results: 结果DataFrame字典

        返回:
            一致性检查结果
        """
        print("\n=== 步骤6: 一致性验证 ===")

        validation = {
            'direction_consistency': None,
            'significance_consistency': None,
            'warnings': []
        }

        # 提取总体ATT估计
        atts = {}

        if 'csatt_overall' in results and len(results['csatt_overall']) > 0:
            csatt_df = results['csatt_overall']
            if 'att' in csatt_df.columns:
                atts['csatt'] = {
                    'att': float(csatt_df['att'].iloc[0]),
                    'p_value': float(csatt_df['p_value'].iloc[0]) if 'p_value' in csatt_df.columns else None
                }

        if 'bjs_overall' in results and len(results['bjs_overall']) > 0:
            bjs_df = results['bjs_overall']
            if 'att' in bjs_df.columns:
                atts['bjs'] = {
                    'att': float(bjs_df['att'].iloc[0]),
                    'p_value': float(bjs_df['p_value'].iloc[0]) if 'p_value' in bjs_df.columns else None
                }

        if len(atts) < 2:
            validation['warnings'].append("可用的总体ATT估计少于2个，无法进行一致性检查")
            print("⚠ 可用的总体ATT估计不足，跳过一致性检查")
            return validation

        # 检查方向一致性（符号）
        signs = [np.sign(v['att']) for v in atts.values()]
        if len(set(signs)) == 1:
            validation['direction_consistency'] = True
            print(f"✓ 方向一致性: 所有估计器符号一致 ({signs[0]:+.0f})")
        else:
            validation['direction_consistency'] = False
            validation['warnings'].append(f"方向不一致: {atts}")
            print(f"❌ 方向一致性: 估计器符号不一致 {atts}")

        # 检查显著性一致性
        significances = [v['p_value'] < 0.05 if v['p_value'] is not None else None for v in atts.values()]
        significances = [s for s in significances if s is not None]

        if len(significances) >= 2:
            if all(significances) or not any(significances):
                validation['significance_consistency'] = True
                print(f"✓ 显著性一致性: 所有估计器显著性一致")
            else:
                validation['significance_consistency'] = False
                validation['warnings'].append(f"显著性不一致: {atts}")
                print(f"⚠ 显著性一致性: 部分估计器显著，部分不显著")

        return validation

    def run(
        self,
        force_regenerate_panel: bool = False,
        auto_install_r_packages: bool = True,
        estimators: List[str] = None
    ) -> Tuple[Dict[str, pd.DataFrame], Dict]:
        """执行完整的DID流程

        参数:
            force_regenerate_panel: 是否强制重新生成面板数据
            auto_install_r_packages: 是否自动安装缺失的R包
            estimators: 估计器列表（默认: ['csatt', 'sunab', 'bjs']）

        返回:
            (results, summary) 元组
        """
        print("=" * 60)
        print("DID因果推断完整流程 (Python-R桥接)")
        print("=" * 60)

        # 步骤1: 准备面板数据
        panel = self.prepare_panel_data(force_regenerate=force_regenerate_panel)

        # 步骤2: 检查R环境
        env_checks = self.check_r_environment()

        if not env_checks['r_installed']:
            raise RuntimeError("R未安装，请先安装R环境")

        # 检查R包并自动安装
        missing_packages = []
        for pkg in ['did', 'fixest', 'didimputation']:
            if not env_checks[f'{pkg}_package']:
                missing_packages.append(pkg)

        if missing_packages:
            if auto_install_r_packages:
                self.install_r_packages(missing_packages)
            else:
                raise RuntimeError(
                    f"缺少R包: {', '.join(missing_packages)}\n"
                    f"请在R中运行: install.packages(c({', '.join([f'\"{p}\"' for p in missing_packages])}))"
                )

        # 步骤3: 执行R DID估计
        output_files = self.run_r_did(
            panel_path=self.panel_path,
            output_dir=self.results_dir,
            estimators=estimators
        )

        # 步骤4: 加载结果
        results = self.load_did_results(output_files)

        # 步骤5: 汇总结果
        summary = self.summarize_results(results)

        # 步骤6: 一致性验证
        validation = self.validate_consistency(results)
        summary['validation'] = validation

        # 保存汇总
        summary_path = self.results_dir / 'did_summary.json'
        self.save_summary(summary, summary_path)

        print("\n" + "=" * 60)
        print("DID流程完成")
        print("=" * 60)

        return results, summary


def main():
    """主函数"""
    runner = DIDRunner()

    try:
        results, summary = runner.run(
            force_regenerate_panel=False,
            auto_install_r_packages=True,
            estimators=['csatt', 'sunab', 'bjs']
        )

        # 输出关键结果
        print("\n" + "=" * 60)
        print("关键结果摘要")
        print("=" * 60)

        if 'csatt' in summary and 'overall' in summary['csatt']:
            csatt = summary['csatt']['overall']
            print(f"\nCS-ATT总体效应:")
            print(f"  ATT: {csatt.get('att', 'N/A'):.4f}")
            print(f"  标准误: {csatt.get('se', 'N/A'):.4f}")
            print(f"  p值: {csatt.get('p_value', 'N/A'):.4f}")

        if 'bjs' in summary:
            bjs = summary['bjs']
            print(f"\nBJS总体效应:")
            print(f"  ATT: {bjs.get('att', 'N/A'):.4f}")
            print(f"  标准误: {bjs.get('se', 'N/A'):.4f}")
            print(f"  p值: {bjs.get('p_value', 'N/A'):.4f}")

        if 'validation' in summary:
            val = summary['validation']
            print(f"\n一致性检查:")
            print(f"  方向一致性: {val.get('direction_consistency', 'N/A')}")
            print(f"  显著性一致性: {val.get('significance_consistency', 'N/A')}")
            if val.get('warnings'):
                print(f"  警告: {len(val['warnings'])}项")
                for w in val['warnings']:
                    print(f"    - {w}")

    except Exception as e:
        print(f"\n❌ 流程执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
