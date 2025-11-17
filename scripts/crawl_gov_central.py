#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PSC-Graph 中央政策爬虫

功能:
- 从国务院政策文件库爬取政策文档
- 支持部门文件、政策解读等多个栏目
- 断点续爬、SHA256去重
- 遵守robots.txt、QPS≤1.0

数据源:
- 部门文件: https://www.gov.cn/zhengce/zhengceku/bmwj/home_{page}.htm
- 政策解读: https://www.gov.cn/zhengce/jiedu/home_{page}.htm

作者: PSC-Graph数据工程组
日期: 2025-11-17

使用方法:
    python scripts/crawl_gov_central.py
    或
    make crawl_gov_central
"""

import os
import sys
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 导入通用模块
from crawler_common import (
    get_session,
    polite_get,
    sha256_text,
    save_json,
    load_checkpoint,
    save_checkpoint,
    init_logger,
)

# 全局变量
BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "data" / "seeds" / "seeds_sites.yaml"
CHECKPOINT_PATH = BASE_DIR / "results" / "checkpoints" / "gov_central.json"
OUTPUT_DIR = BASE_DIR / "corpus" / "raw" / "policy_central"

# 初始化日志
logger = init_logger("gov_central")


def load_config() -> List[Dict[str, Any]]:
    """
    加载站点配置文件

    返回:
        中央政策站点配置列表
    """
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    central_sites = config.get("central", [])
    logger.info(f"加载配置: {len(central_sites)}个中央政策栏目")

    return central_sites


def extract_list_page(html: str, base_url: str) -> List[str]:
    """
    从列表页提取详情页链接

    参数:
        html: 列表页HTML内容
        base_url: 基础URL（用于拼接相对路径）

    返回:
        详情页URL列表
    """
    soup = BeautifulSoup(html, "lxml")
    links = []

    # 查找政策链接（通常在特定的class或id下）
    # 策略1: 查找包含"content_"的链接（gov.cn常见模式）
    for a in soup.find_all("a", href=True):
        href = a["href"]

        # 过滤条件
        if (
            "content_" in href
            or "zhengce/" in href
            or href.startswith("/gongbao/")
        ):
            full_url = urljoin(base_url, href)

            # 只保留gov.cn域名的链接
            if "gov.cn" in full_url:
                links.append(full_url)

    # 去重
    links = list(dict.fromkeys(links))

    return links


def extract_detail_page(html: str, url: str) -> Optional[Dict[str, Any]]:
    """
    从详情页提取政策文档信息

    参数:
        html: 详情页HTML内容
        url: 详情页URL

    返回:
        政策文档字典，失败返回None
    """
    soup = BeautifulSoup(html, "lxml")

    try:
        # 提取标题
        title_elem = (
            soup.find("h1")
            or soup.find("div", class_="title")
            or soup.find("div", {"class": lambda x: x and "title" in x.lower()})
        )
        title = title_elem.get_text(strip=True) if title_elem else ""

        # 提取正文内容
        content_elem = (
            soup.find("div", id="UCAP-CONTENT")
            or soup.find("div", {"class": lambda x: x and "content" in x.lower()})
            or soup.find("div", id="content")
            or soup.find("td", {"class": "jiucuo_content"})
        )

        content_text = ""
        content_html = ""

        if content_elem:
            content_html = str(content_elem)
            content_text = content_elem.get_text(separator="\n", strip=True)

        # 提取发布日期
        pub_date = ""
        date_elem = soup.find("span", {"class": lambda x: x and "date" in x.lower()})

        if not date_elem:
            # 尝试从meta标签提取
            meta_date = soup.find("meta", {"name": "publishdate"})
            if meta_date:
                pub_date = meta_date.get("content", "")
        else:
            pub_date = date_elem.get_text(strip=True)

        # 提取发布机关
        issuer = ""
        issuer_elem = soup.find("span", string=lambda x: x and "来源" in x)
        if issuer_elem:
            issuer = issuer_elem.find_next("span").get_text(strip=True) if issuer_elem.find_next("span") else ""

        # 提取文号
        doc_no = ""
        doc_no_elem = soup.find("span", string=lambda x: x and "文号" in x)
        if doc_no_elem:
            doc_no = doc_no_elem.find_next("span").get_text(strip=True) if doc_no_elem.find_next("span") else ""

        # 构造文档对象
        doc = {
            "doc_id": f"gov_central_{sha256_text(url)[:16]}",
            "title": title,
            "pub_date": pub_date,
            "issuer": issuer,
            "doc_no": doc_no,
            "category": "中央政策",  # 根据URL判断具体栏目
            "status": "现行",  # 默认现行，需后续验证
            "source_url": url,
            "html": content_html,
            "content_text": content_text,
            "sha256": sha256_text(content_text),
            "retrieved_at": datetime.now().isoformat(),
            "region": "CN-Central",
        }

        # 验证必须字段
        if not title or not content_text:
            logger.warning(f"[SKIP] 缺少必要字段: {url}")
            return None

        return doc

    except Exception as e:
        logger.error(f"[ERROR] 解析详情页失败 {url}: {e}")
        return None


def crawl_site(site_config: Dict[str, Any], session, checkpoint: Dict[str, Any]):
    """
    爬取单个站点配置的所有页面

    参数:
        site_config: 站点配置字典
        session: HTTP会话对象
        checkpoint: 断点续爬状态
    """
    site_name = site_config["name"]
    list_url_template = site_config["list_url"]
    start_page = site_config.get("start_page", 1)
    max_pages = site_config.get("max_pages", 10)
    category = site_config.get("category", "未分类")

    logger.info(f"[{site_name}] 开始爬取，页面范围: {start_page}-{max_pages}")

    # 从checkpoint恢复进度
    resume_page = checkpoint.get(site_name, {}).get("next_page", start_page)
    logger.info(f"[{site_name}] 从第{resume_page}页继续")

    # 创建输出目录
    output_subdir = OUTPUT_DIR / category
    output_subdir.mkdir(parents=True, exist_ok=True)

    # 统计信息
    total_links = 0
    total_saved = 0
    total_skipped = 0

    # 遍历列表页
    for page_num in range(resume_page, max_pages + 1):
        # 构造列表页URL
        if "{page}" in list_url_template:
            if page_num == 1:
                # 有些网站第1页没有_1后缀
                list_url = list_url_template.replace("_{page}", "").replace("{page}", "")
            else:
                list_url = list_url_template.replace("{page}", str(page_num))
        else:
            list_url = list_url_template

        logger.info(f"[{site_name}] 正在爬取第{page_num}页: {list_url}")

        try:
            # 获取列表页
            response = polite_get(session, list_url)
            html = response.text

            # 提取详情页链接
            detail_urls = extract_list_page(html, list_url)
            total_links += len(detail_urls)

            logger.info(f"[{site_name}] 第{page_num}页找到{len(detail_urls)}个链接")

            if len(detail_urls) == 0:
                logger.warning(f"[{site_name}] 第{page_num}页没有找到链接，可能已到末页")
                break

            # 遍历详情页
            for detail_url in detail_urls:
                try:
                    # 获取详情页
                    response = polite_get(session, detail_url)
                    html = response.text

                    # 提取文档信息
                    doc = extract_detail_page(html, detail_url)

                    if not doc:
                        total_skipped += 1
                        continue

                    # 更新类别
                    doc["category"] = category

                    # 检查去重
                    sha = doc["sha256"]
                    output_file = output_subdir / f"{sha[:16]}.json"

                    if output_file.exists():
                        logger.info(f"[SKIP] 文档已存在(SHA256去重): {doc['title'][:30]}...")
                        total_skipped += 1
                        continue

                    # 保存文档
                    save_json(doc, output_file)
                    total_saved += 1

                    logger.info(f"[SAVE] {doc['title'][:50]}... -> {output_file.name}")

                except Exception as e:
                    logger.error(f"[ERROR] 处理详情页失败 {detail_url}: {e}")
                    continue

            # 更新checkpoint
            checkpoint[site_name] = {
                "next_page": page_num + 1,
                "last_update": datetime.now().isoformat(),
            }
            save_checkpoint(CHECKPOINT_PATH, checkpoint)

        except Exception as e:
            logger.error(f"[ERROR] 爬取第{page_num}页失败: {e}")
            continue

    # 汇总统计
    logger.info(f"[{site_name}] 爬取完成")
    logger.info(f"[{site_name}] 总链接数: {total_links}")
    logger.info(f"[{site_name}] 保存文档: {total_saved}")
    logger.info(f"[{site_name}] 跳过文档: {total_skipped}")


def main():
    """
    主函数
    """
    logger.info("=" * 60)
    logger.info("PSC-Graph 中央政策爬虫启动")
    logger.info("=" * 60)

    # 加载配置
    sites = load_config()

    if not sites:
        logger.error("配置文件为空，退出")
        sys.exit(1)

    # 创建会话（QPS=1.0）
    session = get_session(qps=1.0)

    # 加载checkpoint
    checkpoint = load_checkpoint(CHECKPOINT_PATH)

    # 遍历所有站点配置
    for site_config in sites:
        try:
            crawl_site(site_config, session, checkpoint)
        except Exception as e:
            logger.error(f"[ERROR] 爬取站点失败 {site_config['name']}: {e}")
            continue

    logger.info("=" * 60)
    logger.info("所有站点爬取完成 ✅")
    logger.info("=" * 60)

    # 统计总数
    total_files = sum(1 for _ in OUTPUT_DIR.rglob("*.json"))
    logger.info(f"总计保存文档: {total_files}条")
    logger.info(f"输出目录: {OUTPUT_DIR}")
    logger.info(f"日志文件: results/logs/gov_central.log")


if __name__ == "__main__":
    main()
