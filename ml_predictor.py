# -*- coding: utf-8 -*-
"""机器学习预测模块: RF方向预测 + LSTM趋势预测"""

import os, json, warnings
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")


def _build_features(prices):
    df = pd.DataFrame({"close": prices})
    for p in [3,5,10,20,60]:
        df[f"ma_{p}"] = df["close"].rolling(p).mean()
        df[f"dist_ma{p}"] = (df["close"] - df[f"ma_{p}"]) / df[f"ma_{p}"] * 100
    for d in [1,3,5,10]:
        df[f"ret_{d}d"] = df["close"].pct_change(d) * 100
    delta = df["close"].diff()
    gain = delta.where(delta>0,0).rolling(14).mean()
    loss = (-delta).where(delta<0,0).rolling(14).mean()
    df["rsi_14"] = 100 - 100/(1+gain/(loss+1e-10))
    e12 = df["close"].ewm(span=12).mean()
    e26 = df["close"].ewm(span=26).mean()
    df["macd"] = e12 - e26
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    bb_mid = df["close"].rolling(20).mean()
    bb_std = df["close"].rolling(20).std()
    df["bb_position"] = (df["close"] - bb_mid) / (bb_std*2 + 1e-10)
    df["vol_5d"] = df["ret_1d"].rolling(5).std() * 100
    return df


def predict_direction(prices, forecast_days=3):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    df = _build_features(prices).dropna()
    if len(df) < 30:
        return {"direction": "数据不足", "confidence": 0}
    future_ret = df["close"].shift(-forecast_days) / df["close"] - 1
    df["label"] = np.where(future_ret >= 0.005, 1, np.where(future_ret <= -0.005, -1, 0))
    df = df.dropna()
    if len(df) < 30:
        return {"direction": "数据不足", "confidence": 0}
    feature_cols = [c for c in df.columns if c not in ["close","label"]]
    X, y = df[feature_cols].values, df["label"].values
    if len(np.unique(y)) < 2:
        return {"direction": "中性", "confidence": 30}
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        clf.fit(X_train, y_train)
        pred = clf.predict(X[-1:].reshape(1, -1))[0]
        proba = clf.predict_proba(X[-1:].reshape(1, -1))[0]
        return {"direction": {1:"看涨",-1:"看跌",0:"震荡"}.get(int(pred),"未知"),
                "confidence": int(max(proba)*100),
                "forecast_days": forecast_days}
    except Exception as e:
        return {"direction": "预测失败", "confidence": 0}


def predict_trend(prices, lookback=20, forecast=7):
    """线性回归 + 动量修正预测趋势"""
    arr = np.array(prices, dtype=float)
    if len(arr) < lookback + 10:
        return None
    recent = arr[-lookback:]
    x = np.arange(lookback)
    slope, intercept = np.polyfit(x, recent, 1)
    ma5 = np.mean(arr[-5:]) if len(arr)>=5 else np.mean(arr)
    ma20 = np.mean(arr[-20:]) if len(arr)>=20 else ma5
    momentum = (ma5 - ma20) / ma20
    predictions = [intercept + slope * (lookback + i) * (1 + momentum * 0.5) for i in range(forecast)]
    current = arr[-1]
    change = (predictions[-1] - current) / current * 100
    return {"current": round(current,2), "pred_7d": round(predictions[-1],2),
            "change_pct": round(change,2),
            "trend": "up" if change > 1 else "down" if change < -1 else "sideways"}


def predict_prices(prices):
    """综合ML预测"""
    rf = predict_direction(prices, 3)
    trend = predict_trend(prices)
    score = 50
    if rf.get("direction") == "看涨": score += rf.get("confidence", 50) * 0.2
    elif rf.get("direction") == "看跌": score -= rf.get("confidence", 50) * 0.2
    if trend:
        score += {"up":10,"down":-10,"sideways":0}.get(trend.get("trend","sideways"), 0)
        score += min(max(trend.get("change_pct", 0) * 2, -15), 15)
    score = max(0, min(100, score))
    return {"ml_score": round(score,1),
            "rf_direction": rf.get("direction","未知"),
            "rf_confidence": rf.get("confidence",0),
            "trend_7d": trend.get("trend","unknown") if trend else "unknown",
            "predicted_change_7d": trend.get("change_pct") if trend else None}


def get_ml_report():
    from data_fetcher import fetch_gold_price
    gold = fetch_gold_price()
    if gold is not None and not gold.empty:
        return predict_prices(gold.iloc[:, 0].values)
    return {"ml_score": 0}