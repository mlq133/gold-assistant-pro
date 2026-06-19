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



_trans_dict = {
    "Gold": "黄金", "gold": "黄金", "Price": "价格", "price": "价格",
    "Market": "市场", "market": "市场", "Today": "今日", "today": "今日",
    "Record": "记录", "High": "高点", "Low": "低点", "Record High": "历史新高",
    "Fed": "美联储", "Federal Reserve": "美联储", "Rate": "利率", "rates": "利率",
    "Hike": "加息", "hike": "加息", "Cut": "降息", "cut": "降息",
    "Inflation": "通胀", "inflation": "通胀", "Dollar": "美元", "dollar": "美元",
    "Analysis": "分析", "analysis": "分析", "Forecast": "预测", "forecast": "预测",
    "Outlook": "展望", "outlook": "展望", "Weekly": "周度", "Daily": "日度",
    "China": "中国", "India": "印度", "Global": "全球", "World": "世界",
    "Central Bank": "央行", "central bank": "央行", "Reserve": "储备", "reserve": "储备",
    "Up": "上涨", "up": "上涨", "Down": "下跌", "down": "下跌",
    "Jump": "飙升", "jump": "飙升", "Drop": "下跌", "drop": "下跌",
    "Fall": "下跌", "fall": "下跌", "Rise": "上涨", "rise": "上涨",
    "Signal": "信号", "signal": "信号", "Update": "更新", "update": "更新",
    "News": "新闻", "news": "新闻", "Report": "报告", "report": "报告",
    "Strong": "强劲", "strong": "强劲", "Weak": "软弱", "weak": "软弱",
    "Support": "支撑", "support": "支撑", "Resistance": "阻力", "resistance": "阻力",
    "Technical": "技术", "technical": "技术", "Trading": "交易", "trading": "交易",
    "Investor": "投资者", "investor": "投资者", "ETF": "ETF",
    "Commodity": "商品", "commodity": "商品", "Safe Haven": "避险资产",
    "Geopolitical": "地缘政治", "geopolitical": "地缘政治",
    "Uncertainty": "不确定性", "uncertainty": "不确定性",
    "Recovery": "复苏", "recovery": "复苏", "Growth": "增长", "growth": "增长",
    "Economy": "经济", "economic": "经济", "Economic": "经济",
    "Trade": "贸易", "trade": "贸易", "Tariff": "关税", "tariff": "关税",
    "War": "战争", "Crisis": "危机", "crisis": "危机",
    "Demand": "需求", "demand": "需求", "Supply": "供应", "supply": "供应",
    "Stock": "股票", "stocks": "股市", "stock": "股票",
    "Rebound": "反弹", "rebound": "反弹", "Surge": "涨停", "surge": "涨停",
    "Plunge": "斩联", "plunge": "斩联", "Slide": "下滑", "slide": "下滑",
    "Bounce": "反弹", "bounce": "反弹", "Gain": "收涨", "gain": "收涨",
    "Loss": "丏损", "loss": "丏损", "lose": "下跌", "lose": "丏损",
    "Strike": "冲击", "strike": "冲击", "Hit": "触及", "hit": "触及",
    "Year": "年度", "year": "年", "Month": "月度", "month": "月",
    "Week": "周", "week": "周", "Session": "交易日", "session": "交易日",
}

def _rough_translate(text):
    result = text
    for eng, cn in sorted(_trans_dict.items(), key=lambda x: -len(x[0])):
        result = result.replace(eng, cn)
    return result

def fetch_gold_news(max_items=15):
    """获取黄金新闻（带翻译+时间）"""
    import urllib.parse
    all_news, seen = [], set()
    urls = [
        "https://news.google.com/rss/search?q=gold+price+market" + chr(38) + "hl=en-US" + chr(38) + "gl=US" + chr(38) + "ceid=US:en",
        "https://www.bing.com/news/search?q=gold+market+price" + chr(38) + "format=rss",
    ]
    for url in urls:
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
                        # rule-based rough translation
                        trans_title = _rough_translate(title)
                        # extract pubDate time
                        pub_date = item.findtext("pubDate", "")
                        time_str = ""
                        if pub_date:
                            try:
                                dt = datetime.strptime(pub_date.replace("GMT","").replace("UTC","").strip(), "%a, %d %b %Y %H:%M:%S %z")
                                time_str = (dt + timedelta(hours=8)).strftime("%m-%d %H:%M")
                            except:
                                pass
                        all_news.append({"title": title, "title_cn": trans_title, "link": link,
                                        "description": desc, "source": "Google" if "google" in url else "Bing",
                                        "time": time_str})
        except:
            pass
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
