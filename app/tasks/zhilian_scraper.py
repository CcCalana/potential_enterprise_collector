#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智联招聘爬虫 - 苏州工业园区人工智能相关岗位
基于DrissionPage实现，参考教程：https://blog.csdn.net/qq_74830852/article/details/148696690
"""

import csv
import json
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode

try:
    from DrissionPage import ChromiumPage
except ImportError:
    print("请先安装DrissionPage: pip install DrissionPage")
    ChromiumPage = None

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import get_db_session
from app.models import Base


# 临时定义ZhilianJob模型，如果models.py中没有的话
try:
    from app.models import ZhilianJob
except ImportError:
    from sqlalchemy import Column, DateTime, Integer, String, Text, func
    from sqlalchemy.dialects.postgresql import JSONB
    
    class ZhilianJob(Base):
        """智联招聘职位信息表"""
        __tablename__ = "zhilian_jobs"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        job_id = Column(String(64), unique=True, nullable=False, index=True)
        job_title = Column(String(256), nullable=False)
        company_name = Column(String(256), nullable=False)
        company_size = Column(String(64))
        company_type = Column(String(64))
        salary = Column(String(64))
        work_city = Column(String(64))
        work_experience = Column(String(64))
        education = Column(String(64))
        job_type = Column(String(32))
        job_description = Column(Text)
        job_requirements = Column(Text)
        welfare = Column(Text)
        publish_time = Column(DateTime(timezone=True))
        update_time = Column(DateTime(timezone=True))
        job_url = Column(String(512))
        raw_json = Column(JSONB)
        created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ZhilianScraper:
    """智联招聘爬虫类"""
    
    def __init__(self):
        self.base_url = "https://www.zhaopin.com"
        self.search_url = "https://www.zhaopin.com/sou/"
        self.page: Optional[Any] = None
        self.session: Optional[Session] = None
        
    def init_browser(self) -> bool:
        """初始化浏览器"""
        if ChromiumPage is None:
            print("DrissionPage未安装，无法初始化浏览器")
            return False
            
        try:
            self.page = ChromiumPage()
            # 设置用户代理
            self.page.set.user_agent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            print("浏览器初始化成功")
            return True
        except Exception as e:
            print(f"浏览器初始化失败: {e}")
            return False
    
    def init_database(self) -> bool:
        """初始化数据库连接"""
        try:
            self.session = get_db_session()
            print("数据库连接成功")
            return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return False
    
    def build_search_url(self, keyword: str = "人工智能", city: str = "苏州", page: int = 1) -> str:
        """构建搜索URL"""
        # 苏州工业园区的特定搜索
        if "苏州" in city:
            search_url = f"{self.search_url}jl538/{urlencode({'kw': keyword})}/p{page}"
        else:
            params = {
                'kw': keyword,
                'jl': city,
                'p': page
            }
            search_url = f"{self.search_url}{urlencode(params)}"
        
        return search_url
    
    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """等待页面加载完成"""
        if not self.page:
            return False
            
        try:
            # 等待职位列表加载
            self.page.wait.ele_loaded('.joblist-item', timeout=timeout)
            time.sleep(random.uniform(2, 4))
            return True
        except Exception as e:
            print(f"页面加载超时: {e}")
            return False
    
    def extract_job_info(self, job_element: Any) -> Optional[Dict]:
        """从职位元素中提取信息"""
        try:
            job_info = {}
            
            # 职位标题和链接
            title_ele = job_element.ele('.job-title a', timeout=2)
            if title_ele:
                job_info['job_title'] = title_ele.text.strip()
                job_info['job_url'] = title_ele.attr('href')
                # 从URL中提取job_id
                job_info['job_id'] = job_info['job_url'].split('/')[-1].replace('.html', '') if job_info['job_url'] else ''
            
            # 公司名称
            company_ele = job_element.ele('.company-name a', timeout=2)
            if company_ele:
                job_info['company_name'] = company_ele.text.strip()
            
            # 薪资
            salary_ele = job_element.ele('.salary', timeout=2)
            if salary_ele:
                job_info['salary'] = salary_ele.text.strip()
            
            # 工作地点
            location_ele = job_element.ele('.work-addr', timeout=2)
            if location_ele:
                job_info['work_city'] = location_ele.text.strip()
            
            # 工作经验和学历要求
            requirement_eles = job_element.eles('.job-require span')
            if len(requirement_eles) >= 2:
                job_info['work_experience'] = requirement_eles[0].text.strip()
                job_info['education'] = requirement_eles[1].text.strip()
            
            # 发布时间
            time_ele = job_element.ele('.job-time', timeout=2)
            if time_ele:
                job_info['publish_time'] = self.parse_publish_time(time_ele.text.strip())
            
            # 公司规模和类型
            company_info_ele = job_element.ele('.company-info', timeout=2)
            if company_info_ele:
                job_info['company_size'] = company_info_ele.text.strip()
            
            return job_info
            
        except Exception as e:
            print(f"提取职位信息失败: {e}")
            return None
    
    def parse_publish_time(self, time_str: str) -> Optional[datetime]:
        """解析发布时间"""
        try:
            if "今天" in time_str:
                return datetime.now()
            elif "昨天" in time_str:
                return datetime.now() - timedelta(days=1)
            elif "天前" in time_str:
                days = int(time_str.replace("天前", ""))
                return datetime.now() - timedelta(days=days)
            else:
                # 尝试解析具体日期格式
                return datetime.strptime(time_str, "%m-%d").replace(year=datetime.now().year)
        except:
            return None
    
    def get_job_detail(self, job_url: str) -> Dict:
        """获取职位详情"""
        detail_info = {}
        
        if not self.page:
            return detail_info
            
        try:
            # 打开职位详情页
            self.page.get(job_url)
            self.wait_for_page_load()
            
            # 职位描述
            desc_ele = self.page.ele('.job-description', timeout=5)
            if desc_ele:
                detail_info['job_description'] = desc_ele.text.strip()
            
            # 职位要求
            requirement_ele = self.page.ele('.job-requirement', timeout=5)
            if requirement_ele:
                detail_info['job_requirements'] = requirement_ele.text.strip()
            
            # 福利待遇
            welfare_ele = self.page.ele('.job-welfare', timeout=5)
            if welfare_ele:
                detail_info['welfare'] = welfare_ele.text.strip()
            
            # 公司详细信息
            company_detail_ele = self.page.ele('.company-detail', timeout=5)
            if company_detail_ele:
                detail_info['company_type'] = company_detail_ele.text.strip()
            
        except Exception as e:
            print(f"获取职位详情失败: {e}")
        
        return detail_info
    
    def save_job_to_db(self, job_info: Dict) -> bool:
        """保存职位信息到数据库"""
        if not self.session:
            return False
            
        try:
            # 检查是否已存在
            existing_job = self.session.query(ZhilianJob).filter_by(job_id=job_info['job_id']).first()
            if existing_job:
                print(f"职位 {job_info['job_id']} 已存在，跳过")
                return False
            
            # 创建新记录
            job = ZhilianJob(
                job_id=job_info.get('job_id', ''),
                job_title=job_info.get('job_title', ''),
                company_name=job_info.get('company_name', ''),
                company_size=job_info.get('company_size', ''),
                company_type=job_info.get('company_type', ''),
                salary=job_info.get('salary', ''),
                work_city=job_info.get('work_city', ''),
                work_experience=job_info.get('work_experience', ''),
                education=job_info.get('education', ''),
                job_type=job_info.get('job_type', '全职'),
                job_description=job_info.get('job_description', ''),
                job_requirements=job_info.get('job_requirements', ''),
                welfare=job_info.get('welfare', ''),
                publish_time=job_info.get('publish_time'),
                job_url=job_info.get('job_url', ''),
                raw_json=job_info
            )
            
            self.session.add(job)
            self.session.commit()
            print(f"保存职位成功: {job_info['job_title']} - {job_info['company_name']}")
            return True
            
        except IntegrityError:
            self.session.rollback()
            print(f"职位 {job_info['job_id']} 已存在，跳过")
            return False
        except Exception as e:
            self.session.rollback()
            print(f"保存职位失败: {e}")
            return False
    
    def scrape_jobs(self, keyword: str = "人工智能", city: str = "苏州", max_pages: int = 10) -> List[Dict]:
        """爬取职位信息"""
        all_jobs = []
        
        if not self.init_browser():
            return all_jobs
        
        if not self.init_database():
            return all_jobs
        
        try:
            for page in range(1, max_pages + 1):
                print(f"正在爬取第 {page} 页...")
                
                # 构建搜索URL
                search_url = self.build_search_url(keyword, city, page)
                print(f"访问URL: {search_url}")
                
                # 访问搜索页面
                self.page.get(search_url)
                
                # 等待页面加载
                if not self.wait_for_page_load():
                    print(f"第 {page} 页加载失败，跳过")
                    continue
                
                # 滚动到页面底部，加载更多内容
                self.page.scroll.to_bottom()
                time.sleep(2)
                
                # 解析页面元素
                job_elements = self.page.eles('.joblist-item')
                
                for job_element in job_elements:
                    job_info = self.extract_job_info(job_element)
                    if job_info:
                        # 获取详细信息
                        if job_info.get('job_url'):
                            detail_info = self.get_job_detail(job_info['job_url'])
                            job_info.update(detail_info)
                        
                        # 保存到数据库
                        self.save_job_to_db(job_info)
                        all_jobs.append(job_info)
                    
                    # 随机延迟
                    time.sleep(random.uniform(1, 3))
                
                # 检查是否有下一页
                next_button = self.page.ele('.soupager a:last-of-type', timeout=5)
                if next_button and "下一页" in next_button.text:
                    next_button.click()
                    time.sleep(random.uniform(3, 5))
                else:
                    print("没有更多页面了")
                    break
                
                # 页面间随机延迟
                time.sleep(random.uniform(5, 10))
        
        finally:
            if self.page:
                self.page.quit()
            if self.session:
                self.session.close()
        
        return all_jobs
    
    def export_to_csv(self, jobs: List[Dict], filename: str = "zhilian_jobs.csv"):
        """导出职位信息到CSV文件"""
        if not jobs:
            print("没有职位数据可导出")
            return
        
        try:
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                fieldnames = [
                    '职位', '薪资', '公司', '城市', '工作经验', '学历要求', 
                    '公司规模', '福利待遇', '发布时间', '职位链接'
                ]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for job in jobs:
                    writer.writerow({
                        '职位': job.get('job_title', ''),
                        '薪资': job.get('salary', ''),
                        '公司': job.get('company_name', ''),
                        '城市': job.get('work_city', ''),
                        '工作经验': job.get('work_experience', ''),
                        '学历要求': job.get('education', ''),
                        '公司规模': job.get('company_size', ''),
                        '福利待遇': job.get('welfare', ''),
                        '发布时间': job.get('publish_time', ''),
                        '职位链接': job.get('job_url', ''),
                    })
            
            print(f"成功导出 {len(jobs)} 条职位信息到 {filename}")
            
        except Exception as e:
            print(f"导出CSV失败: {e}")


def main():
    """主函数"""
    scraper = ZhilianScraper()
    
    # 爬取苏州工业园区人工智能相关岗位
    print("开始爬取苏州工业园区人工智能相关岗位...")
    jobs = scraper.scrape_jobs(
        keyword="人工智能", 
        city="苏州", 
        max_pages=5
    )
    
    print(f"共爬取到 {len(jobs)} 个职位")
    
    # 导出到CSV
    scraper.export_to_csv(jobs, "苏州工业园区人工智能岗位.csv")


if __name__ == "__main__":
    main() 