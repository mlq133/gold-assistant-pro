# -*- coding: utf-8 -*-
"""公众号关键词回复自动更新 - 生成实时数据"""
import os, sys, logging
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
log = logging.getLogger("update_kw")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def get_realtime(keyword):
    from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates
    from news_fetcher import fetch_gold_news, analyze_news_sentiment
    from ml_predictor import get_ml_report
    from data_fetcher import fetch_gold_price, fetch_macro_data
    from analyzer import calculate_rotation_signal, calculate_technical_signals
    from decision_engine import evaluate_full_signal

    usd = get_live_gold_sync()
    cny = fetch_gold_cny()
    dxy = compute_dxy_from_rates()
    ml = get_ml_report()
    news = fetch_gold_news(5)
    sentiment = analyze_news_sentiment(news)
    decision = evaluate_full_signal(
        calculate_rotation_signal(fetch_macro_data()),
        calculate_technical_signals(fetch_gold_price()),
        sentiment, ml, None
    )
    now = datetime.now().strftime("%m-%d %H:%M")
    nl = chr(10)

    if keyword == "行情":
        msg = "实时金价 " + now + nl*2
        msg += "国际金价: $" + str(round(usd,2)) + "/盎司" + nl
        msg += "人民币金价: " + str(cny) + "/克" + nl
        msg += "美元指数: " + str(dxy) + nl*2
        msg += "AI预测: " + ml.get("rf_direction","震荡") + " (" + str(ml.get("rf_confidence",0)) + "%)" + nl
        msg += "建议: 持有观望" + nl*2
        msg += "https://gold-assistant.up.railway.app"
        return msg
    elif keyword == "分析":
        msg = "AI黄金分析 " + now + nl*2
        msg += "ML预测: " + ml.get("rf_direction","震荡") + " (" + str(ml.get("rf_confidence",0)) + "%)" + nl
        msg += "综合评分: " + str(ml.get("ml_score",50)) + "/100" + nl*2
        msg += "建议: 持有观望" + nl
        msg += "新闻情绪: " + sentiment.get("summary","中性")
        return msg
    elif keyword == "决策":
        msg = "今日决策 " + now + nl*2
        msg += "操作: " + decision.get("action","?") + nl
        msg += "综合评分: " + str(round(decision.get("score",0),1)) + "/200" + nl*2
        msg += "国际: $" + str(round(usd,2)) + "/盎司" + nl
        msg += "人民币: " + str(cny) + "/克" + nl
        msg += "美指: " + str(dxy)
        return msg
    elif keyword == "新闻":
        msg = "黄金新闻 " + now + nl*2
        msg += "情绪: " + sentiment.get("summary","中性") + nl*2
        for n in news[:5]:
            msg += "- " + n.get("title","")[:50] + nl
        msg += nl + "https://gold-assistant.up.railway.app"
        return msg
    return "发送 行情/分析/决策/新闻 获取数据"


def update_all():
    contents = {}
    for kw in ["行情", "分析", "决策", "新闻"]:
        try:
            contents[kw] = get_realtime(kw)
            log.info("生成 " + kw + " 成功")
        except Exception as e:
            log.error("生成 " + kw + " 失败: " + str(e))
            contents[kw] = None
    try:
        from wechat_pusher import send_push
        send_push("黄金数据已刷新", "数据已准备好")
    except:
        pass
    return contents


if __name__ == "__main__":
    r = update_all()
    for k, v in r.items():
        if v:
            print("=== " + k + " ===")
            print(v[:200])
            print()

