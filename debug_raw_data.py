#!/usr/bin/env python3
"""
调试原始数据结构
"""

from app.config import SessionLocal
from app.models import XHSNote
import json

def main():
    with SessionLocal() as db:
        # 获取一条无标题的笔记
        note = db.query(XHSNote).filter(XHSNote.title.is_(None)).first()
        
        if note:
            print("🔍 原始JSON数据结构:")
            raw_data = note.raw_json
            print(json.dumps(raw_data, indent=2, ensure_ascii=False))
            
            print("\n📋 数据字段分析:")
            print(f"- id: {raw_data.get('id')}")
            print(f"- model_type: {raw_data.get('model_type')}")
            
            if 'note_card' in raw_data:
                note_card = raw_data['note_card']
                print(f"- note_card.display_title: {note_card.get('display_title')}")
                print(f"- note_card.desc: {note_card.get('desc')}")
                print(f"- note_card.type: {note_card.get('type')}")
                
                if 'user' in note_card:
                    user = note_card['user']
                    print(f"- note_card.user.nickname: {user.get('nickname')}")
                    print(f"- note_card.user.user_id: {user.get('user_id')}")
                
                if 'interact_info' in note_card:
                    interact = note_card['interact_info']
                    print(f"- note_card.interact_info.liked_count: {interact.get('liked_count')}")
                    print(f"- note_card.interact_info.collected_count: {interact.get('collected_count')}")
                    print(f"- note_card.interact_info.comment_count: {interact.get('comment_count')}")
        else:
            print("❌ 未找到无标题的笔记")

if __name__ == "__main__":
    main() 