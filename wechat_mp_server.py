# -*- coding: utf-8 -*-
"""
微信公众号服务 - 黄金智投助手
提供菜单交互：行情、分析、新闻、决策
"""
import os, sys, json, hashlib, time, threading
from datetime import datetime
import requests

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from flask import Flask, request, make_response

app = Flask(__name__)

# ========== 微信配置（注册后填写） ==========
WECHAT_CONFIG = os.path.join(PROJECT_DIR, "wechat_mp_config.json")

def load_mp_config():
    default = {
        "appid": "",
        "appsecret": "",
        "token": "goldassistant2024",
        "encoding_aes_key": "",
        "server_url": ""
    }
    if os.path.exists(WECHAT_CONFIG):
        try:
            with open(WECHAT_CONFIG, "r", encoding="utf-8") as f:
                return {**default, **json.load(f)}
        except:
            pass
    return default

def save_mp_config(**kwargs):
    cfg = load_mp_config()
    cfg.update(kwargs)
    with open(WECHAT_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg

# ========== 消息处理 ==========

def handle_message(content):
    """处理用户消息并返回回复"""
    from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates
    from news_fetcher import fetch_gold_news, analyze_news_sentiment
    from ml_predictor import get_ml_report
    cmd = content.strip() if content else ""

    if not cmd or "帮助" in cmd or "help" in cmd or "菜单" in cmd:
        return (
            "🤖 黄金智投助手\n\n"
            "发送以下指令：\n"
            "📊 行情 - 实时金价\n"
            "📈 分析 - AI预测\n"
            "📰 新闻 - 事件分析\n"
            "🎯 决策 - 今日建议\n"
            "📋 日报 - 完整报告"
        )

    if "行情" in cmd or "price" in cmd:
        usd = get_live_gold_sync()
        cny = fetch_gold_cny()
        dxy = compute_dxy_from_rates()
        now = datetime.now().strftime("%m-%d %H:%M")
        return f"📊 黄金行情 {now}\n\n国际金价: \n人民币金价: {cny} 元/克\n美元指数: {dxy:.2f}"

    if "分析" in cmd or "ml" in cmd:
        ml = get_ml_report()
        d = ml.get("rf_direction", "震荡")
        conf = ml.get("rf_confidence", 0)
        score = ml.get("ml_score", 50)
        trend = ml.get("trend_7d", "unknown")
        return f"📈 AI预测分析\n\n方向: {d}\n置信度: {conf}%\nML评分: {score}/100\n7日趋势: {trend}"

    if "新闻" in cmd or "news" in cmd:
        news = fetch_gold_news(5)
        s = analyze_news_sentiment(news)
        lines = [f"📰 黄金新闻分析\n\n情绪: {s.get('summary','中性')}\n"]
        for n in news[:3]:
            lines.append(f"- {n.get('title','')[:60]}")
        return "\n".join(lines)

    if "决策" in cmd or "建议" in cmd:
        usd = get_live_gold_sync()
        cny = fetch_gold_cny()
        dxy = compute_dxy_from_rates()
        news = fetch_gold_news(5)
        s = analyze_news_sentiment(news)
        ml = get_ml_report()
        score = ml.get("ml_score", 50)
        news_score = s.get("score", 0)
        total = score + news_score

        if total >= 120:
            action, reason = "🔴 建议加仓", "ML偏多 + 新闻利好"
        elif total >= 80:
            action, reason = "🟡 关注加仓机会", "信号偏多"
        elif total <= 30:
            action, reason = "🔴 建议减仓", "ML偏空 + 新闻利空"
        elif total <= 50:
            action, reason = "🟡 注意风险", "信号偏空"
        else:
            action, reason = "🟢 建议持有观望", "信号中性"

        return (
            f"🎯 今日决策\n\n"
            f"{action}\n"
            f"综合评分: {total}/200\n"
            f"理由: {reason}\n\n"
            f"国际金价: \n"
            f"人民币: {cny} 元/克\n"
            f"美元指数: {dxy:.2f}"
        )

    if "日报" in cmd or "daily" in cmd:
        usd = get_live_gold_sync()
        cny = fetch_gold_cny()
        dxy = compute_dxy_from_rates()
        news = fetch_gold_news(5)
        s = analyze_news_sentiment(news)
        ml = get_ml_report()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        return (
            f"📋 黄金日报 {now}\n\n"
            f"国际金价: \n"
            f"人民币: {cny} 元/克\n"
            f"美元指数: {dxy:.2f}\n\n"
            f"AI方向: {ml.get('rf_direction','震荡')}\n"
            f"ML评分: {ml.get('ml_score',50)}/100\n"
            f"新闻情绪: {s.get('summary','中性')}\n\n"
            f"发送「决策」获取操作建议"
        )

    return f"未知指令，发送「帮助」查看菜单"

# ========== 微信服务器验证 & 消息路由 ==========

@app.route("/wechat", methods=["GET", "POST"])
def wechat():
    cfg = load_mp_config()
    token = cfg.get("token", "goldassistant2024")

    if request.method == "GET":
        # 服务器验证
        signature = request.args.get("signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")
        tmp = "".join(sorted([token, timestamp, nonce]))
        if hashlib.sha1(tmp.encode()).hexdigest() == signature:
            return echostr
        return "verify failed"

    # POST - 接收消息
    xml = request.data.decode("utf-8")
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml)
        msg_type = root.findtext("MsgType", "")
        from_user = root.findtext("FromUserName", "")
        content = root.findtext("Content", "")

        if msg_type == "text":
            reply = handle_message(content)
            return build_xml(from_user, reply)
        elif msg_type == "event":
            event = root.findtext("Event", "")
            event_key = root.findtext("EventKey", "")
            if event == "subscribe":
                reply = "欢迎关注黄金智投助手！\n发送「帮助」查看菜单"
            elif event == "CLICK":
                reply = handle_message(event_key)
            else:
                reply = "欢迎使用黄金智投助手"
            return build_xml(from_user, reply)
    except Exception as e:
        return "success"

    return "success"

def build_xml(to_user, content):
    from_user = "gh_goldassistant"
    now = str(int(time.time()))
    xml = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{now}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
    resp = make_response(xml)
    resp.content_type = "application/xml"
    return resp

# ========== 菜单配置 ==========

def create_menu():
    """创建微信公众号菜单"""
    cfg = load_mp_config()
    if not cfg.get("appid") or not cfg.get("appsecret"):
        return {"error": "请先配置 appid 和 appsecret"}

    # 获取 access_token
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={cfg['appid']}&secret={cfg['appsecret']}"
    r = requests.get(url, timeout=10)
    token_data = r.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return token_data

    menu = {
        "button": [
            {
                "name": "📊 行情数据",
                "sub_button": [
                    {"type": "click", "name": "实时金价", "key": "行情"},
                    {"type": "click", "name": "AI分析", "key": "分析"},
                    {"type": "click", "name": "美元指数", "key": "行情"}
                ]
            },
            {
                "name": "📰 新闻决策",
                "sub_button": [
                    {"type": "click", "name": "黄金新闻", "key": "新闻"},
                    {"type": "click", "name": "今日决策", "key": "决策"},
                    {"type": "click", "name": "完整日报", "key": "日报"}
                ]
            },
            {
                "name": "⚙️ 更多",
                "sub_button": [
                    {"type": "click", "name": "帮助菜单", "key": "帮助"},
                    {"type": "view", "name": "网页版", "url": cfg.get("server_url", "http://localhost:8500")}
                ]
            }
        ]
    }

    url = f"https://api.weixin.qq.com/cgi-bin/menu/create?access_token={access_token}"
    r = requests.post(url, json=menu, timeout=10)
    return r.json()

# ========== 主动推送（模板消息） ==========

def push_to_fans(title, content):
    """通过微信公众号推送消息给粉丝"""
    cfg = load_mp_config()
    if not cfg.get("appid") or not cfg.get("appsecret"):
        return {"error": "公众号未配置"}

    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={cfg['appid']}&secret={cfg['appsecret']}"
    r = requests.get(url, timeout=10)
    token_data = r.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return token_data

    # 获取粉丝列表
    r2 = requests.get(f"https://api.weixin.qq.com/cgi-bin/user/get?access_token={access_token}", timeout=10)
    fans = r2.json()
    openids = fans.get("data", {}).get("openid", [])

    results = []
    for openid in openids[:5]:  # 测试时只发前5个
        try:
            msg = {
                "touser": openid,
                "msgtype": "text",
                "text": {"content": f"{title}\n\n{content[:600]}"}
            }
            r3 = requests.post(
                f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}",
                json=msg, timeout=10
            )
            results.append(r3.json())
        except Exception as e:
            results.append({"error": str(e)})
    return results

# ========== 主入口 ==========

def run_server(port=5000):
    print(f"✅ 微信公众号服务启动: http://localhost:{port}/wechat")
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    run_server()
