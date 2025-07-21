"""基于 Selenium 的 51Job 爬虫（苏州工业园区 + 科技）。

用法：
    1. 本地先启动 Chrome 远程调试：
        chrome.exe --remote-debugging-port=9527 --user-data-dir="C:/chrome_tmp"
       （保持窗口常驻，可保登录状态与 Cookie。）
    2. 安装驱动：pip install selenium==4.*
    3. 运行本任务：
        python -m app.tasks.job51_selenium_scraper  
"""

from __future__ import annotations

import json
import os
import time
from typing import List

from loguru import logger
import sys

import requests
from selenium import webdriver
from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
try:
    from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    ChromeDriverManager = None  # type: ignore

from app.config import SessionLocal
from app.models import JobPosting

JOB_AREA_CODE = "070306"  # 苏州工业园区（新版接口代码）
# 关键词留空即可爬取园区所有岗位
KEYWORD = ""

# 不再限制最大页数，可通过 run(max_pages=N) 临时限制
MAX_PAGES = None
SLEEP_SECONDS = 2

SEARCH_URL_TMPL = (
    "https://we.51job.com/pc/search?keyword={kw}&jobArea={area}&pageNum={page}"
)


def init_driver() -> webdriver.Chrome:
    """连接到已开启远程调试端口的 Chrome；若失败则启动新的无头浏览器。"""

    debugger_address = os.getenv("CHROME_DEBUG", "127.0.0.1:9527")

    # 先探测调试端口是否可达
    try:
        requests.get(f"http://{debugger_address}/json/version", timeout=2)
        debug_ok = True
    except Exception:
        debug_ok = False

    if debug_ok:
        logger.debug("检测到调试端口 {} 在线，尝试附加…", debugger_address)
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", debugger_address)
        try:
            if ChromeDriverManager:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            logger.success("已连接到现有 Chrome 会话 {}", debugger_address)
            return driver
        except WebDriverException as exc:  # more specific
            logger.warning("附加失败：{}，将启动无头实例", exc)
    else:
        logger.warning("调试端口 {} 不可用，直接启动无头实例", debugger_address)

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def fetch_page_jobs(driver: webdriver.Chrome, page: int) -> List[dict]:
    url = SEARCH_URL_TMPL.format(area=JOB_AREA_CODE, kw=KEYWORD, page=page)
    logger.debug("[page {}] GET {}", page, url)
    driver.get(url)
    logger.debug("[page {}] 页面载入完成，等待 JS 数据注入…", page)

    # 等待全局变量或 nuxt 数据注入（最长 12 秒）
    data: dict | None = None
    for _ in range(12):
        try:
            data = driver.execute_script(
                "return (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.searchResult) || "
                "(window.__NUXT__ && window.__NUXT__.state && window.__NUXT__.state.searchResult) || null;"
            )  # type: ignore[assignment]
        except JavascriptException:
            data = None
        if data:
            break
        time.sleep(1)
        logger.debug("[page {}] 等待数据…", page)

    if not data:
        # 尝试 ret_nodes（SSR 数据）
        data = driver.execute_script("return window.ret_nodes || null;")
        if data and isinstance(data, dict) and data.get('data'):
            search_result = data['data'].get('jobSearchResult') or data['data']
            if search_result and search_result.get('jobList'):
                job_list = search_result['jobList']
                logger.success("[page {}] 从 ret_nodes 获得 {} 条", page, len(job_list))
                return job_list

        logger.warning("第 {} 页未获取到 searchResult 对象", page)
        keys = driver.execute_script("return Object.keys(window);")
        # 仅打印前 30 个全局变量，避免日志过长
        if isinstance(keys, list):
            logger.debug("窗口键(前30): {}… 共 {} 项", keys[:30], len(keys))
        else:
            logger.debug("窗口键: {}", keys)
        # 执行 API fetch fallback 同前逻辑
        import urllib.parse, time as _t
        kw_enc = urllib.parse.quote(KEYWORD)
        ts = int(_t.time())
        api_url = (
            f"https://we.51job.com/api/job/search-pc?api_key=51job&timestamp={ts}"
            f"&keyword={kw_enc}&searchType=2&jobArea={JOB_AREA_CODE}&jobArea2={JOB_AREA_CODE}"
            f"&sortType=0&pageNum={page}&pageSize=50&source=1&scene=7"
        )

        logger.debug("[page {}] API fetch {}", page, api_url)

        api_js = (
            "const cb = arguments[arguments.length-1];"
            "fetch('" + api_url + "',{credentials:'include'})"
            ".then(r=>r.json()).then(d=>cb(d)).catch(e=>cb({error:e.toString()}));"
        )

        resp = driver.execute_async_script(api_js)
        if isinstance(resp, dict):
            job_list = None
            if resp.get("data") and resp["data"].get("jobList"):
                job_list = resp["data"]["jobList"]
            elif resp.get("resultbody"):
                rb = resp["resultbody"]
                # 兼容两种嵌套
                if rb.get("job") and rb["job"].get("items"):
                    job_list = rb["job"]["items"]
                elif rb.get("items"):
                    job_list = rb["items"]

            if job_list:
                logger.success("[page {}] API 获取到 {} 条", page, len(job_list))
                return job_list
        resp_str = str(resp)
        if len(resp_str) > 800:
            resp_str = resp_str[:800] + "…(truncated)"
        logger.error("[page {}] API fetch 失败: {}", page, resp_str)
        return []

    job_list = data.get("jobList") or data.get("joblist")
    if not job_list:
        logger.warning("第 {} 页 searchResult 内无 jobList 字段，尝试 API fetch", page)
        # 尝试通过页面 fetch 直接请求官方 API
        import urllib.parse, time as _t
        kw_enc = urllib.parse.quote(KEYWORD)
        ts = int(_t.time())
        api_url = (
            f"https://we.51job.com/api/job/search-pc?api_key=51job&timestamp={ts}"
            f"&keyword={kw_enc}&searchType=2&jobArea={JOB_AREA_CODE}&jobArea2={JOB_AREA_CODE}"
            f"&sortType=0&pageNum={page}&pageSize=50&source=1&scene=7"
        )

        logger.debug("[page {}] API fetch {}", page, api_url)

        api_js = (
            "const cb = arguments[arguments.length-1];"
            "fetch('" + api_url + "',{credentials:'include'})"
            ".then(r=>r.json()).then(d=>cb(d)).catch(e=>cb({error:e.toString()}));"
        )

        resp = driver.execute_async_script(api_js)
        if isinstance(resp, dict):
            job_list = None
            if resp.get("data") and resp["data"].get("jobList"):
                job_list = resp["data"]["jobList"]
            elif resp.get("resultbody"):
                rb = resp["resultbody"]
                # 兼容两种嵌套
                if rb.get("job") and rb["job"].get("items"):
                    job_list = rb["job"]["items"]
                elif rb.get("items"):
                    job_list = rb["items"]

            if job_list:
                logger.success("[page {}] API 获取到 {} 条", page, len(job_list))
            else:
                resp_str = str(resp)
                if len(resp_str) > 800:
                    resp_str = resp_str[:800] + "…(truncated)"
                logger.error("[page {}] API fetch 失败: {}", page, resp_str)
                return []

    jobs: List[dict] = job_list or []
    logger.success("[page {}] 解析到 {} 条记录", page, len(jobs))
    return jobs


def save_jobs(jobs: List[dict]) -> None:
    if not jobs:
        return
    with SessionLocal() as ses:
        for j in jobs:
            url = j.get("detail_url") or j.get("jobHref") or j.get("jobUrl")
            if not url:
                continue

            job_obj = JobPosting(
                title=j.get("title") or j.get("jobName"),
                salary=j.get("salary") or j.get("provideSalaryString"),
                location=j.get("location") or j.get("jobAreaString"),
                company_name=j.get("company") or j.get("companyName"),
                post_date=j.get("post_date") or j.get("issueDateString"),
                url=url,
                raw_json=j,
            )
            ses.merge(job_obj)
        ses.commit()
    logger.success("写入 {} 条职位", len(jobs))


def run(max_pages: int | None = MAX_PAGES) -> None:
    logger.debug("=== 爬虫启动，最大页数 {} ===", max_pages if max_pages else "无限")
    driver = init_driver()
    page = 1
    try:
        while True:
            logger.debug("======== 处理第 {} 页 ========", page)
            jobs = fetch_page_jobs(driver, page)
            if not jobs:
                logger.warning("第 {} 页无数据，结束翻页", page)
                break
            save_jobs(jobs)
            page += 1
            if max_pages and page > max_pages:
                logger.info("达到 max_pages={} 限制，停止", max_pages)
                break
            # 可适当休眠，避免过快请求
            time.sleep(SLEEP_SECONDS)
    finally:
        driver.quit()


if __name__ == "__main__":
    run()
