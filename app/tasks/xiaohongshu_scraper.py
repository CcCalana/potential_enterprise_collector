"""小红书爬虫任务

参考：https://blog.csdn.net/weixin_74305707/article/details/144108414

功能：
1. 根据关键词或话题，分页抓取小红书笔记列表（JSON 接口），将结果写入 Postgres 的 ``xhs_notes`` 表。
2. 支持从本地 ``cookies/xhs_cookies.txt`` 读取多个账号 Cookie 轮询使用，降低风控。
3. 简化版签名流程：
   - 小红书接口需要 ``x-s`` / ``x-t`` 等签名头；可以通过阅读博客中的 JS 逆向脚本 ``sign.js`` 丢到 ``tasks/js/sign_xhs.js``，借助 ``execjs`` 计算。
   - 本脚本保留 ``gen_sign`` 占位函数，开发者需将对应 JS 填充后即可运行。

用法：
    python -m app.tasks.xiaohongshu_scraper "科技创新" --pages 20

Cookie 准备：
1. Chrome 打开 https://www.xiaohongshu.com/ ，F12 → Application → Cookies → 右键 copy → "Copy all as cURL (bash)"。
2. 从复制结果中提取 ``Cookie: xxx=yyy; ...`` 部分，保存到 ``app/tasks/cookies/xhs_cookies.txt``，一行一个账号 Cookie。
   (文件路径可自定义，通过 ``--cookie-file`` 参数指定)
3. 若有多账号可写多行，脚本将轮询使用。

依赖：``pip install requests execjs loguru``，若使用 JS 文件签名需 ``pip install PyExecJS``。
"""

from __future__ import annotations

import json
import random
import time
import pathlib
from typing import List, Generator, Dict, Any
from datetime import datetime

import execjs  # type: ignore
import requests
from loguru import logger

from app.config import SessionLocal
from app.models import XHSNote
from app.tasks.selenium_xhs_helper import XHSSeleniumHelper

# ------------------------------------------------------------
# 常量配置
# ------------------------------------------------------------

# 小红书搜索接口 URL
API_URL = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"
FILTER_URL = "https://edith.xiaohongshu.com/api/sns/web/v1/search/filter"

# 备用接口 URL（可能的其他端点）
API_URL_V2 = "https://edith.xiaohongshu.com/api/sns/web/v2/search/notes"
SEARCH_URL = "https://edith.xiaohongshu.com/api/sns/web/v1/search"
HEADERS_BASE = {
    "authority": "edith.xiaohongshu.com",
    "accept": "application/json, text/plain, */*",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://www.xiaohongshu.com",
    "referer": "https://www.xiaohongshu.com/",
}

DEFAULT_COOKIE_FILE = pathlib.Path(__file__).parent / "cookies" / "xhs_cookies.txt"
DEFAULT_PAGE_SIZE = 20


# ------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------

def load_cookies(path: pathlib.Path = DEFAULT_COOKIE_FILE) -> List[str]:
    """读取 Cookie 行列表。一行一个账号。"""
    if not path.exists():
        raise FileNotFoundError(f"Cookie 文件不存在: {path}")
    cookies = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    if not cookies:
        raise ValueError("Cookie 文件为空，请至少放置一行 Cookie")
    return cookies


def gen_sign(url: str, payload: dict, cookie: str) -> Dict[str, str]:
    """生成 x-s / x-t 等签名头。

    优先顺序：
    1) 若项目已 clone xhs-mcp 并存在 `api/xhsvm.js`，
       直接使用里面提供的 `GetXsXt` 函数，速度更快、依赖最少；
    2) 否则回退到旧的 `tasks/js/sign_xhs.js` 方案（需自行准备并能在 Node 环境跑通）。
    """
    # ① 尝试使用 xhsvm.js
    xhsvm_path = pathlib.Path(__file__).parents[2] / "xhs-mcp" / "api" / "xhsvm.js"
    if xhsvm_path.exists():
        try:
            # 缓存编译结果，避免重复开销
            if not hasattr(gen_sign, "_ctx_xhsvm"):
                gen_sign._ctx_xhsvm = execjs.compile(xhsvm_path.read_text(encoding='utf-8'))  # type: ignore
            xs_xt = gen_sign._ctx_xhsvm.call(
                "GetXsXt", url, payload, cookie  # type: ignore[attr-defined]
            )
            if xs_xt:
                result = json.loads(xs_xt)
                # 确保 x-t 是字符串类型
                if 'x-t' in result:
                    result['x-t'] = str(result['x-t'])
                return result
        except Exception as exc:  # noqa: W0703
            logger.error("xhsvm.js 计算签名失败: {}，尝试备用方案", exc)

    # ② 备用 sign_xhs.js
    js_file = pathlib.Path(__file__).parent / "js" / "sign_xhs.js"
    if not js_file.exists():
        logger.warning("未找到可用签名脚本，将不携带签名头，接口可能返回 401/461")
        return {}

    try:
        if not hasattr(gen_sign, "_ctx_sign"):
            gen_sign._ctx_sign = execjs.compile(js_file.read_text(encoding='utf-8'))  # type: ignore
        result = gen_sign._ctx_sign.call(  # type: ignore[attr-defined]
            "get_sign", url, json.dumps(payload, separators=(",", ":")), cookie
        )
        # 确保 x-t 是字符串类型
        if isinstance(result, dict) and 'x-t' in result:
            result['x-t'] = str(result['x-t'])
        return result
    except Exception as exc:  # noqa: W0703
        logger.error("sign_xhs.js 计算签名失败: {}，改为无签名请求", exc)
        return {}


def cycle_cookies(cookies: List[str]) -> Generator[str, None, None]:
    """无限循环 Cookie，以避免单账号频率过高。"""
    while True:
        random.shuffle(cookies)
        for ck in cookies:
            yield ck


# ------------------------------------------------------------
# 核心抓取逻辑
# ------------------------------------------------------------

def get_search_id(keyword: str, cookie: str) -> str | None:
    """获取 search_id；优先使用 Selenium，失败后回退到 API 方式"""
    
    # 方法1: 使用 Selenium 获取 search_id
    logger.info("尝试使用 Selenium 获取 search_id: {}", keyword)
    try:
        with XHSSeleniumHelper(headless=True) as helper:
            search_id = helper.get_search_id(keyword)
            if search_id:
                logger.success("Selenium 成功获取 search_id: {} -> {}", keyword, search_id)
                return search_id
    except Exception as e:
        logger.warning("Selenium 方式失败: {}", e)
    
    # 方法2: 回退到 API 方式（保留原有逻辑）
    logger.info("回退到 API 方式获取 search_id: {}", keyword)
    
    # 尝试不同的参数组合
    params_list = [
        {"keyword": keyword},
        {"keyword": keyword, "page": 1},
        {"keyword": keyword, "sort": "time"},
        {"keyword": keyword, "page": 1, "sort": "time", "note_type": 0},
    ]
    
    for i, params in enumerate(params_list):
        logger.debug("尝试参数组合 {}: {}", i+1, params)
        sign_headers = gen_sign(FILTER_URL, params, cookie)
        
        # 确保所有 header 值都是字符串
        for key, value in sign_headers.items():
            if not isinstance(value, str):
                sign_headers[key] = str(value)
        
        headers = {**HEADERS_BASE, **sign_headers, "cookie": cookie}
        
        # 添加随机延迟
        time.sleep(random.uniform(0.5, 1.5))
        
        r = requests.get(FILTER_URL, headers=headers, params=params, timeout=10)
        try:
            data = r.json()
        except ValueError:
            logger.warning("参数组合 {} 非 JSON 响应: {}", i+1, r.text[:200])
            continue

        if data.get("success", True):
            rid = data.get("data", {}).get("search_id")
            if rid:
                logger.info("API 成功获取 search_id: {} (参数组合 {})", rid, i+1)
                return rid
            else:
                logger.debug("参数组合 {} 无 search_id: {}", i+1, data)
        else:
            logger.debug("参数组合 {} 失败: {}", i+1, data)
    
    # 所有方法都失败了
    logger.error("所有方法都无法获取 search_id: {}", keyword)
    return None


def fetch_notes(keyword: str, pages: int | None = None, cookie_file: pathlib.Path = DEFAULT_COOKIE_FILE):
    cookies = load_cookies(cookie_file)
    ck_iter = cycle_cookies(cookies)

    page = 1
    has_more = True
    ses = requests.Session()

    with SessionLocal() as db:
        while has_more:
            if pages and page > pages:
                logger.info("达到页数上限 {}，停止", pages)
                break

            payload = {
                "keyword": keyword,
                "page": page,
                "page_size": DEFAULT_PAGE_SIZE,
                "sort": "time",  # 按时间排序
                "note_type": 0,  # 0=全部，1=视频，2=图文
            }
            ck = next(ck_iter)
            search_id = get_search_id(keyword, ck)
            if search_id:
                payload["search_id"] = search_id
            else:
                logger.warning("无法获取 search_id，尝试直接搜索...")
            sign_headers = gen_sign(API_URL, payload, ck)
            
            # 确保所有 header 值都是字符串
            for key, value in sign_headers.items():
                if not isinstance(value, str):
                    sign_headers[key] = str(value)
            
            headers = {
                **HEADERS_BASE,
                **sign_headers,
                "cookie": ck,
            }

            resp = ses.post(API_URL, json=payload, headers=headers, timeout=10)
            logger.debug("搜索接口响应状态码: {}", resp.status_code)
            
            if resp.status_code != 200:
                logger.error("HTTP {} @ page {}", resp.status_code, page)
                logger.error("响应内容: {}", resp.text[:500])
                break
                
            data = resp.json()
            logger.debug("搜索接口完整响应: {}", data)
            
            if data.get("success") is False:
                logger.error("接口返回失败: {}", data)
                break
            
            # 检查是否有笔记数据
            data_section = data.get("data", {})
            note_list = data_section.get("notes") or data_section.get("items") or []
            
            logger.info("第 {} 页返回 {} 条笔记", page, len(note_list))
            
            if not note_list:
                logger.warning("第 {} 页无数据，完整响应: {}", page, data)
                break

            save_notes(db, note_list)
            logger.success("保存第 {} 页 {} 条笔记", page, len(note_list))

            page += 1
            has_more = data.get("data", {}).get("has_more", False)
            time.sleep(random.uniform(1.5, 3.0))


# ------------------------------------------------------------
# 数据库存储
# ------------------------------------------------------------

def save_notes(db, notes: List[dict]):
    for n in notes:
        note_id = n.get("id") or n.get("note_id")
        if not note_id:
            continue
        note = XHSNote(
            note_id=note_id,
            title=n.get("title"),
            desc=n.get("desc"),
            url=f"https://www.xiaohongshu.com/explore/{note_id}",
            user_id=n.get("user", {}).get("user_id"),
            user_name=n.get("user", {}).get("nickname"),
            like_count=n.get("like_count"),
            collect_count=n.get("collect_count"),
            comment_count=n.get("comment_count"),
            publish_time=datetime.fromtimestamp(n.get("time", 0)),
            raw_json=n,
        )
        db.merge(note)
    db.commit()


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="XiaoHongShu 爬虫")
    parser.add_argument("keyword", help="搜索关键词，如 '科技创新'")
    parser.add_argument("--pages", type=int, default=None, help="最大页数，默认不限")
    parser.add_argument("--cookie-file", type=pathlib.Path, default=DEFAULT_COOKIE_FILE, help="Cookie 文件路径")
    args = parser.parse_args()

    logger.info("开始爬取小红书笔记，关键词: {}, 页数限制: {}", args.keyword, args.pages or "无限制")
    fetch_notes(args.keyword, args.pages, args.cookie_file)
    logger.info("爬取完成") 