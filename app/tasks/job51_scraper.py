"""51Job 苏州工业园区高新行业爬虫任务。

调用示例：
    python -m app.tasks.job51_scraper  # 直接调试
    # 或者在 scheduler 中引入 `run()`
"""

from __future__ import annotations

import json
import time
import urllib.parse
from typing import List

import requests
from bs4 import BeautifulSoup
from loguru import logger

from app.config import SessionLocal
from app.models import JobPosting

# ---------------------------------------------------------------------------
# 常量配置
# ---------------------------------------------------------------------------

BASE_URL = "https://search.51job.com/list/"
# 中文城市名称，稍后进行 URL 编码
CITY_PARAM = "苏州工业园区"
KEYWORD = "科技"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"),
    "Referer": "https://www.51job.com/",
}
MAX_PAGES = 5  # 可自行调整
REQ_INTERVAL = 1.5  # 秒，简单限速


# ---------------------------------------------------------------------------
# 抓取 & 解析
# ---------------------------------------------------------------------------

def build_url(page: int) -> str:
    """根据页码构建列表页 URL（城市中文 + 关键词）。"""

    city_enc = urllib.parse.quote(CITY_PARAM)
    kw_enc = urllib.parse.quote(KEYWORD)
    url_no_query = f"{BASE_URL}{city_enc},000000,0000,00,9,99,{kw_enc},2,{page}.html"
    # 附加常见查询参数，模拟浏览器搜索
    return (
        url_no_query
        + "?lang=c&stype=1&postchannel=0000&workyear=99&cotype=99&degreefrom=99&jobterm=99"
    )


def parse_list(html: str) -> List[dict]:
    """解析列表页，返回岗位基本信息列表。"""
    soup = BeautifulSoup(html, "lxml")
    results: List[dict] = []
    for div in soup.select("div.el"):
        a_tag = div.select_one("a")
        if not a_tag:
            continue
        url = a_tag.get("href")
        title = a_tag.get("title")
        company = div.select_one("span.t2 a")
        loc_span = div.select_one("span.t3")
        salary_span = div.select_one("span.t4")
        date_span = div.select_one("span.t5")

        results.append(
            {
                "title": title,
                "company": company.text.strip() if company else None,
                "location": loc_span.text.strip() if loc_span else None,
                "salary": salary_span.text.strip() if salary_span else None,
                "post_date": date_span.text.strip() if date_span else None,
                "detail_url": url,
            }
        )
    return results


def save_jobs(jobs: List[dict]) -> None:
    """批量保存到数据库（去重）。"""
    if not jobs:
        return
    with SessionLocal() as ses:
        for item in jobs:
            if not item["detail_url"]:
                continue
            # 简易去重：URL 唯一索引冲突时使用 merge
            job_obj = JobPosting(
                title=item["title"],
                salary=item["salary"],
                location=item["location"],
                company_name=item["company"],
                post_date=item["post_date"],
                url=item["detail_url"],
                raw_json=item,
            )
            ses.merge(job_obj)
        ses.commit()
    logger.info("保存 {} 条职位", len(jobs))


# ---------------------------------------------------------------------------
# 任务入口
# ---------------------------------------------------------------------------

def run(pages: int = MAX_PAGES) -> None:
    """执行爬取任务。"""
    logger.info("开始爬取 51Job：{}×{} 页", CITY_PARAM, pages)
    for page in range(1, pages + 1):
        url = build_url(page)
        logger.debug("GET {}", url)
        try:
            resp = requests.get(
                url,
                headers=HEADERS,
                timeout=15,
                verify=False,
                allow_redirects=True,
                proxies={"http": "", "https": ""},
            )
            resp.encoding = "gbk"  # 51Job 返回页面编码为 GBK
        except requests.RequestException as exc:
            logger.error("请求失败: {}", exc)
            continue

        jobs = parse_list(resp.text)
        save_jobs(jobs)
        time.sleep(REQ_INTERVAL)
        if not jobs:
            logger.warning("第 {} 页未解析到岗位数据", page)
    logger.success("爬取完成")


# ---------------------------------------------------------------------------
# CLI 调试入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()