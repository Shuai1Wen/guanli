#!/usr/bin/env python3
"""
省份政策列表URL自动发现脚本
遍历所有省份的官网，自动发现正确的政策列表页URL
"""

import sys
from pathlib import Path
import yaml
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import random

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "data/seeds/seeds_sites.yaml"

# 加载配置
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
    provinces = config.get('provinces', [])

# 常见政策栏目路径模式
COMMON_PATTERNS = [
    "/zwgk/zcfg/",
    "/zwgk/kjzc/zcwj/",
    "/kjzx/zcfg/",
    "/zcfg/",
    "/zwgk_n/zcfg/",
    "/col/col{}/",  # 需要查找栏目ID
    "/kjt/zcfg/",
    "/zwgk/tzgg/",
]

# 关键词
POLICY_KEYWORDS = [
    "政策法规", "政策文件", "政策解读",
    "通知公告", "文件通知", "规范性文件"
]

def find_policy_url(homepage: str, province_name: str) -> str:
    """自动发现政策列表页URL"""
    print(f"  正在探测 {province_name}...", end=' ', flush=True)

    try:
        # 请求首页
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'PSC-Graph/0.1 (+research; contact: policy@psc-graph.org)'
        })

        resp = session.get(homepage, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'lxml')

        # 策略1：查找包含政策关键词的链接
        for keyword in POLICY_KEYWORDS:
            links = soup.find_all('a', string=lambda t: t and keyword in t)
            if links:
                href = links[0].get('href')
                if href:
                    full_url = urljoin(homepage, href)
                    print(f"✅ 找到: {keyword} -> {full_url}")
                    return full_url

        # 策略2：尝试常见路径模式
        for pattern in COMMON_PATTERNS:
            if '{}" in pattern:
                continue  # 跳过需要栏目ID的模式
            test_url = homepage.rstrip('/') + pattern
            try:
                test_resp = session.get(test_url, timeout=10)
                if test_resp.status_code == 200:
                    print(f"✅ 找到: {pattern} -> {test_url}")
                    return test_url
            except:
                pass

        print(f"❌ 未找到")
        return ""

    except Exception as e:
        print(f"❌ 错误: {str(e)[:50]}")
        return ""

    finally:
        # 礼貌延迟
        time.sleep(1 + random.random())


def main():
    """主函数"""
    print("=" * 70)
    print("省份政策URL自动发现")
    print("=" * 70)
    print()

    discoveries = {}

    for i, prov_config in enumerate(provinces, 1):
        province_name = prov_config.get('region', '未知')
        homepage = prov_config.get('homepage', '')
        current_list_url = prov_config.get('list_url', '')

        print(f"[{i}/{len(provinces)}] {province_name}")
        print(f"  官网: {homepage}")
        print(f"  当前配置: {current_list_url}")

        if not homepage:
            print(f"  ⚠️  跳过：无官网配置")
            print()
            continue

        # 自动发现
        discovered_url = find_policy_url(homepage, province_name)
        discoveries[province_name] = {
            'homepage': homepage,
            'current': current_list_url,
            'discovered': discovered_url
        }

        print()

    # 输出汇总
    print("=" * 70)
    print("发现汇总")
    print("=" * 70)

    success_count = sum(1 for d in discoveries.values() if d['discovered'])
    print(f"成功发现: {success_count}/{len(discoveries)}")
    print()

    print("【建议更新】")
    for prov, info in discoveries.items():
        if info['discovered'] and info['discovered'] != info['current']:
            print(f"{prov}:")
            print(f"  当前: {info['current']}")
            print(f"  建议: {info['discovered']}")
            print()


if __name__ == "__main__":
    main()
