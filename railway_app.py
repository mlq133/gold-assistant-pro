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
        return "发送 行情/分析/决策/新闻/预测/看板 获取实时数据"
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
        if "行情" in cmd or "price" in cmd.lower():
            msg = "实时金价 " + now + nl*2
            msg += "国际金价: $" + str(round(usd,2)) + "/盎司" + nl
            msg += "人民币金价: " + str(cny) + "/克" + nl
            msg += "美元指数: " + str(dxy) + nl*2
            msg += "新闻情绪: " + str(sentiment.get("summary","中性")) + nl*2
            try:
                from ml_predictor import get_ml_report
                ml = get_ml_report()
                msg += "AI预测: " + str(ml.get("rf_direction","震荡")) + " (" + str(ml.get("rf_confidence","0")) + "%)" + nl
                msg += "综合评分: " + str(int(ml.get("ml_score",50))) + "/100"
            except:
                pass
            return msg
        elif "分析" in cmd:
            msg = "AI黄金分析 " + now + nl*2
            msg += "国际金价: $" + str(round(usd,2)) + "/盎司" + nl
            msg += "人民币金价: " + str(cny) + "/克" + nl
            msg += "美元指数: " + str(dxy) + nl*2
            for n in (news or [])[:3]:
                t = n.get("title","?")
                tc = n.get("title_cn","") or n.get("title","?")
                ts = n.get("time","")
                msg += ("[" + ts + "] " if ts else "") + str(tc)[:40] + nl
            msg += nl + "情绪: " + str(sentiment.get("summary","中性"))
            return msg
        elif "决策" in cmd:
            msg = "今日决策 " + now + nl*2
            msg += "国际金价: $" + str(round(usd,2)) + "/盎司" + nl
            msg += "人民币金价: " + str(cny) + "/克" + nl
            msg += "美元指数: " + str(dxy) + nl*2
            try:
                from ml_predictor import get_ml_report
                ml = get_ml_report()
                direction = str(ml.get("rf_direction","震荡"))
                conf = str(ml.get("rf_confidence","0"))
                score = float(ml.get("ml_score",50))
                msg += "AI机器学习分析" + nl
                msg += "趋势: " + direction + " (置信度 " + conf + "%)" + nl
                msg += "综合评分: " + str(int(score)) + "/100" + nl
                if score >= 70: msg += "评级: ★★★★★ 强劲" + nl
                elif score >= 55: msg += "评级: ★★★★ 偏强" + nl
                elif score >= 45: msg += "评级: ★★★ 中性" + nl
                elif score >= 30: msg += "评级: ★★ 偏弱" + nl
                else: msg += "评级: ★ 较弱" + nl
                if score >= 65:
                    msg += "操作: 关注加仓 | 目标: 分批建仓" + nl
                elif score <= 35:
                    msg += "操作: 减仓避险 | 措施: 等待回调" + nl
                else:
                    msg += "操作: 持有观望 | 策略: 保持现有仓位" + nl
            except:
                msg += "建议: 持有观望" + nl
            msg += nl + "新闻情绪: " + str(sentiment.get("summary","中性"))
            return msg
        elif "新闻" in cmd:
            msg = "黄金新闻 " + now + nl*2
            msg += "情绪: " + str(sentiment.get("summary","中性")) + nl*2
            for n in (news or [])[:5]:
                t = n.get("title_cn","") or n.get("title","?")
                ts = n.get("time","")
                msg += ("[" + ts + "] " if ts else "- ") + str(t)[:50] + nl
            return msg
        elif "预测" in cmd:
            try:
                from ml_predictor import get_ml_report
                ml = get_ml_report()
                msg = "AI预测 " + now + nl*2
                msg += "方向: " + str(ml.get("rf_direction","震荡")) + nl
                msg += "置信度: " + str(ml.get("rf_confidence","0")) + "%" + nl
                msg += "ML评分: " + str(ml.get("ml_score","50")) + "/100" + nl*2
                msg += "RF模型: " + str(ml.get("rf_pred","-")) + nl
                msg += "LSTM: " + str(ml.get("lstm_pred","-"))
                return msg
            except Exception as e2:
                return "预测服务暂不可用"
        elif "看板" in cmd:
            msg = "数据看板 " + now
            msg += nl + "https://web-production-305e8.up.railway.app/"
            msg += nl + "请复制到浏览器打开"
            return msg
        return "发送 行情/分析/决策/新闻/预测/看板 获取数据"
    except Exception as e:
        log.error("指令异常: " + str(e))
        return "系统忙，请稍后再试"
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

