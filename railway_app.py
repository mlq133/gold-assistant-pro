# -*- coding: utf-8 -*-
"""
黄金智投助手 - Railway云部署 (Flask版)
"""
import os, sys, json, hashlib, time, threading, logging
from datetime import datetime
from flask import Flask, request, make_response

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("railway")

app = Flask(__name__)
WX_TOKEN = "goldassistant2024"

PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")
if PUSHPLUS_TOKEN:
    try:
        from wechat_pusher import save_config
        save_config(pushplus_token=PUSHPLUS_TOKEN, enabled="pushplus")
        log.info("推送Token已配置")
    except:
        pass


@app.route("/wechat", methods=["GET", "POST"])
def wechat():
    if request.method == "GET":
        signature = request.args.get("signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")
        tmp = "".join(sorted([WX_TOKEN, timestamp, nonce]))
        if hashlib.sha1(tmp.encode()).hexdigest() == signature:
            return echostr
        return "verify failed"
    xml = request.data.decode("utf-8")
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml)
        msg_type = root.findtext("MsgType", "")
        from_user = root.findtext("FromUserName", "")
        to_user = root.findtext("ToUserName", "gh_goldassistant")
        content = root.findtext("Content", "")
        if msg_type == "text":
            reply = _handle_cmd(content.strip())
            return _xml_resp(from_user, reply, to_user)
        elif msg_type == "event":
            event = root.findtext("Event", "")
            event_key = root.findtext("EventKey", "")
            if event == "subscribe":
                reply = "欢迎关注黄金智投助手！\n发送: 行情/分析/决策/新闻 获取实时数据"
            elif event == "CLICK":
                reply = _handle_cmd(event_key)
            else:
                reply = "欢迎使用黄金智投助手"
            return _xml_resp(from_user, reply, to_user)
    except:
        pass
    return "success"


def _handle_cmd(cmd):
    if not cmd:
        return "?? ??/??/??/?? ??????"
    try:
        from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates
        from news_fetcher import fetch_gold_news, analyze_news_sentiment
        usd = get_live_gold_sync()
        cny = fetch_gold_cny()
        dxy = compute_dxy_from_rates()
        news = fetch_gold_news(5)
        sentiment = analyze_news_sentiment(news)
        now = datetime.now().strftime("%m-%d %H:%M")
        nl = chr(10)
        if "??" in cmd:
            msg = f"???? {now}{nl*2}"
            msg += f"????: ${round(usd,2)}/??{nl}"
            msg += f"?????: {cny}/?{nl}"
            msg += f"????: {dxy}{nl*2}"
            msg += f"????: {sentiment.get(chr(115)+chr(117)+chr(109)+chr(109)+chr(97)+chr(114)+chr(121), chr(20013)+chr(24615))}"
            msg += nl*2 + "https://web-production-305e8.up.railway.app"
            return msg
        elif "??" in cmd:
            msg = f"AI???? {now}{nl*2}"
            msg += f"????: ${round(usd,2)}/??{nl}"
            msg += f"?????: {cny}/?{nl}"
            msg += f"????: {dxy}{nl*2}"
            for n in (news or [])[:3]:
                t = n.get(chr(116)+chr(105)+chr(116)+chr(108)+chr(101), "?")
                msg += f"- {t[:40]}{nl}"
            return msg
        elif "??" in cmd:
            msg = f"???? {now}{nl*2}"
            msg += f"??: ${round(usd,2)}/??{nl}"
            msg += f"???: {cny}/?{nl}"
            msg += f"??: {dxy}{nl*2}"
            msg += "??: ????"
            return msg
        elif "??" in cmd:
            msg = f"???? {now}{nl*2}"
            for n in (news or [])[:5]:
                t = n.get(chr(116)+chr(105)+chr(116)+chr(108)+chr(101), "?")
                msg += f"- {t[:50]}{nl}"
            return msg
        return "?? ??/??/??/?? ????"
    except Exception as e:
        log.error(f"????: {e}")
        return "??????????"
def _xml_resp(to_user, content, from_user="gh_goldassistant"):
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


@app.route("/api/data")
def api_data():
    try:
        from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates
        from news_fetcher import fetch_gold_news, analyze_news_sentiment
        usd = get_live_gold_sync()
        cny = fetch_gold_cny()
        dxy = compute_dxy_from_rates()
        news = fetch_gold_news(5)
        sentiment = analyze_news_sentiment(news)
        return {
            "gold_usd": round(usd, 2) if usd else None,
            "gold_cny": cny, "dxy": dxy,
            "news": [{"title": n.get("title",""), "source": n.get("source","")} for n in (news or [])],
            "sentiment": sentiment, "time": time.strftime("%H:%M:%S")
        }
    except Exception as e:
        return {"error": str(e)}


@app.route("/")
def index():
    try:
        with open(os.path.join(PROJECT_DIR, "dashboard.html"), "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>黄金智投助手</h1><p>运行中</p>"


@app.route("/health")
def health():
    return {"status": "ok", "time": time.strftime("%Y-%m-%d %H:%M:%S")}


def scheduler():
    time.sleep(10)
    log.info("定时推送启动")
    last_h = -1
    while True:
        try:
            h = datetime.now().hour
            if h in [9, 15, 21] and h != last_h:
                log.info(f"日报推送 {h}点")
                try:
                    from auto_operate import push_daily_report
                    push_daily_report()
                except: pass
                last_h = h
        except: pass
        time.sleep(300)


threading.Thread(target=scheduler, daemon=True).start()
log.info("黄金智投服务启动完成")

