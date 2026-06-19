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
        return "\u53d1\u9001 \u884c\u60c5/\u5206\u6790/\u51b3\u7b56/\u65b0\u95fb/\u9884\u6d4b/\u770b\u677f \u83b7\u53d6\u5b9e\u65f6\u6570\u636e"
    try:
        from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates
        from news_fetcher import fetch_gold_news, analyze_news_sentiment
        usd = get_live_gold_sync()
        cny = fetch_gold_cny()
        dxy = compute_dxy_from_rates()
        news = fetch_gold_news(5)
        sentiment = analyze_news_sentiment(news)
        now = (datetime.utcnow() + __import__("datetime").timedelta(hours=8)).strftime("%m-%d %H:%M")
        nl = chr(10)
        if "\u884c\u60c5" in cmd or "price" in cmd.lower():
            msg = "\u5b9e\u65f6\u91d1\u4ef7 " + now + nl*2
            msg += "\u56fd\u9645\u91d1\u4ef7: $" + str(round(usd,2)) + "/\u76ce\u53f8" + nl
            msg += "\u4eba\u6c11\u5e01\u91d1\u4ef7: " + str(cny) + "/\u514b" + nl
            msg += "\u7f8e\u5143\u6307\u6570: " + str(dxy) + nl*2
            msg += "\u65b0\u95fb\u60c5\u7eea: " + str(sentiment.get("summary","\u4e2d\u6027")) + nl*2
            msg += "https://web-production-305e8.up.railway.app"
            return msg
        elif "\u5206\u6790" in cmd:
            msg = "AI\u9ec4\u91d1\u5206\u6790 " + now + nl*2
            msg += "\u56fd\u9645\u91d1\u4ef7: $" + str(round(usd,2)) + "/\u76ce\u53f8" + nl
            msg += "\u4eba\u6c11\u5e01\u91d1\u4ef7: " + str(cny) + "/\u514b" + nl
            msg += "\u7f8e\u5143\u6307\u6570: " + str(dxy) + nl*2
            for n in (news or [])[:3]:
                t = n.get("title","?")
                msg += "- " + t[:40] + nl
            msg += nl + "\u60c5\u7eea: " + str(sentiment.get("summary","\u4e2d\u6027"))
            return msg
        elif "\u51b3\u7b56" in cmd:
            msg = "\u4eca\u65e5\u51b3\u7b56 " + now + nl*2
            msg += "\u56fd\u9645: $" + str(round(usd,2)) + "/\u76ce\u53f8" + nl
            msg += "\u4eba\u6c11\u5e01: " + str(cny) + "/\u514b" + nl
            msg += "\u7f8e\u6307: " + str(dxy) + nl*2
            msg += "\u5efa\u8bae: \u6301\u6709\u89c2\u671b"
            return msg
        elif "\u65b0\u95fb" in cmd:
            msg = "\u9ec4\u91d1\u65b0\u95fb " + now + nl*2
            msg += "\u60c5\u7eea: " + str(sentiment.get("summary","\u4e2d\u6027")) + nl*2
            for n in (news or [])[:5]:
                t = n.get("title","?")
                msg += "- " + t[:50] + nl
            return msg
        elif "\u9884\u6d4b" in cmd:
            try:
                from ml_predictor import get_ml_report
                ml = get_ml_report()
                msg = "AI\u9884\u6d4b " + now + nl*2
                msg += "\u65b9\u5411: " + str(ml.get("rf_direction","\u9707\u8361")) + nl
                msg += "\u7f6e\u4fe1\u5ea6: " + str(ml.get("rf_confidence","0")) + "%" + nl
                msg += "ML\u8bc4\u5206: " + str(ml.get("ml_score","50")) + "/100"
                return msg
            except Exception as e2:
                return "\u9884\u6d4b\u670d\u52a1\u6682\u4e0d\u53ef\u7528"
        elif "\u770b\u677f" in cmd:
            msg = "\u6570\u636e\u770b\u677f " + now
            msg += nl + "https://web-production-305e8.up.railway.app/"
            msg += nl + "\u8bf7\u590d\u5236\u5230\u6d4f\u89c8\u5668\u6253\u5f00"
            return msg
        return "\u53d1\u9001 \u884c\u60c5/\u5206\u6790/\u51b3\u7b56/\u65b0\u95fb/\u9884\u6d4b/\u770b\u677f \u83b7\u53d6\u6570\u636e"
    except Exception as e:
        log.error("\u6307\u4ee4\u5f02\u5e38: " + str(e))
        return "\u7cfb\u7edf\u5fd9\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5"
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
        from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates, fetch_london_gold, fetch_au9999
        from news_fetcher import fetch_gold_news, analyze_news_sentiment
        usd = get_live_gold_sync()
        cny = fetch_gold_cny()
        dxy = compute_dxy_from_rates()
        london = fetch_london_gold()
        au = fetch_au9999()
        news = fetch_gold_news(10)
        sentiment = analyze_news_sentiment(news)
        return {
            "gold_usd": round(usd, 2) if usd else None,
            "gold_cny": cny, "dxy": dxy,
            "london_gold": london, "au9999": au,
            "news": [{"title": n.get("title",""), "title_cn": n.get("title_cn",""), "source": n.get("source",""), "time": n.get("time","")} for n in (news or [])],
            "sentiment": sentiment, "time": time.strftime("%H:%M:%S")
        }
    except Exception as e:
        return {"error": str(e)}@app.route("/")
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

