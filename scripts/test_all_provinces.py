#!/usr/bin/env python3
"""
PSC-Graph 省份批量测试脚本
用于验证所有31个省份配置的正确性
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json
import yaml

# 配置路径
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "data/seeds/seeds_sites.yaml"
OUTPUT_BASE = PROJECT_ROOT / "corpus/raw/policy_provinces"
TEST_REPORT = PROJECT_ROOT / "results/logs/province_test_report.txt"

# 加载配置
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
    provinces = config.get('provinces', [])

print("=" * 70)
print("PSC-Graph 省份批量测试")
print("=" * 70)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"待测试省份: {len(provinces)}个")
print()

# 测试结果统计
results = {
    'success': [],
    'failed': [],
    'errors': {}
}

# 遍历每个省份
for i, prov_config in enumerate(provinces, 1):
    province_name = prov_config.get('region', '未知省份')
    adcode = prov_config.get('adcode_prov', '')

    print(f"[{i}/{len(provinces)}] 测试 {province_name} (Adcode: {adcode})...", end=' ', flush=True)

    try:
        # 运行单省份测试（仅1页，超时90秒）
        cmd = [
            'python3',
            'scripts/crawl_provinces.py',
            province_name,
            '--test'
        ]

        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=90,
            encoding='utf-8',
            errors='ignore'
        )

        # 检查输出目录是否有文件
        prov_dir = OUTPUT_BASE / province_name
        if prov_dir.exists():
            doc_count = len(list(prov_dir.glob('*.json')))
            if doc_count > 0:
                print(f"✅ 成功 ({doc_count}份文档)")
                results['success'].append({
                    'province': province_name,
                    'adcode': adcode,
                    'doc_count': doc_count
                })
            else:
                print(f"❌ 失败 (无文档)")
                results['failed'].append(province_name)
                results['errors'][province_name] = "未找到文档"
        else:
            print(f"❌ 失败 (无输出)")
            results['failed'].append(province_name)
            results['errors'][province_name] = "未创建输出目录"

    except subprocess.TimeoutExpired:
        print(f"⏱️  超时")
        results['failed'].append(province_name)
        results['errors'][province_name] = "执行超时(>90秒)"

    except Exception as e:
        print(f"❌ 异常: {str(e)[:50]}")
        results['failed'].append(province_name)
        results['errors'][province_name] = str(e)

# 输出汇总
print()
print("=" * 70)
print("测试汇总")
print("=" * 70)
print(f"总计: {len(provinces)}个省份")
print(f"✅ 成功: {len(results['success'])}个")
print(f"❌ 失败: {len(results['failed'])}个")
print(f"成功率: {len(results['success'])/len(provinces)*100:.1f}%")
print()

if results['success']:
    print("【成功省份】")
    for item in results['success']:
        print(f"  ✅ {item['province']} - {item['doc_count']}份文档")
    print()

if results['failed']:
    print("【失败省份】")
    for prov in results['failed']:
        error = results['errors'].get(prov, '未知错误')
        print(f"  ❌ {prov}: {error}")
    print()

# 保存测试报告
report_content = f"""PSC-Graph 省份批量测试报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

总计: {len(provinces)}个省份
成功: {len(results['success'])}个
失败: {len(results['failed'])}个
成功率: {len(results['success'])/len(provinces)*100:.1f}%

=== 成功省份 ===
"""

for item in results['success']:
    report_content += f"{item['province']} (Adcode: {item['adcode']}): {item['doc_count']}份文档\n"

report_content += f"\n=== 失败省份 ===\n"
for prov in results['failed']:
    error = results['errors'].get(prov, '未知错误')
    report_content += f"{prov}: {error}\n"

TEST_REPORT.parent.mkdir(parents=True, exist_ok=True)
with open(TEST_REPORT, 'w', encoding='utf-8') as f:
    f.write(report_content)

print(f"测试报告已保存: {TEST_REPORT}")
print("=" * 70)

# 退出码：失败数量
sys.exit(len(results['failed']))
