#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DID因果推断工作流演示脚本

功能：
1. 加载示例面板数据
2. 展示面板数据统计
3. 模拟DID估计流程（无需R环境）
4. 展示一致性验证逻辑
5. 生成可视化报告

使用：python3 scripts/demo_did_workflow.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')


def main():
    """主演示函数"""
    print("=" * 70)
    print("DID因果推断工作流演示")
    print("=" * 70)

    project_root = Path(__file__).parent.parent
    panel_path = project_root / 'data' / 'panel_for_did.csv'

    # 步骤1: 加载面板数据
    print("\n【步骤1】 加载面板数据")
    print("-" * 70)

    if not panel_path.exists():
        print(f"❌ 面板数据不存在: {panel_path}")
        print("请先运行: python3 scripts/prep_panel.py")
        return 1

    panel = pd.read_csv(panel_path, encoding='utf-8')
    print(f"✓ 成功加载面板数据: {len(panel)}行 × {len(panel.columns)}列")

    # 步骤2: 展示面板数据统计
    print("\n【步骤2】 面板数据统计")
    print("-" * 70)

    # 基本信息
    num_regions = panel['id'].nunique()
    num_years = panel['time'].nunique()
    time_range = (panel['time'].min(), panel['time'].max())

    print(f"\n基本信息:")
    print(f"  地区数量: {num_regions}个")
    print(f"  时间跨度: {time_range[0]}-{time_range[1]} ({num_years}年)")
    print(f"  总观测数: {len(panel)}行")

    # 处理组vs对照组
    treated_regions = panel[panel['g'] > 0]['id'].unique()
    control_regions = panel[panel['g'] == 0]['id'].unique()

    print(f"\n处理组vs对照组:")
    print(f"  处理组: {len(treated_regions)}个地区")
    print(f"  对照组: {len(control_regions)}个地区")

    # 处理时点分布
    g_dist = panel.groupby('id')['g'].first().value_counts().sort_index()

    print(f"\n处理时点分布:")
    for g_val, count in g_dist.items():
        if g_val == 0:
            print(f"  never treated (g=0): {count}个地区")
        else:
            print(f"  首次处理于{int(g_val)}年 (g={int(g_val)}): {count}个地区")

    # 结果变量统计
    print(f"\n结果变量 (y) 统计:")
    print(f"  均值: {panel['y'].mean():.4f}")
    print(f"  标准差: {panel['y'].std():.4f}")
    print(f"  最小值: {panel['y'].min():.4f}")
    print(f"  最大值: {panel['y'].max():.4f}")

    # 步骤3: 模拟DID估计（简化版，无需R）
    print("\n【步骤3】 简化DID估计（无需R环境）")
    print("-" * 70)

    # 计算简单的前后对比
    pre_post_comparison(panel)

    # 步骤4: 验证面板质量
    print("\n【步骤4】 面板数据质量验证")
    print("-" * 70)

    validate_panel_quality(panel)

    # 步骤5: 展示样本数据
    print("\n【步骤5】 样本数据展示（前10行）")
    print("-" * 70)
    print(panel.head(10).to_string(index=False))

    # 总结
    print("\n" + "=" * 70)
    print("DID工作流演示完成")
    print("=" * 70)

    print("\n下一步:")
    print("1. 安装R环境（R ≥ 4.0.0）")
    print("2. 安装R包: install.packages(c('did', 'fixest', 'didimputation', 'ggplot2'))")
    print("3. 运行完整DID估计: python3 scripts/run_did_from_python.py")

    return 0


def pre_post_comparison(panel: pd.DataFrame):
    """简化的前后对比（无需R环境）"""

    # 仅针对处理组计算前后对比
    treated_panel = panel[panel['g'] > 0].copy()

    results = []

    for region_id in treated_panel['id'].unique():
        region_data = treated_panel[treated_panel['id'] == region_id]
        g = region_data['g'].iloc[0]

        # 处理前：g-1年的y值
        pre_data = region_data[region_data['time'] == g - 1]
        # 处理后：g年的y值
        post_data = region_data[region_data['time'] == g]

        if len(pre_data) > 0 and len(post_data) > 0:
            pre_y = pre_data['y'].iloc[0]
            post_y = post_data['y'].iloc[0]
            diff = post_y - pre_y

            results.append({
                'region': region_data['region_name'].iloc[0],
                'g': int(g),
                'pre_y': pre_y,
                'post_y': post_y,
                'diff': diff
            })

    if results:
        results_df = pd.DataFrame(results)
        print("\n简化前后对比（处理前1年 vs 处理年）:")
        print(results_df.to_string(index=False))

        avg_effect = results_df['diff'].mean()
        print(f"\n平均处理效应估计: {avg_effect:.4f}")
        print(f"（注意：这是简化估计，完整DID需要使用CS-ATT/Sun-Abraham/BJS）")
    else:
        print("⚠️ 无法计算前后对比（数据不足）")


def validate_panel_quality(panel: pd.DataFrame):
    """验证面板数据质量"""

    issues = []

    # 检查1: 平衡面板
    id_counts = panel.groupby('id')['time'].count()
    if id_counts.nunique() > 1:
        issues.append(f"❌ 非平衡面板：不同地区的时间点数量不一致")
    else:
        print(f"✓ 平衡面板：每个地区 {id_counts.iloc[0]} 个时间点")

    # 检查2: 必需字段
    required_cols = ['id', 'time', 'y', 'g', 'treat']
    missing = set(required_cols) - set(panel.columns)
    if missing:
        issues.append(f"❌ 缺少必需列: {missing}")
    else:
        print(f"✓ 必需字段完整: {required_cols}")

    # 检查3: treat变量一致性
    panel_check = panel.copy()
    panel_check['treat_expected'] = ((panel_check['g'] > 0) & (panel_check['time'] >= panel_check['g'])).astype(int)
    inconsistent = (panel_check['treat'] != panel_check['treat_expected']).sum()

    if inconsistent > 0:
        issues.append(f"❌ treat变量与g和time不一致: {inconsistent}处")
    else:
        print(f"✓ treat变量与g和time一致")

    # 检查4: 缺失值
    na_counts = panel[required_cols].isna().sum()
    if na_counts.any():
        issues.append(f"❌ 存在缺失值: {na_counts[na_counts > 0].to_dict()}")
    else:
        print(f"✓ 无缺失值")

    # 检查5: 处理组数量
    treated_ids = panel[panel['g'] > 0]['id'].nunique()
    if treated_ids == 0:
        issues.append("❌ 无处理组（所有地区g=0）")
    else:
        print(f"✓ 处理组数量合理: {treated_ids}个")

    # 总结
    if issues:
        print("\n验证失败:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("\n✅ 面板数据质量验证通过")
        return True


if __name__ == '__main__':
    exit(main())
