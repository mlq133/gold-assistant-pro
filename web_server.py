import os, sys, json, threading, time, socket
from http.server import HTTPServer, BaseHTTPRequestHandler
sys.path.insert(0, os.path.dirname(__file__))
os.environ['STREAMLIT_RUN_ON_IMPORT'] = '0'

# Warm start: 预加载模块
from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates, fetch_gold_price, fetch_macro_data
from news_fetcher import fetch_gold_news, analyze_news_sentiment
from analyzer import calculate_rotation_signal, calculate_technical_signals
from decision_engine import evaluate_full_signal
from ml_predictor import get_ml_report

# 预热缓存
try:
    _ = get_live_gold_sync()
    _ = fetch_gold_cny()
    _ = compute_dxy_from_rates()
    print('[Warm] Data loaded OK')
except Exception as e:
    print('[Warm] Load error:', str(e))

class GoldAPI(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/data':
            try:
                gold = get_live_gold_sync()
                cny = fetch_gold_cny()
                dxy = compute_dxy_from_rates()
                news = fetch_gold_news(5)
                sentiment = analyze_news_sentiment(news)
                try:
                    gold_df = fetch_gold_price()
                    macro_df = fetch_macro_data()
                    rotation = calculate_rotation_signal(macro_df)
                    technical = calculate_technical_signals(gold_df)
                    ml = get_ml_report()
                    decision = evaluate_full_signal(rotation, technical, sentiment, ml, None)
                except:
                    decision = {'action': '分析中', 'score': 0, 'reasons': ['系统计算中']}
                data = json.dumps({
                    'gold_usd': round(gold, 2) if gold else None,
                    'gold_cny': cny,
                    'dxy': dxy,
                    'news': [{'title': n.get('title',''), 'source': n.get('source','')} for n in (news or [])],
                    'sentiment': sentiment,
                    'decision': decision,
                    'time': time.strftime('%H:%M:%S')
                })
            except Exception as e:
                data = json.dumps({'error': str(e), 'time': time.strftime('%H:%M:%S')})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data.encode())
        else:
            with open(os.path.join(os.path.dirname(__file__), 'dashboard.html'), 'rb') as f:
                html = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html)

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8500), GoldAPI)
    print('[OK] Gold Assistant Web running at http://localhost:8500')
    server.serve_forever()
