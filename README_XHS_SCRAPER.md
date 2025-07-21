# 小红书爬虫 - 苏州工业园区企业信息抓取

## 🎯 项目目标
抓取小红书中关于苏州工业园区企业的相关笔记，按热度排序（点赞收藏量）获取高质量内容，包含完整正文，存储到 PostgreSQL 数据库。

## ✅ 已完成功能
- ✅ 完整的爬虫架构（数据库模型、签名系统、数据存储）
- ✅ **热度排序**: 按点赞收藏量排序，确保数据质量和可靠性
- ✅ **完整内容获取**: 获取笔记详情页面的完整正文内容
- ✅ xhs-mcp 签名系统集成（自动生成 X-s/X-t 签名）
- ✅ Selenium 自动化获取 search_id
- ✅ 数据库存储和查询
- ✅ 错误处理和日志记录
- ✅ Cookie 管理和验证

## 🚀 快速开始

### 1. 环境准备
```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python -c "from app.config import init_db; init_db()"
```

### 2. 更新 Cookie
**重要：必须先更新 Cookie 才能使用**

按照 `update_cookie_guide.md` 的步骤：
1. 访问 https://www.xiaohongshu.com 并登录
2. 按 F12 → Application → Cookies → 复制所有 Cookie
3. 更新 `app/tasks/cookies/xhs_cookies.txt` 文件

### 3. 运行爬虫

#### 简化版（推荐）
```bash
# 抓取苏州工业园区企业信息（3页）
python simple_xhs_scraper.py

# 自定义关键词和页数
python simple_xhs_scraper.py --keyword "苏州企业" --pages 5

# 不使用已知的 search_id
python simple_xhs_scraper.py --no-search-id
```

#### 完整版
```bash
# 使用完整的爬虫（包含 Selenium 自动获取 search_id）
python -m app.tasks.xiaohongshu_scraper "苏州工业园区企业" --pages 3
```

### 4. 查看结果
```bash
# 查看数据库中的笔记
python -c "
from app.config import SessionLocal
from app.models import XHSNote
with SessionLocal() as db:
    notes = db.query(XHSNote).all()
    print(f'共 {len(notes)} 条笔记')
    for note in notes[:5]:
        print(f'- {note.title} (👍{note.like_count})')
"
```

## 📁 项目结构
```
app/tasks/
├── xiaohongshu_scraper.py      # 主爬虫（含 Selenium）
├── selenium_xhs_helper.py      # Selenium 辅助类
├── cookies/
│   └── xhs_cookies.txt         # Cookie 文件
└── js/
    ├── sign_xhs.js            # 签名脚本
    └── origin_xhs_sign.js     # 原始签名脚本

simple_xhs_scraper.py           # 简化版爬虫
update_cookie_guide.md          # Cookie 更新指南
```

## 🔧 技术架构

### 数据获取策略
- **热度排序**：使用 `sort=popularity_descending` 参数按点赞收藏量排序
- **双重请求**：先获取笔记列表，再获取每条笔记的详情内容
- **完整内容**：通过 `/api/sns/web/v1/feed` 接口获取笔记正文

### 签名系统
- **xhs-mcp 集成**：自动生成 X-s/X-t 签名
- **ExecJS 调用**：Node.js 环境执行签名脚本
- **双重保障**：API 方式 + Selenium 方式

### 数据存储
- **PostgreSQL**：存储笔记数据
- **模型设计**：完整的笔记信息（标题、内容、用户、互动数据）
- **时间排序**：按发布时间排序存储

### 反爬虫对策
- **动态签名**：实时生成有效的请求签名
- **Cookie 轮换**：支持多账号 Cookie 轮换
- **随机延迟**：避免频率限制
- **错误重试**：自动重试和错误恢复

## 🎯 已知 Search IDs
```python
KNOWN_SEARCH_IDS = {
    "苏州企业": "2f1qtm0ubz1h34wcpu61a",
    "苏州工业园区": "2f1qto8pgfgzd6r2jq4oq", 
    "苏州工业园区企业": "2f1qtp92hrr3ipjoraa07",
}
```

## ⚠️ 注意事项
1. **Cookie 过期**：通常 24-48 小时过期，需定期更新
2. **频率限制**：建议每页间隔 2-5 秒
3. **IP 限制**：避免同一 IP 大量请求
4. **数据合规**：仅用于学习和研究目的

## 🐛 常见问题

### Q: 提示 "登录已过期" (code: -100)
A: Cookie 过期，按照 `update_cookie_guide.md` 更新 Cookie

### Q: 找不到搜索框 (Selenium)
A: 使用简化版爬虫 `simple_xhs_scraper.py`，它使用已知的 search_id

### Q: 签名生成失败
A: 检查 `xhs-mcp/api/xhsvm.js` 文件是否存在

### Q: 数据库连接失败
A: 检查 PostgreSQL 服务是否启动，配置是否正确

## 📊 预期结果
更新 Cookie 后，运行爬虫应该能看到：
- ✅ 成功获取笔记数据
- ✅ 数据保存到数据库
- ✅ 按时间排序的企业相关笔记
- ✅ 完整的笔记信息（标题、内容、用户、互动数据）

## 🔄 下一步优化
- [ ] 自动化 Cookie 更新
- [ ] 代理池支持
- [ ] 更多关键词支持
- [ ] 数据分析和可视化
- [ ] 定时任务调度 