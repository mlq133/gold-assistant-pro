"""
黄金智投助手 - 分析模型层
资产轮动模型、技术指标、趋势判断
"""

import numpy as np
import pandas as pd


def calculate_rotation_signal(macro_df: pd.DataFrame) -> dict:
    """大类资产轮动信号"""
    if macro_df.empty or len(macro_df) < 5:
        return {"error": "数据不足"}

    latest = macro_df.iloc[-1]
    ma10 = macro_df.rolling(10).mean().iloc[-1]
    signals = {}

    dxy = latest.get("美元指数", 100)
    dxy_ma = ma10.get("美元指数", 100)
    signals["美元强弱"] = "美元偏弱(利好黄金)" if dxy < dxy_ma else "美元偏强(利空黄金)"

    tips = latest.get("TIPS ETF (实际利率参考)", 0)
    tips_ma = ma10.get("TIPS ETF (实际利率参考)", 0)
    signals["实际利率趋势"] = "下行(利好黄金)" if tips < tips_ma else "上行(利空黄金)"

    vix = latest.get("VIX恐慌指数", 15)
    signals["市场情绪"] = "恐慌(避险利好黄金)" if vix > 25 else "正常" if vix > 15 else "贪婪(利空黄金)"

    score = 50
    if signals["美元强弱"] == "美元偏弱(利好黄金)":
        score += 15
    else:
        score -= 10
    if signals["实际利率趋势"] == "下行(利好黄金)":
        score += 15
    else:
        score -= 10
    if "恐慌(避险利好黄金)" in signals["市场情绪"]:
        score += 15
    elif signals["市场情绪"] == "贪婪(利空黄金)":
        score -= 10
    score = max(0, min(100, score))

    if score >= 70:
        signals["配置建议"] = "超配黄金 (60-80%仓位)"
    elif score >= 50:
        signals["配置建议"] = "均衡配置 (40-60%仓位)"
    elif score >= 30:
        signals["配置建议"] = "低配黄金 (20-40%仓位)"
    else:
        signals["配置建议"] = "减持黄金 (0-20%仓位)"
    signals["黄金配置评分"] = score
    return signals


def calculate_technical_signals(gold_df: pd.DataFrame) -> dict:
    """技术面分析：均线、RSI、MACD、布林带"""
    if gold_df is None or gold_df.empty:
        return {"error": "无数据"}

    series = gold_df.iloc[:, 0] if isinstance(gold_df, pd.DataFrame) else gold_df
    price = series.values.astype(float)
    signals = {}

    ma5 = pd.Series(price).rolling(5).mean().iloc[-1]
    ma20 = pd.Series(price).rolling(20).mean().iloc[-1]
    ma60 = pd.Series(price).rolling(60).mean().iloc[-1] if len(price) >= 60 else ma20
    current = price[-1]
    signals["当前价格"] = current
    signals["MA5"] = ma5
    signals["MA20"] = ma20
    signals["MA60"] = ma60

    if current > ma5 > ma20:
        signals["均线趋势"] = "多头排列 (强势)"
    elif current < ma5 < ma20:
        signals["均线趋势"] = "空头排列 (弱势)"
    else:
        signals["均线趋势"] = "震荡整理"

    # RSI
    delta = np.diff(price[-30:]) if len(price) >= 30 else np.diff(price)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.mean(gain[-14:]) if len(gain) >= 14 else np.mean(gain)
    avg_loss = np.mean(loss[-14:]) if len(loss) >= 14 else np.mean(loss)
    rsi = 100 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
    signals["RSI"] = round(rsi, 1)
    signals["RSI信号"] = "超买" if rsi > 70 else "超卖" if rsi < 30 else "正常"

    # MACD
    ema12 = pd.Series(price).ewm(span=12).mean().iloc[-1]
    ema26 = pd.Series(price).ewm(span=26).mean().iloc[-1] if len(price) >= 26 else ema12
    macd = ema12 - ema26
    signals["MACD"] = round(macd, 2)
    signals["MACD信号"] = "金叉看多" if macd > 0 else "死叉看空"

    # 布林带
    if len(price) >= 20:
        bb_mid = pd.Series(price[-20:]).mean()
        bb_std = pd.Series(price[-20:]).std()
        signals["布林上轨"] = round(bb_mid + 2 * bb_std, 2)
        signals["布林中轨"] = round(bb_mid, 2)
        signals["布林下轨"] = round(bb_mid - 2 * bb_std, 2)
        if current >= signals["布林上轨"]:
            signals["布林信号"] = "触及上轨 (超买)"
        elif current <= signals["布林下轨"]:
            signals["布林信号"] = "触及下轨 (超卖)"
        else:
            signals["布林信号"] = "区间内运行"

    # 综合判断
    bullish = sum([1 for c in ["多头排列" in signals.get("均线趋势", ""),
                                signals.get("RSI信号") == "超卖",
                                signals.get("MACD信号") == "金叉看多"] if c])
    bearish = sum([1 for c in ["空头排列" in signals.get("均线趋势", ""),
                                signals.get("RSI信号") == "超买",
                                signals.get("MACD信号") == "死叉看空"] if c])
    signals["技术面总评"] = "偏多" if bullish > bearish else "偏空" if bearish > bullish else "中性"
    return signals


def get_investment_advice(rotation: dict, technical: dict) -> str:
    """综合给出投资建议"""
    parts = []
    score = rotation.get("黄金配置评分", 50)
    tech = technical.get("技术面总评", "中性")

    if score >= 70:
        parts.append("宏观面强烈看多黄金")
    elif score >= 50:
        parts.append("宏观面温和看多黄金")
    elif score >= 30:
        parts.append("宏观面偏谨慎")
    else:
        parts.append("宏观面看空黄金")

    parts.append(f"技术面: {tech}")
    parts.append(f"轮动模型建议: {rotation.get('配置建议', '观望')}")

    if "偏多" in tech and score >= 50:
        parts.append("综合建议: 技术面和宏观面共振看多，可考虑加仓")
    elif "偏空" in tech and score < 50:
        parts.append("综合建议: 技术面和宏观面共振看空，建议减仓")
    else:
        parts.append("综合建议: 信号分歧，建议观望或轻仓操作")

    return "\n".join(parts)
