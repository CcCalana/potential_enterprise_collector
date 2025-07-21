#!/usr/bin/env python3
"""
检查数据库中的小红书笔记数据
"""

from app.config import SessionLocal
from app.models import XHSNote
from sqlalchemy import func

def main():
    with SessionLocal() as db:
        # 总数统计
        total_count = db.query(XHSNote).count()
        print(f"📊 数据库中共有 {total_count} 条小红书笔记")
        
        # 有标题的笔记数量
        with_title_count = db.query(XHSNote).filter(XHSNote.title.isnot(None), XHSNote.title != '').count()
        print(f"📝 有标题的笔记: {with_title_count} 条")
        
        # 无标题的笔记数量
        without_title_count = db.query(XHSNote).filter(
            (XHSNote.title.is_(None)) | (XHSNote.title == '')
        ).count()
        print(f"❌ 无标题的笔记: {without_title_count} 条")
        
        # 显示最近的10条有标题的笔记
        print("\n📋 最近的10条有标题笔记:")
        recent_notes = db.query(XHSNote).filter(
            XHSNote.title.isnot(None), 
            XHSNote.title != ''
        ).order_by(XHSNote.created_at.desc()).limit(10).all()
        
        for i, note in enumerate(recent_notes, 1):
            title_text = note.title or ""
            if len(title_text) > 50:
                title_text = title_text[:50] + "..."
            print(f"{i:2d}. {title_text}")
            print(f"    👤 {note.user_name} | 👍 {note.like_count} | 💬 {note.comment_count}")
            print(f"    🔗 {note.url}")
            print()
        
        # 按用户统计
        print("👥 按用户统计 (前10):")
        user_stats = db.query(
            XHSNote.user_name, 
            func.count(XHSNote.id).label('count')
        ).filter(
            XHSNote.user_name.isnot(None)
        ).group_by(XHSNote.user_name).order_by(
            func.count(XHSNote.id).desc()
        ).limit(10).all()
        
        for user, count in user_stats:
            print(f"  {user}: {count} 条笔记")

if __name__ == "__main__":
    main() 