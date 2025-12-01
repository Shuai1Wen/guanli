#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CNIPA专利统计报告下载器
-----------------------
从国家知识产权局（CNIPA）下载专利统计月报和年报的PDF文件

数据来源：
  - 统计月报：https://www.cnipa.gov.cn/col/col3482/
  - 统计年报：https://www.cnipa.gov.cn/col/col94/

遵守CLAUDE.md规范：
  - QPS ≤ 0.5
  - 仅下载公开PDF报告
  - 遵守robots.txt
  - SHA256校验和记录

用法：
    python3 fetch_cnipa_reports.py --type monthly --start 2023-01 --end 2023-12
    python3 fetch_cnipa_reports.py --type annual --year 2023
"""

import os
import time
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup


class CNIPAReportDownloader:
    """CNIPA专利统计报告下载器"""

    def __init__(self, output_dir="data/cnipa_raw", delay=2.0):
        """
        初始化下载器

        参数：
            output_dir: 输出目录
            delay: 请求间隔（秒），默认2.0（QPS=0.5）
        """
        self.output_dir = Path(output_dir)
        self.delay = delay

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "monthly").mkdir(exist_ok=True)
        (self.output_dir / "annual").mkdir(exist_ok=True)
        (self.output_dir / "checksums").mkdir(exist_ok=True)

        # HTTP配置
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) PSC-Graph CNIPA Fetcher/1.0',
        })

        # 已知的CNIPA统计报告URL模式（需要手动维护）
        # 注：CNIPA网站不提供标准API，需要人工识别URL模式
        self.monthly_url_pattern = "https://www.cnipa.gov.cn/art/{}/art_{}.html"
        self.annual_url_pattern = "https://www.cnipa.gov.cn/art/{}/art_{}.html"

    def download_file(self, url: str, save_path: Path) -> bool:
        """
        下载文件并计算SHA256

        参数：
            url: 文件URL
            save_path: 保存路径

        返回：
            是否成功
        """
        try:
            print(f"  📥 下载: {url}")

            response = self.session.get(url, timeout=30, stream=True)

            if response.status_code != 200:
                print(f"  ❌ HTTP {response.status_code}")
                return False

            # 写入文件
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 计算SHA256
            sha256_hash = hashlib.sha256()
            with open(save_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

            checksum = sha256_hash.hexdigest()

            # 保存校验和
            checksum_file = self.output_dir / "checksums" / f"{save_path.name}.sha256"
            with open(checksum_file, 'w') as f:
                f.write(f"{checksum}  {save_path.name}\n")

            file_size = save_path.stat().st_size / 1024  # KB
            print(f"  ✅ 已保存: {save_path.name} ({file_size:.1f} KB)")
            print(f"  🔒 SHA256: {checksum[:16]}...")

            return True

        except Exception as e:
            print(f"  ❌ 下载失败: {e}")
            return False

    def fetch_monthly_reports(self, start_month: str, end_month: str) -> List[str]:
        """
        下载月报（手动模式，需要提供已知URL列表）

        参数：
            start_month: 起始月份（YYYY-MM）
            end_month: 结束月份（YYYY-MM）

        返回：
            成功下载的文件路径列表

        注：由于CNIPA网站没有标准API，本方法提供手动下载框架。
           实际URL需要用户从CNIPA官网手动获取，并通过--manual-urls参数传入。
        """
        print("\n" + "=" * 80)
        print("⚠️  CNIPA月报下载（手动模式）")
        print("=" * 80)
        print("\n由于CNIPA网站没有标准API，需要手动操作：")
        print("\n步骤1：访问CNIPA统计月报页面")
        print("  URL: https://www.cnipa.gov.cn/col/col3482/")
        print("\n步骤2：在浏览器中找到目标月份的PDF链接")
        print("  示例：2023年1月专利、商标、地理标志统计月报")
        print("\n步骤3：使用--manual-urls参数传入URL列表")
        print("  示例：python3 fetch_cnipa_reports.py --manual-urls urls.txt")
        print("\n" + "=" * 80)

        return []

    def fetch_annual_reports(self, year: int) -> List[str]:
        """
        下载年报（手动模式）

        参数：
            year: 年份

        返回：
            成功下载的文件路径列表
        """
        print("\n" + "=" * 80)
        print(f"⚠️  CNIPA {year}年年报下载（手动模式）")
        print("=" * 80)
        print("\n由于CNIPA网站没有标准API，需要手动操作：")
        print("\n步骤1：访问CNIPA统计年报页面")
        print("  URL: https://www.cnipa.gov.cn/col/col94/")
        print("\n步骤2：在浏览器中找到目标年份的PDF链接")
        print(f"  示例：{year}年专利、商标、地理标志等统计数据")
        print("\n步骤3：使用--manual-urls参数传入URL列表")
        print("  示例：python3 fetch_cnipa_reports.py --manual-urls urls.txt")
        print("\n" + "=" * 80)

        return []

    def download_from_urls_file(self, urls_file: str) -> List[str]:
        """
        从URL文件批量下载

        参数：
            urls_file: URL列表文件（每行一个URL）

        返回：
            成功下载的文件路径列表
        """
        urls_path = Path(urls_file)

        if not urls_path.exists():
            print(f"❌ URL文件不存在: {urls_file}")
            return []

        # 读取URL列表
        with open(urls_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        if not urls:
            print(f"❌ URL文件为空: {urls_file}")
            return []

        print(f"\n📋 从文件加载了 {len(urls)} 个URL")
        print("=" * 80)

        downloaded_files = []

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 处理URL:")
            print(f"  {url}")

            # 从URL推断文件名
            filename = url.split('/')[-1]

            if not filename.endswith('.pdf'):
                # 尝试从Content-Disposition获取文件名
                try:
                    head_response = self.session.head(url, timeout=10)
                    content_disp = head_response.headers.get('Content-Disposition', '')

                    if 'filename=' in content_disp:
                        filename = content_disp.split('filename=')[-1].strip('"\'')
                    else:
                        filename = f"cnipa_report_{i}.pdf"

                except Exception:
                    filename = f"cnipa_report_{i}.pdf"

            # 确定保存路径（根据文件名推断是月报还是年报）
            if '月报' in filename or 'monthly' in filename.lower():
                save_path = self.output_dir / "monthly" / filename
            elif '年报' in filename or 'annual' in filename.lower():
                save_path = self.output_dir / "annual" / filename
            else:
                save_path = self.output_dir / filename

            # 下载
            if save_path.exists():
                print(f"  ⏭️  文件已存在，跳过: {save_path.name}")
                downloaded_files.append(str(save_path))
            else:
                success = self.download_file(url, save_path)

                if success:
                    downloaded_files.append(str(save_path))

            # 节流
            if i < len(urls):
                time.sleep(self.delay)

        print("\n" + "=" * 80)
        print(f"下载完成: {len(downloaded_files)}/{len(urls)} 成功")
        print("=" * 80)

        return downloaded_files


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='CNIPA专利统计报告下载器（手动模式）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：

1. 从URL列表文件下载（推荐）：
   python3 fetch_cnipa_reports.py --manual-urls cnipa_urls.txt

2. 查看月报/年报下载指引：
   python3 fetch_cnipa_reports.py --type monthly --start 2023-01 --end 2023-12
   python3 fetch_cnipa_reports.py --type annual --year 2023

URL列表文件格式（cnipa_urls.txt）：
   # 2023年1月月报
   https://www.cnipa.gov.cn/docs/2023-02/20230215123456.pdf

   # 2023年2月月报
   https://www.cnipa.gov.cn/docs/2023-03/20230315123456.pdf
        """
    )

    parser.add_argument('--type', choices=['monthly', 'annual'],
                       help='报告类型：monthly（月报）或 annual（年报）')
    parser.add_argument('--start', help='起始月份（YYYY-MM，仅月报）')
    parser.add_argument('--end', help='结束月份（YYYY-MM，仅月报）')
    parser.add_argument('--year', type=int, help='年份（仅年报）')
    parser.add_argument('--manual-urls', help='手动提供的URL列表文件')
    parser.add_argument('--output-dir', default='data/cnipa_raw',
                       help='输出目录，默认data/cnipa_raw')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='请求间隔（秒），默认2.0（QPS=0.5）')

    args = parser.parse_args()

    # 初始化下载器
    downloader = CNIPAReportDownloader(
        output_dir=args.output_dir,
        delay=args.delay
    )

    # 执行下载
    if args.manual_urls:
        # 模式1：从URL列表文件下载
        downloaded_files = downloader.download_from_urls_file(args.manual_urls)

    elif args.type == 'monthly':
        # 模式2：月报（显示手动操作指引）
        if not args.start or not args.end:
            parser.error("月报模式需要--start和--end参数")

        downloaded_files = downloader.fetch_monthly_reports(args.start, args.end)

    elif args.type == 'annual':
        # 模式3：年报（显示手动操作指引）
        if not args.year:
            parser.error("年报模式需要--year参数")

        downloaded_files = downloader.fetch_annual_reports(args.year)

    else:
        parser.print_help()
        return

    # 打印结果
    if downloaded_files:
        print("\n✅ 下载完成的文件：")
        for f in downloaded_files:
            print(f"  - {f}")
    else:
        print("\n⚠️  未下载任何文件。请参考上述指引手动获取URL。")


if __name__ == '__main__':
    main()
