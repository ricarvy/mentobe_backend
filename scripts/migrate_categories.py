import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from app.db_models import TarotSpreadCategory

CATEGORIES = [
    {"slug": "recommended", "name": "推荐", "name_en": "Recommended", "name_jp": "おすすめ", "sort_order": 1},
    {"slug": "basic", "name": "基础", "name_en": "Basic", "name_jp": "基本", "sort_order": 2},
    {"slug": "love", "name": "爱情", "name_en": "Love", "name_jp": "恋愛", "sort_order": 3},
    {"slug": "decision", "name": "决策", "name_en": "Decision", "name_jp": "決定", "sort_order": 4},
    {"slug": "career", "name": "事业", "name_en": "Career", "name_jp": "仕事", "sort_order": 5},
    {"slug": "self", "name": "自我", "name_en": "Self", "name_jp": "自己", "sort_order": 6},
    {"slug": "advanced", "name": "进阶", "name_en": "Advanced", "name_jp": "上級", "sort_order": 7},
]

def migrate():
    db = SessionLocal()
    try:
        print("Migrating categories...")
        for cat_data in CATEGORIES:
            existing = db.query(TarotSpreadCategory).filter(TarotSpreadCategory.slug == cat_data["slug"]).first()
            if not existing:
                print(f"Adding category: {cat_data['slug']}")
                new_cat = TarotSpreadCategory(
                    slug=cat_data["slug"],
                    name=cat_data["name"],
                    name_en=cat_data["name_en"],
                    name_jp=cat_data["name_jp"],
                    sort_order=cat_data["sort_order"],
                    description=f"{cat_data['name']}牌阵"
                )
                db.add(new_cat)
            else:
                print(f"Updating category: {cat_data['slug']}")
                existing.name = cat_data["name"]
                existing.name_en = cat_data["name_en"]
                existing.name_jp = cat_data["name_jp"]
                existing.sort_order = cat_data["sort_order"]
        
        db.commit()
        print("Migration complete.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
