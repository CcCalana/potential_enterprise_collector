# 智联招聘爬虫使用说明

## 功能概述

本爬虫专门用于爬取智联招聘网站上**苏州工业园区人工智能相关岗位**的信息，基于Selenium实现，参考了[这个教程](https://blog.csdn.net/qq_74830852/article/details/148696690)进行开发。

## 主要特性

- ✅ 专门针对苏州工业园区人工智能岗位
- ✅ 使用Selenium自动化浏览器操作
- ✅ 支持数据库存储（PostgreSQL）
- ✅ 支持CSV文件导出
- ✅ 自动去重处理
- ✅ 随机延迟防止反爬虫
- ✅ 详细的错误处理和日志输出

## 环境要求

### 依赖安装

```bash
pip install selenium webdriver-manager
```

### 数据库配置

确保PostgreSQL数据库已启动，并且在`app/config.py`中配置了正确的数据库连接信息。

## 使用方法

### 1. 初始化数据库表

```bash
python init_zhilian_db.py
```

### 2. 运行爬虫

```bash
python zhilian_ai_scraper.py
```

### 3. 自定义参数

```python
from zhilian_ai_scraper import ZhilianAIScraper

scraper = ZhilianAIScraper()
jobs = scraper.scrape_jobs(
    keyword="人工智能",  # 搜索关键词
    city="苏州",        # 城市
    max_pages=5         # 最大爬取页数
)
```

## 数据结构

### 数据库表结构 (zhilian_jobs)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键ID |
| job_id | String(64) | 职位ID（唯一） |
| job_title | String(256) | 职位名称 |
| company_name | String(256) | 公司名称 |
| company_size | String(64) | 公司规模 |
| company_type | String(64) | 公司类型 |
| salary | String(64) | 薪资范围 |
| work_city | String(64) | 工作城市 |
| work_experience | String(64) | 工作经验要求 |
| education | String(64) | 学历要求 |
| job_type | String(32) | 工作类型 |
| job_description | Text | 职位描述 |
| job_requirements | Text | 职位要求 |
| welfare | Text | 福利待遇 |
| publish_time | DateTime | 发布时间 |
| job_url | String(512) | 职位链接 |
| raw_json | JSONB | 原始数据 |
| created_at | DateTime | 创建时间 |

### CSV导出字段

- 职位
- 薪资
- 公司
- 城市
- 工作经验
- 学历要求
- 公司规模
- 福利待遇
- 发布时间
- 职位链接

## 核心功能

### 1. 智能URL构建

```python
def build_search_url(self, keyword: str = "人工智能", city: str = "苏州", page: int = 1) -> str:
    """构建搜索URL"""
    # 苏州的城市代码是538
    encoded_keyword = quote(keyword)
    search_url = f"https://www.zhaopin.com/sou/jl538/kw{encoded_keyword}/p{page}"
    return search_url
```

### 2. 数据提取

- 职位基本信息（标题、公司、薪资等）
- 职位详细信息（描述、要求、福利等）
- 时间解析（今天、昨天、N天前）

### 3. 反爬虫机制

- 随机用户代理
- 随机延迟时间
- 页面滚动模拟
- 错误重试机制

## 注意事项

1. **Chrome浏览器**：需要安装Chrome浏览器，webdriver-manager会自动下载对应版本的ChromeDriver
2. **网络环境**：确保网络连接稳定，智联招聘可能有地域限制
3. **爬取频率**：内置了随机延迟机制，建议不要过于频繁地运行
4. **数据去重**：基于job_id进行去重，重复数据会被跳过
5. **错误处理**：程序会自动处理大部分异常情况，并输出详细的错误信息

## 扩展功能

### 1. 修改搜索关键词

```python
# 搜索机器学习相关岗位
jobs = scraper.scrape_jobs(keyword="机器学习")

# 搜索深度学习相关岗位
jobs = scraper.scrape_jobs(keyword="深度学习")
```

### 2. 修改城市范围

```python
# 搜索其他城市（需要修改城市代码）
jobs = scraper.scrape_jobs(city="上海")
```

### 3. 增加数据分析

可以结合现有的`content_analysis.py`对爬取的数据进行进一步分析。

## 文件结构

```
├── zhilian_ai_scraper.py      # 主爬虫文件
├── init_zhilian_db.py         # 数据库初始化脚本
├── README_ZHILIAN_SCRAPER.md  # 使用说明
└── app/
    ├── config.py              # 数据库配置
    └── models.py              # 数据模型
```

## 故障排除

### 1. 浏览器驱动问题

```bash
# 手动更新ChromeDriver
pip install --upgrade webdriver-manager
```

### 2. 数据库连接问题

检查`app/config.py`中的数据库配置是否正确。

### 3. 页面加载超时

可以增加等待时间：

```python
self.wait = WebDriverWait(self.driver, 20)  # 增加到20秒
```

## 更新日志

- **v1.0.0** (2024-01-XX): 初始版本，支持基本的职位信息爬取
- 基于DrissionPage和Selenium的双重实现
- 完整的数据库存储和CSV导出功能
- 智能的反爬虫机制

## 参考资料

- [智联招聘爬虫教程](https://blog.csdn.net/qq_74830852/article/details/148696690)
- [Selenium官方文档](https://selenium-python.readthedocs.io/)
- [WebDriver Manager](https://github.com/SergeyPirogov/webdriver_manager) 