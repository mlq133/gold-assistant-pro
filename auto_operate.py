# -*- coding: utf-8 -*-
"""
黄金智投 - 公众号自动运营服务
定时推送金价分析 + AI生成运营内容
"""
import os, sys, time, threading, logging
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
CACHE_DIR = os.path.join(PROJECT_DIR, ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(os.path.join(CACHE_DIR, "auto_operate.log"), encoding="utf-8"), logging.StreamHandler()]
)
log = logging.getLogger("auto_operate")


def generate_daily_report():
    from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates
    from news_fetcher import fetch_gold_news, analyze_news_sentiment
    from ml_predictor import get_ml_report

    gold_usd = get_live_gold_sync()
    gold_cny = fetch_gold_cny()
    dxy = compute_dxy_from_rates()
    news = fetch_gold_news(10)
    sentiment = analyze_news_sentiment(news)
    ml = get_ml_report()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    action = ml.get("rf_direction", "震荡")
    conf = ml.get("rf_confidence", 0)
    score = ml.get("ml_score", 50)
    news_summary = sentiment.get("summary", "中性")

    if score >= 65: advice = "关注加仓机会"
    elif score <= 35: advice = "减仓避险"
    else: advice = "持有观望"

    nl = chr(10)
    news_items = []
    for n in news[:5]:
        title = n.get("title", "")[:50]
        if title: news_items.append("- " + title)
    news_text = nl.join(news_items) if news_items else "暂无最新新闻"

    msg = "黄金日报 " + now + nl*2
    msg += "实时金价" + nl
    msg += "国际金价: " + f"{gold_usd:.2f}" + "/盎司" + nl
    msg += "人民币金价: " + str(gold_cny) + " 元/克" + nl
    msg += "美元指数: " + f"{dxy:.2f}" + nl*2
    msg += "AI预测分析" + nl
    msg += "方向: " + action + " (置信度 " + str(conf) + "%)" + nl
    msg += "ML评分: " + str(score) + "/100" + nl
    msg += "建议: " + advice + nl*2
    msg += "新闻情绪" + nl + news_summary + nl*2
    msg += "今日要闻" + nl + news_text + nl*2
    msg += "-- 黄金智投助手 自动生成"
    return msg


def push_daily_report():
    from wechat_pusher import send_push
    report = generate_daily_report()
    if not report: return False
    ok = send_push("黄金日报 " + datetime.now().strftime("%m-%d"), report)
    if ok: log.info("日报推送成功")
    return ok


def push_price_alert():
    from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates
    from wechat_pusher import send_push
    gold_usd = get_live_gold_sync()
    gold_cny = fetch_gold_cny()
    dxy = compute_dxy_from_rates()
    now = datetime.now().strftime("%H:%M")
    nl = chr(10)
    msg = "实时金价提醒 " + now + nl*2
    msg += "国际金价: " + f"{gold_usd:.2f}" + "/盎司" + nl
    msg += "人民币金价: " + str(gold_cny) + " 元/克" + nl
    msg += "美元指数: " + f"{dxy:.2f}" + nl*2
    msg += "持续监控中，异动自动推送"
    return send_push("金价提醒 " + now, msg)


def push_news_analysis():
    from news_fetcher import fetch_gold_news, analyze_news_sentiment
    from wechat_pusher import send_push
    news = fetch_gold_news(10)
    sentiment = analyze_news_sentiment(news)
    nl = chr(10)
    news_items = []
    for n in news[:5]:
        title = n.get("title", "")[:60]
        if title: news_items.append("- " + title)
    news_text = nl.join(news_items) if news_items else "暂无最新新闻"
    s = sentiment.get("summary", "中性")
    score = sentiment.get("score", 0)
    msg = "黄金新闻分析" + nl*2
    msg += "市场情绪: " + s + nl
    msg += "情绪评分: " + f"{score:+d}" + nl*2
    msg += "最新要闻" + nl + news_text + nl*2
    msg += "-- 黄金智投 实时监控"
    return send_push("黄金新闻分析", msg)


def scheduler():
    last_daily = -1; last_price_min = -1; last_news = -1; last_update_kw = -1
    while True:
        try:
            now = datetime.now(); h, m = now.hour, now.minute
            if m < 2 and h in [9,15,21] and h != last_daily:
                log.info(">>> 推送日报"); push_daily_report(); last_daily = h
            cur = h*60+m
            if (m==0 or m==30) and 8<=h<=23 and cur != last_price_min:
                log.info(">>> 推送金价"); push_price_alert(); last_price_min = cur
            if m<2 and h%2==0 and 8<=h<=22 and h != last_news:
                log.info(">>> 推送新闻"); push_news_analysis(); last_news = h
            if m % 30 == 0 and 8 <= h <= 22 and cur != last_update_kw:
                log.info(">>> 更新关键词回复")
                try:
                    from update_reply import update_all
                    r = update_all()
                    log.info(f"关键词已更新: {len(r)}条")
                except Exception as e:
                    log.error("更新关键词失败: " + str(e))
                last_update_kw = cur
        except Exception as e:
            log.error("调度异常: " + str(e))
        time.sleep(60)


def run_auto_operate():
    log.info("="*50)
    log.info("黄金智投 - 公众号自动运营服务启动")
    log.info("定时: 日报(9/15/21点) | 金价(每30分) | 新闻(每2小时)")
    log.info("="*50)
    t = threading.Thread(target=scheduler, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    run_auto_operate()
    try:
        while True: time.sleep(60)
    except KeyboardInterrupt:
        log.info("服务停止")
