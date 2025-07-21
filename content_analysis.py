#!/usr/bin/env python3
"""
基于现有数据的企业信息分析工具
即使没有正文内容，也能从标题和基本信息中提取有价值的企业信息
"""

import sys
import re
from typing import List, Dict, Any

sys.path.insert(0, '.')

from app.config import SessionLocal
from app.models import XHSNote
from loguru import logger

class EnterpriseAnalyzer:
    """企业信息分析器"""
    
    def __init__(self):
        # 企业关键词模式
        self.enterprise_patterns = [
            r'(.*?)(公司|企业|集团|科技|有限公司|股份|实业)',
            r'(.*?)(工业园区|产业园|科技园)',
            r'(.*?)(招聘|入职|工作|岗位|职位)',
            r'(.*?)(投资|融资|上市|IPO)',
            r'(.*?)(AI|人工智能|大数据|云计算|区块链)',
            r'(.*?)(生物医药|医疗|健康|制药)',
            r'(.*?)(新能源|环保|绿色)',
            r'(.*?)(金融|银行|保险|证券)',
            r'(.*?)(制造|生产|工厂|车间)',
            r'(.*?)(研发|技术|创新|专利)'
        ]
        
        # 地区关键词
        self.location_patterns = [
            r'苏州工业园区',
            r'苏州园区',
            r'园区',
            r'苏州',
            r'江苏'
        ]
    
    def extract_enterprise_info(self, note: XHSNote) -> Dict[str, Any]:
        """从笔记中提取企业信息"""
        title = str(note.title or "")
        info = {
            'note_id': note.note_id,
            'title': title,
            'author': note.user_name,
            'likes': note.like_count or 0,
            'collects': note.collect_count or 0,
            'comments': note.comment_count or 0,
            'url': note.url,
            'enterprise_keywords': [],
            'location_keywords': [],
            'category': 'unknown',
            'confidence': 0.0
        }
        
        # 提取企业关键词
        for pattern in self.enterprise_patterns:
            matches = re.findall(pattern, title, re.IGNORECASE)
            if matches:
                info['enterprise_keywords'].extend(matches)
        
        # 提取地区关键词
        for pattern in self.location_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                info['location_keywords'].append(pattern)
        
        # 分类判断
        info['category'] = self._categorize_note(title)
        
        # 计算置信度
        info['confidence'] = self._calculate_confidence(title, info)
        
        return info
    
    def _categorize_note(self, title: str) -> str:
        """对笔记进行分类"""
        title_lower = title.lower()
        
        if any(keyword in title_lower for keyword in ['招聘', '入职', '工作', '岗位', '职位', '面试']):
            return 'recruitment'
        elif any(keyword in title_lower for keyword in ['公司', '企业', '集团', '科技']):
            return 'company'
        elif any(keyword in title_lower for keyword in ['政策', '补贴', '扶持', '优惠']):
            return 'policy'
        elif any(keyword in title_lower for keyword in ['投资', '融资', '上市', 'ipo']):
            return 'investment'
        elif any(keyword in title_lower for keyword in ['ai', '人工智能', '大数据', '云计算']):
            return 'technology'
        elif any(keyword in title_lower for keyword in ['旅游', '攻略', '景点', '游玩']):
            return 'tourism'
        elif any(keyword in title_lower for keyword in ['生活', '居住', '房租', '租房']):
            return 'lifestyle'
        else:
            return 'general'
    
    def _calculate_confidence(self, title: str, info: Dict[str, Any]) -> float:
        """计算企业相关性置信度"""
        confidence = 0.0
        
        # 基于关键词数量
        confidence += len(info['enterprise_keywords']) * 0.3
        confidence += len(info['location_keywords']) * 0.2
        
        # 基于分类
        category_weights = {
            'company': 0.8,
            'recruitment': 0.7,
            'technology': 0.6,
            'investment': 0.6,
            'policy': 0.5,
            'tourism': 0.2,
            'lifestyle': 0.1,
            'general': 0.1
        }
        confidence += category_weights.get(info['category'], 0.1)
        
        # 基于热度（高热度内容更可能有价值）
        likes = info['likes']
        if likes > 1000:
            confidence += 0.3
        elif likes > 500:
            confidence += 0.2
        elif likes > 100:
            confidence += 0.1
        
        return min(confidence, 1.0)  # 限制在0-1之间

def analyze_enterprise_notes():
    """分析数据库中的企业笔记"""
    analyzer = EnterpriseAnalyzer()
    
    with SessionLocal() as db:
        # 获取所有笔记
        notes = db.query(XHSNote).order_by(XHSNote.like_count.desc()).all()
        
        logger.info("开始分析 {} 条笔记", len(notes))
        
        # 分析每条笔记
        results = []
        for note in notes:
            info = analyzer.extract_enterprise_info(note)
            results.append(info)
        
        # 按置信度排序
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 输出高价值企业信息
        print("\n🏢 高价值企业相关笔记 (置信度 > 0.5):")
        print("=" * 80)
        
        high_value_count = 0
        for info in results:
            if info['confidence'] > 0.5:
                high_value_count += 1
                print(f"\n{high_value_count}. {info['title']}")
                print(f"   分类: {info['category']} | 置信度: {info['confidence']:.2f}")
                print(f"   作者: {info['author']} | 热度: 👍{info['likes']} 💾{info['collects']} 💬{info['comments']}")
                print(f"   企业关键词: {info['enterprise_keywords']}")
                print(f"   地区关键词: {info['location_keywords']}")
                print(f"   链接: {info['url']}")
        
        # 统计分析
        print(f"\n📊 统计分析:")
        print(f"总笔记数: {len(results)}")
        print(f"高价值笔记数: {high_value_count}")
        
        # 按分类统计
        category_stats = {}
        for info in results:
            category = info['category']
            category_stats[category] = category_stats.get(category, 0) + 1
        
        print(f"\n📈 分类统计:")
        for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count} 条")
        
        # 推荐关注的企业信息
        print(f"\n🎯 推荐关注的企业信息:")
        company_notes = [info for info in results if info['category'] == 'company' and info['confidence'] > 0.6]
        recruitment_notes = [info for info in results if info['category'] == 'recruitment' and info['confidence'] > 0.6]
        tech_notes = [info for info in results if info['category'] == 'technology' and info['confidence'] > 0.6]
        
        if company_notes:
            print(f"  🏢 企业信息: {len(company_notes)} 条")
            for info in company_notes[:3]:
                print(f"    - {info['title']} (👍{info['likes']})")
        
        if recruitment_notes:
            print(f"  👔 招聘信息: {len(recruitment_notes)} 条")
            for info in recruitment_notes[:3]:
                print(f"    - {info['title']} (👍{info['likes']})")
        
        if tech_notes:
            print(f"  💻 技术信息: {len(tech_notes)} 条")
            for info in tech_notes[:3]:
                print(f"    - {info['title']} (👍{info['likes']})")

if __name__ == "__main__":
    analyze_enterprise_notes() 