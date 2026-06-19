# -*- coding: utf-8 -*-
"""微信推送模块 (Server酱 / PushPlus / Bark)"""
import os
import json
import ssl
from datetime import datetime
import requests

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wechat_config.json")


def _load_config():
    """加载推送配置"""
    default = {
        "pushplus_token": "",  # https://www.pushplus.plus
        "serverchan_key": "",  # https://sct.ftqq.com
        "bark_key": "",        # https://bark.day.app
        "enabled": "pushplus",  # pushplus / serverchan / bark
        "push_on_buy": True,
        "push_on_sell": True,
        "push_on_alert": True,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**default, **json.load(f)}
        except Exception:
            pass
    return default


def save_config(**kwargs):
    """保存推送配置"""
    config = _load_config()
    config.update(kwargs)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return config


def send_push(title, content, config=None):
    """发送推送消息"""
    if config is None:
        config = _load_config()

    method = config.get("enabled", "pushplus")
    results = []

    # PushPlus (推荐: 简单稳定)
    if method == "pushplus" and config.get("pushplus_token"):
        try:
            r = requests.post(
                "https://www.pushplus.plus/send",
                json={"token": config["pushplus_token"], "title": title, "content": content, "template": "markdown"},
                timeout=10,
            )
            results.append(("pushplus", r.status_code == 200))
            if r.status_code == 200:
                return True
        except Exception:
            pass

    # Server酱
    if method == "serverchan" and config.get("serverchan_key"):
        try:
            r = requests.post(
                f"https://sctapi.ftqq.com/{config['serverchan_key']}.send",
                data={"title": title, "desp": content},
                timeout=10,
            )
            results.append(("serverchan", r.status_code == 200))
            if r.status_code == 200:
                return True
        except Exception:
            pass

    # Bark (iOS)
    if method == "bark" and config.get("bark_key"):
        try:
            r = requests.get(
                f"https://api.day.app/{config['bark_key']}/{title}/{content[:500]}",
                timeout=10,
            )
            results.append(("bark", r.status_code == 200))
            if r.status_code == 200:
                return True
        except Exception:
            pass

    return False


def build_price_alert_msg(gold_usd, gold_cny, change_pct, dxy, action):
    """构建金价变动提醒消息"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    emoji = {"买入": "\U0001f7e2", "加仓": "\U0001f7e2", "卖出": "\U0001f534", "减仓": "\U0001f534", "关注": "\U0001f7e1"}.get(action, "\u26a0\ufe0f")
    msg = f"""## {emoji} 黄金交易提醒

**时间**: {now}
**操作建议**: **{action}**

---

### 当前行情
| 指标 | 数值 |
|------|------|
| 伦敦金 (XAU/USD) | ${gold_usd:,.2f} |
| 人民币金价 | {gold_cny:.2f} 元/克 |
| 美元指数 | {dxy:.2f} |
| 日内涨跌 | {change_pct:+.2f}% |

---

### 操作理由
"""
    if "加仓" in action:
        msg += """
- \ud83d\udcca 技术面或宏观面发出买入信号
- \ud83c\udf0d 地缘政治/经济不确定性支撑
- \ud83d\udcc8 长期上升趋势保持完好

> \u26a0\ufe0f 建议分批建仓，控制仓位在总资产的10-20%
"""
    elif "减仓" in action:
        msg += """
- \ud83d\udcca 技术面或宏观面发出卖出信号
- \ud83d\udcc9 短期涨幅过大，存在回调风险
- \ud83d\udcb0 锁定利润，落袋为安

> \u26a0\ufe0f 建议分批减仓，保留核心仓位
"""
    else:
        msg += """
- \ud83d\udcca 当前市场情绪中性
- \ud83d\udd0d 等待更明确的信号
- \ud83d\udccb 建议观望或轻仓持有
"""
    return msg


def build_daily_report_msg(gold_usd, gold_cny, dxy, sentiment, analysis, news_count):
    """构建每日行情报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"""## \ud83d\udcca 黄金日报

**时间**: {now}

---

### \ud83d\udfe1 实时行情
| 指标 | 数值 |
|------|------|
| 伦敦金 | ${gold_usd:,.2f} |
| 人民币 | {gold_cny:.2f} 元/克 |
| 美元指数 | {dxy:.2f} |

---

### \ud83d\udcf0 新闻情绪分析
**整体判断**: {sentiment}

- 利多新闻: {analysis.get('bullish', 0)} 条
- 利空新闻: {analysis.get('bearish', 0)} 条
- 今日抓取: {news_count} 条新闻

---

### \ud83d\udca1 今日关注
"""
    if analysis.get("score", 0) >= 20:
        msg += "\n- \ud83d\udfe2 市场情绪偏多，关注突破关键阻力位的时机\n"
    elif analysis.get("score", 0) <= -20:
        msg += "\n- \ud83d\udd34 市场情绪偏空，注意控制仓位风险\n"
    else:
        msg += "\n- \ud83d\udfe1 市场情绪中性，等待方向性信号\n"

    msg += f"""
> \ud83d\udd14 设置推送令牌后，每日自动推送此报告
> \ud83d\uded2 回复 "行情" 获取实时价格
"""
    return msg
