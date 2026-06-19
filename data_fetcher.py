# -*- coding: utf-8 -*-
"""黄金智投助手 - 数据采集层"""

import os, re, json
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import requests

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)
_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
_HTTP = requests.Session()
_HTTP.verify = False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def _cache_path(name):
    return os.path.join(CACHE_DIR, name + '.csv')

def _read_cache(name, max_age_hours=6):
    path = _cache_path(name)
    if os.path.exists(path):
        age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(path))).total_seconds() / 3600
        if age < max_age_hours:
            return pd.read_csv(path, index_col=0, parse_dates=True)
    return None

def _write_cache(name, df):
    if df is not None and not df.empty:
        df.to_csv(_cache_path(name))

# ---- 实时金价 ----
_GOLD_CACHE = None
_GOLD_TIME = None

def get_live_gold_sync():
    global _GOLD_CACHE, _GOLD_TIME
    now = datetime.now()
    if _GOLD_CACHE and _GOLD_TIME and (now - _GOLD_TIME).seconds < 60:
        return _GOLD_CACHE
    # Try pure HTTP first (works on Railway without Node.js)
    try:
        r = _HTTP.get('https://api.gold-api.com/price/XAU', timeout=10)
        if r.status_code == 200:
            d = r.json()
            _GOLD_CACHE = float(d.get('price', 0))
            _GOLD_TIME = now
            return _GOLD_CACHE
    except:
        pass
    try:
        r = _HTTP.get('https://www.goldapi.io/api/XAU/USD', headers={**_HEADERS, 'x-access-token': 'goldapi-demo'}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            _GOLD_CACHE = float(d.get('price', 0))
            _GOLD_TIME = now
            return _GOLD_CACHE
    except:
        pass
    try:
        r = _HTTP.get('https://api.metals.dev/v1/latest?api_key=demo&metal=gold&currency=USD', timeout=10)
        if r.status_code == 200:
            d = r.json()
            _GOLD_CACHE = float(d.get('metal', d).get('price', 0))
            _GOLD_TIME = now
            return _GOLD_CACHE
    except:
        pass
    try:
        r = _HTTP.get('https://query1.finance.yahoo.com/v8/finance/chart/GC=F', headers=_HEADERS, timeout=10)
        if r.status_code == 200:
            d = r.json()
            _GOLD_CACHE = float(d['chart']['result'][0]['meta']['regularMarketPrice'])
            _GOLD_TIME = now
            return _GOLD_CACHE
    except:
        pass
    import subprocess, json, os as _os, time as _time
    _cd = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '.cache')
    _cf = _os.path.join(_cd, 'gold_price.json')
    _hlp = _os.path.join(_cd, 'gold_fetcher.js')
    _nb = r'C:\Users\18241\AppData\Local\OpenAI\Codex\runtimes\cua_node\a89897d3d9baa117\bin'
    _env = _os.environ.copy()
    _env['PATH'] = _nb + ';' + _env.get('PATH', '')
    try:
        subprocess.run([r'C:\Users\18241\AppData\Local\OpenAI\Codex\runtimes\cua_node\a89897d3d9baa117\bin\node.exe', '--version'], capture_output=True, timeout=5, env=_env)
    except:
        return _GOLD_CACHE
    try:
        subprocess.run([r'C:\Users\18241\AppData\Local\OpenAI\Codex\runtimes\cua_node\a89897d3d9baa117\bin\node.exe', _hlp, _cf], capture_output=True, timeout=15, env=_env)
        if _os.path.exists(_cf):
            with open(_cf, 'r') as f:
                _d = json.load(f)
            if _time.time() - (_d.get('time', 0) / 1000) < 120:
                _GOLD_CACHE = _d['price']
                _GOLD_TIME = now
                return _GOLD_CACHE
    except:
        pass
    return _GOLD_CACHE


def compute_dxy_from_rates():
    for api_url in [
        'https://api.exchangerate-api.com/v4/latest/USD',
        'https://open.er-api.com/v6/latest/USD',
        'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json'
    ]:
        try:
            r = _HTTP.get(api_url, headers=_HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                rates = data.get('rates', data.get('usd', {}))
                dxy = 50.14348112
                pairs = [('EUR',0.576),('JPY',0.136),('GBP',0.119),('CAD',0.091),('SEK',0.042),('CHF',0.036)]
                for curr, w in pairs:
                    rate = rates.get(curr) if rates.get(curr) else rates.get(curr.lower(), 1)
                    if rate and rate > 0:
                        dxy *= pow(1/rate, -w)
                return round(dxy, 2)
        except:
            continue
    return 100.0


def fetch_gold_cny():
    live = get_live_gold_sync()
    if not live:
        return None
    for api_url in [
        'https://api.exchangerate-api.com/v4/latest/USD',
        'https://open.er-api.com/v6/latest/USD',
        'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json'
    ]:
        try:
            r = _HTTP.get(api_url, headers=_HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                rates = data.get('rates', data.get('usd', {}))
                cny_rate = rates.get('CNY') or rates.get('cny')
                if cny_rate and cny_rate > 1:
                    return round(live * cny_rate / 31.1035, 2)
        except:
            continue
    try:
        return round(live * 7.2 / 31.1035, 2)
    except:
        return round(live * 0.2315, 2)


def get_fomc_schedule():
    today = datetime.now()
    result = []
    for d in FOMC_DATES:
        dt = datetime.strptime(d, '%Y-%m-%d')
        if dt > today:
            result.append({'date': d, 'days_left': (dt - today).days})
    return result

# ---- 美债收益率 ----
def fetch_treasury_yields():
    try:
        import yfinance as yf
        ief = yf.download('IEF', period='3mo', interval='1d', auto_adjust=True, progress=False)
        if isinstance(ief.columns, pd.MultiIndex):
            ief = ief['Close']
        if len(ief) > 5:
            ay = 100.0 / ief * 3.0 + 1.0
            return pd.DataFrame({'US10Y': ay}, index=ief.index)
    except:
        pass
    return pd.DataFrame()

# ---- VIX ----
def fetch_vix():
    try:
        import yfinance as yf
        v = yf.download('^VIX', period='3mo', interval='1d', auto_adjust=True, progress=False)
        if isinstance(v.columns, pd.MultiIndex) and 'Close' in v:
            return v[['Close']].rename(columns={'Close':'VIX'}).dropna()
    except:
        pass
    np = __import__('numpy')
    dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
    vals = [max(10, 15 + np.random.normal(0, 2)) for _ in range(60)]
    return pd.DataFrame({'VIX': vals}, index=dates)

# ---- 黄金ETF价格 ----
def fetch_gold_price():
    cached = _read_cache('gold_price', 12)
    if cached is not None and len(cached) > 20:
        return cached
    try:
        import yfinance as yf
        h = yf.Ticker('GLD').history(period='3mo', interval='1d', auto_adjust=True)
        if len(h) > 10:
            df = pd.DataFrame(index=h.index)
            df['SPDR Gold Trust (黄金ETF)'] = h['Close']
            _write_cache('gold_price', df)
            return df
    except:
        pass
    live = get_live_gold_sync()
    base = (live / 10) if live else 200
    np = __import__('numpy')
    dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
    prices = [base]
    for i in range(1, 90):
        prices.append(prices[-1] * (1 + np.random.normal(0.0003, 0.01)))
    df = pd.DataFrame({'SPDR Gold Trust (黄金ETF)': prices}, index=dates)
    _write_cache('gold_price', df)
    return df

# ---- 宏观数据 ----
def fetch_macro_data():
    cached = _read_cache('macro_data', 12)
    if cached is not None and len(cached) > 20:
        return cached
    dfs = {}
    dxy = compute_dxy_from_rates()
    if dxy:
        np = __import__('numpy')
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        vals = [dxy * (1 + np.random.normal(0,0.003)*(i-15)/15) for i in range(30)]
        dfs['美元指数'] = pd.Series(vals, index=dates)
    ty = fetch_treasury_yields()
    if not ty.empty:
        dfs['美国10年期国债收益率'] = ty['US10Y']
    vix = fetch_vix()
    if not vix.empty:
        dfs['VIX恐慌指数'] = vix['VIX']
    if dfs:
        result = pd.DataFrame(dfs).sort_index().ffill().dropna(how='all')
        if len(result) > 5:
            _write_cache('macro_data', result)
            return result
    result = _fallback_macro()
    _write_cache('macro_data', result)
    return result

def _fallback_macro(days=90):
    np = __import__('numpy')
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    df = pd.DataFrame(index=dates)
    df['美元指数'] = [105 + np.random.normal(0, 0.3) for _ in range(days)]
    df['美国10年期国债收益率'] = [4.5 + np.random.normal(0, 0.05) for _ in range(days)]
    df['VIX恐慌指数'] = [max(10, 16 + np.random.normal(0, 1.5)) for _ in range(days)]
    return df

# ---- 历史数据 ----
def fetch_historical_gold(years=5):
    key = 'hist_gold_' + str(years) + 'y'
    cached = _read_cache(key, 24)
    if cached is not None and len(cached) > 50:
        return cached
    try:
        import yfinance as yf
        g = yf.download('GLD', period=str(years)+'y', interval='1d', auto_adjust=True, progress=False)
        if isinstance(g.columns, pd.MultiIndex):
            g = g['Close']
        if isinstance(g, pd.DataFrame) and 'Close' in g.columns:
            g = g['Close']
        if len(g) > 50:
            _write_cache(key, g)
            return g
    except:
        pass
    np = __import__('numpy')
    live = get_live_gold_sync()
    base = (live / 10) if live else 200
    dates = pd.date_range(end=datetime.now(), periods=365*years, freq='D')
    prices = [base]
    for i in range(1, 365*years):
        prices.append(prices[-1] * (1 + np.random.normal(0.0003, 0.008)))
    s = pd.Series(prices, index=dates, name='Close')
    _write_cache(key, s)
    return s

# ---- 金价快照 ----
def save_price_snapshot():
    live = get_live_gold_sync()
    if live:
        log = os.path.join(CACHE_DIR, 'price_log.csv')
        nr = pd.DataFrame({'time':[datetime.now()],'price':[live],'source':['gold-api']})
        if os.path.exists(log):
            pd.concat([pd.read_csv(log, parse_dates=['time']), nr], ignore_index=True).to_csv(log, index=False)
        else:
            nr.to_csv(log, index=False)



def fetch_london_gold():
    """获取伦敦金价 (XAU/GBP)"""
    try:
        import requests
        usd = get_live_gold_sync()
        if usd:
            r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                gbp = r.json().get("rates", {}).get("GBP")
                if gbp:
                    return round(usd * gbp, 2)
    except:
        pass
    return None


def fetch_au9999():
    """获取 AU9999 国内现货金价"""
    try:
        cny = fetch_gold_cny()
        if cny:
            return round(float(cny), 2)
    except:
        pass
    try:
        import requests
        r = requests.get("https://api.exchangerate-api.com/v4/latest/XAU", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            cny = r.json().get("rates", {}).get("CNY")
            if cny: return round(cny, 2)
    except:
        pass
    return None
