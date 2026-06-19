# -*- coding: utf-8 -*-
"""黄金新闻与事件影响分析 (升级版: 深度NLP + 事件分类)"""

import os, re, json, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import requests
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 事件类型分类体系
EVENT_TYPES = {
    "monetary": ["美联储","fed","利率","加息","降息","QE","taper","央","monetary","rate"],
    "geopolitical": ["地缘","战争","冲突","制裁","制裁","military","nuclear","invasion","territory"],
    "economic": ["GDP","CPI","通胀","非农","失业","retail","PMI","制造业","服务业","consumer"],
    "market": ["避险","safe haven","避险","risk","volatility","恐慌","selloff","rally"],
    "supply_demand": ["产量","mining","金矿","supply","demand","reserve","央行购金","ETF持仓"],
}

IMPACT_KEYWORDS = {
    "rate hike": -3, "加息": -3, "tightening": -2,
    "rate cut": 3, "降息": 3, "easing": 2,
    "inflation": 2, "通胀": 2, "CPI": 1,
    "geopolitical": 3, "战争": 3, "冲突": 3, "制裁": 2,
    "recession": 2, "衰退": 2, "slowdown": 1,
    "safe haven": 3, "避险": 3, "uncertainty": 2,
    "strong dollar": -2, "weak dollar": 2,
    "central bank buying": 3, "央行购金": 3,
    "tariff": 2, "tariffs": 2,
    "GDP": 1, "非农": 1, "失业": -1,
    "rally": -1, "selloff": 1,
}


def fetch_gold_news(max_items=15):
    """从Google News / Bing抓取黄金新闻"""
    all_news, seen = [], set()
    for url in [
        "https://news.google.com/rss/search?q=gold+price+market&hl=en-US&gl=US&ceid=US:en",
        "https://www.bing.com/news/search?q=gold+market+price&format=rss",
    ]:
        try:
            r = requests.get(url, headers=_HEADERS, timeout=10)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.findall(".//item")[:max_items]:
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    desc = re.sub(r"<[^>]+>", "", item.findtext("description") or "")[:300]
                    if title and title not in seen:
                        seen.add(title)
                        all_news.append({"title": title, "link": link, "description": desc,
                                        "source": "Google" if "google" in url else "Bing"})
        except: pass
    return all_news[:max_items]


def classify_event(news_item):
    """对新闻事件分类"""
    text = (news_item.get("title","") + " " + news_item.get("description","")).lower()
    for event_type, keywords in EVENT_TYPES.items():
        for kw in keywords:
            if kw.lower() in text:
                return event_type
    return "other"


def analyze_impact(news_item):
    """计算单条新闻影响得分"""
    text = (news_item.get("title","") + " " + news_item.get("description","")).lower()
    score = 0
    matched = []
    for keyword, impact in IMPACT_KEYWORDS.items():
        if keyword.lower() in text:
            score += impact
            matched.append(keyword)
    return {"score": score, "matched_keywords": matched[:5]}


def analyze_news_sentiment(news_list):
    """升级版: 对新闻列表进行深度分析"""
    results = []
    total_score = 0
    event_stats = {}
    max_impact_news = None
    max_impact_score = 0

    for item in news_list:
        event_type = classify_event(item)
        impact = analyze_impact(item)
        event_stats[event_type] = event_stats.get(event_type, 0) + 1
        total_score += impact["score"]
        if abs(impact["score"]) > abs(max_impact_score):
            max_impact_score = impact["score"]
            max_impact_news = item["title"][:100]
        category_map = {"monetary":"货币政策","geopolitical":"地缘政治","economic":"经济数据",
                        "market":"市场情绪","supply_demand":"供需","other":"其他"}
        results.append({"title": item["title"][:80], "source": item.get("source",""),
                        "event_type": category_map.get(event_type, "其他"),
                        "impact_score": impact["score"],
                        "keywords": impact["matched_keywords"][:3]})

    total = max(len(news_list), 1)
    avg_score = round(total_score / total, 1)
    if avg_score >= 1.5: summary = "利多黄金 (利好因素占主导)"
    elif avg_score <= -1.5: summary = "利空黄金 (利空因素占主导)"
    else: summary = "中性震荡 (多空因素较为均衡)"

    return {"results": results, "score": round(total_score, 1), "avg_score": avg_score,
            "summary": summary, "total": total, "event_stats": event_stats,
            "top_news": max_impact_news}


def get_news_impact_report():
    news = fetch_gold_news()
    analysis = analyze_news_sentiment(news)
    return {"news": news, "analysis": analysis}
