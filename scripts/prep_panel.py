#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DID面板数据准备脚本

功能：
1. 从标注数据提取政策落地时点
2. 模拟或加载统计指标（GDP、R&D、专利等）
3. 生成标准DID面板数据格式
4. 验证面板数据质量

输出：
- data/panel_for_did.csv：标准DID面板数据
- data/policy_landing.csv：政策落地时点表

依赖：
- pandas
- numpy
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')


class PanelDataPreparer:
    """DID面板数据准备器"""

    def __init__(self, project_root: Path = None):
        """初始化

        参数:
            project_root: 项目根目录路径
        """
        self.project_root = project_root or Path(__file__).parent.parent
        self.annotations_dir = self.project_root / 'annotations' / 'annotator_A'
        self.data_dir = self.project_root / 'data'
        self.province_codes_path = self.data_dir / 'province_codes.csv'

        # 加载省份编码
        self.province_codes = self._load_province_codes()

        # 政策落地时点字典: {地区ID: 首次处理年份}
        self.policy_landing: Dict[str, int] = {}

    def _load_province_codes(self) -> pd.DataFrame:
        """加载省份编码表

        返回:
            省份编码DataFrame
        """
        if not self.province_codes_path.exists():
            raise FileNotFoundError(f"省份编码文件不存在: {self.province_codes_path}")

        df = pd.read_csv(self.province_codes_path, encoding='utf-8')
        print(f"✓ 加载省份编码表：{len(df)}个省份")
        return df

    def extract_policy_landing(self) -> pd.DataFrame:
        """从标注数据提取政策落地时点

        返回:
            政策落地时点DataFrame，包含列：region_id, region_name, first_treated_year
        """
        print("\n=== 提取政策落地时点 ===")

        policy_events = []

        # 遍历所有标注文件
        if not self.annotations_dir.exists():
            print(f"警告：标注目录不存在: {self.annotations_dir}")
            print("将使用示例政策时点数据")
            return self._generate_example_policy_landing()

        json_files = list(self.annotations_dir.glob('*.json'))
        print(f"找到 {len(json_files)} 个标注文件")

        for json_file in json_files:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 提取region和timeframe
            region_info = data.get('region', {})
            timeframe = data.get('timeframe', {})

            if not region_info or not timeframe:
                continue

            region_name = region_info.get('name', '')
            admin_code = region_info.get('admin_code', '')
            effective_date = timeframe.get('effective_date', '')

            if effective_date:
                try:
                    year = int(effective_date.split('-')[0])
                    policy_events.append({
                        'region_id': admin_code[:2] if admin_code else '',
                        'region_name': region_name,
                        'policy_year': year,
                        'effective_date': effective_date
                    })
                except (ValueError, IndexError) as e:
                    print(f"  警告：解析日期失败 '{effective_date}': {e}")

        if not policy_events:
            print("警告：未从标注中提取到政策时点，使用示例数据")
            return self._generate_example_policy_landing()

        # 汇总：每个地区的首次处理年份
        df = pd.DataFrame(policy_events)
        landing = df.groupby(['region_id', 'region_name']).agg({
            'policy_year': 'min'
        }).reset_index()
        landing.columns = ['region_id', 'region_name', 'first_treated_year']

        print(f"✓ 提取到 {len(landing)} 个地区的政策落地时点")
        print(landing.head())

        return landing

    def _generate_example_policy_landing(self) -> pd.DataFrame:
        """生成示例政策落地时点（用于测试）

        返回:
            示例政策落地DataFrame
        """
        # 示例：部分省份在不同年份开始政策试点
        examples = [
            {'region_id': '11', 'region_name': '北京', 'first_treated_year': 2015},
            {'region_id': '44', 'region_name': '广东', 'first_treated_year': 2016},
            {'region_id': '31', 'region_name': '上海', 'first_treated_year': 2016},
            {'region_id': '33', 'region_name': '浙江', 'first_treated_year': 2017},
            {'region_id': '32', 'region_name': '江苏', 'first_treated_year': 2017},
            # 其他省份作为对照组（never treated, g=0）
        ]

        return pd.DataFrame(examples)

    def generate_simulated_panel(
        self,
        landing: pd.DataFrame,
        start_year: int = 2010,
        end_year: int = 2022
    ) -> pd.DataFrame:
        """生成模拟面板数据（用于测试DID流程）

        参数:
            landing: 政策落地时点DataFrame
            start_year: 面板起始年份
            end_year: 面板结束年份

        返回:
            完整面板数据DataFrame
        """
        print("\n=== 生成模拟面板数据 ===")
        print(f"时间跨度: {start_year}-{end_year}")

        # 所有省份（来自province_codes）
        regions = self.province_codes[['province_name', 'adcode_prov']].copy()
        regions.columns = ['region_name', 'region_id']
        regions['region_id'] = regions['region_id'].astype(str).str.zfill(2)

        # 合并政策时点信息
        regions = regions.merge(
            landing[['region_id', 'first_treated_year']],
            on='region_id',
            how='left'
        )

        # 未处理地区的g设为0
        regions['first_treated_year'] = regions['first_treated_year'].fillna(0).astype(int)

        # 构建面板
        years = list(range(start_year, end_year + 1))
        panel_data = []

        np.random.seed(42)  # 确保可重复性

        for _, region in regions.iterrows():
            region_id = region['region_id']
            region_name = region['region_name']
            g = region['first_treated_year']

            # 地区固定效应（随机基准水平）
            region_fe = np.random.uniform(0.05, 0.15)

            for year in years:
                # 是否已处理
                treated = 1 if (g > 0 and year >= g) else 0

                # 模拟结果变量（例如：GDP增长率）
                # 基准增长率 + 地区固定效应 + 年份趋势 + 政策效应 + 噪声
                time_trend = (year - start_year) * 0.002
                policy_effect = 0.03 if treated else 0  # 真实政策效应：3个百分点
                noise = np.random.normal(0, 0.01)

                y = 0.06 + region_fe + time_trend + policy_effect + noise

                # 控制变量
                # 产业结构（第二产业占比）
                industry_share = 0.40 + np.random.uniform(-0.05, 0.05)

                # 人口规模（对数）
                pop_log = np.random.uniform(7.5, 9.0)

                # R&D强度（研发支出/GDP）
                rd_intensity = 0.02 + np.random.uniform(-0.005, 0.01)

                panel_data.append({
                    'id': region_id,
                    'region_name': region_name,
                    'time': year,
                    'y': y,
                    'g': g,
                    'treat': treated,
                    'industry_share': industry_share,
                    'pop_log': pop_log,
                    'rd_intensity': rd_intensity
                })

        df = pd.DataFrame(panel_data)
        print(f"✓ 生成面板数据：{len(df)}行（{len(regions)}个地区 × {len(years)}年）")

        return df

    def validate_panel(self, panel: pd.DataFrame) -> bool:
        """验证面板数据质量

        参数:
            panel: 面板数据DataFrame

        返回:
            是否通过验证
        """
        print("\n=== 验证面板数据 ===")

        errors = []

        # 检查必须字段
        required_cols = ['id', 'time', 'y', 'g', 'treat']
        missing = set(required_cols) - set(panel.columns)
        if missing:
            errors.append(f"缺少必需列: {missing}")

        # 检查是否为平衡面板
        id_counts = panel.groupby('id')['time'].count()
        if id_counts.nunique() > 1:
            errors.append(f"非平衡面板：不同地区的时间点数量不一致")
        else:
            print(f"✓ 平衡面板：每个地区 {id_counts.iloc[0]} 个时间点")

        # 检查时间范围
        time_range = (panel['time'].min(), panel['time'].max())
        print(f"✓ 时间范围: {time_range[0]}-{time_range[1]}")

        # 检查处理组数量
        treated_ids = panel[panel['g'] > 0]['id'].unique()
        control_ids = panel[panel['g'] == 0]['id'].unique()
        print(f"✓ 处理组: {len(treated_ids)} 个地区")
        print(f"✓ 对照组: {len(control_ids)} 个地区")

        # 检查g的分布
        g_dist = panel.groupby('id')['g'].first().value_counts().sort_index()
        print("\n处理时点分布:")
        for g_val, count in g_dist.items():
            if g_val == 0:
                print(f"  g=0 (never treated): {count} 个地区")
            else:
                print(f"  g={int(g_val)}: {count} 个地区")

        # 检查treat的一致性
        inconsistent = panel.groupby(['id', 'time']).apply(
            lambda x: (x['treat'] == ((x['g'] > 0) & (x['time'] >= x['g']))).all()
        )
        if not inconsistent.all():
            errors.append("treat变量与g和time不一致")
        else:
            print("✓ treat变量与g和time一致")

        # 检查缺失值
        na_counts = panel[required_cols].isna().sum()
        if na_counts.any():
            errors.append(f"存在缺失值:\n{na_counts[na_counts > 0]}")
        else:
            print("✓ 必需列无缺失值")

        if errors:
            print("\n❌ 验证失败:")
            for err in errors:
                print(f"  - {err}")
            return False
        else:
            print("\n✅ 面板数据验证通过")
            return True

    def save_panel_data(
        self,
        panel: pd.DataFrame,
        landing: pd.DataFrame,
        output_panel_path: Path = None,
        output_landing_path: Path = None
    ):
        """保存面板数据和政策时点表

        参数:
            panel: 面板数据DataFrame
            landing: 政策落地时点DataFrame
            output_panel_path: 面板数据输出路径
            output_landing_path: 政策时点输出路径
        """
        if output_panel_path is None:
            output_panel_path = self.data_dir / 'panel_for_did.csv'
        if output_landing_path is None:
            output_landing_path = self.data_dir / 'policy_landing.csv'

        # 保存面板数据
        panel.to_csv(output_panel_path, index=False, encoding='utf-8')
        print(f"\n✓ 保存面板数据: {output_panel_path}")
        print(f"  行数: {len(panel)}")
        print(f"  列数: {len(panel.columns)}")

        # 保存政策时点
        landing.to_csv(output_landing_path, index=False, encoding='utf-8')
        print(f"✓ 保存政策时点: {output_landing_path}")
        print(f"  行数: {len(landing)}")

    def run(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """执行完整的面板数据准备流程

        返回:
            (panel_data, policy_landing) 元组
        """
        print("=" * 60)
        print("DID面板数据准备")
        print("=" * 60)

        # 1. 提取政策落地时点
        landing = self.extract_policy_landing()

        # 2. 生成模拟面板数据
        panel = self.generate_simulated_panel(landing)

        # 3. 验证面板数据
        if not self.validate_panel(panel):
            raise ValueError("面板数据验证失败")

        # 4. 保存数据
        self.save_panel_data(panel, landing)

        print("\n" + "=" * 60)
        print("面板数据准备完成")
        print("=" * 60)

        return panel, landing


def main():
    """主函数"""
    preparer = PanelDataPreparer()
    panel, landing = preparer.run()

    # 输出数据摘要
    print("\n面板数据摘要:")
    print(panel.head(10))
    print("\n描述性统计:")
    print(panel[['y', 'industry_share', 'pop_log', 'rd_intensity']].describe())


if __name__ == '__main__':
    main()
