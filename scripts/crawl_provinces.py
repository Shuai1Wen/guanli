#!/usr/bin/env python3
"""
PSC-Graph 省级政策爬虫
支持所有31个省份的科技厅政策文档爬取
符合CLAUDE.md合规要求：QPS≤0.7, robots.txt检查, SHA256去重, 断点续爬
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import yaml
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入通用爬虫模块
from scripts.crawler_common import (
    get_session,
    polite_get,
    sha256_text,
    save_json,
    load_checkpoint,
    save_checkpoint,
    init_logger,
)

# 配置路径
CONFIG_PATH = PROJECT_ROOT / "data/seeds/seeds_sites.yaml"
OUTPUT_BASE = PROJECT_ROOT / "corpus/raw/policy_provinces"
CHECKPOINT_PATH = PROJECT_ROOT / "results/checkpoints/provinces.json"

# 初始化日志
logger = init_logger("provinces")


def load_config() -> List[Dict[str, Any]]:
    """加载省级站点配置"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    provinces = config.get("provinces", [])
    logger.info(f"加载配置: {len(provinces)}个省级站点")
    return provinces


def extract_list_page_generic(html: str, base_url: str, province_name: str) -> List[str]:
    """
    通用列表页链接提取（支持多种网站结构）

    策略：
    1. 查找所有包含"政策"、"文件"、"通知"等关键词的链接
    2. 过滤掉导航、页脚等非内容链接
    3. 返回去重后的详情页URL列表
    """
    soup = BeautifulSoup(html, "lxml")
    links = []

    # 策略1：查找包含政策相关路径的链接
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)

        # 过滤条件：包含政策相关关键词或路径
        policy_keywords = [
            "zcfg", "policy", "zhengce", "wenjian", "tongzhi",
            "content", "article", "info", "detail", "view",
            "tzgs", "gsgg", "zhtz", "zcwj", "kjzc",  # 上海等地特殊路径
            "zwgk", "xxgk", "gkml",  # 政务公开相关路径
            "/art/",  # 江苏等地CMS系统的文章路径格式
            "xzgfxwj", "qtwj", "gstz",  # 四川等地：行政规范性文件、其他文件、公示通知
            "kjdt", "tzgg",  # 湖北等地：科技动态、通知公告
        ]

        # 排除导航、首页、搜索等非内容链接
        exclude_keywords = [
            "index.html", "index.htm", "home.htm",
            "javascript:", "#", "search", "login",
            "sitemap", "导航", "首页", "搜索"
        ]

        # 检查是否包含政策关键词
        has_keyword = any(kw in href.lower() for kw in policy_keywords)

        # 检查是否包含日期模式（如 2024, 2025, /202411/, ./202511/ 等）
        import re
        has_date_pattern = bool(re.search(r'202[0-9]', href))

        # 检查是否为排除项
        is_excluded = any(kw in href.lower() or kw in text for kw in exclude_keywords)

        if (has_keyword or has_date_pattern) and not is_excluded:
            full_url = urljoin(base_url, href)
            # 确保是同域名或政府域名
            parsed = urlparse(full_url)
            if "gov.cn" in parsed.netloc or "gd.gov.cn" in parsed.netloc:
                links.append(full_url)

    # 去重并保持顺序
    unique_links = list(dict.fromkeys(links))
    logger.debug(f"[{province_name}] 提取到{len(unique_links)}个候选链接")

    return unique_links


def extract_detail_page_generic(html: str, url: str, province_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    通用详情页信息提取（适应多种网站结构）

    策略：
    1. 多重选择器fallback提取标题
    2. 多重选择器fallback提取正文
    3. 尝试提取元数据（发布日期、发文机关、文号等）
    4. 构建标准化文档对象
    """
    soup = BeautifulSoup(html, "lxml")

    # === 提取标题 ===
    title = ""
    title_selectors = [
        ("h1", None),
        ("div", {"class": "xxgk_content_title"}),  # 上海市
        ("div", {"class": "title"}),
        ("div", {"class": lambda x: x and "title" in str(x).lower()}),
        ("span", {"class": "title"}),
        ("p", {"class": "title"}),
    ]

    for tag, attrs in title_selectors:
        if attrs:
            title_elem = soup.find(tag, attrs)
        else:
            title_elem = soup.find(tag)

        if title_elem:
            title = title_elem.get_text(strip=True)
            if title:
                break

    # === 提取正文 ===
    content_html = ""
    content_text = ""

    content_selectors = [
        ("div", {"class": "xxgk_content_nr"}),  # 上海市
        ("div", {"id": "ivs_content"}),  # 上海市备选
        ("div", {"id": "content"}),
        ("div", {"class": "content"}),
        ("div", {"class": lambda x: x and "content" in str(x).lower()}),
        ("div", {"id": "article"}),
        ("div", {"class": "article"}),
        ("td", {"class": "content"}),
        ("div", {"id": "zoom"}),  # 常见政府网站内容区域
    ]

    for tag, attrs in content_selectors:
        content_elem = soup.find(tag, attrs)
        if content_elem:
            content_html = str(content_elem)
            content_text = content_elem.get_text(separator="\n", strip=True)
            if content_text and len(content_text) > 50:  # 确保不是空内容
                break

    # 如果仍未找到内容，尝试提取body中最大的文本块
    if not content_text or len(content_text) < 50:
        body = soup.find("body")
        if body:
            # 移除导航、页脚等
            for unwanted in body.find_all(["nav", "header", "footer", "aside", "script", "style"]):
                unwanted.decompose()
            content_text = body.get_text(separator="\n", strip=True)
            content_html = str(body)

    # === 提取元数据 ===
    pub_date = ""
    issuer = ""
    doc_no = ""

    # 查找发布日期（多种格式）
    date_patterns = [
        ("span", {"class": lambda x: x and "date" in x.lower()}),
        ("div", {"class": lambda x: x and "date" in x.lower()}),
        ("td", {"class": lambda x: x and "date" in x.lower()}),
        ("span", {"id": lambda x: x and "date" in x.lower()}),
    ]

    for tag, attrs in date_patterns:
        date_elem = soup.find(tag, attrs)
        if date_elem:
            pub_date = date_elem.get_text(strip=True)
            if pub_date:
                break

    # 查找发文机关
    issuer_patterns = [
        ("span", {"class": lambda x: x and "source" in x.lower()}),
        ("span", {"class": lambda x: x and "issuer" in x.lower()}),
    ]

    for tag, attrs in issuer_patterns:
        issuer_elem = soup.find(tag, attrs)
        if issuer_elem:
            issuer = issuer_elem.get_text(strip=True)
            if issuer:
                break

    # 如果未找到，使用省份名称作为默认发文机关
    if not issuer:
        issuer = province_info.get("region", "")

    # === 构建文档对象 ===
    province_name = province_info.get("region", "未知省份")
    adcode = province_info.get("adcode_prov", "")

    doc = {
        "doc_id": f"prov_{adcode}_{sha256_text(url)[:16]}",
        "title": title,
        "pub_date": pub_date,
        "issuer": issuer,
        "doc_no": doc_no,
        "category": "省级政策",
        "status": "现行",
        "source_url": url,
        "html": content_html,
        "content_text": content_text,
        "sha256": sha256_text(content_text),
        "retrieved_at": datetime.now().isoformat(),
        "region": f"CN-{adcode}",
        "province_name": province_name,
        "adcode_prov": adcode,
    }

    # === 验证必需字段 ===
    if not title or not content_text:
        logger.warning(f"[{province_name}] [SKIP] 缺少必要字段: {url}")
        return None

    if len(content_text) < 100:
        logger.warning(f"[{province_name}] [SKIP] 内容过短(<100字符): {url}")
        return None

    return doc


def crawl_province(
    province_config: Dict[str, Any],
    session,
    checkpoint: Dict[str, Any],
    max_pages: int = 3,
    test_mode: bool = True
):
    """
    爬取单个省份的政策文档

    Args:
        province_config: 省份配置字典
        session: HTTP会话
        checkpoint: 断点状态
        max_pages: 最大爬取页数（测试模式默认3页）
        test_mode: 是否为测试模式
    """
    province_name = province_config.get("region", "未知省份")
    adcode = province_config.get("adcode_prov", "")
    list_url = province_config.get("list_url", "")

    if not list_url:
        logger.warning(f"[{province_name}] 跳过：未配置list_url")
        return

    logger.info("=" * 60)
    logger.info(f"开始爬取: {province_name} (Adcode: {adcode})")
    logger.info(f"列表URL: {list_url}")
    logger.info("=" * 60)

    # 创建输出目录
    output_dir = OUTPUT_BASE / province_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # 获取checkpoint状态
    province_key = f"{province_name}_{adcode}"
    resume_page = checkpoint.get(province_key, {}).get("next_page", 1)

    # 统计信息
    total_links = 0
    total_saved = 0
    total_skipped = 0

    # 确定页数范围
    start_page = resume_page
    end_page = max_pages if test_mode else province_config.get("max_pages", 10)

    logger.info(f"[{province_name}] 页面范围: {start_page}-{end_page}")

    # 遍历列表页
    for page_num in range(start_page, end_page + 1):
        # 构建列表URL（支持多种分页格式）
        if "{page}" in list_url:
            # 格式1: mindex_{page}.html
            if page_num == 1:
                current_list_url = list_url.replace("mindex_{page}", "index").replace("_{page}", "")
            else:
                current_list_url = list_url.replace("{page}", str(page_num))
        else:
            # 无分页或单页列表
            current_list_url = list_url
            if page_num > 1:
                logger.info(f"[{province_name}] 无分页配置，跳过第{page_num}页")
                break

        logger.info(f"[{province_name}] 正在爬取第{page_num}页: {current_list_url}")

        try:
            # 获取列表页
            response = polite_get(session, current_list_url)
            response.raise_for_status()

            # 提取详情页链接
            detail_urls = extract_list_page_generic(
                response.text, current_list_url, province_name
            )

            total_links += len(detail_urls)
            logger.info(f"[{province_name}] 第{page_num}页找到{len(detail_urls)}个链接")

            if not detail_urls:
                logger.warning(f"[{province_name}] 第{page_num}页未找到链接，可能已到达末页")
                break

            # 处理每个详情页
            for detail_url in detail_urls:
                try:
                    response = polite_get(session, detail_url)
                    response.raise_for_status()

                    # 提取文档信息
                    doc = extract_detail_page_generic(
                        response.text, detail_url, province_config
                    )

                    if not doc:
                        total_skipped += 1
                        continue

                    # SHA256去重
                    sha = doc["sha256"]
                    output_file = output_dir / f"{sha[:16]}.json"

                    if output_file.exists():
                        logger.info(f"[{province_name}] [SKIP] 文档已存在(SHA256去重): {doc['title'][:30]}...")
                        total_skipped += 1
                        continue

                    # 保存文档
                    save_json(doc, output_file)
                    total_saved += 1
                    logger.info(f"[{province_name}] [SAVE] {doc['title'][:50]}... -> {output_file.name}")

                except Exception as e:
                    logger.error(f"[{province_name}] 处理详情页失败 {detail_url}: {e}")
                    total_skipped += 1
                    continue

            # 更新checkpoint
            checkpoint[province_key] = {
                "next_page": page_num + 1,
                "last_update": datetime.now().isoformat(),
            }
            save_checkpoint(CHECKPOINT_PATH, checkpoint)

        except Exception as e:
            logger.error(f"[{province_name}] 处理列表页失败 第{page_num}页: {e}")
            break

    # 输出统计
    logger.info("=" * 60)
    logger.info(f"[{province_name}] 爬取完成")
    logger.info(f"[{province_name}] 总链接数: {total_links}")
    logger.info(f"[{province_name}] 保存文档: {total_saved}")
    logger.info(f"[{province_name}] 跳过文档: {total_skipped}")
    logger.info("=" * 60)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("PSC-Graph 省级政策爬虫启动")
    logger.info("=" * 60)

    # 加载配置
    provinces = load_config()

    # 创建会话（QPS=0.7，更保守）
    session = get_session(qps=0.7)

    # 加载checkpoint
    checkpoint = load_checkpoint(CHECKPOINT_PATH)

    # 检查是否有命令行参数指定省份
    if len(sys.argv) > 1:
        # 仅爬取指定省份
        target_province = sys.argv[1]
        provinces = [p for p in provinces if p.get("region") == target_province]
        if not provinces:
            logger.error(f"未找到省份配置: {target_province}")
            return
        logger.info(f"仅爬取指定省份: {target_province}")

    # 检查是否为测试模式
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    max_pages = 3 if test_mode else 10

    if test_mode:
        logger.info("⚠️  测试模式：每个省份仅爬取3页")

    # 遍历所有省份
    for i, province_config in enumerate(provinces, 1):
        logger.info(f"\n进度: [{i}/{len(provinces)}] 省份")

        try:
            crawl_province(province_config, session, checkpoint, max_pages, test_mode)
        except Exception as e:
            province_name = province_config.get("region", "未知")
            logger.error(f"[{province_name}] 爬取失败: {e}")
            continue

    # 汇总统计
    total_files = sum(1 for _ in OUTPUT_BASE.rglob("*.json"))
    logger.info("\n" + "=" * 60)
    logger.info("所有省份爬取完成 ✅")
    logger.info(f"总计保存文档: {total_files}条")
    logger.info(f"输出目录: {OUTPUT_BASE}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
