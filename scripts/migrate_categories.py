import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from app.db_models import TarotSpreadCategory

CATEGORIES = [
    {"slug": "recommended", "name": "推荐", "sort_order": 1},
    {"slug": "basic", "name": "基础", "sort_order": 2},
    {"slug": "love", "name": "爱情", "sort_order": 3},
    {"slug": "decision", "name": "决策", "sort_order": 4},
    {"slug": "career", "name": "事业", "sort_order": 5},
    {"slug": "self", "name": "自我", "sort_order": 6},
    {"slug": "advanced", "name": "进阶", "sort_order": 7},
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
                    sort_order=cat_data["sort_order"],
                    description=f"{cat_data['name']}牌阵"
                )
                db.add(new_cat)
            else:
                print(f"Category exists: {cat_data['slug']}")
        
        db.commit()
        print("Migration complete.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
