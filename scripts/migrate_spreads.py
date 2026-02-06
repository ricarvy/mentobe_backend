import sys
import os
import csv
from sqlalchemy.orm import Session

# Add parent dir to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.db_models import TarotSpread, TarotSpreadCategory

def migrate_spreads():
    db = SessionLocal()
    try:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tarot_spreads.csv")
        
        if not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            return

        print("Migrating spreads from CSV...")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Map Chinese headers to model fields
            # 牌阵名,牌阵描述,牌阵牌数,权限,分类
            
            for row in reader:
                name = row['牌阵名']
                description = row['牌阵描述']
                card_count = int(row['牌阵牌数'])
                permission = row['权限']
                category_slug = row['分类']
                
                # Find category
                category = db.query(TarotSpreadCategory).filter(TarotSpreadCategory.slug == category_slug).first()
                if not category:
                    print(f"Category not found for spread {name}: {category_slug}")
                    continue
                
                # Check if spread exists
                spread = db.query(TarotSpread).filter(TarotSpread.name == name).first()
                if spread:
                    print(f"Updating existing spread: {name}")
                    spread.description = description
                    spread.card_count = card_count
                    spread.permission = permission
                    spread.category_id = category.id
                else:
                    print(f"Creating new spread: {name}")
                    spread = TarotSpread(
                        name=name,
                        description=description,
                        card_count=card_count,
                        permission=permission,
                        category_id=category.id,
                        # Default sort order can be handled later or just increment
                        sort_order=0
                    )
                    db.add(spread)
        
        db.commit()
        print("Spread migration completed.")
        
    except Exception as e:
        print(f"Error migrating spreads: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_spreads()
