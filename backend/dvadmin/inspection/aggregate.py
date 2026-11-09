# -*- coding: utf-8 -*-
"""巡检日报 · 聚合内核（纯函数，零 Django 依赖）

设计要点
--------
1. **不碰 ORM**：输入是普通 list[dict]，输出是报告结构 dict。
   好处是能在本地用假数据跑全量断言，不必连库；上线时取数层换掉即可。

2. **一行 AlertEvent = 一次告警生命周期**（firing 创建，resolved 改写同一行）。
   所以「当日告警数」只能数 starts_at 落在当日的行，不能用 status 数 ——
   一条告警恢复后 status 会变成 resolved，用 status 统计永远为 0。

3. **口径写死为 starts_at 落在当日**。跨天告警（昨晚 23:00 firing、今早 10:00 恢复）
   只算昨天那天的，今天不重复计。这样「日报告警数之和」才等于「区间告警总数」，
   不会出现 7 天日报加起来比 7 天总量还多的情况。

4. 所有派生结论（环比、峰值、集中度）都由数据算出，不含任何常量文案。

5. 真实数据的 instance 有三种形态，都要能归一：
     192.168.0.5:9107                              → 192.168.0.5
     http://192.168.201.114:5000/actuator/health   → 192.168.201.114
     lat-spl-xyfw.cn                               → lat-spl-xyfw.cn（域名原样）
"""

from datetime import datetime, timedelta

from .category import CATEGORY_ORDER, DEFAULT_CATEGORY, classify

# 级别顺序固定：严重 → 警告 → 提示。库里出现未知 severity 时归入「其他」并排在最后。
SEVERITY_ORDER = ("critical", "warning", "info")
SEVERITY_CN = {"critical": "严重", "warning": "警告", "info": "提示"}

# 报告正文里最多展示的明细行数（其余进 Excel 附表）
TOP_TYPES = 10
TOP_NODES = 10

# 明显是联调残留的规则名，报告里单列提示，不混进正式统计口径
TEST_RULE_HINTS = ("test", "测试", "demo", "tmp")


def _norm_host(instance):
    """instance → 可读主机标识。

    真实数据里 instance 可能是：
      192.168.0.163:9116 ／ http://192.168.201.114:5000/actuator/health ／ lat-spl-xyfw.cn
    这里只做「去协议 + 去端口 + 去路径」，取不到就原样返回，绝不丢信息。
    """
    if not instance:
        return "（未知实例）"
    s = str(instance).strip()
    for prefix in ("http://", "https://"):
        if s.lower().startswith(prefix):
            s = s[len(prefix):]
            break
    s = s.split("/")[0]
    if ":" in s:
        head, _, tail = s.rpartition(":")
        # 只削「主机:纯数字端口」，且主机部分不能再含冒号 ——
        # 否则 ::1 会被 rpartition 切成 ":"（IPv6 裸地址直接报废）。
        if head and tail.isdigit() and ":" not in head:
            s = head
        elif head.startswith("[") and head.endswith("]") and tail.isdigit():
            s = head.strip("[]")        # [::1]:9100 → ::1
    return s or "（未知实例）"


def _hour_of(dt):
    return dt.hour if isinstance(dt, datetime) else 0


def _hours_between(start, end):
    if not isinstance(start, datetime):
        return 0.0
    end = end if isinstance(end, datetime) else datetime.now()
    return max(round((end - start).total_seconds() / 3600.0, 1), 0.0)


def _severity_key(raw):
    key = (raw or "").strip().lower()
    return key if key in SEVERITY_ORDER else "other"


def _name_of(evt):
    return (evt.get("alertname") or "（未命名告警）").strip()


def build_report(day, events, prev_events=None, scope=None, host_map=None,
                 now=None, extra_note="", include_details=True):
    """把一天的告警聚合成报告结构。

    参数
    ----
    day        : datetime.date，巡检日
    events     : 当日告警 [{"alertname","severity","instance","starts_at","ends_at","status","summary"}]
    prev_events: 前一日告警，用于环比；None 或空表示不可比
    scope      : {"jobs": [...], "targets_total": n, "targets_up": n, "rules_total": n,
                  "targets_down_today": n, "source_desc": str}
    host_map   : {ip: hostname}，来自 CMDB；取不到就显示 instance
    now        : 报告生成时刻，用于算未恢复时长

    ★ 断言：sum(severity) == sum(types) == sum(categories) == sum(hourly) == sum(nodes) == total
      任一维度对不上，报告就自相矛盾。`verify_aggregate.py` 会逐条验。
    """
    now = now or datetime.now()
    events = list(events or [])
    prev_events = list(prev_events or [])
    scope = dict(scope or {})
    host_map = dict(host_map or {})

    total = len(events)
    prev_total = len(prev_events)

    # ---------- 1. 级别分布
    sev_raw, prev_sev = {}, {}
    for e in events:
        k = _severity_key(e.get("severity"))
        sev_raw[k] = sev_raw.get(k, 0) + 1
    for e in prev_events:
        k = _severity_key(e.get("severity"))
        prev_sev[k] = prev_sev.get(k, 0) + 1

    ordered = [k for k in SEVERITY_ORDER if sev_raw.get(k)]
    if sev_raw.get("other"):
        ordered.append("other")
    severity_map, severity_delta = [], []
    for k in ordered:
        cnt = sev_raw[k]
        label = SEVERITY_CN.get(k, "其他")
        severity_map.append(("%s（%s）" % (label, k), cnt))
        if prev_total:
            d = cnt - prev_sev.get(k, 0)
            severity_delta.append(("%+d" % d) if d else "0")
        else:
            severity_delta.append("—")

    # ---------- 2. 类型分布
    type_cnt, type_sev = {}, {}
    for e in events:
        name = _name_of(e)
        type_cnt[name] = type_cnt.get(name, 0) + 1
        type_sev.setdefault(name, {})
        k = _severity_key(e.get("severity"))
        type_sev[name][k] = type_sev[name].get(k, 0) + 1

    types = []
    for name, cnt in sorted(type_cnt.items(), key=lambda kv: (-kv[1], kv[0])):
        worst = next((k for k in SEVERITY_ORDER if type_sev[name].get(k)), "other")
        types.append({
            "alertname": name,
            "name_cn": name,          # 线上规则名本身就是中文，无需映射
            "count": cnt,
            "worst": worst,
            "worst_cn": SEVERITY_CN.get(worst, "其他"),
            "category": classify(name),
        })

    # ---------- 3. 类别分布（把流水账收敛成结论）
    cat_cnt, cat_types = {}, {}
    for t in types:
        c = t["category"]
        cat_cnt[c] = cat_cnt.get(c, 0) + t["count"]
        cat_types.setdefault(c, []).append(t)

    categories = []
    for c in list(CATEGORY_ORDER) + [k for k in cat_cnt if k not in CATEGORY_ORDER]:
        if not cat_cnt.get(c):
            continue
        sub = sorted(cat_types[c], key=lambda x: (-x["count"], x["alertname"]))
        categories.append({
            "name": c,
            "count": cat_cnt[c],
            "ratio": round(cat_cnt[c] * 100.0 / total, 1) if total else 0.0,
            "top_type": sub[0]["alertname"] if sub else "",
            "types": sub,
        })

    # ---------- 4. 时段分布
    hourly = [{"hour": h, "count": 0} for h in range(24)]
    for e in events:
        hourly[_hour_of(e.get("starts_at"))]["count"] += 1
    peak_hour = max(hourly, key=lambda x: x["count"]) if total else {"hour": 0, "count": 0}

    # ---------- 5. 节点分布
    node_cnt, node_types = {}, {}
    for e in events:
        key = _norm_host(e.get("instance"))
        node_cnt[key] = node_cnt.get(key, 0) + 1
        node_types.setdefault(key, {})
        nm = _name_of(e)
        node_types[key][nm] = node_types[key].get(nm, 0) + 1

    nodes = []
    for key, cnt in sorted(node_cnt.items(), key=lambda kv: (-kv[1], kv[0])):
        tops = sorted(node_types[key].items(), key=lambda kv: (-kv[1], kv[0]))[:2]
        nodes.append({
            "instance": key,
            "hostname": host_map.get(key, ""),
            "count": cnt,
            "top_type": "、".join("%s（%d）" % (n, c) for n, c in tops),
        })

    # ---------- 6. 未恢复
    unresolved = []
    for e in events:
        if (e.get("status") or "").strip().lower() != "firing":
            continue
        st = e.get("starts_at")
        unresolved.append({
            "alertname_cn": _name_of(e),
            "instance": _norm_host(e.get("instance")),
            "severity_cn": SEVERITY_CN.get(_severity_key(e.get("severity")), "其他"),
            "starts_at": st.strftime("%Y-%m-%d %H:%M") if isinstance(st, datetime) else "—",
            "duration_hours": _hours_between(st, now),
        })
    unresolved.sort(key=lambda x: -x["duration_hours"])

    # ---------- 7. 监控覆盖
    t_total = int(scope.get("targets_total") or 0)
    t_up = int(scope.get("targets_up") or 0)
    jobs = scope.get("jobs") or []
    coverage = [
        {"item": "Prometheus 采集任务", "expect": "%d 个" % len(jobs),
         "actual": "%d 个已加载" % len(jobs), "result": "正常" if jobs else "未取到"},
        {"item": "监控目标（target）", "expect": "%d 个" % t_total,
         "actual": "%d 个在线" % t_up,
         "result": "正常（在线率 %.1f%%）" % (t_up * 100.0 / t_total) if t_total and t_up == t_total
         else ("需关注（%d 个不可达）" % (t_total - t_up) if t_total else "未取到")},
        {"item": "告警规则", "expect": "%d 条" % int(scope.get("rules_total") or 0),
         "actual": "%d 条已加载" % int(scope.get("rules_total") or 0),
         "result": "正常" if scope.get("rules_total") else "未取到"},
        {"item": "告警事件入库", "expect": "—", "actual": "%d 条" % total, "result": "正常"},
    ]
    down = int(scope.get("targets_down_today") or 0)
    if down:
        coverage.append({"item": "当日 target 掉线", "expect": "0 次",
                         "actual": "%d 次" % down,
                         "result": "需关注（请核实是否已恢复）"})

    # ---------- 8. 数据质量提示（口径透明，避免"数字看着对其实有坑"）
    data_notes = []
    test_cnt = sum(c for n, c in type_cnt.items()
                   if any(h in n.lower() for h in TEST_RULE_HINTS))
    if test_cnt:
        data_notes.append("当日有 %d 条告警来自疑似测试规则（%s），已计入总量，"
                          "如需排除请在告警规则中停用对应规则。"
                          % (test_cnt, "、".join(n for n in type_cnt
                                                if any(h in n.lower() for h in TEST_RULE_HINTS))))
    no_host = sum(1 for n in nodes if not n["hostname"])
    if no_host and host_map:
        data_notes.append("有 %d 个告警来源未能匹配 CMDB 主机（多为域名或 URL 形式的探测目标），"
                          "报告中按原始实例名展示。" % no_host)

    # ---------- 9. 明细（Excel 附表用，直接来自原始事件，绝不按汇总反推）
    details = []
    if include_details:
        for e in events:
            st, en = e.get("starts_at"), e.get("ends_at")
            host = _norm_host(e.get("instance"))
            is_open = (e.get("status") or "").strip().lower() == "firing"
            details.append({
                "starts_at": st.strftime("%Y-%m-%d %H:%M:%S") if isinstance(st, datetime) else "—",
                "alertname": _name_of(e),
                "category": classify(_name_of(e)),
                "severity_cn": SEVERITY_CN.get(_severity_key(e.get("severity")), "其他"),
                "instance": host,
                "hostname": host_map.get(host, ""),
                "status": "未恢复" if is_open else "已恢复",
                "ends_at": en.strftime("%Y-%m-%d %H:%M:%S") if isinstance(en, datetime) else "—",
                "duration": "进行中" if is_open else "%.1f 小时" % _hours_between(st, en),
            })

    result = {
        "date": day.strftime("%Y-%m-%d"),
        "date_cn": "%d 年 %02d 月 %02d 日" % (day.year, day.month, day.day),
        "weekday": "周" + "一二三四五六日"[day.weekday()],
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "scope": {
            "jobs": jobs,
            "targets_total": t_total,
            "targets_up": t_up,
            "rules_total": int(scope.get("rules_total") or 0),
        },
        "total": total,
        "prev_total": prev_total,
        "severity_map": severity_map,
        # ★ 渲染层要的是「按 key 取值」而不是「按展示文案取值」。
        #   severity_map 的键是「严重（critical）」这种展示串，直接 dict() 后
        #   .get("critical") 恒为 0 —— 曾让报告写出「严重 0 条」而数据里明明有 3 条。
        "severity_counts": {k: sev_raw.get(k, 0) for k in SEVERITY_ORDER},
        "severity_delta": severity_delta,
        "types": types,
        "type_total_kinds": len(types),
        "categories": categories,
        "hourly": hourly,
        "peak_hour": peak_hour["hour"],
        "peak_count": peak_hour["count"],
        "nodes": nodes,
        "coverage": coverage,
        "unresolved": unresolved,
        "data_notes": data_notes,
        "extra_note": extra_note,
        "caliber": "按告警触发时间（starts_at）落在当日 00:00—24:00 内统计，"
                   "一行代表一次告警生命周期",
        "source_desc": scope.get("source_desc") or "平台告警事件库 alert_event",
        "top_types": types[:TOP_TYPES],
        "top_nodes": nodes[:TOP_NODES],
        "details": details,
    }

    # 结论与建议在这里一次性算好，页面和 Word/Excel 共用同一份文案。
    # 局部 import 避免与 narrative 形成循环依赖（narrative 只吃结构、不碰 ORM）。
    from .narrative import build_findings, build_suggestions
    result["findings"] = build_findings(result)
    result["suggestions"] = build_suggestions(result)
    return result


def build_scope_from_prom(targets, rules_total, down_today=0, url=""):
    """从 Prometheus /api/v1/targets 的返回拼 scope。"""
    active = (targets or {}).get("data", {}).get("activeTargets", []) or []
    jobs = sorted({t.get("labels", {}).get("job", "") for t in active} - {""})
    up = sum(1 for t in active if (t.get("health") or "").lower() == "up")
    return {
        "jobs": jobs,
        "targets_total": len(active),
        "targets_up": up,
        "rules_total": rules_total,
        "targets_down_today": down_today,
        "source_desc": ("Prometheus（%s）指标 + 平台告警事件库 alert_event" % url) if url
                       else "平台告警事件库 alert_event",
    }
