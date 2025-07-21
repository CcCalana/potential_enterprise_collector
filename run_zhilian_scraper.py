#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智联招聘爬虫运行脚本
专门爬取苏州工业园区人工智能相关岗位
"""

import sys
import os
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zhilian_ai_scraper import ZhilianAIScraper
from init_zhilian_db import init_zhilian_db


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 智联招聘爬虫 - 苏州工业园区人工智能岗位")
    print("=" * 60)
    
    # 初始化数据库
    print("\n📋 步骤1: 初始化数据库...")
    try:
        init_zhilian_db()
        print("✅ 数据库初始化成功")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return
    
    # 创建爬虫实例
    print("\n🕷️  步骤2: 创建爬虫实例...")
    scraper = ZhilianAIScraper()
    
    # 配置爬取参数
    config = {
        'keyword': '人工智能',
        'city': '苏州',
        'max_pages': 3  # 先爬取3页测试
    }
    
    print(f"📝 爬取配置:")
    print(f"   关键词: {config['keyword']}")
    print(f"   城市: {config['city']}")
    print(f"   最大页数: {config['max_pages']}")
    
    # 开始爬取
    print(f"\n🎯 步骤3: 开始爬取职位信息...")
    print("⚠️  注意: 请确保Chrome浏览器已安装")
    print("⚠️  爬取过程可能需要几分钟，请耐心等待...")
    
    try:
        jobs = scraper.scrape_jobs(
            keyword=config['keyword'],
            city=config['city'],
            max_pages=config['max_pages']
        )
        
        if jobs:
            print(f"\n🎉 爬取成功！共获取到 {len(jobs)} 个职位")
            
            # 显示前几个职位的信息
            print("\n📊 职位预览:")
            for i, job in enumerate(jobs[:5]):  # 显示前5个
                print(f"  {i+1}. {job.get('job_title', 'N/A')} - {job.get('company_name', 'N/A')}")
                print(f"     薪资: {job.get('salary', 'N/A')} | 地点: {job.get('work_city', 'N/A')}")
                print(f"     经验: {job.get('work_experience', 'N/A')} | 学历: {job.get('education', 'N/A')}")
                print()
            
            if len(jobs) > 5:
                print(f"   ... 还有 {len(jobs) - 5} 个职位")
            
            # 导出CSV
            print("\n📄 步骤4: 导出CSV文件...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"苏州工业园区人工智能岗位_{timestamp}.csv"
            
            scraper.export_to_csv(jobs, csv_filename)
            print(f"✅ CSV文件已保存: {csv_filename}")
            
            # 统计信息
            print("\n📈 统计信息:")
            companies = set(job.get('company_name', '') for job in jobs if job.get('company_name'))
            print(f"   涉及公司数量: {len(companies)}")
            
            salaries = [job.get('salary', '') for job in jobs if job.get('salary')]
            print(f"   有薪资信息的职位: {len(salaries)}")
            
            experiences = [job.get('work_experience', '') for job in jobs if job.get('work_experience')]
            print(f"   有经验要求的职位: {len(experiences)}")
            
        else:
            print("❌ 没有爬取到任何职位信息")
            print("可能原因:")
            print("  1. 网络连接问题")
            print("  2. 智联招聘网站结构变化")
            print("  3. 被反爬虫机制拦截")
            print("  4. 搜索条件过于严格")
            
    except Exception as e:
        print(f"❌ 爬取过程中出现错误: {e}")
        print("建议:")
        print("  1. 检查网络连接")
        print("  2. 确认Chrome浏览器已安装")
        print("  3. 尝试减少爬取页数")
        print("  4. 检查数据库连接")
    
    print("\n" + "=" * 60)
    print("🏁 爬虫运行完成")
    print("=" * 60)


if __name__ == "__main__":
    main() 