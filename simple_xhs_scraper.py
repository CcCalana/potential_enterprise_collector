#!/usr/bin/env python3
"""
简化版小红书爬虫 - 苏州工业园区企业信息抓取
使用已知的 search_id，只需要更新 Cookie 即可使用
"""

import sys
import requests
import json
import time
import random
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '.')

from app.tasks.xiaohongshu_scraper import gen_sign, HEADERS_BASE, save_notes
from app.config import SessionLocal
from loguru import logger

# 已知有效的 search_id (从 Selenium 获取)
KNOWN_SEARCH_IDS = {
    "苏州企业": "2f1qtm0ubz1h34wcpu61a",
    "苏州工业园区": "2f1qto8pgfgzd6r2jq4oq", 
    "苏州工业园区企业": "2f1qtp92hrr3ipjoraa07",
}

# 关键词映射 - 将相似关键词映射到已知的 search_id
KEYWORD_MAPPING = {
    "苏州工业园区人工智能": "苏州工业园区",
    "苏州工业园区AI": "苏州工业园区",
    "苏州工业园区科技": "苏州工业园区",
    "苏州工业园区创新": "苏州工业园区",
    "苏州园区人工智能": "苏州工业园区",
    "苏州园区AI": "苏州工业园区",
}

def get_note_detail(note_id: str, cookie: str) -> dict:
    """
    获取笔记详情，包括正文内容
    """
    detail_url = "https://edith.xiaohongshu.com/api/sns/web/v1/feed"
    
    payload = {
        "source_note_id": note_id,
        "image_formats": ["jpg", "webp", "avif"],
        "extra": {"need_body_topic": "1"}
    }
    
    try:
        # 添加随机延迟，避免请求过快
        time.sleep(random.uniform(2, 4))
        
        sign_headers = gen_sign(detail_url, payload, cookie)
        
        # 确保所有 header 值都是字符串
        for key, value in sign_headers.items():
            if not isinstance(value, str):
                sign_headers[key] = str(value)
        
        headers = {**HEADERS_BASE, **sign_headers, "cookie": cookie}
        
        # 添加更多重试和延迟
        for attempt in range(3):  # 增加到3次重试
            try:
                response = requests.post(detail_url, json=payload, headers=headers, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success", True):
                        logger.info("成功获取笔记 {} 详情", note_id)
                        return data.get("data", {})
                    else:
                        logger.debug("获取笔记详情失败: {}", data.get("msg", "未知错误"))
                elif response.status_code == 406:
                    logger.warning("笔记详情API被限制，等待更长时间后重试...")
                    if attempt < 2:  # 不是最后一次尝试
                        time.sleep(random.uniform(5, 10))  # 等待5-10秒
                        continue
                    else:
                        logger.warning("笔记详情API持续被限制，跳过详情获取")
                        break
                elif response.status_code == 461:
                    logger.warning("签名验证失败，可能需要更新Cookie")
                    break
                else:
                    logger.debug("获取笔记详情HTTP错误: {}", response.status_code)
                    
                if attempt < 2:  # 如果不是最后一次尝试
                    time.sleep(random.uniform(3, 6))  # 等待后重试
                    
            except requests.exceptions.RequestException as e:
                logger.debug("获取笔记详情请求异常: {}", str(e)[:100])
                if attempt < 2:
                    time.sleep(random.uniform(3, 6))
                    
    except Exception as e:
        logger.debug("获取笔记详情异常: {}", str(e)[:100])
    
    return {}

def save_notes_safe(db, notes, cookie: str):
    """
    安全保存笔记到数据库，逐个处理避免批量失败
    同时获取笔记详情内容
    """
    from app.models import XHSNote
    
    saved_count = 0
    for n in notes:
        try:
            note_id = n.get("id") or n.get("note_id")
            if not note_id:
                continue
                
            # 检查是否已存在
            existing_note = db.query(XHSNote).filter(XHSNote.note_id == note_id).first()
            if existing_note:
                logger.info("笔记 {} 已存在，跳过", note_id)
                continue
                
            # 获取笔记详情（可选，如果失败则跳过）
            note_content = ""
            try:
                detail_data = get_note_detail(note_id, cookie)
                if detail_data.get("items"):
                    item = detail_data["items"][0]
                    note_detail = item.get("note_card", {})
                    note_content = note_detail.get("desc", "")
            except Exception as e:
                logger.warning("获取笔记 {} 详情失败，使用基本信息: {}", note_id, str(e)[:100])
            
            # 解析嵌套的JSON结构
            note_card = n.get("note_card", {})
            if not note_card:
                continue
                
            # 提取标题
            title = note_card.get("display_title", "")
            
            # 提取用户信息
            user_info = note_card.get("user", {})
            user_id = user_info.get("user_id", "")
            user_name = user_info.get("nickname", "")
            
            # 提取互动信息
            interact_info = note_card.get("interact_info", {})
            
            # 安全转换数字字段
            def safe_int(value):
                if isinstance(value, str):
                    try:
                        return int(value)
                    except ValueError:
                        return 0
                return value if isinstance(value, int) else 0
            
            like_count = safe_int(interact_info.get("liked_count", 0))
            collect_count = safe_int(interact_info.get("collected_count", 0))
            comment_count = safe_int(interact_info.get("comment_count", 0))
            
            # 提取发布时间
            publish_time = None
            if n.get("publish_time"):
                try:
                    publish_time = datetime.fromtimestamp(n["publish_time"] / 1000)
                except:
                    pass
            
            # 构建笔记URL
            url = f"https://www.xiaohongshu.com/explore/{note_id}"
            
            # 合并原始数据和详情数据
            raw_json = n.copy()
            
            note = XHSNote(
                note_id=note_id,
                title=title,
                desc=note_content,  # 使用从详情获取的正文内容
                url=url,
                user_id=user_id,
                user_name=user_name,
                like_count=like_count,
                collect_count=collect_count,
                comment_count=comment_count,
                publish_time=publish_time,
                raw_json=raw_json
            )
            
            db.add(note)
            db.commit()
            saved_count += 1
            
            content_preview = note_content[:50] + "..." if len(note_content) > 50 else note_content
            logger.info("保存笔记: {} - {} (点赞:{}, 收藏:{}, 评论:{}) 内容: {}", 
                       note_id, title[:30], like_count, collect_count, comment_count, content_preview)
            
            # 添加延迟避免请求过快
            time.sleep(random.uniform(0.5, 1.0))
            
        except Exception as e:
            logger.error("保存笔记失败: {}", str(e)[:200])
            db.rollback()  # 回滚当前事务
            continue
    
    logger.success("成功保存 {} 条笔记", saved_count)
    return saved_count

def scrape_xhs_notes(keyword: str, pages: int = 1, use_known_search_id: bool = True):
    """
    抓取小红书笔记
    
    Args:
        keyword: 搜索关键词
        pages: 抓取页数
        use_known_search_id: 是否使用已知的 search_id
    """
    
    # 加载 Cookie
    cookie_file = "app/tasks/cookies/xhs_cookies.txt"
    try:
        with open(cookie_file, 'r') as f:
            cookie = f.read().strip()
    except:
        logger.error("无法读取 Cookie 文件: {}", cookie_file)
        logger.info("请按照 update_cookie_guide.md 更新 Cookie")
        return
    
    logger.info("开始抓取小红书笔记")
    logger.info("关键词: {}", keyword)
    logger.info("页数: {}", pages)
    logger.info("Cookie 长度: {}", len(cookie))
    
    api_url = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"
    total_notes = 0
    
    with SessionLocal() as db:
        for page in range(1, pages + 1):
            logger.info("正在抓取第 {} 页...", page)
            
            # 构建请求参数 - 修改为按热度排序
            payload = {
                "keyword": keyword,
                "page": page,
                "page_size": 20,
                "sort": "popularity_descending",  # 按热度排序（点赞收藏量）
                "note_type": 0,  # 0=全部，1=视频，2=图文
            }
            
            # 如果有已知的 search_id，使用它
            search_keyword = keyword
            if use_known_search_id:
                # 首先检查是否有直接匹配的关键词
                if keyword in KNOWN_SEARCH_IDS:
                    payload["search_id"] = KNOWN_SEARCH_IDS[keyword]
                    logger.info("使用已知 search_id: {}", KNOWN_SEARCH_IDS[keyword])
                # 检查是否有映射的关键词
                elif keyword in KEYWORD_MAPPING:
                    mapped_keyword = KEYWORD_MAPPING[keyword]
                    if mapped_keyword in KNOWN_SEARCH_IDS:
                        payload["search_id"] = KNOWN_SEARCH_IDS[mapped_keyword]
                        logger.info("使用映射关键词 '{}' 的 search_id: {}", mapped_keyword, KNOWN_SEARCH_IDS[mapped_keyword])
                    else:
                        logger.warning("映射关键词 '{}' 没有对应的 search_id", mapped_keyword)
                else:
                    logger.warning("关键词 '{}' 没有已知的 search_id，将尝试动态获取", keyword)
            
            # 生成签名
            sign_headers = gen_sign(api_url, payload, cookie)
            
            # 确保所有 header 值都是字符串
            for key, value in sign_headers.items():
                if not isinstance(value, str):
                    sign_headers[key] = str(value)
            
            headers = {**HEADERS_BASE, **sign_headers, "cookie": cookie}
            
            # 发送请求
            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=15)
                
                if response.status_code != 200:
                    logger.error("第 {} 页请求失败，状态码: {}", page, response.status_code)
                    continue
                
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    logger.error("第 {} 页响应不是有效JSON: {}", page, response.text[:200])
                    continue
                
                if not data.get("success", True):
                    logger.error("第 {} 页API返回错误: {}", page, data.get("msg", "未知错误"))
                    continue
                
                # 提取笔记列表
                items = data.get("data", {}).get("items", [])
                if not items:
                    logger.warning("第 {} 页无数据", page)
                    continue
                
                logger.info("第 {} 页获取到 {} 条笔记", page, len(items))
                
                # 保存笔记（包括获取详情内容）
                saved_count = save_notes_safe(db, items, cookie)
                total_notes += saved_count
                
                # 页面间延迟
                if page < pages:
                    delay = random.uniform(2, 4)
                    logger.info("等待 {:.1f} 秒后继续...", delay)
                    time.sleep(delay)
                
            except requests.exceptions.RequestException as e:
                logger.error("第 {} 页请求异常: {}", page, e)
                continue
    
    logger.success("抓取完成！总共保存 {} 条笔记", total_notes)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python simple_xhs_scraper.py <关键词> [页数]")
        print("示例: python simple_xhs_scraper.py 苏州工业园区人工智能 2")
        return
    
    keyword = sys.argv[1]
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    logger.info("=" * 50)
    logger.info("简化版小红书爬虫启动")
    logger.info("关键词: {}", keyword)
    logger.info("页数: {}", pages)
    logger.info("排序方式: 按热度排序（点赞收藏量）")
    logger.info("=" * 50)
    
    scrape_xhs_notes(keyword, pages)

if __name__ == "__main__":
    main() 