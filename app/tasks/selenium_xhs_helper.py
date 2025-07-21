#!/usr/bin/env python3
"""
Selenium 辅助模块，用于获取小红书的 search_id
"""

import json
import time
import random
import pathlib
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger


class XHSSeleniumHelper:
    """小红书 Selenium 辅助类"""
    
    def __init__(self, headless: bool = False, cookie_file: Optional[pathlib.Path] = None):
        self.headless = headless
        self.cookie_file = cookie_file or pathlib.Path(__file__).parent / "cookies" / "xhs_cookies.txt"
        self.driver = None
        self.search_id_cache = {}  # 缓存 search_id
        
    def setup_driver(self) -> webdriver.Chrome:
        """设置 Chrome 驱动"""
        options = Options()
        
        # 基本配置
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 无头模式
        if self.headless:
            options.add_argument('--headless')
            
        # 禁用图片和CSS加载以加速
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        # 启用性能日志
        options.add_argument('--enable-logging')
        options.add_argument('--log-level=0')
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        # 自动管理 ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 执行反检测脚本
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def load_cookies(self) -> Dict[str, str]:
        """加载 Cookie 文件"""
        if not self.cookie_file.exists():
            logger.warning("Cookie 文件不存在: {}", self.cookie_file)
            return {}
            
        cookie_string = self.cookie_file.read_text().strip()
        cookies = {}
        
        for item in cookie_string.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
                
        logger.info("加载了 {} 个 Cookie", len(cookies))
        return cookies
    
    def set_cookies(self, cookies: Dict[str, str]):
        """设置 Cookie 到浏览器"""
        if not self.driver:
            return
            
        for name, value in cookies.items():
            try:
                self.driver.add_cookie({"name": name, "value": value})
            except Exception as e:
                logger.debug("设置 Cookie 失败 {}: {}", name, e)
    
    def get_search_id(self, keyword: str, max_retries: int = 3) -> Optional[str]:
        """获取搜索关键词的 search_id"""
        
        # 检查缓存
        if keyword in self.search_id_cache:
            logger.info("从缓存获取 search_id: {}", keyword)
            return self.search_id_cache[keyword]
        
        for attempt in range(max_retries):
            try:
                logger.info("尝试获取 search_id，关键词: {}, 第 {} 次", keyword, attempt + 1)
                
                # 设置驱动
                if not self.driver:
                    self.driver = self.setup_driver()
                
                # 访问小红书首页
                self.driver.get("https://www.xiaohongshu.com")
                time.sleep(2)
                
                # 设置 Cookie
                cookies = self.load_cookies()
                if cookies:
                    self.set_cookies(cookies)
                    self.driver.refresh()
                    time.sleep(2)
                
                # 清空之前的网络日志
                self.driver.get_log('performance')
                
                # 搜索关键词
                search_id = self._perform_search(keyword)
                
                if search_id:
                    # 缓存结果
                    self.search_id_cache[keyword] = search_id
                    logger.success("成功获取 search_id: {} -> {}", keyword, search_id)
                    return search_id
                else:
                    logger.warning("第 {} 次尝试未获取到 search_id", attempt + 1)
                    
            except Exception as e:
                logger.error("第 {} 次尝试失败: {}", attempt + 1, e)
                
                # 重新创建驱动
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                    
                time.sleep(random.uniform(2, 5))
        
        logger.error("所有尝试都失败，无法获取 search_id: {}", keyword)
        return None
    
    def _perform_search(self, keyword: str) -> Optional[str]:
        """执行搜索操作"""
        if not self.driver:
            return None
            
        try:
            # 查找搜索框
            search_selectors = [
                "input[placeholder*='搜索']",
                "input[placeholder*='search']", 
                ".search-input input",
                ".search-box input",
                "input[type='search']",
                "input[class*='search']",
                ".search input",
                "[data-testid*='search'] input",
                "input[name*='search']",
                "input[id*='search']"
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.debug("找到搜索框: {}", selector)
                    break
                except:
                    continue
            
            if not search_box:
                # 尝试直接导航到搜索页面
                logger.warning("找不到搜索框，尝试直接导航到搜索页面")
                search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}"
                self.driver.get(search_url)
                time.sleep(3)
                
                # 检查是否成功跳转到搜索结果页面
                current_url = self.driver.current_url
                if 'search_result' in current_url:
                    logger.info("成功导航到搜索结果页面")
                    # 从当前页面提取 search_id
                    search_id = self._extract_search_id_from_logs()
                    if not search_id:
                        search_id = self._extract_search_id_from_page()
                    if not search_id:
                        search_id = self._extract_search_id_from_url()
                    return search_id
                else:
                    logger.error("无法导航到搜索页面")
                    return None
            
            # 输入关键词并搜索
            search_box.clear()
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)
            
            # 等待页面加载
            time.sleep(3)
            
            # 方法1: 从网络日志获取 search_id
            search_id = self._extract_search_id_from_logs()
            if search_id:
                return search_id
            
            # 方法2: 从页面数据获取 search_id
            search_id = self._extract_search_id_from_page()
            if search_id:
                return search_id
            
            # 方法3: 从 URL 获取 search_id
            search_id = self._extract_search_id_from_url()
            if search_id:
                return search_id
                
            return None
            
        except Exception as e:
            logger.error("搜索操作失败: {}", e)
            return None
    
    def _extract_search_id_from_logs(self) -> Optional[str]:
        """从网络日志中提取 search_id"""
        if not self.driver:
            return None
            
        try:
            logs = self.driver.get_log('performance')
            
            for log in logs:
                message = json.loads(log['message'])
                
                if message['message']['method'] == 'Network.responseReceived':
                    url = message['message']['params']['response']['url']
                    
                    if 'search/filter' in url and 'search_id=' in url:
                        logger.debug("发现 filter 请求: {}", url)
                        
                        # 直接从 URL 中提取 search_id
                        try:
                            import urllib.parse
                            parsed = urllib.parse.urlparse(url)
                            params = urllib.parse.parse_qs(parsed.query)
                            search_id = params.get('search_id', [None])[0]
                            if search_id:
                                logger.info("从网络日志 URL 获取到 search_id: {}", search_id)
                                return search_id
                        except Exception as e:
                            logger.debug("从 URL 解析 search_id 失败: {}", e)
                            
        except Exception as e:
            logger.debug("从网络日志提取 search_id 失败: {}", e)
            
        return None
    
    def _extract_search_id_from_page(self) -> Optional[str]:
        """从页面数据中提取 search_id"""
        if not self.driver:
            return None
            
        try:
            # 尝试获取页面中的全局数据
            scripts = [
                "return window.__INITIAL_STATE__ || {}",
                "return window.__NUXT__ || {}",
                "return window.__INITIAL_DATA__ || {}",
                "return window.pageData || {}",
                "return window.searchData || {}"
            ]
            
            for script in scripts:
                try:
                    page_data = self.driver.execute_script(script)
                    if page_data:
                        search_id = self._find_search_id_in_data(page_data)
                        if search_id:
                            logger.info("从页面数据获取到 search_id: {}", search_id)
                            return search_id
                except Exception as e:
                    logger.debug("执行脚本失败: {}", e)
                    
        except Exception as e:
            logger.debug("从页面数据提取 search_id 失败: {}", e)
            
        return None
    
    def _extract_search_id_from_url(self) -> Optional[str]:
        """从 URL 中提取 search_id"""
        if not self.driver:
            return None
            
        try:
            current_url = self.driver.current_url
            logger.debug("当前 URL: {}", current_url)
            
            # 检查 URL 参数
            if 'search_id=' in current_url:
                import urllib.parse
                parsed = urllib.parse.urlparse(current_url)
                params = urllib.parse.parse_qs(parsed.query)
                search_id = params.get('search_id', [None])[0]
                if search_id:
                    logger.info("从 URL 获取到 search_id: {}", search_id)
                    return search_id
                    
        except Exception as e:
            logger.debug("从 URL 提取 search_id 失败: {}", e)
            
        return None
    
    def _find_search_id_in_data(self, data: Any) -> Optional[str]:
        """递归查找数据中的 search_id"""
        if isinstance(data, dict):
            if 'search_id' in data and data['search_id']:
                return data['search_id']
            for value in data.values():
                result = self._find_search_id_in_data(value)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_search_id_in_data(item)
                if result:
                    return result
        return None
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def test_selenium_helper():
    """测试 Selenium 辅助类"""
    logger.info("开始测试 Selenium 辅助类")
    
    keywords = ["旅游", "苏州企业", "苏州工业园区"]
    
    with XHSSeleniumHelper(headless=False) as helper:
        for keyword in keywords:
            logger.info("测试关键词: {}", keyword)
            search_id = helper.get_search_id(keyword)
            
            if search_id:
                logger.success("✅ 成功获取 search_id: {} -> {}", keyword, search_id)
            else:
                logger.error("❌ 未能获取 search_id: {}", keyword)
            
            time.sleep(2)


if __name__ == "__main__":
    test_selenium_helper() 