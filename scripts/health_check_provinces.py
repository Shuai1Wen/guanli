#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
省级政策网站健康检查脚本（轻量级）
--------------------------------------
功能：
  - 只GET一页，不进行大规模爬取
  - 检查HTTP状态码、页面结构、元素数量
  - 生成简洁的健康报告

用法：
  python3 health_check_provinces.py                    # 检查所有省份
  python3 health_check_provinces.py --class A          # 只检查A类省份
  python3 health_check_provinces.py --priority P0      # 只检查P0优先级
  python3 health_check_provinces.py --prov 广东省      # 只检查指定省份
"""

import sys
import time
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

# 尝试导入依赖，优雅处理缺失情况
try:
    import requests
    from bs4 import BeautifulSoup
    DEPS_AVAILABLE = True
except ImportError as e:
    DEPS_AVAILABLE = False
    MISSING_DEP = str(e)


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    prov_code: str
    prov_name: str
    classification: str
    priority: str
    url: str

    # 检查结果
    success: bool
    status_code: Optional[int] = None
    error_message: Optional[str] = None

    # 页面元数据
    page_title: Optional[str] = None
    page_size: Optional[int] = None
    link_count: int = 0
    table_row_count: int = 0
    list_item_count: int = 0

    # 诊断建议
    diagnosis: str = "未检查"


class ProvinceHealthChecker:
    """省级政策网站健康检查器"""

    def __init__(self, config_path: str = "data/provinces.yaml"):
        self.config_path = Path(config_path)
        self.provinces = []
        self.results: List[HealthCheckResult] = []

        # HTTP配置
        self.timeout = 10
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) PSC-Graph Health Checker/1.0',
        }

    def load_config(self):
        """加载省份配置"""
        if not self.config_path.exists():
            print(f"❌ 配置文件不存在: {self.config_path}")
            sys.exit(1)

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.provinces = config.get('provinces', [])
        print(f"✅ 加载配置: {len(self.provinces)}个省份")

    def filter_provinces(self, classification: Optional[str] = None,
                        priority: Optional[str] = None,
                        prov_name: Optional[str] = None) -> List[Dict]:
        """筛选省份"""
        filtered = self.provinces

        if classification:
            filtered = [p for p in filtered if p.get('classification') == classification]

        if priority:
            filtered = [p for p in filtered if p.get('priority') == priority]

        if prov_name:
            filtered = [p for p in filtered if p.get('prov_name') == prov_name]

        return filtered

    def check_province(self, prov: Dict) -> HealthCheckResult:
        """检查单个省份"""
        result = HealthCheckResult(
            prov_code=prov['prov_code'],
            prov_name=prov['prov_name'],
            classification=prov['classification'],
            priority=prov['priority'],
            url=prov.get('policy_channel_url', ''),
            success=False,
        )

        # 检查URL是否存在
        if not result.url:
            result.error_message = "配置中无policy_channel_url"
            result.diagnosis = "配置缺失"
            return result

        # 尝试GET请求
        try:
            # 替换分页占位符为第1页
            test_url = result.url.replace('{page}', '1').replace('_1.', '.')

            print(f"  🔍 GET {test_url[:80]}...")
            response = requests.get(
                test_url,
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True
            )

            result.status_code = response.status_code
            result.page_size = len(response.content)

            # HTTP状态码检查
            if response.status_code != 200:
                result.error_message = f"HTTP {response.status_code}"
                result.diagnosis = "HTTP错误"
                return result

            # 解析HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # 提取页面标题
            title_tag = soup.find('title')
            if title_tag:
                result.page_title = title_tag.get_text(strip=True)[:50]

            # 统计元素数量
            result.link_count = len(soup.find_all('a'))
            result.table_row_count = len(soup.find_all('tr'))
            result.list_item_count = len(soup.find_all('li'))

            # 诊断
            if result.link_count == 0:
                result.diagnosis = "⚠️ 无链接（可能需要JS渲染）"
            elif result.table_row_count == 0 and result.list_item_count == 0:
                result.diagnosis = "⚠️ 无表格/列表（结构异常）"
            elif result.link_count < 10:
                result.diagnosis = "⚠️ 链接数量少（可能是错误页面）"
            else:
                result.diagnosis = "✅ 结构正常"
                result.success = True

        except requests.exceptions.Timeout:
            result.error_message = "超时（>10秒）"
            result.diagnosis = "网络超时"
        except requests.exceptions.ConnectionError:
            result.error_message = "连接失败"
            result.diagnosis = "无法连接"
        except requests.exceptions.TooManyRedirects:
            result.error_message = "重定向过多"
            result.diagnosis = "重定向异常"
        except Exception as e:
            result.error_message = str(e)[:50]
            result.diagnosis = "未知错误"

        return result

    def run_checks(self, provinces: List[Dict], delay: float = 0.5):
        """批量运行健康检查"""
        print(f"\n开始健康检查: {len(provinces)}个省份")
        print("=" * 80)

        for i, prov in enumerate(provinces, 1):
            print(f"\n[{i}/{len(provinces)}] {prov['prov_name']} ({prov['classification']}类, {prov['priority']})")

            result = self.check_province(prov)
            self.results.append(result)

            # 简洁输出
            if result.success:
                print(f"  ✅ {result.diagnosis}")
                print(f"     链接:{result.link_count} | 表格行:{result.table_row_count} | 列表:{result.list_item_count}")
            else:
                print(f"  ❌ {result.diagnosis}: {result.error_message}")

            # 节流
            if i < len(provinces):
                time.sleep(delay)

    def print_summary(self):
        """打印摘要报告"""
        print("\n" + "=" * 80)
        print("健康检查摘要")
        print("=" * 80)

        # 按分类统计
        by_class = {}
        for r in self.results:
            cls = r.classification
            if cls not in by_class:
                by_class[cls] = {'total': 0, 'success': 0, 'failed': 0}
            by_class[cls]['total'] += 1
            if r.success:
                by_class[cls]['success'] += 1
            else:
                by_class[cls]['failed'] += 1

        print(f"\n总计: {len(self.results)}个省份")
        for cls in sorted(by_class.keys()):
            stats = by_class[cls]
            success_rate = stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"  {cls}类: {stats['success']}/{stats['total']} 成功 ({success_rate:.1f}%)")

        # 失败列表
        failed = [r for r in self.results if not r.success]
        if failed:
            print(f"\n失败省份 ({len(failed)}个):")
            for r in failed:
                print(f"  ❌ {r.prov_name} ({r.classification}类): {r.diagnosis} - {r.error_message}")

        # 成功列表
        success = [r for r in self.results if r.success]
        if success:
            print(f"\n成功省份 ({len(success)}个):")
            for r in success:
                print(f"  ✅ {r.prov_name} ({r.classification}类): {r.diagnosis}")

    def save_report(self, output_path: str = "results/logs/health_check_report.txt"):
        """保存详细报告"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("PSC-Graph 省级政策网站健康检查报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"检查省份: {len(self.results)}个\n\n")

            # 详细结果
            f.write("详细结果:\n")
            f.write("-" * 80 + "\n")
            for r in self.results:
                f.write(f"\n省份: {r.prov_name} ({r.prov_code})\n")
                f.write(f"分类: {r.classification}类 | 优先级: {r.priority}\n")
                f.write(f"URL: {r.url}\n")
                f.write(f"状态: {'✅ 成功' if r.success else '❌ 失败'}\n")

                if r.status_code:
                    f.write(f"HTTP状态码: {r.status_code}\n")
                if r.page_title:
                    f.write(f"页面标题: {r.page_title}\n")
                if r.page_size:
                    f.write(f"页面大小: {r.page_size} 字节\n")

                f.write(f"链接数: {r.link_count} | 表格行: {r.table_row_count} | 列表项: {r.list_item_count}\n")
                f.write(f"诊断: {r.diagnosis}\n")

                if r.error_message:
                    f.write(f"错误信息: {r.error_message}\n")

        print(f"\n✅ 详细报告已保存: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='省级政策网站健康检查（轻量级）')
    parser.add_argument('--class', dest='classification', choices=['A', 'B', 'C', 'D'],
                       help='只检查指定分类的省份')
    parser.add_argument('--priority', choices=['P0', 'P1', 'P2', 'P3'],
                       help='只检查指定优先级的省份')
    parser.add_argument('--prov', dest='prov_name', help='只检查指定省份（如：广东省）')
    parser.add_argument('--delay', type=float, default=0.5, help='请求间隔（秒，默认0.5）')
    parser.add_argument('--config', default='data/provinces.yaml', help='配置文件路径')

    args = parser.parse_args()

    # 检查依赖
    if not DEPS_AVAILABLE:
        print(f"❌ 缺少Python依赖: {MISSING_DEP}")
        print("\n请先安装依赖:")
        print("  pip3 install -r scripts/requirements.txt")
        print("\n或手动安装:")
        print("  pip3 install requests beautifulsoup4 lxml pyyaml")
        sys.exit(1)

    # 初始化检查器
    checker = ProvinceHealthChecker(config_path=args.config)
    checker.load_config()

    # 筛选省份
    provinces = checker.filter_provinces(
        classification=args.classification,
        priority=args.priority,
        prov_name=args.prov_name
    )

    if not provinces:
        print("❌ 没有符合条件的省份")
        sys.exit(1)

    # 运行检查
    checker.run_checks(provinces, delay=args.delay)

    # 打印摘要
    checker.print_summary()

    # 保存报告
    checker.save_report()


if __name__ == '__main__':
    main()
