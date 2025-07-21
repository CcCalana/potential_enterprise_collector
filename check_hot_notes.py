#!/usr/bin/env python3
"""
检查热门笔记排序
"""

import sys
sys.path.insert(0, '.')

from app.config import SessionLocal
from app.models import XHSNote

def main():
    with SessionLocal() as db:
        # 按点赞数排序获取前10条
        hot_notes = db.query(XHSNote).order_by(XHSNote.like_count.desc()).limit(10).all()
        
        print('🔥 按热度排序的前10条笔记:')
        for i, note in enumerate(hot_notes, 1):
            title = note.title or "无标题"
            likes = note.like_count or 0
            collects = note.collect_count or 0
            comments = note.comment_count or 0
            print(f'{i:2}. {title[:40]} (👍{likes} 💾{collects} 💬{comments})')
        
        # 统计总数
        total = db.query(XHSNote).count()
        print(f'\n📊 数据库中总共有 {total} 条笔记')
        
        # 检查是否有正文内容
        with_content = db.query(XHSNote).filter(XHSNote.desc.isnot(None), XHSNote.desc != "").count()
        print(f'📝 有正文内容的笔记: {with_content} 条')

if __name__ == "__main__":
    main() 