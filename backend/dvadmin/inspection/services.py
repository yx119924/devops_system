# -*- coding: utf-8 -*-
"""巡检日报 · 取数层

职责边界：
  取数（本文件）→ 聚合（aggregate.py，纯函数）→ 渲染（exporters/*）
这样拆的好处是聚合逻辑能在本地无库跑断言，不必为了验报表去连生产库。

★ 外部依赖全部降级处理。Prometheus 挂了、CMDB 空了，报告照样出得来，
  只是"监控覆盖"那一段会如实写「未取到」——不能因为查不到指标就让整份报告 500。
"""

import logging
from datetime import datetime, time, timedelta

import requests
from django.core.cache import cache

from dvadmin.alert.models import AlertEvent, AlertRule
from dvadmin.cmdb.models import Server
from dvadmin.monitor.models import PrometheusSource

from .aggregate import build_report, build_scope_from_prom

logger = logging.getLogger(__name__)

PROM_TIMEOUT = 5          # Prometheus 单独设短超时：报告不能被指标查询拖死
SCOPE_CACHE_KEY = "inspection:scope:v1"
SCOPE_CACHE_TTL = 60      # 同一分钟内多人查同一天，不必重复打 Prometheus


def _day_range(day):
    """返回 [当天 00:00, 次日 00:00)。用 __lt 而非 __lte，避免边界那一秒被算两次。"""
    start = datetime.combine(day, time.min)
    return start, start + timedelta(days=1)


def fetch_events(day):
    """取某天触发的全部告警（一行 = 一次告警生命周期）。

    ★ 只用 starts_at 过滤，不看 status：
      告警恢复后 status 会从 firing 改写为 resolved，用 status 统计永远数不到已恢复的。
    """
    start, end = _day_range(day)
    return list(
        AlertEvent.objects
        .filter(starts_at__gte=start, starts_at__lt=end)
        .values("alertname", "severity", "instance",
                "starts_at", "ends_at", "status", "summary")
        .order_by("starts_at")
    )


def fetch_host_map():
    """IP → 主机名。extra_ips 是逗号分隔的多网卡地址，一并纳入。

    对应 bastion/access.py:251-273 的口径，避免两处各写一套。
    """
    mapping = {}
    try:
        for ip, hostname, extra in Server.objects.values_list("ip", "hostname", "extra_ips"):
            if ip:
                mapping[str(ip).strip()] = hostname
            for one in str(extra or "").split(","):
                one = one.strip()
                if one:
                    mapping[one] = hostname
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("巡检取 CMDB 主机映射失败，主机名列将留空：%s", exc)
    return mapping


def _fallback_scope(rules_total, note):
    return {"jobs": [], "targets_total": 0, "targets_up": 0,
            "rules_total": rules_total, "targets_down_today": 0,
            "source_desc": note}


def fetch_scope():
    """监控覆盖情况：采集任务、target 在线数、规则数。

    失败一律降级——Prometheus 不可达时，报告仍要能出，只是覆盖段写「未取到」。
    """
    rules_total = AlertRule.objects.filter(enabled=True).count()
    url = (PrometheusSource.get_url("prometheus") or "").strip()
    if not url:
        return _fallback_scope(rules_total,
                               "平台告警事件库 alert_event（未配置 Prometheus 数据源）")

    cached = cache.get(SCOPE_CACHE_KEY)
    if cached:
        return cached

    try:
        resp = requests.get(url.rstrip("/") + "/api/v1/targets", timeout=PROM_TIMEOUT)
        resp.raise_for_status()
        scope = build_scope_from_prom(resp.json(), rules_total, url=url)
        cache.set(SCOPE_CACHE_KEY, scope, SCOPE_CACHE_TTL)
        return scope
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("巡检取 Prometheus targets 失败（%s）：%s", url, exc)
        return _fallback_scope(
            rules_total,
            "平台告警事件库 alert_event（Prometheus 暂时不可达，覆盖信息未采集）")


def collect_daily(day, now=None):
    """一天的完整报告数据。前端展示与 Word/Excel 导出都走这里，保证同源。"""
    events = fetch_events(day)
    prev_events = fetch_events(day - timedelta(days=1))
    return build_report(
        day, events, prev_events,
        scope=fetch_scope(),
        host_map=fetch_host_map(),
        now=now or datetime.now(),
        extra_note="本报告统计平台告警事件库（alert_event）中的全部告警记录；"
                   "经 Alertmanager 独立 route 分流、未回调平台的告警不在此列。",
    )


def collect_range(start_day, end_day, now=None):
    """区间汇总（周报/月报复用）。按天聚合后再合并，保证与日报口径完全一致。"""
    from collections import Counter

    day = start_day
    merged, total_prev = [], 0
    days = []
    while day <= end_day:
        r = collect_daily(day, now=now)
        days.append({"date": r["date"], "total": r["total"],
                     "critical": sum(c for lab, c in r["severity_map"] if "critical" in lab),
                     "categories": r["categories"]})
        merged.append(r)
        total_prev += r["prev_total"]
        day += timedelta(days=1)

    agg_total = sum(r["total"] for r in merged)
    cat_cnt, type_cnt = Counter(), Counter()
    hourly = [0] * 24
    for r in merged:
        for c in r["categories"]:
            cat_cnt[c["name"]] += c["count"]
        for t in r["types"]:
            type_cnt[t["alertname"]] += t["count"]
        for h in r["hourly"]:
            hourly[h["hour"]] += h["count"]

    return {
        "start": start_day.strftime("%Y-%m-%d"),
        "end": end_day.strftime("%Y-%m-%d"),
        "days": len(days),
        "total": agg_total,
        "daily": days,
        "categories": [{"name": k, "count": v,
                        "ratio": round(v * 100.0 / agg_total, 1) if agg_total else 0.0}
                       for k, v in cat_cnt.most_common()],
        "types": [{"alertname": k, "count": v,
                   "ratio": round(v * 100.0 / agg_total, 1) if agg_total else 0.0}
                  for k, v in type_cnt.most_common()],
        "hourly": [{"hour": i, "count": c} for i, c in enumerate(hourly)],
    }
