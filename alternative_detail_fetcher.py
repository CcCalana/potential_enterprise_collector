#!/usr/bin/env python3
"""
备用的小红书笔记详情获取方法
尝试不同的API端点和策略
"""

import sys
import requests
import json
import time
import random
from loguru import logger

sys.path.insert(0, '.')

from app.tasks.xiaohongshu_scraper import gen_sign, HEADERS_BASE

def get_note_detail_v2(note_id: str, cookie: str) -> dict:
    """
    方法2：使用不同的API端点
    """
    detail_url = "https://edith.xiaohongshu.com/api/sns/web/v2/note/feed"
    
    payload = {
        "note_id": note_id,
        "cursor_score": "",
        "num": 30,
        "image_formats": ["jpg", "webp", "avif"]
    }
    
    try:
        sign_headers = gen_sign(detail_url, payload, cookie)
        
        # 确保所有 header 值都是字符串
        for key, value in sign_headers.items():
            if not isinstance(value, str):
                sign_headers[key] = str(value)
        
        headers = {**HEADERS_BASE, **sign_headers, "cookie": cookie}
        
        response = requests.post(detail_url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success", True):
                return data.get("data", {})
        
        logger.debug("V2 API 失败: {}", response.status_code)
        
    except Exception as e:
        logger.debug("V2 API 异常: {}", str(e)[:100])
    
    return {}

def get_note_detail_v3(note_id: str, cookie: str) -> dict:
    """
    方法3：使用GET请求方式
    """
    detail_url = f"https://edith.xiaohongshu.com/api/sns/web/v1/feed"
    
    params = {
        "source_note_id": note_id,
        "image_formats": "jpg,webp,avif"
    }
    
    try:
        sign_headers = gen_sign(detail_url, params, cookie)
        
        # 确保所有 header 值都是字符串
        for key, value in sign_headers.items():
            if not isinstance(value, str):
                sign_headers[key] = str(value)
        
        headers = {**HEADERS_BASE, **sign_headers, "cookie": cookie}
        
        response = requests.get(detail_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success", True):
                return data.get("data", {})
        
        logger.debug("V3 API 失败: {}", response.status_code)
        
    except Exception as e:
        logger.debug("V3 API 异常: {}", str(e)[:100])
    
    return {}

def get_note_detail_comprehensive(note_id: str, cookie: str) -> dict:
    """
    综合方法：依次尝试多种API方式
    """
    logger.info("尝试获取笔记 {} 的详情...", note_id)
    
    # 方法1：原始POST方式
    try:
        from simple_xhs_scraper import get_note_detail
        result = get_note_detail(note_id, cookie)
        if result:
            logger.success("方法1成功获取详情")
            return result
    except Exception as e:
        logger.debug("方法1失败: {}", str(e)[:100])
    
    # 添加延迟
    time.sleep(random.uniform(2, 4))
    
    # 方法2：V2 API
    result = get_note_detail_v2(note_id, cookie)
    if result:
        logger.success("方法2成功获取详情")
        return result
    
    # 添加延迟
    time.sleep(random.uniform(2, 4))
    
    # 方法3：GET方式
    result = get_note_detail_v3(note_id, cookie)
    if result:
        logger.success("方法3成功获取详情")
        return result
    
    logger.warning("所有方法都无法获取笔记 {} 的详情", note_id)
    return {}

def test_detail_fetcher():
    """测试详情获取功能"""
    
    # 从数据库获取一个笔记ID进行测试
    sys.path.insert(0, '.')
    from app.config import SessionLocal
    from app.models import XHSNote
    
    with SessionLocal() as db:
        note = db.query(XHSNote).first()
        if not note:
            logger.error("数据库中没有笔记数据")
            return
        
        note_id = str(note.note_id)
        logger.info("测试笔记ID: {}", note_id)
        
        # 读取Cookie
        try:
            with open("app/tasks/cookies/xhs_cookies.txt", 'r') as f:
                cookie = f.read().strip()
        except:
            logger.error("无法读取Cookie文件")
            return
        
        # 测试获取详情
        result = get_note_detail_comprehensive(note_id, cookie)
        
        if result:
            logger.success("成功获取详情数据")
            # 提取正文内容
            if result.get("items"):
                item = result["items"][0]
                note_detail = item.get("note_card", {})
                content = note_detail.get("desc", "")
                logger.info("正文内容: {}", content[:200] + "..." if len(content) > 200 else content)
            else:
                logger.info("详情数据结构: {}", list(result.keys()))
        else:
            logger.error("无法获取详情数据")

if __name__ == "__main__":
    test_detail_fetcher() 