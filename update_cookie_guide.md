# 小红书 Cookie 更新指南

## 当前状态
✅ 签名系统正常工作  
✅ search_id 机制正确  
❌ Cookie 已过期 (code: -100)

## 更新 Cookie 步骤

### 方法一：Chrome 浏览器
1. 打开 Chrome 浏览器
2. 访问 https://www.xiaohongshu.com
3. 登录你的小红书账号
4. 按 F12 打开开发者工具
5. 点击 "Application" 标签
6. 在左侧找到 "Cookies" → "https://www.xiaohongshu.com"
7. 右键点击空白处 → "Select All" → 复制所有 Cookie
8. 或者手动复制以下关键 Cookie：
   - `a1` (最重要)
   - `web_session` (最重要)
   - `webId`
   - `gid`
   - `xsecappid`

### 方法二：直接复制 Cookie 字符串
1. 在小红书页面按 F12
2. 点击 "Network" 标签
3. 刷新页面
4. 找到任意一个请求
5. 在 "Request Headers" 中找到 "Cookie" 行
6. 复制完整的 Cookie 字符串

### 更新文件
将新的 Cookie 字符串替换到：
```
app/tasks/cookies/xhs_cookies.txt
```

### 验证更新
运行测试脚本：
```bash
python test_with_manual_search_id.py
```

## 预期结果
更新 Cookie 后应该能看到：
- ✅ 成功获取笔记数据
- ✅ 数据保存到数据库
- ✅ 显示笔记标题和内容

## 注意事项
- Cookie 通常 24-48 小时过期
- 建议定期更新 Cookie
- 不要在多个地方同时使用同一个 Cookie 