#!/usr/bin/env python3
"""
修复现有数据库中的笔记数据
"""

from app.config import SessionLocal
from app.models import XHSNote
import json

def safe_int(value, default=0):
    """安全转换为整数"""
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return int(value)

def main():
    with SessionLocal() as db:
        # 获取所有无标题的笔记
        notes = db.query(XHSNote).filter(XHSNote.title.is_(None)).all()
        
        print(f"🔧 开始修复 {len(notes)} 条笔记数据...")
        
        fixed_count = 0
        for note in notes:
            try:
                raw_data = note.raw_json
                
                if 'note_card' in raw_data:
                    note_card = raw_data['note_card']
                    
                    # 更新标题
                    if 'display_title' in note_card:
                        note.title = note_card['display_title']
                    
                    # 更新描述
                    if 'desc' in note_card:
                        note.desc = note_card['desc']
                    
                    # 更新用户信息
                    if 'user' in note_card:
                        user = note_card['user']
                        note.user_id = user.get('user_id')
                        note.user_name = user.get('nickname')
                    
                    # 更新互动信息
                    if 'interact_info' in note_card:
                        interact = note_card['interact_info']
                        note.like_count = safe_int(interact.get('liked_count'))
                        note.collect_count = safe_int(interact.get('collected_count'))
                        note.comment_count = safe_int(interact.get('comment_count'))
                    
                    db.commit()
                    fixed_count += 1
                    
                    print(f"✅ 修复笔记: {note.title}")
                    
            except Exception as e:
                print(f"❌ 修复笔记 {note.note_id} 失败: {e}")
                db.rollback()
        
        print(f"\n🎉 修复完成！共修复 {fixed_count} 条笔记")

if __name__ == "__main__":
    main() 