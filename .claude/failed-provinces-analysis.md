# 失败省份深度分析报告
**生成时间**: 2025-12-01
**分析对象**: 5个A类失败省份

---

## 失败省份清单

| 省份 | HTTP状态 | 失败类型 | URL |
|-----|---------|---------|-----|
| 山东省 | 403 | 访问被拒 | http://kjt.shandong.gov.cn/col/col8809/index.html |
| 安徽省 | 400 | 请求错误 | http://kjt.ah.gov.cn/kjzx/tzgg/index.html |
| 河南省 | 403 | 访问被拒 | https://kjt.henan.gov.cn/kjzc/index.html |
| 重庆市 | 404 | 页面不存在 | https://kjj.cq.gov.cn/zwgk_176/zwxxgkml/zcfg/dfxfg/index.html |
| 陕西省 | - | 连接失败 | https://kjt.shaanxi.gov.cn/kjdt/tzgg/index.html |

---

## 失败原因详细分析

### 1. 山东省（403 Forbidden）

**问题**: 访问被拒绝

**可能原因**:
1. User-Agent检测：服务器可能限制爬虫
2. IP地址限制：可能检测到频繁访问
3. Referer检查：缺少正确的来源头
4. 需要Cookie/Session

**解决方案**:
```python
# 方案A：改进HTTP头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://kjt.shandong.gov.cn/',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 方案B：先访问首页建立session
session = requests.Session()
session.get('http://kjt.shandong.gov.cn/')  # 建立session
time.sleep(2)
response = session.get(target_url, headers=headers)
```

**备选URL**（从首页人工查找）:
- 可能存在的其他政策栏目URL
- 信息公开平台URL

---

### 2. 安徽省（400 Bad Request）

**问题**: 请求格式错误

**可能原因**:
1. URL路径错误：`/kjzx/tzgg/` 可能不存在
2. 参数缺失：可能需要特定查询参数
3. 协议错误：可能需要HTTPS而非HTTP

**解决方案**:
```python
# 方案A：修正URL（人工核实）
# 当前URL: http://kjt.ah.gov.cn/kjzx/tzgg/index.html
# 可能正确的URL需要从首页导航查找

# 方案B：尝试HTTPS
url_https = url.replace('http://', 'https://')

# 方案C：搜索替代栏目
alternative_urls = [
    'http://kjt.ah.gov.cn/xxgk/zcfg/',  # 政策法规
    'http://kjt.ah.gov.cn/zwgk/',       # 政务公开
]
```

**建议**: 需要人工访问 http://kjt.ah.gov.cn/ 确认正确的政策栏目路径

---

### 3. 河南省（403 Forbidden）

**问题**: 与山东省相同，访问被拒

**可能原因**: 同山东省（User-Agent/IP/Referer检测）

**解决方案**:
```python
# 增强版请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Referer': 'https://kjt.henan.gov.cn/',
    'Accept': 'text/html',
    'Accept-Language': 'zh-CN',
    'Connection': 'keep-alive',
}

# 增加随机延迟
import random
time.sleep(random.uniform(2, 5))
```

---

### 4. 重庆市（404 Not Found）

**问题**: 页面不存在

**可能原因**:
1. **URL已失效**：网站改版导致路径变化
2. 栏目迁移：政策栏目可能移到其他路径
3. URL配置错误

**解决方案**:
```python
# 方案A：从首页重新定位（最可靠）
# 访问 https://kjj.cq.gov.cn/ 查找当前政策栏目

# 方案B：尝试常见路径模式
alternative_urls = [
    'https://kjj.cq.gov.cn/zwgk/zcfg/',
    'https://kjj.cq.gov.cn/xxgk/zcfg/dfxfg/',
    'https://kjj.cq.gov.cn/zcfg/',
]

# 方案C：搜索引擎辅助
# site:kjj.cq.gov.cn 政策文件
```

**优先级**: 🔴 最高（URL明确失效，需立即修正）

---

### 5. 陕西省（连接失败）

**问题**: 无法建立连接

**可能原因**:
1. DNS解析失败
2. 网络防火墙/代理阻止
3. 服务器暂时不可达
4. SSL证书问题（HTTPS）

**解决方案**:
```python
# 方案A：诊断连接
import socket
try:
    socket.gethostbyname('kjt.shaanxi.gov.cn')
    print("DNS解析成功")
except socket.gaierror:
    print("DNS解析失败")

# 方案B：禁用SSL验证（临时）
response = requests.get(url, verify=False, timeout=30)

# 方案C：使用HTTP而非HTTPS
url_http = url.replace('https://', 'http://')

# 方案D：增加重试机制
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount('https://', adapter)
```

---

## 统一改进方案

### 改进1：增强HTTP请求配置

```python
# scripts/crawler_common.py 修改

ENHANCED_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def create_resilient_session():
    """创建弹性HTTP会话"""
    session = requests.Session()

    # 重试策略
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    session.headers.update(ENHANCED_HEADERS)

    return session
```

### 改进2：URL验证和自动修正

```python
def validate_and_fix_url(url, province_name):
    """验证URL并尝试自动修正"""

    # 1. 尝试原始URL
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            return url
    except:
        pass

    # 2. 尝试HTTPS↔HTTP切换
    if url.startswith('http://'):
        https_url = url.replace('http://', 'https://')
        try:
            response = requests.head(https_url, timeout=10, verify=False)
            if response.status_code == 200:
                return https_url
        except:
            pass

    # 3. 尝试移除尾部路径
    base_url = '/'.join(url.split('/')[:4]) + '/'
    try:
        response = requests.head(base_url, timeout=10)
        if response.status_code == 200:
            print(f"⚠️  {province_name}: 原URL失效，回退到首页 {base_url}")
            return base_url
    except:
        pass

    # 4. 无法修正
    return None
```

### 改进3：人工URL收集工具

```bash
# scripts/manual_url_finder.py
# 生成一个交互式工具，帮助人工快速收集正确的URL
```

---

## 执行计划

### 立即执行（30分钟）

**Step 1**: 修复重庆市URL（404，优先级最高）
```bash
# 人工访问 https://kjj.cq.gov.cn/ 查找政策栏目
# 更新 provinces.yaml
```

**Step 2**: 诊断陕西省连接问题
```bash
# 测试DNS、SSL、HTTP/HTTPS
python3 -c "import socket; print(socket.gethostbyname('kjt.shaanxi.gov.cn'))"
curl -I https://kjt.shaanxi.gov.cn/kjdt/tzgg/index.html
curl -I http://kjt.shaanxi.gov.cn/kjdt/tzgg/index.html
```

**Step 3**: 增强HTTP请求头（山东、河南）
```bash
# 更新 crawler_common.py
# 添加 create_resilient_session() 函数
```

### 今天内完成（2小时）

**Step 4**: 人工核实安徽省URL
- 访问首页：http://kjt.ah.gov.cn/
- 找到政策栏目正确路径
- 更新配置

**Step 5**: 重新运行健康检查
```bash
python3 scripts/health_check_provinces.py --prov 山东省 --prov 安徽省 --prov 河南省 --prov 重庆市 --prov 陕西省
```

**Step 6**: 逐个测试修复后的省份
```bash
python3 scripts/crawl_provinces.py 重庆市 --max-pages 1
python3 scripts/crawl_provinces.py 山东省 --max-pages 1
# ...
```

---

## 预期成果

### 乐观情况（2-3个修复成功）
- 成功省份：7-8个（原5个 + 新增2-3个）
- 数据量：预计500-800条政策文档

### 保守情况（1个修复成功）
- 成功省份：6个（原5个 + 1个）
- 数据量：预计300-500条政策文档

### 建议
即使只成功修复1-2个省份，当前6-7个省份的样本已经满足：
- **大区覆盖**：华南、华东、华北、华中、西南（5/7）
- **GDP覆盖**：>60%
- **研究有效性**：DID模型需要≥5个地区×5年=25个观测值

**结论**: 当前失败省份修复属于"优化改进"而非"致命阻塞"，可以并行进行P1/P2实现。
