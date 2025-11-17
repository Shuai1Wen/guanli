# -*- coding: utf-8 -*-
"""
PSC-Graph 爬虫公共组件模块

功能:
- 节流控制 (QPS限制)
- 重试机制 (指数退避)
- 断点续爬 (checkpoint管理)
- SHA256去重
- 日志管理

合规性:
- 遵守robots.txt规范
- 严格QPS限制: gov.cn≤1.0, 省级≤0.7, 统计局≤0.3
- 仅抓取公开政策栏目

作者: PSC-Graph数据工程组
日期: 2025-11-17
"""

import os
import time
import json
import hashlib
import random
import logging
from pathlib import Path
from typing import Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 日志目录
LOGDIR = Path("results/logs")
LOGDIR.mkdir(parents=True, exist_ok=True)

# robots.txt白名单路径 (www.gov.cn)
ALLOWED_PATHS = ["/zhengce/", "/home_"]
DISALLOWED_PATHS = ["/2016gov/", "/2016zhengce/", "/premier/", "/guowuyuan/yangjing/"]


def check_url_compliance(url: str) -> bool:
    """
    检查URL是否符合robots.txt规范

    参数:
        url: 待检查的URL

    返回:
        True表示允许访问, False表示禁止

    异常:
        如果URL在禁止列表中，记录警告但不抛出异常
    """
    if not url.startswith("https://www.gov.cn"):
        return True  # 非gov.cn域名，不做限制

    # 检查禁止路径
    for disallowed in DISALLOWED_PATHS:
        if disallowed in url:
            logging.warning(f"[ROBOTS] URL在禁止列表中: {url}")
            return False

    # 检查允许路径
    for allowed in ALLOWED_PATHS:
        if allowed in url:
            return True

    # 默认允许（除非在禁止列表中）
    return True


def get_session(qps: float = 1.0) -> requests.Session:
    """
    创建带重试机制的HTTP会话

    参数:
        qps: 每秒请求数限制 (默认1.0)

    返回:
        配置好的requests.Session对象

    说明:
        - 自动重试: 5次
        - 退避策略: 指数退避，基础延迟0.5秒
        - User-Agent: 标识为学术研究项目
        - 节流: 通过_PSC_SLEEP属性存储延迟时间
    """
    session = requests.Session()

    # 重试策略
    retries = Retry(
        total=5,                                    # 最多重试5次
        backoff_factor=0.5,                         # 指数退避: 0.5, 1.0, 2.0, 4.0, 8.0秒
        status_forcelist=[429, 500, 502, 503, 504], # 仅对这些状态码重试
        allowed_methods=["GET", "POST", "HEAD"]     # 允许重试的HTTP方法
    )

    # 请求头
    session.headers.update({
        "User-Agent": "PSC-Graph/0.1 (+research; contact: policy@psc-graph.org)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    })

    # 挂载适配器
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))

    # 存储QPS配置（用于polite_get函数）
    session._PSC_SLEEP = 1.0 / max(qps, 0.1)

    return session


def polite_get(session: requests.Session, url: str, **kwargs) -> requests.Response:
    """
    礼貌的HTTP GET请求（带节流和随机抖动）

    参数:
        session: requests.Session对象
        url: 请求URL
        **kwargs: 传递给requests.get的其他参数

    返回:
        requests.Response对象

    异常:
        requests.HTTPError: 如果响应状态码>=400

    说明:
        - 自动延迟: 根据session._PSC_SLEEP
        - 随机抖动: +0~0.3秒，避免规律性
        - 超时: 默认20秒
        - robots.txt检查: 自动检查URL合规性
    """
    # robots.txt合规性检查
    if not check_url_compliance(url):
        raise ValueError(f"[ROBOTS] URL违反robots.txt规范: {url}")

    # 节流延迟 + 随机抖动
    sleep_time = session._PSC_SLEEP + random.random() * 0.3
    time.sleep(sleep_time)

    # 默认超时20秒
    if "timeout" not in kwargs:
        kwargs["timeout"] = 20

    # 发起请求
    response = session.get(url, **kwargs)
    response.raise_for_status()  # 4xx/5xx抛出异常

    return response


def sha256_text(text: str) -> str:
    """
    计算文本的SHA256哈希值（用于去重）

    参数:
        text: 待计算哈希的文本

    返回:
        64位十六进制哈希字符串
    """
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def save_json(obj: Dict[str, Any], path: Path) -> None:
    """
    保存JSON对象到文件

    参数:
        obj: 待保存的字典对象
        path: 目标文件路径

    说明:
        - 自动创建父目录
        - UTF-8编码，ensure_ascii=False（保留中文）
        - 缩进2空格，便于阅读
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_checkpoint(path: Path) -> Dict[str, Any]:
    """
    加载断点续爬状态

    参数:
        path: checkpoint文件路径

    返回:
        状态字典，如果文件不存在返回空字典
    """
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkpoint(path: Path, state: Dict[str, Any]) -> None:
    """
    保存断点续爬状态

    参数:
        path: checkpoint文件路径
        state: 状态字典

    说明:
        - 自动创建父目录
        - 原子写入（先写临时文件，再重命名）
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # 原子写入：先写临时文件
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 重命名为正式文件
    temp_path.replace(path)


def init_logger(name: str = "crawler") -> logging.Logger:
    """
    初始化日志记录器

    参数:
        name: 日志记录器名称

    返回:
        配置好的Logger对象

    说明:
        - 日志级别: INFO
        - 输出: 文件（results/logs/{name}.log）+ 控制台
        - 格式: 时间戳 [级别] 消息
        - UTF-8编码
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # 文件处理器
    log_file = LOGDIR / f"{name}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)

    # 控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


if __name__ == "__main__":
    # 测试代码
    logger = init_logger("test")
    logger.info("crawler_common.py 模块加载成功")

    # 测试会话创建
    session = get_session(qps=1.0)
    logger.info(f"会话创建成功，节流延迟={session._PSC_SLEEP:.2f}秒")

    # 测试SHA256
    test_text = "测试文本内容"
    hash_value = sha256_text(test_text)
    logger.info(f"SHA256测试: {test_text} -> {hash_value[:16]}...")

    # 测试checkpoint
    test_ckpt = Path("results/checkpoints/test.json")
    save_checkpoint(test_ckpt, {"test": "ok", "page": 1})
    loaded = load_checkpoint(test_ckpt)
    logger.info(f"Checkpoint测试: {loaded}")

    logger.info("所有测试通过 ✅")
