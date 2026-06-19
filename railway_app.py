# -*- coding: utf-8 -*-
"""黄金智投助手 Railway v3.3 - 内联仪表盘+翻译增强"""
import os, sys, json, hashlib, time, threading, logging, re, base64
from datetime import datetime
from flask import Flask, request, make_response

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("railway")
app = Flask(__name__)
WX_TOKEN = "goldassistant2024"

DASHBOARD_HTML = base64.b64decode("PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9InpoLUNOIj4KPGhlYWQ+PG1ldGEgY2hhcnNldD0iVVRGLTgiPjxtZXRhIG5hbWU9InZpZXdwb3J0IiBjb250ZW50PSJ3aWR0aD1kZXZpY2Utd2lkdGgsaW5pdGlhbC1zY2FsZT0xLjAiPgo8dGl0bGU+6buE6YeR5pm65oqV5Yqp5omLPC90aXRsZT4KPHNjcmlwdCBzcmM9Imh0dHBzOi8vY2RuLmpzZGVsaXZyLm5ldC9ucG0vY2hhcnQuanNANC40LjAvZGlzdC9jaGFydC51bWQubWluLmpzIj48L3NjcmlwdD4KPHN0eWxlPgoqe21hcmdpbjowO3BhZGRpbmc6MDtib3gtc2l6aW5nOmJvcmRlci1ib3g7Zm9udC1mYW1pbHk6LWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1NlZ29lIFVJJyxSb2JvdG8sc2Fucy1zZXJpZn0KYm9keXtiYWNrZ3JvdW5kOiMwYTBlMWE7Y29sb3I6I2UwZTZmMDtwYWRkaW5nOjE2cHh9Ci5jb250YWluZXJ7bWF4LXdpZHRoOjg2MHB4O21hcmdpbjowIGF1dG99Cmgxe2ZvbnQtc2l6ZToyMnB4O21hcmdpbi1ib3R0b206MTZweDtjb2xvcjojZjBiOTBiO2Rpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7Z2FwOjhweH0KLmdyaWR7ZGlzcGxheTpncmlkO2dyaWQtdGVtcGxhdGUtY29sdW1uczoxZnIgMWZyO2dhcDoxMHB4O21hcmdpbi1ib3R0b206MTRweH0KLmNhcmR7YmFja2dyb3VuZDojMTMxYTJlO2JvcmRlci1yYWRpdXM6MTBweDtwYWRkaW5nOjE0cHg7Ym9yZGVyOjFweCBzb2xpZCAjMWUyYTQ1fQouY2FyZCBoM3tmb250LXNpemU6MTFweDtjb2xvcjojODg5MmIwO21hcmdpbi1ib3R0b206NHB4O3RleHQtdHJhbnNmb3JtOnVwcGVyY2FzZTtsZXR0ZXItc3BhY2luZzoxcHh9Ci5jYXJkIC52YWx1ZXtmb250LXNpemU6MjZweDtmb250LXdlaWdodDo3MDA7Y29sb3I6I2ZmZn0KLmNhcmQgLnZhbHVlLmdvbGR7Y29sb3I6I2YwYjkwYn0KLmNhcmQgLmxhYmVse2ZvbnQtc2l6ZToxMnB4O2NvbG9yOiM4ODkyYjA7bWFyZ2luLXRvcDoycHh9Ci5mdWxse2dyaWQtY29sdW1uOjEvLTF9Ci5jaGFydC13cmFwe2JhY2tncm91bmQ6IzBkMTUyNTtib3JkZXItcmFkaXVzOjhweDtwYWRkaW5nOjEycHg7bWFyZ2luLXRvcDo4cHg7aGVpZ2h0OjE4MHB4O3Bvc2l0aW9uOnJlbGF0aXZlfQoubmV3cy1pdGVte3BhZGRpbmc6NnB4IDA7Ym9yZGVyLWJvdHRvbToxcHggc29saWQgIzFlMmE0NTtmb250LXNpemU6MTJweDtsaW5lLWhlaWdodDoxLjR9Ci5uZXdzLWl0ZW06bGFzdC1jaGlsZHtib3JkZXI6bm9uZX0KLmZvb3Rlcnt0ZXh0LWFsaWduOmNlbnRlcjtjb2xvcjojNGE1NTY4O2ZvbnQtc2l6ZToxMXB4O21hcmdpbi10b3A6MTZweDtwYWRkaW5nOjhweH0KPC9zdHlsZT48L2hlYWQ+Cjxib2R5Pgo8ZGl2IGNsYXNzPSJjb250YWluZXIiPgo8aDE+8J+lhyDpu4Tph5HmmbrmipXliqnmiYs8L2gxPgo8ZGl2IGNsYXNzPSJncmlkIj4KPGRpdiBjbGFzcz0iY2FyZCI+PGgzPuWbvemZhemHkeS7tzwvaDM+PGRpdiBjbGFzcz0idmFsdWUgZ29sZCIgaWQ9ImdVc2QiPi0tPC9kaXY+PGRpdiBjbGFzcz0ibGFiZWwiIGlkPSJnVXNkVCI+JC9vejwvZGl2PjwvZGl2Pgo8ZGl2IGNsYXNzPSJjYXJkIj48aDM+5Lq65rCR5biB6YeR5Lu3PC9oMz48ZGl2IGNsYXNzPSJ2YWx1ZSBnb2xkIiBpZD0iZ0NueSI+LS08L2Rpdj48ZGl2IGNsYXNzPSJsYWJlbCI+5YWDL+WFizwvZGl2PjwvZGl2Pgo8ZGl2IGNsYXNzPSJjYXJkIj48aDM+5Lym5pWm6YeRPC9oMz48ZGl2IGNsYXNzPSJ2YWx1ZSIgaWQ9ImdMb24iPi0tPC9kaXY+PGRpdiBjbGFzcz0ibGFiZWwiPlhBVS9HQlA8L2Rpdj48L2Rpdj4KPGRpdiBjbGFzcz0iY2FyZCI+PGgzPue+juWFg+aMh+aVsDwvaDM+PGRpdiBjbGFzcz0idmFsdWUiIGlkPSJnRHh5Ij4tLTwvZGl2PjxkaXYgY2xhc3M9ImxhYmVsIj5EWFk8L2Rpdj48L2Rpdj4KPC9kaXY+CjxkaXYgY2xhc3M9ImNhcmQgZnVsbCI+PGgzPuS8puaVpumHkSBYQVUvR0JQIOi1sOWKvzwvaDM+PGRpdiBjbGFzcz0iY2hhcnQtd3JhcCI+PGNhbnZhcyBpZD0iY2hhcnRMb24iPjwvY2FudmFzPjwvZGl2PjwvZGl2Pgo8ZGl2IGNsYXNzPSJjYXJkIGZ1bGwiIHN0eWxlPSJtYXJnaW4tdG9wOjEwcHgiPjxoMz5BVTk5OTkg5Zu95YaF6YeRIOi1sOWKvzwvaDM+PGRpdiBjbGFzcz0iY2hhcnQtd3JhcCI+PGNhbnZhcyBpZD0iY2hhcnRBdSI+PC9jYW52YXM+PC9kaXY+PC9kaXY+CjxkaXYgY2xhc3M9ImNhcmQgZnVsbCIgc3R5bGU9Im1hcmdpbi10b3A6MTBweCI+PGgzPvCfk7Ag5paw6Ze7PC9oMz48ZGl2IGlkPSJuZXdzU2VjIiBzdHlsZT0ibWFyZ2luLXRvcDo4cHgiPuWKoOi9veS4rS4uLjwvZGl2PjwvZGl2Pgo8ZGl2IGNsYXNzPSJmb290ZXIiPuavjzMw56eS6Ieq5Yqo5Yi35pawPC9kaXY+CjwvZGl2Pgo8c2NyaXB0Pgp2YXIgaExvbj1bXSxoQXU9W10sY0xvbj1udWxsLGNBdT1udWxsOwpmdW5jdGlvbiBta0MoaWQsYyl7dmFyIGN0eD1kb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCkuZ2V0Q29udGV4dCgnMmQnKTtyZXR1cm4gbmV3IENoYXJ0KGN0eCx7dHlwZTonbGluZScsZGF0YTp7bGFiZWxzOltdLGRhdGFzZXRzOlt7ZGF0YTpbXSxib3JkZXJDb2xvcjpjLGJhY2tncm91bmRDb2xvcjpjKycyMCcsYm9yZGVyV2lkdGg6MixmaWxsOnRydWUsdGVuc2lvbjowLjMscG9pbnRSYWRpdXM6MH1dfSxvcHRpb25zOntyZXNwb25zaXZlOnRydWUsbWFpbnRhaW5Bc3BlY3RSYXRpbzpmYWxzZSxwbHVnaW5zOntsZWdlbmQ6e2Rpc3BsYXk6ZmFsc2V9fSxzY2FsZXM6e3g6e2Rpc3BsYXk6ZmFsc2V9LHk6e2dyaWQ6e2NvbG9yOicjMWUyYTQ1J30sdGlja3M6e2NvbG9yOicjODg5MmIwJyxmb250OntzaXplOjEwfX19fX19KX0KZnVuY3Rpb24gdXBDKGNoLHYpe2lmKCFjaHx8dj09bnVsbClyZXR1cm47dmFyIGQ9bmV3IERhdGUoKTtjaC5kYXRhLmxhYmVscy5wdXNoKGQuZ2V0SG91cnMoKSsnOicrU3RyaW5nKGQuZ2V0TWludXRlcygpKS5wYWRTdGFydCgyLCcwJykpO2NoLmRhdGEuZGF0YXNldHNbMF0uZGF0YS5wdXNoKHYpO2lmKGNoLmRhdGEubGFiZWxzLmxlbmd0aD4zMCl7Y2guZGF0YS5sYWJlbHMuc2hpZnQoKTtjaC5kYXRhLmRhdGFzZXRzWzBdLmRhdGEuc2hpZnQoKX1jaC51cGRhdGUoJ25vbmUnKX0KY0xvbj1ta0MoJ2NoYXJ0TG9uJywnI2YwYjkwYicpO2NBdT1ta0MoJ2NoYXJ0QXUnLCcjMDBjODUzJyk7CmFzeW5jIGZ1bmN0aW9uIHJlZigpe3RyeXsKdmFyIHI9YXdhaXQgZmV0Y2goJy9hcGkvZGF0YScpO2lmKCFyLm9rKXJldHVybjt2YXIgZD1hd2FpdCByLmpzb24oKTsKaWYoZC5nb2xkX3VzZCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2dVc2QnKS50ZXh0Q29udGVudD0nJCcrZC5nb2xkX3VzZC50b0ZpeGVkKDIpO2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdnVXNkVCcpLnRleHRDb250ZW50PSckL296ICcrZC50aW1lfQppZihkLmdvbGRfY255KWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdnQ255JykudGV4dENvbnRlbnQ9ZC5nb2xkX2NueTsKaWYoZC5keHkpZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2dEeHknKS50ZXh0Q29udGVudD1kLmR4eS50b0ZpeGVkKDIpOwppZihkLmxvbmRvbl9nb2xkKXtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnZ0xvbicpLnRleHRDb250ZW50PWQubG9uZG9uX2dvbGQ7dXBDKGNMb24scGFyc2VGbG9hdChkLmxvbmRvbl9nb2xkKSl9CmlmKGQuYXU5OTk5KXVwQyhjQXUscGFyc2VGbG9hdChkLmF1OTk5OSkpOwppZihkLm5ld3Mpe3ZhciBoPScnO2QubmV3cy5mb3JFYWNoKGZ1bmN0aW9uKG4pe2grPSc8ZGl2IGNsYXNzPSJuZXdzLWl0ZW0iPicrKChuLnRpbWV8fG4udGltZSk/JzxzcGFuIHN0eWxlPSJjb2xvcjojODg5MmIwO2ZvbnQtc2l6ZToxMHB4Ij4nK24udGltZSsnIDwvc3Bhbj4nOicnKSsobi50aXRsZV9jbnx8bi50aXRsZXx8Jz8nKSsnPC9kaXY+J30pO2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCduZXdzU2VjJykuaW5uZXJIVE1MPWh9Cn1jYXRjaChlKXt9fQpyZWYoKTtzZXRJbnRlcnZhbChyZWYsMzAwMDApOwo8L3NjcmlwdD48L2JvZHk+PC9odG1sPg==").decode("utf-8")

# ========== 智能翻译引擎 ==========
_CN_TRANSLATE = {
    "Gold Price Analysis": "金价分析",
    "Federal Reserve": "美联储",
    "Market Strength": "市场强势",
    "Seeking Alpha": "Seeking Alpha",
    "Yahoo Finance": "雅虎财经",
    "Central Bank": "央行",
    "central bank": "央行",
    "Geopolitical": "地缘政治",
    "geopolitical": "地缘政治",
    "Hawkish Fed": "鹰派美联储",
    "Record High": "历史新高",
    "Uncertainty": "不确定性",
    "uncertainty": "不确定性",
    "Weekly Loss": "周线下跌",
    "Gold Market": "黄金市场",
    "Gold Prices": "金价",
    "Dovish Fed": "鸽派美联储",
    "Resistance": "阻力",
    "Safe Haven": "避险资产",
    "SD Bullion": "SD Bullion",
    "Gold Price": "金价",
    "Spot Price": "现货价格",
    "Inflation": "通胀",
    "inflation": "通胀",
    "Technical": "技术",
    "Commodity": "商品",
    "USA Today": "今日美国",
    "Resources": "资源",
    "Positions": "布局",
    "Analysis": "分析",
    "analysis": "分析",
    "Forecast": "预测",
    "Investor": "投资者",
    "Recovery": "复苏",
    "economic": "经济",
    "Tumbling": "暴跌",
    "tumbling": "暴跌",
    "FXEmpire": "FXEmpire",
    "Position": "布局",
    "Straight": "连续",
    "Hawkish": "鹰派",
    "Outlook": "展望",
    "Reserve": "储备",
    "reserve": "储备",
    "Support": "支撑",
    "Trading": "交易",
    "Economy": "经济",
    "Rebound": "反弹",
    "rebound": "反弹",
    "Selloff": "抛售",
    "selloff": "抛售",
    "Holiday": "假日",
    "Session": "交易日",
    "Reuters": "路透",
    "Fortune": "财富杂志",
    "Royalty": "特许权",
    "Current": "当前",
    "Signals": "信号",
    "Dovish": "鸽派",
    "prices": "价格",
    "Market": "市场",
    "market": "市场",
    "Dollar": "美元",
    "dollar": "美元",
    "Weekly": "周度",
    "Global": "全球",
    "Signal": "信号",
    "Update": "更新",
    "Report": "报告",
    "Strong": "强劲",
    "Growth": "增长",
    "growth": "增长",
    "Tariff": "关税",
    "tariff": "关税",
    "Crisis": "危机",
    "crisis": "危机",
    "Demand": "需求",
    "demand": "需求",
    "Supply": "供应",
    "supply": "供应",
    "stocks": "股市",
    "Plunge": "暴跌",
    "plunge": "暴跌",
    "Bounce": "反弹",
    "bounce": "反弹",
    "Losses": "下跌",
    "Tumble": "暴跌",
    "Target": "目标",
    "Price": "价格",
    "price": "价格",
    "Today": "今日",
    "rates": "利率",
    "Daily": "日度",
    "China": "中国",
    "India": "印度",
    "World": "世界",
    "Falls": "下跌",
    "Trade": "贸易",
    "trade": "贸易",
    "Stock": "股票",
    "stock": "股票",
    "Surge": "飙升",
    "surge": "飙升",
    "Slide": "下滑",
    "slide": "下滑",
    "Rally": "上涨",
    "rally": "上涨",
    "Ounce": "盎司",
    "KITCO": "KITCO",
    "Faces": "面临",
    "Mixed": "多空交织",
    "Views": "观点",
    "Cools": "降温",
    "Gold": "黄金",
    "gold": "黄金",
    "Rate": "利率",
    "Hike": "加息",
    "hike": "加息",
    "Down": "下跌",
    "Jump": "飙升",
    "Drop": "下跌",
    "Fall": "下跌",
    "Rise": "上涨",
    "News": "新闻",
    "Weak": "疲软",
    "Gain": "收涨",
    "gain": "收涨",
    "Loss": "亏损",
    "loss": "亏损",
    "Amid": "背景下",
    "Send": "推动",
    "Cool": "降温",
    "Fed": "美联储",
    "Cut": "降息",
    "cut": "降息",
    "ETF": "ETF",
    "War": "战争",
    "Up": "上涨",
}

def smart_translate(text):
    result = text
    for eng, cn in sorted(_CN_TRANSLATE.items(), key=lambda x: -len(x[0])):
        result = re.sub(r"\b" + re.escape(eng) + r"\b", cn, result)
    result = re.sub(r"\s+", " ", result).strip()
    return result

@app.route("/")
def index():
    return DASHBOARD_HTML

@app.route("/health")
def health():
    return {"status": "ok", "time": time.strftime("%Y-%m-%d %H:%M:%S")}

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
            "gold_cny": cny,
            "dxy": dxy,
            "london_gold": london,
            "au9999": au,
            "news": [{
                "title": n.get("title",""),
                "title_cn": smart_translate(n.get("title","")),
                "source": n.get("source",""),
                "time": n.get("time","")
            } for n in (news or [])],
            "sentiment": sentiment,
            "time": time.strftime("%H:%M:%S")
        }
    except Exception as e:
        log.error("API异常: " + str(e))
        return {"error": str(e)}

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
        to_user = root.findtext("ToUserName", "")
        from_user = root.findtext("FromUserName", "")
        msg_type = root.findtext("MsgType", "")
        event = root.findtext("Event", "")
        if msg_type == "event" and event == "subscribe":
            log.info("新用户关注")
            return xml_resp(from_user, "🤖 欢迎关注黄金智投助手！\n---\n发送关键词:\n📊 行情 - 实时金价\n📈 分析 - 走势分析\n🎯 决策 - 投资建议\n📰 新闻 - 黄金新闻\n---\n例如: 行情 查金价", to_user)
        content = root.findtext("Content", "").strip()
        log.info(f"微信消息: {content}")
        reply = handle_msg(content)
        return xml_resp(from_user, reply, to_user)
    except Exception as e:
        log.error("微信异常: " + str(e))
        return xml_resp("user", "系统繁忙请稍后再试", "gh_goldassistant")

def handle_msg(cmd):
    nl = "\n"
    now = datetime.now().strftime("%m-%d %H:%M")
    cmd = cmd.strip()
    try:
        from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates, fetch_london_gold, fetch_au9999
        usd = get_live_gold_sync()
        cny = fetch_gold_cny()
        dxy = compute_dxy_from_rates()
        london = fetch_london_gold()
        au = fetch_au9999()
    except:
        usd = cny = dxy = london = au = None

    if cmd in ["行情", "国际金价", "实时行情"]:
        msg = f"📊 实时行情 {now}" + nl
        if usd: msg += f"国际金价: ${usd:.2f}/盎司" + nl
        if cny: msg += f"人民币金价: {cny}/克" + nl
        if london: msg += f"伦敦金: {london}" + nl
        if au: msg += f"AU9999: {au}/克" + nl
        if dxy: msg += f"美元指数: {dxy}" + nl
        return msg

    elif cmd in ["分析", "黄金分析"]:
        msg = f"📈 黄金分析 {now}" + nl
        if usd: msg += f"国际金价: ${usd:.2f}/盎司" + nl
        if dxy: msg += f"美元指数: {dxy}" + nl
        if usd and dxy:
            msg += "---" + nl
            if dxy > 105: msg += "⚠️ 美元强势压制金价，短期注意回调风险" + nl
            elif dxy < 98: msg += "✅ 美元走弱利好黄金，可考虑逢低布局" + nl
            else: msg += "➡️ 美元指数中性，关注后续经济数据" + nl
            if usd > 4100: msg += "🔥 金价历史高位，注意控制仓位" + nl
            elif usd < 3900: msg += "💡 金价相对低位，可分批建仓" + nl
            else: msg += "➡️ 金价区间震荡，建议观望为主" + nl
        return msg

    elif cmd in ["决策", "今日决策"]:
        msg = f"🎯 今日决策 {now}" + nl
        try:
            from news_fetcher import fetch_gold_news, analyze_news_sentiment
            news = fetch_gold_news(15)
            sentiment = analyze_news_sentiment(news)
            avg = sentiment.get("avg_score", 0)
            msg += f"市场情绪: {sentiment.get('summary', '中性')}" + nl
            msg += f"情绪得分: {avg}" + nl + "---" + nl
            if avg >= 1.5:
                dirr, op = "看多🔥", "逢低建仓，建议增加黄金配置"
            elif avg <= -1.5:
                dirr, op = "看空⚠️", "减仓避险，建议降低黄金仓位"
            elif avg >= 0.5:
                dirr, op = "偏多", "轻仓持有，保持当前仓位"
            elif avg <= -0.5:
                dirr, op = "偏空", "谨慎为主，暂时观望"
            else:
                dirr, op = "中性震荡", "多看少动，等待明确信号"
            score = min(100, max(0, int(50 + avg * 12)))
            msg += f"建议: {dirr} (信心指数: {score}/100)" + nl
            msg += f"操作: {op}" + nl
            if sentiment.get("top_news"):
                msg += f"重点关注: {smart_translate(sentiment['top_news'][:60])}" + nl
        except:
            msg += "新闻分析服务暂不可用" + nl
        return msg

    elif cmd in ["新闻", "黄金新闻"]:
        msg = f"📰 黄金新闻 {now}" + nl
        try:
            from news_fetcher import fetch_gold_news
            news = fetch_gold_news(10)
            if news:
                msg += f"共{len(news)}条最新消息" + nl + "---" + nl
                for i, n in enumerate(news, 1):
                    t = smart_translate(n.get("title",""))
                    nt = n.get("time","")
                    msg += f"{i}. {t}" + nl
                    if nt:
                        msg += f"   ⏱ {nt}" + nl
            else:
                msg += "暂无新闻数据" + nl
        except:
            msg += "新闻获取失败" + nl
        return msg

    elif "预测" in cmd or "AI" in cmd:
        msg = f"🤖 AI预测 {now}" + nl
        try:
            from decision_engine import get_decision
            d = get_decision()
            msg += f"方向: {d.get('direction', '震荡')}" + nl
            msg += f"信心: {d.get('confidence', 50)}%" + nl
            msg += f"评分: {d.get('score', 50)}/100" + nl
        except:
            msg += "AI预测暂不可用" + nl
        return msg

    elif cmd in ["看板", "数据看板"]:
        return f"📊 数据看板{nl}https://web-production-305e8.up.railway.app/{nl}请复制到浏览器打开"

    elif cmd in ["帮助", "help", "菜单", "怎么用", "使用", "hello", "你好", "hi"]:
        msg = f"🤖 黄金智投助手 {now}" + nl + "---" + nl
        msg += "发送关键词获取服务:" + nl
        msg += "📊 行情 - 实时金价" + nl
        msg += "📈 分析 - 黄金分析" + nl
        msg += "🎯 决策 - 投资建议" + nl
        msg += "📰 新闻 - 黄金新闻" + nl
        msg += "🤖 AI预测 - AI分析" + nl
        msg += "📊 看板 - 数据仪表盘" + nl
        return msg

    # 默认回复：引导用户使用
    msg = (
        "🤖 黄金智投助手 " + now + "\n"
        + "---\n"
        + "发送关键词获取服务:\n"
        + "📊 行情 - 实时国际金价\n"
        + "📈 分析 - 黄金走势分析\n"
        + "🎯 决策 - 今日投资建议\n"
        + "📰 新闻 - 黄金新闻(带翻译)\n"
        + "🤖 AI预测 - AI分析预测\n"
        + "📊 看板 - 数据仪表盘\n"
        + "---\n"
        + "例如发送: 行情 查看实时金价"
    )
    return msg

def xml_resp(to_user, content, from_user="gh_goldassistant"):
    now_str = str(int(time.time()))
    xml = (
        "<xml>"
        + "<ToUserName><![CDATA[" + to_user + "]]></ToUserName>"
        + "<FromUserName><![CDATA[" + from_user + "]]></FromUserName>"
        + "<CreateTime>" + now_str + "</CreateTime>"
        + "<MsgType><![CDATA[text]]></MsgType>"
        + "<Content><![CDATA[" + content + "]]></Content>"
        + "</xml>"
    )
    resp = make_response(xml)
    resp.content_type = "application/xml"
    return resp

def scheduler():
    time.sleep(15)
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
