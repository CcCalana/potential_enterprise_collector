#!/usr/bin/env python3
"""
使用Selenium获取小红书笔记详情
模拟浏览器访问，绕过API限制
"""

import sys
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from loguru import logger

sys.path.insert(0, '.')

def create_driver():
    """创建Chrome驱动"""
    options = Options()
    options.add_argument('--headless')  # 无头模式
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        logger.error("创建Chrome驱动失败: {}", e)
        return None

def get_note_content_selenium(note_id: str, cookie: str) -> str:
    """
    使用Selenium获取笔记内容
    """
    driver = create_driver()
    if not driver:
        return ""
    
    try:
        # 访问笔记页面
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        logger.info("访问笔记页面: {}", url)
        
        # 设置Cookie
        driver.get("https://www.xiaohongshu.com")
        
        # 解析Cookie字符串并设置
        cookie_pairs = cookie.split('; ')
        for pair in cookie_pairs:
            if '=' in pair:
                name, value = pair.split('=', 1)
                try:
                    driver.add_cookie({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.xiaohongshu.com'
                    })
                except Exception as e:
                    logger.debug("设置Cookie失败: {} - {}", name, e)
        
        # 访问目标页面
        driver.get(url)
        
        # 等待页面加载
        wait = WebDriverWait(driver, 10)
        
        # 尝试多种选择器找到笔记内容
        content_selectors = [
            '.note-content',
            '.content',
            '.desc',
            '[class*="desc"]',
            '[class*="content"]',
            '.note-text',
            '.text-content',
            'span[class*="text"]',
            'div[class*="text"]'
        ]
        
        content = ""
        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 10:  # 过滤太短的文本
                            content += text + "\n"
                    if content:
                        break
            except Exception as e:
                logger.debug("选择器 {} 失败: {}", selector, e)
        
        # 如果还没找到内容，尝试获取页面中的所有文本
        if not content:
            try:
                # 获取页面标题作为备选
                title_element = driver.find_element(By.TAG_NAME, "title")
                if title_element:
                    content = title_element.get_attribute("textContent") or ""
            except:
                pass
        
        if content:
            logger.success("成功获取笔记内容: {} 字符", len(content))
            return content.strip()
        else:
            logger.warning("未找到笔记内容")
            return ""
            
    except TimeoutException:
        logger.warning("页面加载超时")
        return ""
    except Exception as e:
        logger.error("获取笔记内容失败: {}", e)
        return ""
    finally:
        driver.quit()

def update_note_content_batch():
    """
    批量更新数据库中笔记的内容
    """
    from app.config import SessionLocal
    from app.models import XHSNote
    
    # 读取Cookie
    try:
        with open("app/tasks/cookies/xhs_cookies.txt", 'r') as f:
            cookie = f.read().strip()
    except:
        logger.error("无法读取Cookie文件")
        return
    
    with SessionLocal() as db:
        # 获取没有内容的笔记
        notes_without_content = db.query(XHSNote).filter(
            (XHSNote.desc.is_(None)) | (XHSNote.desc == "")
        ).limit(5).all()  # 限制5条，避免过多请求
        
        if not notes_without_content:
            logger.info("所有笔记都已有内容")
            return
        
        logger.info("找到 {} 条需要更新内容的笔记", len(notes_without_content))
        
        updated_count = 0
        for note in notes_without_content:
            logger.info("正在获取笔记 {} 的内容...", note.note_id)
            
            content = get_note_content_selenium(str(note.note_id), cookie)
            
            if content:
                # 更新笔记内容
                db.query(XHSNote).filter(XHSNote.note_id == note.note_id).update({"desc": content})
                db.commit()
                updated_count += 1
                logger.success("已更新笔记 {} 的内容", note.note_id)
            else:
                logger.warning("无法获取笔记 {} 的内容", note.note_id)
            
            # 添加延迟避免被限制
            time.sleep(random.uniform(3, 6))
        
        logger.success("批量更新完成，共更新 {} 条笔记", updated_count)

def test_single_note():
    """测试单个笔记的内容获取"""
    from app.config import SessionLocal
    from app.models import XHSNote
    
    # 读取Cookie
    try:
        with open("app/tasks/cookies/xhs_cookies.txt", 'r') as f:
            cookie = f.read().strip()
    except:
        logger.error("无法读取Cookie文件")
        return
    
    with SessionLocal() as db:
        note = db.query(XHSNote).first()
        if not note:
            logger.error("数据库中没有笔记数据")
            return
        
        note_id = str(note.note_id)
        logger.info("测试笔记: {} - {}", note_id, note.title)
        
        content = get_note_content_selenium(note_id, cookie)
        
        if content:
            logger.success("获取到内容: {}", content[:200] + "..." if len(content) > 200 else content)
        else:
            logger.error("未获取到内容")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="使用Selenium获取小红书笔记详情")
    parser.add_argument("--test", action="store_true", help="测试单个笔记")
    parser.add_argument("--batch", action="store_true", help="批量更新笔记内容")
    
    args = parser.parse_args()
    
    if args.test:
        test_single_note()
    elif args.batch:
        update_note_content_batch()
    else:
        logger.info("请使用 --test 测试单个笔记或 --batch 批量更新")
        logger.info("示例: python selenium_detail_fetcher.py --test") 