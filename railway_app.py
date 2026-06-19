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
    import base64
    return base64.b64decode("PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9InpoLUNOIj4KPGhlYWQ+PG1ldGEgY2hhcnNldD0iVVRGLTgiPjxtZXRhIG5hbWU9InZpZXdwb3J0IiBjb250ZW50PSJ3aWR0aD1kZXZpY2Utd2lkdGgsaW5pdGlhbC1zY2FsZT0xLjAiPgo8dGl0bGU+6buE6YeR5pm65oqV5Yqp5omLPC90aXRsZT4KPHNjcmlwdCBzcmM9Imh0dHBzOi8vY2RuLmpzZGVsaXZyLm5ldC9ucG0vY2hhcnQuanNANC40LjAvZGlzdC9jaGFydC51bWQubWluLmpzIj48L3NjcmlwdD4KPHN0eWxlPgoqe21hcmdpbjowO3BhZGRpbmc6MDtib3gtc2l6aW5nOmJvcmRlci1ib3g7Zm9udC1mYW1pbHk6LWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1NlZ29lIFVJJyxSb2JvdG8sc2Fucy1zZXJpZn0KYm9keXtiYWNrZ3JvdW5kOiMwYTBlMWE7Y29sb3I6I2UwZTZmMDtwYWRkaW5nOjE2cHh9Ci5jb250YWluZXJ7bWF4LXdpZHRoOjg2MHB4O21hcmdpbjowIGF1dG99Cmgxe2ZvbnQtc2l6ZToyMnB4O21hcmdpbi1ib3R0b206MTZweDtjb2xvcjojZjBiOTBiO2Rpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7Z2FwOjhweH0KLmdyaWR7ZGlzcGxheTpncmlkO2dyaWQtdGVtcGxhdGUtY29sdW1uczoxZnIgMWZyO2dhcDoxMHB4O21hcmdpbi1ib3R0b206MTRweH0KLmNhcmR7YmFja2dyb3VuZDojMTMxYTJlO2JvcmRlci1yYWRpdXM6MTBweDtwYWRkaW5nOjE0cHg7Ym9yZGVyOjFweCBzb2xpZCAjMWUyYTQ1fQouY2FyZCBoM3tmb250LXNpemU6MTFweDtjb2xvcjojODg5MmIwO21hcmdpbi1ib3R0b206NHB4O3RleHQtdHJhbnNmb3JtOnVwcGVyY2FzZTtsZXR0ZXItc3BhY2luZzoxcHh9Ci5jYXJkIC52YWx1ZXtmb250LXNpemU6MjZweDtmb250LXdlaWdodDo3MDA7Y29sb3I6I2ZmZn0KLmNhcmQgLnZhbHVlLmdvbGR7Y29sb3I6I2YwYjkwYn0KLmNhcmQgLmxhYmVse2ZvbnQtc2l6ZToxMnB4O2NvbG9yOiM4ODkyYjA7bWFyZ2luLXRvcDoycHh9Ci5mdWxse2dyaWQtY29sdW1uOjEvLTF9Ci5jaGFydC13cmFwe2JhY2tncm91bmQ6IzBkMTUyNTtib3JkZXItcmFkaXVzOjhweDtwYWRkaW5nOjEycHg7bWFyZ2luLXRvcDo4cHg7aGVpZ2h0OjE4MHB4O3Bvc2l0aW9uOnJlbGF0aXZlfQoubmV3cy1pdGVte3BhZGRpbmc6NnB4IDA7Ym9yZGVyLWJvdHRvbToxcHggc29saWQgIzFlMmE0NTtmb250LXNpemU6MTJweDtsaW5lLWhlaWdodDoxLjR9Ci5uZXdzLWl0ZW06bGFzdC1jaGlsZHtib3JkZXI6bm9uZX0KLmZvb3Rlcnt0ZXh0LWFsaWduOmNlbnRlcjtjb2xvcjojNGE1NTY4O2ZvbnQtc2l6ZToxMXB4O21hcmdpbi10b3A6MTZweDtwYWRkaW5nOjhweH0KPC9zdHlsZT48L2hlYWQ+Cjxib2R5Pgo8ZGl2IGNsYXNzPSJjb250YWluZXIiPgo8aDE+8J+lhyDpu4Tph5HmmbrmipXliqnmiYs8L2gxPgo8ZGl2IGNsYXNzPSJncmlkIj4KPGRpdiBjbGFzcz0iY2FyZCI+PGgzPuWbvemZhemHkeS7tzwvaDM+PGRpdiBjbGFzcz0idmFsdWUgZ29sZCIgaWQ9ImdVc2QiPi0tPC9kaXY+PGRpdiBjbGFzcz0ibGFiZWwiIGlkPSJnVXNkVCI+JC9vejwvZGl2PjwvZGl2Pgo8ZGl2IGNsYXNzPSJjYXJkIj48aDM+5Lq65rCR5biB6YeR5Lu3PC9oMz48ZGl2IGNsYXNzPSJ2YWx1ZSBnb2xkIiBpZD0iZ0NueSI+LS08L2Rpdj48ZGl2IGNsYXNzPSJsYWJlbCI+5YWDL+WFizwvZGl2PjwvZGl2Pgo8ZGl2IGNsYXNzPSJjYXJkIj48aDM+5Lym5pWm6YeRPC9oMz48ZGl2IGNsYXNzPSJ2YWx1ZSIgaWQ9ImdMb24iPi0tPC9kaXY+PGRpdiBjbGFzcz0ibGFiZWwiPlhBVS9HQlA8L2Rpdj48L2Rpdj4KPGRpdiBjbGFzcz0iY2FyZCI+PGgzPue+juWFg+aMh+aVsDwvaDM+PGRpdiBjbGFzcz0idmFsdWUiIGlkPSJnRHh5Ij4tLTwvZGl2PjxkaXYgY2xhc3M9ImxhYmVsIj5EWFk8L2Rpdj48L2Rpdj4KPC9kaXY+CjxkaXYgY2xhc3M9ImNhcmQgZnVsbCI+PGgzPuS8puaVpumHkSBYQVUvR0JQIOi1sOWKvzwvaDM+PGRpdiBjbGFzcz0iY2hhcnQtd3JhcCI+PGNhbnZhcyBpZD0iY2hhcnRMb24iPjwvY2FudmFzPjwvZGl2PjwvZGl2Pgo8ZGl2IGNsYXNzPSJjYXJkIGZ1bGwiIHN0eWxlPSJtYXJnaW4tdG9wOjEwcHgiPjxoMz5BVTk5OTkg5Zu95YaF6YeRIOi1sOWKvzwvaDM+PGRpdiBjbGFzcz0iY2hhcnQtd3JhcCI+PGNhbnZhcyBpZD0iY2hhcnRBdSI+PC9jYW52YXM+PC9kaXY+PC9kaXY+CjxkaXYgY2xhc3M9ImNhcmQgZnVsbCIgc3R5bGU9Im1hcmdpbi10b3A6MTBweCI+PGgzPvCfk7Ag5paw6Ze7PC9oMz48ZGl2IGlkPSJuZXdzU2VjIiBzdHlsZT0ibWFyZ2luLXRvcDo4cHgiPuWKoOi9veS4rS4uLjwvZGl2PjwvZGl2Pgo8ZGl2IGNsYXNzPSJmb290ZXIiPuavjzMw56eS6Ieq5Yqo5Yi35pawPC9kaXY+CjwvZGl2Pgo8c2NyaXB0Pgp2YXIgaExvbj1bXSxoQXU9W10sY0xvbj1udWxsLGNBdT1udWxsOwpmdW5jdGlvbiBta0MoaWQsYyl7dmFyIGN0eD1kb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCkuZ2V0Q29udGV4dCgnMmQnKTtyZXR1cm4gbmV3IENoYXJ0KGN0eCx7dHlwZTonbGluZScsZGF0YTp7bGFiZWxzOltdLGRhdGFzZXRzOlt7ZGF0YTpbXSxib3JkZXJDb2xvcjpjLGJhY2tncm91bmRDb2xvcjpjKycyMCcsYm9yZGVyV2lkdGg6MixmaWxsOnRydWUsdGVuc2lvbjowLjMscG9pbnRSYWRpdXM6MH1dfSxvcHRpb25zOntyZXNwb25zaXZlOnRydWUsbWFpbnRhaW5Bc3BlY3RSYXRpbzpmYWxzZSxwbHVnaW5zOntsZWdlbmQ6e2Rpc3BsYXk6ZmFsc2V9fSxzY2FsZXM6e3g6e2Rpc3BsYXk6ZmFsc2V9LHk6e2dyaWQ6e2NvbG9yOicjMWUyYTQ1J30sdGlja3M6e2NvbG9yOicjODg5MmIwJyxmb250OntzaXplOjEwfX19fX19KX0KZnVuY3Rpb24gdXBDKGNoLHYpe2lmKCFjaHx8dj09bnVsbClyZXR1cm47dmFyIGQ9bmV3IERhdGUoKTtjaC5kYXRhLmxhYmVscy5wdXNoKGQuZ2V0SG91cnMoKSsnOicrU3RyaW5nKGQuZ2V0TWludXRlcygpKS5wYWRTdGFydCgyLCcwJykpO2NoLmRhdGEuZGF0YXNldHNbMF0uZGF0YS5wdXNoKHYpO2lmKGNoLmRhdGEubGFiZWxzLmxlbmd0aD4zMCl7Y2guZGF0YS5sYWJlbHMuc2hpZnQoKTtjaC5kYXRhLmRhdGFzZXRzWzBdLmRhdGEuc2hpZnQoKX1jaC51cGRhdGUoJ25vbmUnKX0KY0xvbj1ta0MoJ2NoYXJ0TG9uJywnI2YwYjkwYicpO2NBdT1ta0MoJ2NoYXJ0QXUnLCcjMDBjODUzJyk7CmFzeW5jIGZ1bmN0aW9uIHJlZigpe3RyeXsKdmFyIHI9YXdhaXQgZmV0Y2goJy9hcGkvZGF0YScpO2lmKCFyLm9rKXJldHVybjt2YXIgZD1hd2FpdCByLmpzb24oKTsKaWYoZC5nb2xkX3VzZCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2dVc2QnKS50ZXh0Q29udGVudD0nJCcrZC5nb2xkX3VzZC50b0ZpeGVkKDIpO2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdnVXNkVCcpLnRleHRDb250ZW50PSckL296ICcrZC50aW1lfQppZihkLmdvbGRfY255KWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdnQ255JykudGV4dENvbnRlbnQ9ZC5nb2xkX2NueTsKaWYoZC5keHkpZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2dEeHknKS50ZXh0Q29udGVudD1kLmR4eS50b0ZpeGVkKDIpOwppZihkLmxvbmRvbl9nb2xkKXtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnZ0xvbicpLnRleHRDb250ZW50PWQubG9uZG9uX2dvbGQ7dXBDKGNMb24scGFyc2VGbG9hdChkLmxvbmRvbl9nb2xkKSl9CmlmKGQuYXU5OTk5KXVwQyhjQXUscGFyc2VGbG9hdChkLmF1OTk5OSkpOwppZihkLm5ld3Mpe3ZhciBoPScnO2QubmV3cy5mb3JFYWNoKGZ1bmN0aW9uKG4pe2grPSc8ZGl2IGNsYXNzPSJuZXdzLWl0ZW0iPicrKChuLnRpbWV8fG4udGltZSk/JzxzcGFuIHN0eWxlPSJjb2xvcjojODg5MmIwO2ZvbnQtc2l6ZToxMHB4Ij4nK24udGltZSsnIDwvc3Bhbj4nOicnKSsobi50aXRsZV9jbnx8bi50aXRsZXx8Jz8nKSsnPC9kaXY+J30pO2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCduZXdzU2VjJykuaW5uZXJIVE1MPWh9Cn1jYXRjaChlKXt9fQpyZWYoKTtzZXRJbnRlcnZhbChyZWYsMzAwMDApOwo8L3NjcmlwdD48L2JvZHk+PC9odG1sPg==").decode()


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

+d.gold_usd.toFixed(2);document.getElementById('gUsdT').textContent='$/oz '+d.time}\nif(d.gold_cny)document.getElementById('gCny').textContent=d.gold_cny;\nif(d.dxy)document.getElementById('gDxy').textContent=d.dxy.toFixed(2);\nif(d.london_gold){document.getElementById('gLon').textContent=d.london_gold;upC(cLon,parseFloat(d.london_gold))}\nif(d.au9999)upC(cAu,parseFloat(d.au9999));\nif(d.news){var h='';d.news.forEach(function(n){h+='<div class=\"news-item\">'+((n.time||n.time)?'<span style=\"color:#8892b0;font-size:10px\">'+n.time+' </span>':'')+(n.title_cn||n.title||'?')+'</div>'});document.getElementById('newsSec').innerHTML=h}\n}catch(e){}}\nref();setInterval(ref,30000);\n</script></body></html>"@app.route("/health")
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

