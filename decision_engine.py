# -*- coding: utf-8 -*-
"""智能交易决策引擎 v2 (融合ML + 多资产 + 深度新闻)"""
import os, json
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
DECISION_LOG = os.path.join(CACHE_DIR, "decision_log.json")


def evaluate_full_signal(rotation, technical, news_sentiment, ml_report, multi_asset):
    """综合5维评分引擎"""
    score = 0
    reasons = []
    details = {}

    # 1. 宏观面 (权重25%)
    macro_score = rotation.get(chr(40644)+chr(37329)+chr(37197)+chr(32622)+chr(20998)+chr(20998), 50)
    macro_w = (macro_score - 50) * 0.25
    score += macro_w
    details["macro"] = round(macro_w, 1)
    if macro_score >= 70: reasons.append("宏观强烈看多(+%.0f)" % macro_w)
    elif macro_score >= 55: reasons.append("宏观偏多(+%.0f)" % macro_w)
    elif macro_score <= 30: reasons.append("宏观看空(%.0f)" % macro_w)
    elif macro_score <= 45: reasons.append("宏观偏空(%.0f)" % macro_w)
    else: reasons.append("宏观中性(+%.0f)" % macro_w)

    # 2. 技术面 (权重25%)
    tr = technical.get(chr(25216)+chr(26415)+chr(38754)+chr(24635)+chr(35780), "中性")
    tech_w = 10 if "偏多" in tr else -10 if "偏空" in tr else 0
    score += tech_w
    details["tech"] = tech_w
    if tech_w > 0: reasons.append("技术偏多(+%d)" % tech_w)
    elif tech_w < 0: reasons.append("技术偏空(%d)" % tech_w)

    # 3. 机器学习 (权重20%)
    ml_score = ml_report.get("ml_score", 50) if ml_report else 50
    ml_w = (ml_score - 50) * 0.2
    score += ml_w
    details["ml"] = round(ml_w, 1)
    if abs(ml_w) > 2: reasons.append("ML预测%s(%.0f)" % ("偏多" if ml_w>0 else "偏空", ml_w))

    # 4. 新闻情绪 (权重15%)
    news_score = news_sentiment.get("score", 0) if news_sentiment else 0
    news_w = max(-15, min(15, news_score)) * 0.15
    score += news_w
    details["news"] = round(news_w, 1)
    if abs(news_w) > 2: reasons.append("新闻%s(%.0f)" % ("利多" if news_w>0 else "利空", news_w))

    # 5. 多资产联动 (权重15%)
    multi_score = 0
    if multi_asset:
        ratios = multi_asset.get("ratios", {})
        for k, v in ratios.items():
            sig = v.get("signal", "")
            if "看多黄金" in sig: multi_score += 3
            elif "看多白银" in sig: multi_score += 2
            elif "衰退" in sig: multi_score += 5
            elif "避险" in sig: multi_score += 3
    score += multi_score
    details["multi_asset"] = multi_score
    if multi_score > 0: reasons.append("多资产联动利多(+%d)" % multi_score)
    elif multi_score < 0: reasons.append("多资产联动利空(%d)" % multi_score)

    # 综合判断
    total_score = round(score, 1)
    details["total"] = total_score

    if total_score >= 15:
        action, confidence = "加仓", "高"
    elif total_score >= 5:
        action, confidence = "加仓", "中"
    elif total_score <= -15:
        action, confidence = "减仓", "高"
    elif total_score <= -5:
        action, confidence = "减仓", "中"
    else:
        action, confidence = "持有", "低"

    return {"action": action, "confidence": confidence, "score": total_score,
            "reasons": reasons, "details": details, "timestamp": datetime.now().isoformat()}


def evaluate_signal(rotation, technical, news_sentiment):
    """旧版接口兼容"""
    return evaluate_full_signal(rotation, technical, news_sentiment, None, None)


def save_decision(decision):
    history = load_decision_history(30)
    history.append(decision)
    with open(DECISION_LOG, "w", encoding="utf-8") as f:
        json.dump(history[-200:], f, ensure_ascii=False, indent=2)


def load_decision_history(days=7):
    if os.path.exists(DECISION_LOG):
        try:
            with open(DECISION_LOG, "r", encoding="utf-8") as f:
                data = json.load(f)
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            return [d for d in data if d.get("timestamp", "") >= cutoff]
        except: pass
    return []


def check_should_push(decision, history, first_run=False):
    if not history or first_run:
        return True
    last = history[-1]
    if last.get("action") != decision["action"]:
        return True
    try:
        last_time = datetime.fromisoformat(last.get("timestamp", "2000-01-01"))
        if (datetime.now() - last_time).total_seconds() > 14400:
            return True
    except: pass
    return False
