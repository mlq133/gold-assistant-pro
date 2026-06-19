# -*- coding: utf-8 -*-
"""黄金智投助手 - Streamlit 主仪表盘 (完整版)"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time, os, json

from data_fetcher import (fetch_gold_price, fetch_macro_data, fetch_historical_gold,
    get_live_gold_sync, compute_dxy_from_rates, fetch_gold_cny,
    get_fomc_schedule, save_price_snapshot)
from analyzer import calculate_rotation_signal, calculate_technical_signals, get_investment_advice
from news_fetcher import fetch_gold_news, analyze_news_sentiment, get_news_impact_report
from decision_engine import evaluate_signal, save_decision, load_decision_history
from wechat_pusher import send_push, build_price_alert_msg, build_daily_report_msg, save_config, _load_config

st.set_page_config(page_title="黄金智投助手", page_icon=":ear_of_rice:", layout="wide", initial_sidebar_state="expanded")

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "news_cache" not in st.session_state:
    st.session_state.news_cache = None

st.sidebar.title(":ear_of_rice: 黄金智投助手")
st.sidebar.subheader(":zap: 实时行情")

live_usd = get_live_gold_sync()
gold_cny = fetch_gold_cny()
dxy = compute_dxy_from_rates()
fomc = get_fomc_schedule()

if live_usd:
    c1, c2 = st.sidebar.columns(2)
    c1.metric("XAU/USD", f"${live_usd:,.0f}")
    c2.metric("人民币", f"{gold_cny}元/克" if gold_cny else "N/A")
    st.sidebar.caption(f"美元指数: {dxy:.2f}" if dxy else "")
else:
    st.sidebar.warning("金价获取中...")
if fomc:
    st.sidebar.caption(f"下次FOMC: {fomc[0]["date"]}({fomc[0]["days_left"]}天)")

st.sidebar.markdown("---")
st.sidebar.subheader(":arrows_counterclockwise: 自动刷新")
auto_ref = st.sidebar.toggle("启用实时刷新", value=st.session_state.auto_refresh)
st.session_state.auto_refresh = auto_ref
if st.session_state.auto_refresh:
    st.sidebar.caption(f"最后刷新: {st.session_state.last_refresh.strftime(chr(37)+chr(72)+chr(58)+chr(37)+chr(77)+chr(58)+chr(37)+chr(83))}")
    if (datetime.now() - st.session_state.last_refresh).seconds > 60:
        st.session_state.last_refresh = datetime.now()
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader(":bell: 微信推送设置")
push_config = _load_config()
cur_m = push_config.get("enabled", "pushplus")
push_method = st.sidebar.selectbox("推送方式", ["pushplus","serverchan","bark"],
    index=["pushplus","serverchan","bark"].index(cur_m) if cur_m in ["pushplus","serverchan","bark"] else 0)
token_key = {"pushplus":"pushplus_token","serverchan":"serverchan_key","bark":"bark_key"}.get(push_method,"pushplus_token")
token_label = {"pushplus":"PushPlus Token(推荐)","serverchan":"Server酱 SendKey","bark":"Bark Key"}.get(push_method,"Token")
token_val = st.sidebar.text_input(token_label, value=push_config.get(token_key,""), type="password")
if st.sidebar.button("保存推送设置"):
    save_config(**{token_key: token_val, "enabled": push_method})
    st.sidebar.success("已保存!")
if st.sidebar.button(":bell: 测试推送"):
    cfg = _load_config()
    if cfg.get(token_key):
        ok = send_push("黄金智投助手测试", "推送配置正确!", cfg)
        st.sidebar.success("推送成功!") if ok else st.sidebar.error("推送失败")

st.sidebar.markdown("---")
page = st.sidebar.radio("导航", [":bar_chart: 总览", ":chart_with_upwards_trend: 技术分析",
    ":globe_with_meridians: 宏观轮动", ":scroll: 回测", ":newspaper: 新闻", ":bell: 决策"], key="nav")
st.sidebar.caption(":warning: 仅供参考，不构成投资建议")

@st.cache_data(ttl=300, show_spinner="加载中...")
def load_all_data():
    g = fetch_gold_price()
    m = fetch_macro_data()
    h = fetch_historical_gold(5)
    save_price_snapshot()
    n = get_news_impact_report()
    return g, m, h, n

gold_df, macro_df, hist_gold, news_report = load_all_data()
rotation = calculate_rotation_signal(macro_df)
tech = calculate_technical_signals(gold_df)
advice = get_investment_advice(rotation, tech)
analysis = news_report.get("analysis", {"score":0,"bullish":0,"bearish":0,"total":0})
decision = evaluate_signal(rotation, tech, analysis)
save_decision(decision)

if ":bar_chart:" in page:
    st.title("黄金智投助手 - 总览")
    c1,c2,c3,c4,c5 = st.columns(5)
    delta = ""
    if not gold_df.empty and len(gold_df) > 1:
        pct = (gold_df.iloc[-1, 0] - gold_df.iloc[-2, 0]) / gold_df.iloc[-2, 0] * 100
        delta = f"{pct:+.2f}%"
    c1.metric("伦敦金", f"${live_usd:,.2f}" if live_usd else "N/A", delta)
    c2.metric("人民币金价", f"{gold_cny:.2f}元/克" if gold_cny else "N/A")
    c3.metric("配置评分", f"{rotation.get(chr(40644)+chr(37329)+chr(37197)+chr(32622)+chr(20998)+chr(20998),50)}/100")
    c4.metric("技术面", tech.get(chr(25216)+chr(26415)+chr(38754)+chr(24635)+chr(35780), chr(20013)+chr(24615)))
    c5.metric("操作建议", decision.get("action","持有"), f"评分{decision.get(chr(20998)+chr(20998),0):+.1f}")
    st.info(advice)
    st.subheader("金价走势")
    if gold_df is not None and not gold_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=gold_df.index, y=gold_df.iloc[:,0], mode="lines", name=gold_df.columns[0], line=dict(color="#FFD700", width=2), fill="tozeroy", fillcolor="rgba(255,215,0,0.1)"))
        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
    cl, cr = st.columns(2)
    with cl:
        st.subheader("新闻情绪")
        s = analysis.get("score", 0)
        if s >= 20: st.success(f"利多 ({analysis.get(chr(98+87+92+92-13),0)}利多 vs {analysis.get(chr(98+87+92+92-27),0)}利空)")
        elif s <= -20: st.error(f"利空 ({analysis.get(chr(98+87+92+92-13),0)}利多 vs {analysis.get(chr(98+87+92+92-27),0)}利空)")
        else: st.info(f"中性 ({analysis.get(chr(98+87+92+92-13),0)}利多 vs {analysis.get(chr(98+87+92+92-27),0)}利空)")
    with cr:
        st.subheader("技术指标")
        c1,c2 = st.columns(2)
        c1.metric("RSI", tech.get("RSI","N/A"))
        c2.metric("MACD", tech.get("MACD","N/A"))

elif ":chart_with_upwards_trend:" in page:
    st.title("技术分析")
    if gold_df is not None and not gold_df.empty:
        price = gold_df.iloc[:, 0]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.5,0.25,0.25], subplot_titles=("价格&均线","RSI","MACD"))
        fig.add_trace(go.Scatter(x=gold_df.index, y=price, name="价格", line=dict(color="#FFD700")), row=1, col=1)
        for p,c in [(5,"#00FF00"),(20,"#FF00FF"),(60,"#00FFFF")]:
            fig.add_trace(go.Scatter(x=gold_df.index, y=price.rolling(p).mean(), name=f"MA{p}", line=dict(color=c, width=1)), row=1, col=1)
        delta = price.diff(); gain = delta.where(delta>0,0); loss = (-delta).where(delta<0,0)
        ag = gain.rolling(14).mean(); al = loss.rolling(14).mean()
        rsi_s = 100-100/(1+ag/al)
        fig.add_trace(go.Scatter(x=gold_df.index, y=rsi_s, name="RSI", line=dict(color="orange")), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        e12=price.ewm(span=12).mean(); e26=price.ewm(span=26).mean(); md=e12-e26
        sg=md.ewm(span=9).mean(); hst=md-sg
        fig.add_trace(go.Bar(x=gold_df.index, y=hst, name="Hist", marker_color="gray"), row=3, col=1)
        fig.add_trace(go.Scatter(x=gold_df.index, y=md, name="MACD", line=dict(color="blue")), row=3, col=1)
        fig.add_trace(go.Scatter(x=gold_df.index, y=sg, name="Signal", line=dict(color="red")), row=3, col=1)
        fig.update_layout(template="plotly_dark", height=700, showlegend=True, margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(pd.DataFrame([(k,v) for k,v in tech.items() if k!="当前价格"], columns=["指标","数值"]), use_container_width=True, hide_index=True)

elif ":globe_with_meridians:" in page:
    st.title("宏观轮动分析")
    st.dataframe(pd.DataFrame(list(rotation.items()), columns=["指标","信号"]), use_container_width=True, hide_index=True)
    if macro_df is not None and not macro_df.empty:
        sel = st.multiselect("选择指标", macro_df.columns.tolist(), default=["美元指数","VIX恐慌指数"])
        if sel:
            fig = go.Figure()
            for col in sel: fig.add_trace(go.Scatter(x=macro_df.index, y=macro_df[col], mode="lines", name=col, line=dict(width=2)))
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)

elif ":scroll:" in page:
    st.title("历史回测")
    st.markdown("策略: MA5>MA20持仓 | 区间: 近5年")
    if hist_gold is not None and not hist_gold.empty:
        p = hist_gold if isinstance(hist_gold, pd.Series) else hist_gold.iloc[:,0]
        s = (p.rolling(5).mean() > p.rolling(20).mean()).astype(int).shift(1).fillna(0)
        r = p.pct_change(); sr = r * s
        ch = (1+r).cumprod(); cs = (1+sr).cumprod()
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("持有收益", f"{(ch.iloc[-1]-1):.1%}")
        c2.metric("策略收益", f"{(cs.iloc[-1]-1):.1%}")
        sh = sr.mean()/sr.std()*(252**0.5) if sr.std()!=0 else 0
        c3.metric("夏普", f"{sh:.2f}")
        win = (sr>0).sum()/(sr!=0).sum() if (sr!=0).sum()>0 else 0
        c4.metric("胜率", f"{win:.1%}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ch.index, y=ch, name="持有", line=dict(color="gray", dash="dash")))
        fig.add_trace(go.Scatter(x=cs.index, y=cs, name="策略", line=dict(color="#FFD700", width=2)))
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)
    st.caption(":warning: 历史数据不代表未来表现")

elif ":newspaper:" in page:
    st.title(":newspaper: 黄金新闻分析")
    s = analysis.get("score", 0)
    if s >= 20: st.success(f":arrow_up: 利多 (评分:{s:+.0f})")
    elif s <= -20: st.error(f":arrow_down: 利空 (评分:{s:+.0f})")
    else: st.info(f":left_right_arrow: 中性 (评分:{s:+.0f})")
    st.metric("利多", analysis.get("bullish",0)); st.metric("利空", analysis.get("bearish",0))
    st.divider()
    st.subheader("决策依据")
    for r in decision.get("reasons",[]): st.write(f"- {r}")
    st.write(f"评分: {decision.get(chr(20998)+chr(20998),0):+.1f} | 建议: {decision.get(chr(97+99+97+96-39),chr(100+100+99+98-11))}")
    st.divider()
    st.subheader("最新新闻")
    news_items = news_report.get("news", [])
    if news_items:
        for item in news_items:
            imp = ""
            for r2 in analysis.get("results",[]):
                if r2.get("title","")[:20] in item.get("title",""):
                    imp = {"bullish":":arrow_up:利多","bearish":":arrow_down:利空","neutral":":left_right_arrow:中性","volatile":":warning:波动"}.get(r2.get("impact",""),"")
            with st.expander(f"{imp} {item[chr(116)+chr(105)+chr(116)+chr(108)+chr(101)][:70]}"):
                st.write(f"来源: {item.get("来源", "未知")}")

elif ":bell:" in page:
    st.title(":bell: 决策记录")
    d = decision
    em = {"加仓":":large_green_square:","减仓":":red_square:","持有":":white_large_square:"}
    st.markdown(f"### {em.get(d.get("加仓","持有"),"○")} {d.get(chr(97+99+97+96-39),chr(100+100+99+98-11))} (评分:{d.get(chr(20998)+chr(20998),0):+.1f})")
    st.write("依据:"); " ".join([str(r) for r in d.get("reasons",[])])
    history = load_decision_history(7)
    if history:
        df = pd.DataFrame(history)
        if "timestamp" in df.columns:
            df["time"] = pd.to_datetime(df["timestamp"]).dt.strftime("%m-%d %H:%M")
        st.dataframe(df[["time","action","score","confidence"]].tail(20), use_container_width=True, hide_index=True)
    else: st.info("暂无记录")