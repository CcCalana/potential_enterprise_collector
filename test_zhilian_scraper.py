#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智联招聘爬虫测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zhilian_ai_scraper import ZhilianAIScraper
from init_zhilian_db import init_zhilian_db


def test_database_init():
    """测试数据库初始化"""
    print("=== 测试数据库初始化 ===")
    try:
        engine = init_zhilian_db()
        print("✅ 数据库初始化成功")
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False


def test_url_building():
    """测试URL构建"""
    print("\n=== 测试URL构建 ===")
    scraper = ZhilianAIScraper()
    
    # 测试默认参数
    url1 = scraper.build_search_url()
    print(f"默认URL: {url1}")
    
    # 测试自定义参数
    url2 = scraper.build_search_url(keyword="机器学习", city="苏州", page=2)
    print(f"自定义URL: {url2}")
    
    # 验证URL格式
    expected_pattern = "https://www.zhaopin.com/sou/jl538/kw"
    if expected_pattern in url1 and expected_pattern in url2:
        print("✅ URL构建测试通过")
        return True
    else:
        print("❌ URL构建测试失败")
        return False


def test_time_parsing():
    """测试时间解析"""
    print("\n=== 测试时间解析 ===")
    scraper = ZhilianAIScraper()
    
    test_cases = [
        "今天",
        "昨天", 
        "3天前",
        "12-25",
        "01-15"
    ]
    
    all_passed = True
    for time_str in test_cases:
        result = scraper.parse_publish_time(time_str)
        if result:
            print(f"✅ '{time_str}' -> {result}")
        else:
            print(f"❌ '{time_str}' -> None")
            all_passed = False
    
    return all_passed


def test_basic_scraping():
    """测试基本爬取功能（只爬取1页）"""
    print("\n=== 测试基本爬取功能 ===")
    
    scraper = ZhilianAIScraper()
    
    try:
        # 只爬取1页进行测试
        jobs = scraper.scrape_jobs(
            keyword="人工智能",
            city="苏州",
            max_pages=1
        )
        
        if jobs:
            print(f"✅ 成功爬取到 {len(jobs)} 个职位")
            
            # 显示第一个职位的信息
            if jobs:
                first_job = jobs[0]
                print(f"示例职位: {first_job.get('job_title', 'N/A')}")
                print(f"公司: {first_job.get('company_name', 'N/A')}")
                print(f"薪资: {first_job.get('salary', 'N/A')}")
                print(f"地点: {first_job.get('work_city', 'N/A')}")
            
            return True
        else:
            print("❌ 没有爬取到任何职位数据")
            return False
            
    except Exception as e:
        print(f"❌ 爬取测试失败: {e}")
        return False


def test_csv_export():
    """测试CSV导出功能"""
    print("\n=== 测试CSV导出功能 ===")
    
    scraper = ZhilianAIScraper()
    
    # 创建测试数据
    test_jobs = [
        {
            'job_title': '人工智能工程师',
            'company_name': '测试公司A',
            'salary': '15K-25K',
            'work_city': '苏州',
            'work_experience': '3-5年',
            'education': '本科',
            'company_size': '100-499人',
            'welfare': '五险一金',
            'publish_time': '2024-01-15',
            'job_url': 'https://www.zhaopin.com/job/test1.html'
        },
        {
            'job_title': '机器学习工程师',
            'company_name': '测试公司B',
            'salary': '20K-30K',
            'work_city': '苏州',
            'work_experience': '5-10年',
            'education': '硕士',
            'company_size': '500-999人',
            'welfare': '五险一金,年终奖',
            'publish_time': '2024-01-14',
            'job_url': 'https://www.zhaopin.com/job/test2.html'
        }
    ]
    
    try:
        scraper.export_to_csv(test_jobs, "test_jobs.csv")
        
        # 检查文件是否存在
        if os.path.exists("test_jobs.csv"):
            print("✅ CSV导出测试通过")
            
            # 清理测试文件
            os.remove("test_jobs.csv")
            return True
        else:
            print("❌ CSV文件未生成")
            return False
            
    except Exception as e:
        print(f"❌ CSV导出测试失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始运行智联招聘爬虫测试套件...\n")
    
    tests = [
        ("数据库初始化", test_database_init),
        ("URL构建", test_url_building),
        ("时间解析", test_time_parsing),
        ("CSV导出", test_csv_export),
        # ("基本爬取", test_basic_scraping),  # 注释掉实际爬取测试，避免频繁访问网站
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name}测试出现异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查相关功能")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 