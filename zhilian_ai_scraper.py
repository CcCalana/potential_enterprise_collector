#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智联招聘爬虫 - 苏州工业园区人工智能岗位
使用Selenium实现，基于参考教程改进
"""

import csv
import json
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlencode, quote

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from app.config import get_db_session
from init_zhilian_db import ZhilianJob, init_zhilian_db


class ZhilianAIScraper:
    """智联招聘AI岗位爬虫类"""
    
    def __init__(self):
        self.base_url = "https://www.zhaopin.com"
        self.driver = None
        self.session = None
        self.wait = None
        
    def init_driver(self) -> bool:
        """初始化浏览器驱动"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 如果不需要显示浏览器界面，可以取消注释下面这行
            # chrome_options.add_argument('--headless')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            
            print("浏览器驱动初始化成功")
            return True
            
        except Exception as e:
            print(f"浏览器驱动初始化失败: {e}")
            return False
    
    def init_database(self) -> bool:
        """初始化数据库连接"""
        try:
            # 先初始化数据库表
            init_zhilian_db()
            
            # 获取数据库会话
            self.session = get_db_session()
            print("数据库连接成功")
            return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return False
    
    def build_search_url(self, keyword: str = "人工智能", city: str = "苏州", page: int = 1) -> str:
        """构建搜索URL"""
        # 智联招聘的搜索URL格式
        # 苏州的城市代码是538
        encoded_keyword = quote(keyword)
        search_url = f"https://www.zhaopin.com/sou/jl538/kw{encoded_keyword}/p{page}"
        
        return search_url
    
    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """等待页面加载完成"""
        try:
            # 等待职位列表加载
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "joblist-item"))
            )
            time.sleep(random.uniform(2, 4))
            return True
        except Exception as e:
            print(f"页面加载超时: {e}")
            return False
    
    def extract_job_info(self, job_element) -> Optional[Dict]:
        """从职位元素中提取信息"""
        try:
            job_info = {}
            
            # 职位标题和链接
            try:
                title_element = job_element.find_element(By.CSS_SELECTOR, ".job-title a")
                job_info['job_title'] = title_element.text.strip()
                job_info['job_url'] = title_element.get_attribute('href')
                # 从URL中提取job_id
                if job_info['job_url']:
                    job_info['job_id'] = job_info['job_url'].split('/')[-1].replace('.html', '')
            except:
                pass
            
            # 公司名称
            try:
                company_element = job_element.find_element(By.CSS_SELECTOR, ".company-name a")
                job_info['company_name'] = company_element.text.strip()
            except:
                pass
            
            # 薪资
            try:
                salary_element = job_element.find_element(By.CSS_SELECTOR, ".salary")
                job_info['salary'] = salary_element.text.strip()
            except:
                pass
            
            # 工作地点
            try:
                location_element = job_element.find_element(By.CSS_SELECTOR, ".work-addr")
                job_info['work_city'] = location_element.text.strip()
            except:
                pass
            
            # 工作经验和学历要求
            try:
                requirement_elements = job_element.find_elements(By.CSS_SELECTOR, ".job-require span")
                if len(requirement_elements) >= 2:
                    job_info['work_experience'] = requirement_elements[0].text.strip()
                    job_info['education'] = requirement_elements[1].text.strip()
            except:
                pass
            
            # 发布时间
            try:
                time_element = job_element.find_element(By.CSS_SELECTOR, ".job-time")
                job_info['publish_time'] = self.parse_publish_time(time_element.text.strip())
            except:
                pass
            
            # 公司规模
            try:
                company_info_element = job_element.find_element(By.CSS_SELECTOR, ".company-info")
                job_info['company_size'] = company_info_element.text.strip()
            except:
                pass
            
            return job_info if job_info else None
            
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
        
        try:
            # 打开职位详情页
            self.driver.get(job_url)
            time.sleep(random.uniform(2, 4))
            
            # 职位描述
            try:
                desc_element = self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "job-detail-content"))
                )
                detail_info['job_description'] = desc_element.text.strip()
            except:
                pass
            
            # 职位要求
            try:
                requirement_element = self.driver.find_element(By.CSS_SELECTOR, ".job-requirement")
                detail_info['job_requirements'] = requirement_element.text.strip()
            except:
                pass
            
            # 福利待遇
            try:
                welfare_element = self.driver.find_element(By.CSS_SELECTOR, ".job-welfare")
                detail_info['welfare'] = welfare_element.text.strip()
            except:
                pass
            
            # 公司详细信息
            try:
                company_detail_element = self.driver.find_element(By.CSS_SELECTOR, ".company-detail")
                detail_info['company_type'] = company_detail_element.text.strip()
            except:
                pass
            
        except Exception as e:
            print(f"获取职位详情失败: {e}")
        
        return detail_info
    
    def save_job_to_db(self, job_info: Dict) -> bool:
        """保存职位信息到数据库"""
        if not self.session:
            return False
            
        try:
            # 检查是否已存在
            job_id = job_info.get('job_id', '')
            if not job_id:
                return False
                
            existing_job = self.session.query(ZhilianJob).filter_by(job_id=job_id).first()
            if existing_job:
                print(f"职位 {job_id} 已存在，跳过")
                return False
            
            # 创建新记录
            job = ZhilianJob(
                job_id=job_id,
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
            print(f"保存职位成功: {job_info.get('job_title', '')} - {job_info.get('company_name', '')}")
            return True
            
        except Exception as e:
            if self.session:
                self.session.rollback()
            print(f"保存职位失败: {e}")
            return False
    
    def scrape_jobs(self, keyword: str = "人工智能", city: str = "苏州", max_pages: int = 5) -> List[Dict]:
        """爬取职位信息"""
        all_jobs = []
        
        if not self.init_driver():
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
                self.driver.get(search_url)
                
                # 等待页面加载
                if not self.wait_for_page_load():
                    print(f"第 {page} 页加载失败，跳过")
                    continue
                
                # 滚动到页面底部，加载更多内容
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # 查找职位元素
                try:
                    job_elements = self.driver.find_elements(By.CLASS_NAME, "joblist-item")
                    print(f"找到 {len(job_elements)} 个职位")
                    
                    for job_element in job_elements:
                        job_info = self.extract_job_info(job_element)
                        if job_info and job_info.get('job_title'):
                            # 获取详细信息
                            if job_info.get('job_url'):
                                detail_info = self.get_job_detail(job_info['job_url'])
                                job_info.update(detail_info)
                                
                                # 返回列表页面
                                self.driver.get(search_url)
                                time.sleep(2)
                            
                            # 保存到数据库
                            if self.save_job_to_db(job_info):
                                all_jobs.append(job_info)
                        
                        # 随机延迟
                        time.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    print(f"解析职位元素失败: {e}")
                
                # 检查是否有下一页
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, ".soupager .next")
                    if next_button.is_enabled():
                        next_button.click()
                        time.sleep(random.uniform(3, 5))
                    else:
                        print("没有更多页面了")
                        break
                except:
                    print("没有找到下一页按钮")
                    break
                
                # 页面间随机延迟
                time.sleep(random.uniform(5, 10))
        
        finally:
            if self.driver:
                self.driver.quit()
            if self.session:
                self.session.close()
        
        return all_jobs
    
    def export_to_csv(self, jobs: List[Dict], filename: str = "苏州工业园区人工智能岗位.csv"):
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
    scraper = ZhilianAIScraper()
    
    # 爬取苏州工业园区人工智能相关岗位
    print("开始爬取苏州工业园区人工智能相关岗位...")
    jobs = scraper.scrape_jobs(
        keyword="人工智能", 
        city="苏州", 
        max_pages=5
    )
    
    print(f"共爬取到 {len(jobs)} 个职位")
    
    # 导出到CSV
    scraper.export_to_csv(jobs)


if __name__ == "__main__":
    main() 