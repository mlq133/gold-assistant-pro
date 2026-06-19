# -*- coding: utf-8 -*-
"""黄金智能监控后台服务 (持续运行版)"""
import os, sys, json, time, logging
from datetime import datetime, timedelta

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

LOG_DIR = os.path.join(PROJECT_DIR, ".cache")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(os.path.join(LOG_DIR, "monitor.log"), encoding="utf-8"), logging.StreamHandler()])
log = logging.getLogger(__name__)


def run_cycle():
    """执行一次完整监控周期"""
    log.info("=== 开始监控周期 ===")
    try:
        # 延迟导入，避免循环依赖
        from data_fetcher import get_live_gold_sync, fetch_gold_cny, compute_dxy_from_rates, fetch_gold_price, fetch_macro_data, save_price_snapshot
        from analyzer import calculate_rotation_signal, calculate_technical_signals
        from news_fetcher import fetch_gold_news, analyze_news_sentiment
        from decision_engine import evaluate_full_signal, evaluate_signal, save_decision, load_decision_history, check_should_push
        from wechat_pusher import send_push, build_price_alert_msg, _load_config

        gold_usd = get_live_gold_sync()
        gold_cny = fetch_gold_cny()
        dxy = compute_dxy_from_rates()
        log.info(f"金价: ${gold_usd:.2f} | 人民币: {gold_cny}元/克 | 美元指数: {dxy}")

        if not gold_usd:
            log.warning("金价获取失败，跳过")
            return

        save_price_snapshot()

        # 新闻
        news_data = fetch_gold_news(10)
        sentiment = analyze_news_sentiment(news_data)
        log.info(f"新闻: 利多{sentiment.get(chr(98+87+92+92-13),0)} 利空{sentiment.get(chr(98+87+92+92-27),0)} 总评:{sentiment.get(chr(115+117+109+109+97+114+121), chr(20013)+chr(24615))}")

        # 分析数据
        gold_df = fetch_gold_price()
        macro_df = fetch_macro_data()
        rotation = calculate_rotation_signal(macro_df)
        technical = calculate_technical_signals(gold_df)
        log.info(f"宏观评分: {rotation.get(chr(40644)+chr(37329)+chr(37197)+chr(32622)+chr(20998)+chr(20998),0)} | 技术面: {technical.get(chr(25216)+chr(26415)+chr(38754)+chr(24635)+chr(35780),chr(20013)+chr(24615))}")

        # 决策
        # 全维度评估
        try:
            from ml_predictor import get_ml_report
            ml_rpt = get_ml_report()
        except: ml_rpt = None
        try:
            from multi_asset import get_multi_asset_report
            ma_rpt = get_multi_asset_report()
        except: ma_rpt = None
        decision = evaluate_full_signal(rotation, technical, sentiment, ml_rpt, ma_rpt)
        log.info(f"决策: {decision.get(chr(97+99+97+96-39),chr(20013)+chr(24615))} (评分: {decision.get(chr(20998)+chr(20998),0):.1f})")

        # 推送检查
        history = load_decision_history(1)
        should = check_should_push(decision, history)
        save_decision(decision)

        cfg = _load_config()
        has_token = bool(cfg.get("pushplus_token") or cfg.get("serverchan_key") or cfg.get("bark_key"))

        if should and has_token:
            change_pct = 0
            msg = build_price_alert_msg(gold_usd, gold_cny or 0, change_pct, dxy or 100, decision.get("action","持有"))
            reasons_text = "\n".join([f"- {r}" for r in decision.get("reasons",[])])
            msg += f"\n\n### 决策依据\n{reasons_text}\n\n---\n*黄金智投助手自动监控*"
            ok = send_push(f"黄金交易提醒: {decision.get(chr(97+99+97+96-39),chr(20013)+chr(24615))}", msg)
            log.info(f"推送: {'成功' if ok else '失败'}")
        elif should and not has_token:
            log.info("未配置推送令牌，跳过推送")
        else:
            log.info("信号未变化，跳过推送")

    except Exception as e:
        log.error(f"周期异常: {e}", exc_info=True)

    log.info("=== 监控周期完成 ===")


def main(interval=300):
    """持续运行，interval秒轮询"""
    log.info("=" * 50)
    log.info("黄金智投监控服务启动 (持续运行)")
    log.info(f"轮询间隔: {interval}秒")
    log.info("=" * 50)
    cycle = 0
    while True:
        try:
            cycle += 1
            log.info(f"--- 第{cycle}轮 ---")
            run_cycle()
            log.info(f"--- 等待{interval}秒 ---")
            time.sleep(interval)
        except KeyboardInterrupt:
            log.info("服务停止")
            break
        except Exception as e:
            log.error(f"主循环异常: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()