#!/bin/bash
# 快速批量测试所有31个省份
# 每个省份仅爬取第1页前5个链接，超时45秒

echo "======================================================================"
echo "PSC-Graph 省份快速批量测试"
echo "======================================================================"
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 省份列表（按配置文件顺序）
provinces=(
    "广东省" "上海市" "江苏省" "浙江省" "山东省" "安徽省"
    "北京市" "河南省" "四川省" "重庆市"
    "天津市" "河北省" "山西省" "内蒙古自治区"
    "辽宁省" "吉林省" "黑龙江省"
    "福建省" "江西省" "湖北省" "湖南省"
    "广西壮族自治区" "海南省"
    "贵州省" "云南省" "西藏自治区"
    "陕西省" "甘肃省" "青海省" "宁夏回族自治区" "新疆维吾尔自治区"
)

success_count=0
fail_count=0

for i in "${!provinces[@]}"; do
    prov="${provinces[$i]}"
    num=$((i+1))

    echo "[$num/31] 测试 $prov ..."

    # 运行爬虫（仅1页，超时45秒）
    timeout 45s python3 scripts/crawl_provinces.py "$prov" --test > /dev/null 2>&1
    exit_code=$?

    # 检查结果
    doc_count=$(find "corpus/raw/policy_provinces/$prov" -name "*.json" 2>/dev/null | wc -l)

    if [ $doc_count -gt 0 ]; then
        echo "  ✅ 成功 ($doc_count 份文档)"
        ((success_count++))
    elif [ $exit_code -eq 124 ]; then
        echo "  ⏱️  超时"
        ((fail_count++))
    else
        echo "  ❌ 失败"
        ((fail_count++))
    fi

    echo ""
done

echo "======================================================================"
echo "测试汇总"
echo "======================================================================"
echo "总计: 31 个省份"
echo "✅ 成功: $success_count"
echo "❌ 失败: $fail_count"
echo "成功率: $(awk "BEGIN {printf \"%.1f\", $success_count/31*100}")%"
echo ""
echo "结束时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"
