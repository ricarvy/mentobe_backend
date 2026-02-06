import sys
import os
from sqlalchemy.orm import Session

# Add parent dir to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.db_models import TarotSpread

SPREAD_I18N = {
    "单张牌": {
        "name_en": "Single Card Reading",
        "name_jp": "ワンオラクル",
        "desc_en": "Quick insight for a single question.",
        "desc_jp": "一つの質問に対する迅速な洞察。"
    },
    "三张牌阵": {
        "name_en": "Three Card Spread",
        "name_jp": "スリーカード",
        "desc_en": "Past, Present, Future. Understand the evolution of events.",
        "desc_jp": "過去・現在・未来。物事の成り行きを理解する。"
    },
    "凯尔特十字": {
        "name_en": "Celtic Cross",
        "name_jp": "ケルト十字",
        "desc_en": "Comprehensive analysis of a situation.",
        "desc_jp": "問題の包括的な分析。"
    },
    "时间流牌阵": {
        "name_en": "Time Flow Spread",
        "name_jp": "タイムフロー",
        "desc_en": "Predict the future & explore the unknown with a timeline.",
        "desc_jp": "未来予測＆未知の探求。時間軸のある占い。"
    },
    "圣三角牌阵": {
        "name_en": "Holy Triangle",
        "name_jp": "ホーリートライアングル",
        "desc_en": "Analyze the situation & find causes. Clarify the context.",
        "desc_jp": "状況判断＆原因究明。事の経緯を整理する。"
    },
    "直指核心牌阵": {
        "name_en": "Heart of the Matter",
        "name_jp": "核心へのアプローチ",
        "desc_en": "Explore the problem & hit the key point. Quickly find the crux.",
        "desc_jp": "問題探求＆要点直撃。問題の核心を素早く見つける。"
    },
    "恋人金字塔": {
        "name_en": "Lovers' Pyramid",
        "name_jp": "ラバーズピラミッド",
        "desc_en": "Relationship & interaction analysis. Simple and direct.",
        "desc_jp": "恋人関係＆相互作用の分析。シンプルで直接的。"
    },
    "爱情大十字": {
        "name_en": "Love Cross",
        "name_jp": "愛の十字架",
        "desc_en": "Relationship & love status. Focus on inner feelings.",
        "desc_jp": "男女関係＆恋愛状況。内なる感情に焦点を当てる。"
    },
    "寻找对象牌阵": {
        "name_en": "Soulmate Search",
        "name_jp": "ソウルメイトサーチ",
        "desc_en": "Find your destined one.",
        "desc_jp": "意中の人＆縁のある人を探す。"
    },
    "爱情树牌阵": {
        "name_en": "Love Tree",
        "name_jp": "愛の樹",
        "desc_en": "Trace back to the source & find the crux. Review love history.",
        "desc_jp": "根源遡及＆核心究明。過去の恋愛を振り返る。"
    },
    "二选一牌阵": {
        "name_en": "Two Options Decision",
        "name_jp": "二者択一",
        "desc_en": "Choice & judgment between two options.",
        "desc_jp": "選択＆判断。二つの状況からの選択。"
    },
    "三选一牌阵": {
        "name_en": "Three Options Decision",
        "name_jp": "三者択一",
        "desc_en": "Choice & judgment among three options.",
        "desc_jp": "選択＆判断。三つの選択肢の分析。"
    },
    "财富之树": {
        "name_en": "Wealth Tree",
        "name_jp": "富の樹",
        "desc_en": "Career development & financial status.",
        "desc_jp": "仕事の発展＆金運状況。"
    },
    "问题解决牌阵": {
        "name_en": "Problem Solving Spread",
        "name_jp": "問題解決スプレッド",
        "desc_en": "Analyze the problem & answer doubts.",
        "desc_jp": "問題分析＆疑問解消。"
    },
    "身心灵牌阵": {
        "name_en": "Mind, Body, Spirit",
        "name_jp": "心・体・精神",
        "desc_en": "Self-exploration & understanding yourself.",
        "desc_jp": "自己探求＆自分自身を知る。"
    },
    "四元素牌阵": {
        "name_en": "Four Elements",
        "name_jp": "四元素",
        "desc_en": "Problem exploration & multi-faceted analysis.",
        "desc_jp": "問題探求＆多角的分析。"
    },
    "周运势牌阵": {
        "name_en": "Weekly Forecast",
        "name_jp": "週間運勢",
        "desc_en": "Weekly analysis & forecast.",
        "desc_jp": "週運分析＆一週間の占い。"
    },
    "六芒星牌阵": {
        "name_en": "Hexagram Spread",
        "name_jp": "ヘキサグラム",
        "desc_en": "Development of events & predicting the future.",
        "desc_jp": "事の発展＆未来予測。"
    }
}

def update_spread_i18n():
    db = SessionLocal()
    try:
        print("Updating spread i18n data...")
        for name, data in SPREAD_I18N.items():
            spread = db.query(TarotSpread).filter(TarotSpread.name == name).first()
            if spread:
                print(f"Updating {name}...")
                spread.name_en = data["name_en"]
                spread.name_jp = data["name_jp"]
                spread.description_en = data["desc_en"]
                spread.description_jp = data["desc_jp"]
            else:
                print(f"Spread not found: {name}")
        
        db.commit()
        print("Spread i18n update completed.")
        
    except Exception as e:
        print(f"Error updating spread i18n: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_spread_i18n()
