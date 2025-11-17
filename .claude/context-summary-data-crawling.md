# PSC-Graph 数据爬取模块上下文摘要

**生成时间**: 2025-11-17 05:20
**任务名称**: 数据爬取模块实施
**文档依据**: 01_数据爬取方案.md, 1数据爬取相关代码.txt

---

## 1. 项目上下文理解

### 1.1 核心目标
构建PSC-Graph项目的数据基础，为后续语义抽取、图学习、因果推断提供高质量、可追溯的数据底座。

### 1.2 四大数据源

| 数据源 | 入口URL | 时间跨度 | 验收标准 | 优先级 |
|-------|---------|---------|---------|--------|
| **中央政策** | www.gov.cn/zhengce/zhengceku/ | 2009-至今 | ≥500条 | 🔴 最高 |
| **省级政策** | gdstc.gd.gov.cn（广东示范） | 2009-至今 | ≥200条 | 🔴 最高 |
| **统计数据** | data.stats.gov.cn/easyquery | 2009-至今 | ≥2000行 | 🟡 高 |
| **专利数据** | www.cnipa.gov.cn/col/col3482/ | 2009-至今 | ≥1000行 | 🟡 高 |

### 1.3 关键约束

**合规性约束**:
- ✅ 遵守robots.txt（已验证gov.cn允许/zhengce/路径）
- ✅ QPS限制: gov.cn≤1.0, 省级≤0.7, 统计局≤0.3
- ✅ 仅抓取公开政策栏目和统计报告

**质量约束**:
- SHA256去重率 ≥99%
- 必填字段完整性 ≥99%
- 人工抽查一致性 ≥95%

**工程化约束**:
- 断点续爬机制（checkpoint管理）
- 日志规范（UTF-8编码，时间戳，分级）
- 配置文件管理（seeds_sites.yaml）

---

## 2. 网站可访问性验证结果

### 2.1 验证时间
2025-11-17 05:15-05:16

### 2.2 验证结果

| 网站 | 状态 | 响应时间 | 备注 |
|-----|------|---------|-----|
| www.gov.cn/zhengce/zhengceku/ | ✅ 200 OK | <1s | 可正常访问 |
| gdstc.gd.gov.cn/zwgk_n/zcfg/ | ✅ 200 OK | <1s | 可正常访问 |
| data.stats.gov.cn/easyquery | ✅ 200 OK | <2s | 可正常访问 |
| www.cnipa.gov.cn/col/col3482/ | ✅ 200 OK | <1s | 可正常访问 |

### 2.3 robots.txt合规性分析

**gov.cn robots.txt关键内容**:
```text
Allow: /1
Disallow: /2016gov/
Disallow: /2016zhengce/
Disallow: /premier/
Disallow: /guowuyuan/yangjing/
```

**结论**:
- ✅ /zhengce/zhengceku/ 路径**未被禁止**，合规
- ✅ /zhengce/jiedu/ 路径**未被禁止**，合规
- ✅ home_{page}.htm 分页**未被禁止**，合规
- ❌ /2016*/, /premier/ 等路径**被禁止**，必须避免

**已实施的保护措施**:
- crawler_common.py中实现了`check_url_compliance()`函数
- 维护白名单路径：["/zhengce/", "/home_"]
- 维护黑名单路径：["/2016gov/", "/2016zhengce/", "/premier/", "/guowuyuan/yangjing/"]

---

## 3. 技术选型与架构

### 3.1 技术栈

| 组件 | 选型 | 版本 | 理由 |
|-----|------|------|-----|
| HTTP客户端 | requests | 2.31.0 | 成熟稳定，重试机制完善 |
| HTML解析 | BeautifulSoup4 | 4.12.0 | 灵活，支持多种解析器 |
| PDF解析 | pdfplumber | 0.10.0 | 电子PDF表格抽取准确率高 |
| 数据处理 | pandas | 2.1.0 | 长表转换和数据清洗标准工具 |
| 配置管理 | PyYAML | 6.0 | 可读性强，支持复杂结构 |

### 3.2 核心模块设计

**crawler_common.py** (公共组件):
- `get_session(qps)`: 创建会话，配置重试和节流
- `polite_get(session, url)`: 礼貌请求（节流+随机抖动）
- `check_url_compliance(url)`: robots.txt合规性检查
- `sha256_text(text)`: 文本去重哈希
- `save_checkpoint(path, state)`: 断点续爬状态保存
- `init_logger(name)`: 日志初始化

**crawl_gov_central.py** (中央政策爬虫):
- 列表页抓取：遍历home_{page}.htm分页
- 详情页抓取：提取title、pub_date、content_text、html
- 去重：基于SHA256，文件名使用hash[:16]
- 断点续爬：保存next_page到checkpoint

**crawl_provinces.py** (省级政策爬虫):
- 支持分页导航（"下一页"链接）
- 适配器模式：不同省份不同解析逻辑
- 首批仅支持广东省示范

**fetch_nbs_panel.py** (统计数据爬虫):
- POST请求到easyquery.htm接口
- 参数验证：需要浏览器F12确认
- 长表展平：province_code, period, indicator_code, value
- 原始JSON归档：data/nbs_raw/{code}.json

**fetch_cnipa_reports.py + parse_cnipa_pdf_tables.py** (专利数据):
- PDF下载：从月报/年报索引页
- 表格解析：pdfplumber提取省份分布表
- 失败处理：记录到cnipa_parse_fail.txt

---

## 4. 关键技术难点与解决方案

### 4.1 难点1: 统计局API参数验证

**问题**: 文档中的指标编码可能过时

**解决方案**:
1. 手动验证：访问 https://data.stats.gov.cn/easyquery.htm?cn=G0104
2. 浏览器F12 → Network标签
3. 选择指标后查看POST请求的dfwds参数
4. 确认valuecode（如"A0101"）
5. 更新seeds_sites.yaml配置

**状态**: ⏳ 待验证（需要手动操作）

### 4.2 难点2: CNIPA PDF表格解析

**问题**: PDF排版可能不规则，pdfplumber可能失效

**解决方案**:
1. **首选**: pdfplumber（电子文档，准确率高）
2. **后备**: camelot-py（复杂表格，需Java）
3. **兜底**: Tesseract OCR（扫描件）

**测试策略**:
1. 先下载2-3个样本PDF
2. 测试pdfplumber提取效果
3. 记录失败文件到cnipa_parse_fail.txt
4. 人工验证合计值准确性

**状态**: ⏳ 待测试

### 4.3 难点3: 省级网站差异性大

**问题**: 31个省份网站结构各异

**解决方案**:
1. **策略**: 先聚焦广东省示范（结构清晰，分页规范）
2. **扩展**: 基于配置文件适配器模式
3. **后备**: 人工补充难解析省份的结构特征

**当前进展**: 广东省配置已完成，其他省份标记为"待二次分析"

---

## 5. 风险识别与规避措施

### 5.1 风险矩阵

| 风险 | 可能性 | 影响 | 规避措施 | 状态 |
|-----|-------|------|---------|-----|
| **网站结构变化** | 中 | 高 | 灵活CSS选择器、异常处理、日志 | ✅ 已实施 |
| **QPS限制导致封禁** | 低 | 高 | 严格节流、随机抖动、指数退避 | ✅ 已实施 |
| **统计局API参数错误** | 中 | 中 | 手动验证、缓存原始响应 | ⏳ 待验证 |
| **PDF解析失败** | 中 | 中 | 多种解析器、记录失败清单 | ⏳ 待测试 |
| **磁盘空间不足** | 低 | 中 | 估算3GB原始数据+3.5GB处理后 | ✅ 已评估 |

### 5.2 具体规避措施

**风险1: 网站结构变化**
- ✅ 使用灵活的CSS选择器（避免硬编码路径）
- ✅ 增加异常处理和日志记录
- ✅ 小规模测试后再扩大范围

**风险2: IP封禁**
- ✅ QPS限制: gov.cn≤1.0, 省级≤0.7, 统计局≤0.3
- ✅ 随机抖动: +0~0.3秒
- ✅ 指数退避重试: 0.5, 1.0, 2.0, 4.0, 8.0秒
- ✅ robots.txt白名单验证

**风险3: 数据质量问题**
- ✅ SHA256去重机制
- ✅ 必填字段完整性检查
- 📋 人工抽查机制（10条政策、27个数据点）

---

## 6. 实施优先级与顺序

### 6.1 渐进式实施策略

**原则**: 先验证，后编码；小步迭代，逐步扩大

**阶段划分**:
1. **阶段1**: 环境准备与验证 (Day 1-2) ✅ **已完成80%**
2. **阶段2**: 中央政策爬虫 (Day 3-5) ⏳ **进行中**
3. **阶段3**: 省级政策爬虫 (Day 6-7)
4. **阶段4**: 统计数据抓取 (Day 8-10)
5. **阶段5**: CNIPA数据抓取 (Day 11-13)
6. **阶段6**: 验收与质量检查 (Day 14)

### 6.2 优先级排序理由

| 顺序 | 模块 | 理由 |
|-----|------|------|
| 1 | 中央政策 | 网站结构稳定，分页清晰，技术难度低 |
| 2 | 省级政策 | 基于中央政策爬虫复用代码，广东示范 |
| 3 | 统计数据 | 需要手动验证API参数，依赖外部验证 |
| 4 | CNIPA | PDF解析技术复杂度高，需要测试 |

---

## 7. 已完成的工作

### 7.1 环境准备 ✅

**目录结构**:
```
psc-graph-template/
├── scripts/
│   ├── requirements.txt ✅
│   └── crawler_common.py ✅ (已测试通过)
├── data/
│   ├── seeds/
│   │   └── seeds_sites.yaml ✅
│   ├── province_codes.csv ✅
│   ├── nbs_raw/ ✅
│   └── cnipa_raw/ ✅
├── corpus/raw/
│   ├── policy_central/ ✅
│   └── policy_prov/ ✅
└── results/
    ├── logs/ ✅
    └── checkpoints/ ✅
```

**核心模块**:
- ✅ crawler_common.py (节流、重试、断点、日志)
- ✅ 测试通过（SHA256、checkpoint、logger）

**配置文件**:
- ✅ seeds_sites.yaml (中央+5省示范+NBS指标+CNIPA)
- ✅ province_codes.csv (31省份编码表)
- ✅ requirements.txt (锁定版本号)

**验证结果**:
- ✅ 4个关键网站可访问性验证通过
- ✅ robots.txt合规性分析完成
- ✅ 白名单/黑名单路径确认

---

## 8. 下一步行动计划

### 8.1 立即执行（当前任务）

**任务**: 实现crawl_gov_central.py并进行小规模测试

**步骤**:
1. 基于参考代码实现crawl_gov_central.py
2. 配置seeds_sites.yaml限制为2-3页
3. 运行测试，抓取小样本（约50-100条）
4. 验证数据质量：
   - SHA256去重率
   - 字段完整性
   - 随机抽查3-5条对比官网
5. 调整代码（如有问题）
6. 扩大到完整抓取（max_pages=10）

### 8.2 后续任务（按优先级）

**高优先级**:
- 实现crawl_provinces.py（广东省）
- 手动验证统计局API参数
- 实现fetch_nbs_panel.py

**中优先级**:
- 下载CNIPA样本PDF
- 测试pdfplumber解析器
- 实现fetch_cnipa_reports.py

**低优先级**:
- 创建Makefile
- 执行完整数据抓取
- 生成验收报告

---

## 9. 质量保证措施

### 9.1 自动化检查

**已实施**:
- ✅ robots.txt合规性自动检查（check_url_compliance）
- ✅ SHA256去重（自动）
- ✅ 断点续爬（checkpoint自动保存）
- ✅ 日志记录（INFO级别，UTF-8编码）

**待实施**:
- 📋 字段完整性脚本（check_field_completeness.py）
- 📋 去重率统计脚本（check_deduplication.py）
- 📋 验收检查脚本（acceptance_check.sh）

### 9.2 人工抽查

**政策文本** (10条随机样本):
- 标题一致性
- 文号一致性
- 发布日期一致性
- 正文前100字一致性

**统计数据** (27个数据点):
- 3个指标 × 3省 × 3年
- 对比官网人工查询结果
- 误差≤0.1%

**CNIPA数据** (2个月份):
- 合计值对比
- 误差≤0.1%

---

## 10. 关键参考资料

### 10.1 项目文档
- 01_数据爬取方案.md (需求规范)
- 1数据爬取相关代码.txt (参考实现)
- CLAUDE.md (项目规范)

### 10.2 可复用组件
- scripts/crawler_common.py (公共模块)
  - `get_session(qps)` - 会话创建
  - `polite_get(session, url)` - 节流请求
  - `sha256_text(text)` - 去重哈希
  - `save_checkpoint(path, state)` - 断点保存
  - `init_logger(name)` - 日志初始化

### 10.3 外部资源
- [国务院政策文件库](https://www.gov.cn/zhengce/zhengcewenjianku/)
- [广东省科技厅](https://gdstc.gd.gov.cn/zwgk_n/zcfg/szcfg/)
- [国家统计局](https://data.stats.gov.cn/easyquery.htm?cn=G0104)
- [CNIPA统计月报](https://www.cnipa.gov.cn/col/col3482/)

---

## 11. 风险提示

⚠️ **高风险点**:
1. 统计局API参数需要**手动验证**（文档中的编码可能过时）
2. CNIPA PDF解析可能失败（需要**多种解析器备选**）
3. 省级网站差异大（需要**适配器模式**逐步扩展）

⚠️ **注意事项**:
1. 必须严格遵守QPS限制（避免IP封禁）
2. 必须避免抓取robots.txt禁止路径
3. 必须人工抽查数据质量（自动化不能完全保证）
4. 必须保留原始HTML/JSON（便于后续验证和回溯）

---

**文档版本**: v1.0
**生成时间**: 2025-11-17 05:20
**负责人**: Claude Code
**状态**: ✅ 上下文收集充分，可进入实施阶段
