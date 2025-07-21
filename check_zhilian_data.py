#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看智联招聘数据库数据
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import get_db_session
from init_zhilian_db import ZhilianJob


def check_zhilian_data():
    """查看智联招聘数据"""
    print("=" * 60)
    print("📊 智联招聘数据库数据查看")
    print("=" * 60)
    
    try:
        session = get_db_session()
        
        # 查询总数
        total_count = session.query(ZhilianJob).count()
        print(f"\n📈 总职位数量: {total_count}")
        
        if total_count == 0:
            print("❌ 数据库中没有职位数据")
            print("请先运行爬虫程序: python run_zhilian_scraper.py")
            return
        
        # 查询最新的10条数据
        latest_jobs = session.query(ZhilianJob).order_by(ZhilianJob.created_at.desc()).limit(10).all()
        
        print(f"\n🔍 最新 {len(latest_jobs)} 条职位信息:")
        print("-" * 80)
        
        for i, job in enumerate(latest_jobs, 1):
            print(f"{i}. {job.job_title}")
            print(f"   公司: {job.company_name}")
            print(f"   薪资: {job.salary or 'N/A'}")
            print(f"   地点: {job.work_city or 'N/A'}")
            print(f"   经验: {job.work_experience or 'N/A'}")
            print(f"   学历: {job.education or 'N/A'}")
            print(f"   发布时间: {job.publish_time or 'N/A'}")
            print(f"   创建时间: {job.created_at}")
            print(f"   职位链接: {job.job_url}")
            print("-" * 80)
        
        # 统计信息
        print("\n📊 统计信息:")
        
        # 公司统计
        from sqlalchemy import func
        company_stats = session.query(ZhilianJob.company_name, func.count(ZhilianJob.id))\
                              .group_by(ZhilianJob.company_name)\
                              .order_by(func.count(ZhilianJob.id).desc())\
                              .limit(10).all()
        
        print("\n🏢 招聘最多的公司 (Top 10):")
        for company, count in company_stats:
            print(f"   {company}: {count} 个职位")
        
        # 薪资统计
        salary_jobs = session.query(ZhilianJob).filter(ZhilianJob.salary.isnot(None)).all()
        if salary_jobs:
            print(f"\n💰 薪资信息:")
            print(f"   有薪资信息的职位: {len(salary_jobs)}/{total_count}")
            
            # 显示几个薪资示例
            print("   薪资示例:")
            for job in salary_jobs[:5]:
                print(f"     {job.job_title}: {job.salary}")
        
        # 经验要求统计
        experience_stats = {}
        for job in session.query(ZhilianJob).filter(ZhilianJob.work_experience.isnot(None)).all():
            exp = job.work_experience
            experience_stats[exp] = experience_stats.get(exp, 0) + 1
        
        if experience_stats:
            print(f"\n💼 经验要求分布:")
            for exp, count in sorted(experience_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   {exp}: {count} 个职位")
        
        # 学历要求统计
        education_stats = {}
        for job in session.query(ZhilianJob).filter(ZhilianJob.education.isnot(None)).all():
            edu = job.education
            education_stats[edu] = education_stats.get(edu, 0) + 1
        
        if education_stats:
            print(f"\n🎓 学历要求分布:")
            for edu, count in sorted(education_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"   {edu}: {count} 个职位")
        
        session.close()
        
    except Exception as e:
        print(f"❌ 查询数据时出错: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 数据查看完成")
    print("=" * 60)


def export_all_to_csv():
    """导出所有数据到CSV"""
    print("\n📄 导出所有数据到CSV...")
    
    try:
        session = get_db_session()
        all_jobs = session.query(ZhilianJob).all()
        
        if not all_jobs:
            print("❌ 没有数据可导出")
            return
        
        # 转换为字典格式
        jobs_data = []
        for job in all_jobs:
            jobs_data.append({
                'job_title': job.job_title,
                'company_name': job.company_name,
                'salary': job.salary,
                'work_city': job.work_city,
                'work_experience': job.work_experience,
                'education': job.education,
                'company_size': job.company_size,
                'welfare': job.welfare,
                'publish_time': job.publish_time,
                'job_url': job.job_url,
            })
        
        # 使用爬虫的导出功能
        from zhilian_ai_scraper import ZhilianAIScraper
        scraper = ZhilianAIScraper()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"智联招聘_全部数据_{timestamp}.csv"
        
        scraper.export_to_csv(jobs_data, filename)
        print(f"✅ 已导出 {len(jobs_data)} 条数据到 {filename}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ 导出数据时出错: {e}")


if __name__ == "__main__":
    check_zhilian_data()
    
    # 询问是否导出CSV
    try:
        export_choice = input("\n是否导出所有数据到CSV? (y/n): ").lower()
        if export_choice == 'y':
            export_all_to_csv()
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    except:
        pass 