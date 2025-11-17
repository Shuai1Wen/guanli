#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# PSC-Graph 项目环境初始化脚本
#
# 功能:
# - 创建Python虚拟环境
# - 安装Python依赖
# - 安装R包（用于后续因果推断）
# - 创建必要目录结构
#
# 作者: PSC-Graph数据工程组
# 日期: 2025-11-17
#
# 使用方法:
#   bash scripts/bootstrap.sh
#   或
#   make setup

set -euo pipefail

echo "========================================"
echo "PSC-Graph 项目环境初始化"
echo "========================================"

# 1. 检查Python版本
echo ""
echo "[1/6] 检查Python版本..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到python3命令"
    echo "请安装Python 3.9或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python版本: $PYTHON_VERSION"

# 2. 创建虚拟环境
echo ""
echo "[2/6] 创建Python虚拟环境..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ 虚拟环境创建成功: .venv/"
else
    echo "ℹ️  虚拟环境已存在: .venv/"
fi

# 3. 激活虚拟环境并安装依赖
echo ""
echo "[3/6] 安装Python依赖..."
source .venv/bin/activate

pip install --upgrade pip -q
pip install -r scripts/requirements.txt -q

echo "✅ Python依赖安装完成"

# 4. 检查R环境（可选，用于因果推断）
echo ""
echo "[4/6] 检查R环境（可选）..."
if command -v Rscript &> /dev/null; then
    R_VERSION=$(Rscript --version 2>&1 | head -1)
    echo "✅ R环境已安装: $R_VERSION"

    # 安装R包（静默模式）
    echo "   正在安装R包（did, didimputation）..."
    Rscript -e 'if (!requireNamespace("did", quietly=TRUE)) install.packages("did", repos="https://cloud.r-project.org", quiet=TRUE)' 2>/dev/null || true
    Rscript -e 'if (!requireNamespace("didimputation", quietly=TRUE)) install.packages("didimputation", repos="https://cloud.r-project.org", quiet=TRUE)' 2>/dev/null || true
    Rscript -e 'if (!requireNamespace("fixest", quietly=TRUE)) install.packages("fixest", repos="https://cloud.r-project.org", quiet=TRUE)' 2>/dev/null || true
    echo "✅ R包安装完成"
else
    echo "⚠️  未找到Rscript命令"
    echo "   R环境非必需（仅用于因果推断模块）"
    echo "   如需使用，请安装R 4.0+: https://www.r-project.org/"
fi

# 5. 创建必要目录结构
echo ""
echo "[5/6] 创建项目目录结构..."

# 数据目录
mkdir -p data/nbs_raw
mkdir -p data/cnipa_raw
mkdir -p data/seeds

# 语料目录
mkdir -p corpus/raw/policy_central/部门文件
mkdir -p corpus/raw/policy_central/政策解读
mkdir -p corpus/raw/policy_prov/广东省
mkdir -p corpus/raw/policy_prov/北京市
mkdir -p corpus/raw/policy_prov/上海市

# 索引目录
mkdir -p indexes/bm25
mkdir -p indexes

# 结果目录
mkdir -p results/logs
mkdir -p results/checkpoints

# 抽取结果目录
mkdir -p extractions

# 标注目录
mkdir -p annotations/to_annotate
mkdir -p annotations/annotator_A
mkdir -p annotations/annotator_B
mkdir -p annotations/adjudicated

# 模型目录
mkdir -p models

# Schema目录
mkdir -p schemas

# .claude工作目录
mkdir -p .claude

echo "✅ 目录结构创建完成"

# 6. 验证关键依赖
echo ""
echo "[6/6] 验证关键依赖..."
python3 -c "import requests, bs4, pdfplumber, pandas, yaml; print('✅ 所有Python依赖可用')"

# 验证Java（用于Lucene BM25索引）
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -1 | awk -F '"' '{print $2}')
    echo "✅ Java环境已安装: $JAVA_VERSION"
else
    echo "⚠️  未找到Java环境"
    echo "   Java非必需（仅用于BM25索引构建）"
    echo "   如需使用，请安装Java 17+: https://adoptium.net/"
fi

echo ""
echo "========================================"
echo "✅ 环境初始化完成！"
echo "========================================"
echo ""
echo "下一步操作:"
echo "  1. 激活虚拟环境: source .venv/bin/activate"
echo "  2. 运行爬虫测试: python scripts/crawl_gov_central.py"
echo "  3. 查看日志: tail -f results/logs/gov_central.log"
echo ""
echo "详细文档请参考: 01_数据爬取方案.md"
echo ""
