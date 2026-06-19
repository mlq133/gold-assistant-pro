# -*- coding: utf-8 -*-
"""多资产联动分析 (带缓存, 避免频繁限流)"""
import os, json
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")


def _read_cache():
    path = os.path.join(CACHE_DIR, "asset_prices.json")
    if os.path.exists(path):
        age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(path))).total_seconds()
        if age < 7200:
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except: pass
    return None


def _write_cache(data):
    path = os.path.join(CACHE_DIR, "asset_prices.json")
    with open(path, "w") as f:
        json.dump(data, f)


def fetch_asset_prices():
    cached = _read_cache()
    if cached:
        return cached
    results = {}
    import yfinance as yf
    try:
        etfs = ["GLD","SLV","USO","SPY","UUP","TLT","IBIT"]
        data = yf.download(etfs, period="1mo", interval="1d", auto_adjust=True, progress=False)
        if isinstance(data.columns, pd.MultiIndex) and "Close" in data:
            close = data["Close"]
            names = {"GLD":"黄金","SLV":"白银","USO":"原油","SPY":"标普500","UUP":"美元","TLT":"长债","IBIT":"比特币"}
            for sym, name in names.items():
                if sym in close.columns and not close[sym].dropna().empty:
                    p = float(close[sym].iloc[-1])
                    c = float(close[sym].pct_change().iloc[-1] * 100) if len(close[sym]) > 1 else 0
                    results[name] = {"price": p, "change": round(c, 2)}
    except: pass
    from data_fetcher import get_live_gold_sync
    live = get_live_gold_sync()
    if live:
        results["黄金"] = {"price": live, "change": results.get("黄金",{}).get("change", 0)}
    if results:
        _write_cache(results)
    return results


def compute_ratios(prices):
    ratios = {}
    g = prices.get("黄金", {}).get("price")
    s = prices.get("白银", {}).get("price")
    o = prices.get("原油", {}).get("price")
    sp = prices.get("标普500", {}).get("price")
    if g and s and s > 0:
        r = round(g / s, 1)
        ratios["金银比"] = {"value": r, "signal": "看多白银" if r > 85 else "看多黄金" if r < 60 else "正常"}
    if g and o and o > 0:
        r = round(g / o, 1)
        ratios["金油比"] = {"value": r, "signal": "衰退风险" if r > 25 else "正常"}
    if g and sp and sp > 0:
        r = round(g / sp, 3)
        ratios["金股比"] = {"value": r, "signal": "避险" if r > 2.0 else "正常"}
    return ratios


def get_multi_asset_report():
    prices = fetch_asset_prices()
    ratios = compute_ratios(prices)
    return {"prices": prices, "ratios": ratios}
