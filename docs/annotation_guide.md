# PSC-Graph 政策标注指南

## 概览

本指南用于指导标注人员对政策文档进行五元组语义标注，确保标注质量达到项目要求。

---

## 一、标注目标

将政策文档转化为结构化的**五元组（Goal-Instrument-Actor-Strength-Evidence）**，用于后续的：
- 政策语义图谱构建
- 政策-产业关联分析
- 因果推断评估

---

## 二、五元组定义

### 1. Goal（政策目标）

**定义**：政策要达成的目标或任务

**要求**：
- 长度：5-500字符
- 描述清晰、具体
- 避免过于宽泛（如"促进发展"）

**示例**：
- ✓ "完善绿色贸易政策制度体系"
- ✓ "提升外贸企业绿色低碳发展能力"
- ✗ "促进经济发展"（过于宽泛）

---

### 2. Instrument（政策工具）

**定义**：政策使用的手段或措施

**类型（枚举多选）**：
- `funding`: 财政资金、补贴、奖励
- `tax`: 税收优惠、减免
- `land`: 用地支持、土地优惠
- `talent`: 人才政策、人才引进
- `standard`: 标准制定、监管规则
- `platform`: 平台建设、载体支持
- `ip`: 知识产权保护、专利支持
- `finance`: 投融资支持、金融服务
- `procurement`: 政府采购、优先采购
- `pilot`: 试点示范、先行先试
- `data_compute`: 数据资源、算力支持
- `other`: 其他（需注释说明）

**要求**：
- 至少选择1个
- 可多选
- 避免仅选择`other`

**示例**：
```json
"instrument": ["funding", "tax"]
"instrument": ["platform", "standard"]
```

---

### 3. Target_Actor（政策对象）

**定义**：政策面向的主体或受益方

**要求**：
- 长度：2-200字符
- 明确具体
- 可包含多个对象（用顿号或逗号分隔）

**示例**：
- ✓ "外贸企业"
- ✓ "外贸企业、中小企业"
- ✓ "高新技术企业、科研院所、高校"
- ✗ "企业"（过于宽泛）

---

### 4. Strength（政策强度）

**定义**：政策的约束性或强制程度

**分级**：
- `0`: **背景/无约束** - 仅为背景描述，无具体政策措施
- `1`: **倡议性** - 鼓励、引导、支持（无硬性要求）
- `2`: **一般性** - 有明确执行路径和责任主体
- `3`: **强约束** - 包含考核、问责、硬性资金指标

**示例**：
| 强度 | 文本示例 |
|------|----------|
| 0 | "近年来，绿色发展成为全球趋势..." |
| 1 | "鼓励企业开展绿色设计和生产" |
| 2 | "要加快完善绿色贸易政策制度体系，加强政策协同" |
| 3 | "对未达标企业实施问责，纳入年度考核" |

---

### 5. Evidence_Spans（证据段落）

**定义**：标注的原文证据（可追溯性）

**必填字段**：
- `start`: 证据起始字符位置（从0开始）
- `end`: 证据结束字符位置
- `from_doc`: 证据来源（`policy`=政策原文, `interpretation`=政策解读）
- `text`: 证据文本（便于人工查阅）

**要求**：
- **必须提供**：每个标注项至少1个证据
- `start < end`
- 证据文本需直接支撑标注结论
- 长度建议：20-300字符

**示例**：
```json
"evidence_spans": [
  {
    "start": 245,
    "end": 302,
    "from_doc": "interpretation",
    "text": "要加快完善绿色贸易政策制度体系，加强与产业、科技、财税、金融等政策协同配合"
  }
]
```

---

### 6. Confidence（置信度）

**定义**：标注人员对本次标注的确信程度

**范围**：0.0-1.0

**建议**：
- ≥0.90：非常确定，证据明确
- 0.70-0.89：较为确定，证据充分但稍有歧义
- <0.70：不确定，需要复核（**不建议提交**）

---

## 三、可选字段

### Region（地域）

**适用场景**：政策有明确地域限定

**字段**：
- `name`: 地区名称（如"北京市"、"广东省深圳市"）
- `admin_code`: 行政区划码（2位=省级, 4位=市级, 6位=区级）
- `uncertain`: 地域范围是否模糊（默认false）

**示例**：
```json
"region": {
  "name": "广东省",
  "admin_code": "44",
  "uncertain": false
}
```

---

### Timeframe（时间）

**适用场景**：政策有明确时间要求

**字段**：
- `effective_date`: 生效日期（YYYY-MM-DD）
- `expiry_date`: 失效日期
- `revision_of`: 修订自哪个文件的doc_id
- `revision_date`: 修订日期

**示例**：
```json
"timeframe": {
  "effective_date": "2024-10-17",
  "expiry_date": "2026-12-31"
}
```

---

### Support（配套措施）

**适用场景**：政策提供具体配套支持

**类型**：
- `funding`: 资金支持
- `tax`: 税收支持
- `quota`: 配额
- `land`: 用地支持
- `energy_quota`: 能源配额
- `emission_quota`: 排放配额
- `fast_track`: 快速通道
- `other`: 其他

**字段**：
- `type`: 类型（必填）
- `value`: 数值（可为null）
- `unit`: 单位（可为null）
- `note`: 备注

**示例**：
```json
"support": [
  {
    "type": "funding",
    "value": 500,
    "unit": "万元",
    "note": "单个项目最高支持额度"
  }
]
```

---

## 四、质量标准

### 4.1 必须遵守的规则

1. **每个标注项必须有证据**：`evidence_spans`不能为空
2. **证据必须准确**：`start`和`end`必须对应实际文本
3. **避免重复标注**：相同内容不要重复提取
4. **置信度门槛**：提交的标注`confidence ≥ 0.70`
5. **instrument不能仅为other**：如果选择`other`，必须有其他类型或在`note`中说明

### 4.2 质量门槛（CLAUDE.md要求）

- **实体/关系抽取 F1 ≥ 0.85**（开发集评估）
- **双标注人员 Cohen's κ ≥ 0.80**（一致性检验）
- **证据命中率 ≥ 0.90**（必须可追溯）

### 4.3 常见错误

❌ **错误1**：证据范围不准确
```json
// 错误
"evidence_spans": [{"start": 0, "end": 10, "text": "..."}]  // start/end不对应
```

❌ **错误2**：过于宽泛的goal
```json
// 错误
"goal": "促进发展"  // 太宽泛

// 正确
"goal": "提升外贸企业绿色低碳发展能力"
```

❌ **错误3**：仅选择other
```json
// 错误
"instrument": ["other"]

// 正确
"instrument": ["platform", "funding"]
```

---

## 五、标注流程

### 步骤1：阅读文档
- 完整阅读政策原文或解读
- 理解政策背景、目标和措施

### 步骤2：识别政策要点
- 标记关键段落
- 识别政策目标、工具、对象

### 步骤3：提取五元组
- 按照schema定义填写字段
- 确保每个字段准确、完整

### 步骤4：标记证据
- 精确定位证据文本的`start`和`end`
- 复制证据文本到`text`字段

### 步骤5：自检
- 运行`python scripts/validate_annotations.py`验证
- 检查所有必填字段是否完整
- 确认`confidence ≥ 0.70`

### 步骤6：提交
- 保存为`annotations/annotator_X/文件名.json`
- 文件名格式：`{doc_id}.json`

---

## 六、验证工具使用

### 验证单个标注人员
```bash
python scripts/validate_annotations.py --annotator A
```

### 计算双标注一致性
```bash
python scripts/validate_annotations.py --annotator all --compute-kappa
```

### 查看验证报告
```bash
cat .claude/verification-report.md
```

---

## 七、示例标注

完整示例见：`annotations/annotator_A/gov_central_7075381a9dd79cd9_example.json`

**简化示例**：
```json
{
  "doc_id": "gov_central_7075381a9dd79cd9",
  "source_title": "国务院常务会议解读 | 激活绿色贸易新动能",
  "annotations": [
    {
      "goal": "完善绿色贸易政策制度体系",
      "instrument": ["standard", "platform"],
      "target_actor": "外贸企业",
      "strength": 2,
      "evidence_spans": [
        {
          "start": 245,
          "end": 302,
          "from_doc": "interpretation",
          "text": "要加快完善绿色贸易政策制度体系..."
        }
      ],
      "confidence": 0.90
    }
  ],
  "annotator": "annotator_A",
  "annotated_at": "2025-11-17T10:15:00Z"
}
```

---

## 八、FAQ

**Q1: 一个文档应该提取多少个五元组？**
A: 没有固定数量，根据文档内容而定。通常1篇政策文档可提取3-10个五元组。

**Q2: 如何确定strength等级？**
A: 关键看是否有明确的责任主体、执行路径和考核机制。
- 有考核/问责 → 3
- 有明确执行路径 → 2
- 仅鼓励/引导 → 1
- 无具体措施 → 0

**Q3: 证据可以跨段落吗？**
A: 可以，但建议每个evidence_span保持在一个完整语义单元内（1-3句话）。

**Q4: 如果两个标注人员结果不一致怎么办？**
A: 由仲裁人员（adjudicator）进行最终裁定，结果保存到`annotations/adjudicated/`。

**Q5: 可以使用LLM辅助标注吗？**
A: 可以使用LLM辅助提取候选项，但**必须人工复核**并确保：
- 证据准确
- 置信度合理
- 符合质量标准

---

## 九、联系方式

- 技术支持：查看`.claude/operations-log.md`
- Schema定义：`schemas/policy_schema.json`
- 验证脚本：`scripts/validate_annotations.py`

---

**版本**: v1.0
**最后更新**: 2025-11-17
