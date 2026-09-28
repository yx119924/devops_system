# -*- coding: utf-8 -*-
"""
告警规则同步服务：把平台告警规则生成 Prometheus alerting rules 并热加载
"""
import os

import requests
import yaml

# Django 容器内路径（backend 挂载到 /backend），宿主机对应 backend/dvadmin/alert/rules
RULES_DIR = "/backend/dvadmin/alert/rules"
RULES_FILE = os.path.join(RULES_DIR, "devops_rules.yml")

# 注意：Prometheus / Alertmanager 地址不再硬编码，统一从「数据源管理」页读取
# （dvadmin.monitor.models.PrometheusSource，source_type=prometheus / alertmanager）
# 部署后请在 监控告警 → 数据源管理 页面添加对应记录，无需改代码。


def get_monitor_url(source_type):
    """从数据源表取地址（prometheus / alertmanager），无配置时返回空串。

    延迟 import，避免 Django app 未就绪时模块级查询数据库。
    """
    from dvadmin.monitor.models import PrometheusSource

    return PrometheusSource.get_url(source_type)


def _require_url(source_type, label):
    """取地址并在缺失时抛出明确错误，避免裸 ConnectionError 难以排查。"""
    url = get_monitor_url(source_type)
    if not url:
        raise RuntimeError(
            f"未配置{label}地址，请到「监控告警 → 数据源管理」页面添加一条"
            f" source_type={source_type} 的启用记录"
        )
    return url


def generate_rules():
    """遍历所有启用规则，生成 Prometheus alerting rules yaml 文件，返回文件路径"""
    from dvadmin.alert.models import AlertRule

    rules = []
    for rule in AlertRule.objects.filter(enabled=True).order_by("id"):
        rules.append({
            "alert": rule.name,
            "expr": rule.expr,
            "for": rule.duration or "1m",
            "labels": {"severity": rule.severity},
            "annotations": {
                "summary": rule.summary or rule.name,
                "description": rule.description or "",
            },
        })

    data = {
        "groups": [
            {"name": "devops_alert_rules", "rules": rules},
        ]
    }
    os.makedirs(RULES_DIR, exist_ok=True)
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
    return RULES_FILE


def reload_prometheus():
    """热加载 Prometheus 规则（需要 Prometheus 开启 --web.enable-lifecycle）"""
    url = _require_url("prometheus", "Prometheus")
    resp = requests.post(f"{url}/-/reload", timeout=10)
    return resp.status_code == 200


def sync_rules():
    """生成规则文件并热加载 Prometheus，返回 (文件路径, reload是否成功)"""
    path = generate_rules()
    ok = reload_prometheus()
    return path, ok


def _fmt_prom_duration(value):
    """Prometheus /api/v1/rules 的 for 字段可能是 int(秒) 或 string('5m') / 0，规范化字符串。"""
    if value is None:
        return "0s"
    if isinstance(value, (int, float)):
        return "0s" if int(value) == 0 else f"{int(value)}s"
    s = str(value).strip()
    return s or "0s"


def fetch_prometheus_rules():
    """从 Prometheus /api/v1/rules 拉取所有已加载的 alerting 规则。
    返回 (rule_groups, error_str)：
      rule_groups 形如 [{"name": "group", "file": "...", "rules": [
        {"alert": "Name", "expr": "up == 0", "for": "1m",
         "severity": "warning", "summary": "...", "description": "...",
         "state": "inactive|pending|firing",
         "source_file": "...", "source_group": "..."},
        ...
      ]}]
    出错时 rule_groups=None，error_str 为人类可读错误。
    """
    from dvadmin.alert.models import SEVERITY_CHOICES
    valid_severity = dict(SEVERITY_CHOICES)
    try:
        url = _require_url("prometheus", "Prometheus")
    except RuntimeError as e:
        return None, str(e)
    try:
        resp = requests.get(f"{url}/api/v1/rules", timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.RequestException as e:
        return None, f"调用 Prometheus /api/v1/rules 失败：{e}"
    except ValueError as e:
        return None, f"Prometheus 响应非 JSON：{e}"
    if payload.get("status") != "success":
        return None, f"Prometheus 返回错误：{payload.get('error', payload.get('errorType', '未知错误'))}"

    groups_out = []
    for g in (payload.get("data", {}).get("groups") or []):
        gname = g.get("name", "")
        gfile = g.get("file", "")
        rules_out = []
        for r in (g.get("rules") or []):
            if r.get("type") != "alerting":
                continue  # 跳过 recording rules
            labels = r.get("labels") or {}
            annotations = r.get("annotations") or {}
            severity = (labels.get("severity") or "warning").lower()
            if severity not in valid_severity:
                severity = "warning"
            rules_out.append({
                "alert": r.get("name", ""),
                "expr": r.get("query", ""),
                "for": _fmt_prom_duration(r.get("for")),
                "severity": severity,
                "summary": annotations.get("summary", ""),
                "description": annotations.get("description", ""),
                "state": r.get("state", "inactive"),
                "source_file": gfile,
                "source_group": gname,
            })
        groups_out.append({"name": gname, "file": gfile, "rules": rules_out})
    return groups_out, None


def sync_rules_from_prometheus():
    """从 Prometheus 反向同步 alerting 规则到 XwOps 库（可逆：仅改 XwOps 库，不动 Prom 资源）。

    策略：
    - 按 alert 名匹配 XwOps 库 AlertRule
    - 命中：更新 expr/duration/severity/summary/description，**保留 group/template/enabled**（不覆盖用户配置）
    - 未命中：新建，默认启用（平台纳管即启用）。Prom 的 state 是运行态（是否正在触发），与平台是否纳管无关；已存在规则的 enabled 由用户手动控制，同步不覆盖
    - 任何一步出错不中断，记录到 errors 列表

    返回 {"created":[...], "updated":[...], "skipped":[...], "errors":[...], "total_in_prom": int}
    """
    from dvadmin.alert.models import AlertRule

    groups, err = fetch_prometheus_rules()
    if err:
        raise RuntimeError(err)

    result = {"created": [], "updated": [], "skipped": [], "errors": [], "total_in_prom": 0}

    for g in groups:
        for r in g["rules"]:
            result["total_in_prom"] += 1
            name = r["alert"]
            if not name:
                result["errors"].append({"rule": "(无名)", "reason": "缺少 alert 名"})
                continue
            try:
                existing = AlertRule.objects.filter(name=name).first()
                if existing:
                    existing.expr = r["expr"]
                    existing.duration = r["for"]
                    existing.severity = r["severity"]
                    existing.summary = r["summary"] or None
                    existing.description = r["description"] or None
                    existing.save(update_fields=["expr", "duration", "severity",
                                                 "summary", "description"])
                    result["updated"].append({
                        "name": name,
                        "source_group": r["source_group"],
                        "source_file": r["source_file"],
                        "state": r["state"],
                    })
                else:
                    AlertRule.objects.create(
                        name=name,
                        expr=r["expr"],
                        duration=r["for"],
                        severity=r["severity"],
                        summary=r["summary"] or None,
                        description=r["description"] or None,
                        enabled=True,  # 平台纳管即启用；Prom 的 state 是运行态，不决定平台启用
                    )
                    result["created"].append({
                        "name": name,
                        "source_group": r["source_group"],
                        "source_file": r["source_file"],
                        "state": r["state"],
                    })
            except Exception as e:
                result["errors"].append({"rule": name, "reason": str(e)})
    return result


def query_active_alerts():
    """查询 Alertmanager 当前活跃告警"""
    url = _require_url("alertmanager", "Alertmanager")
    resp = requests.get(f"{url}/api/v2/alerts", timeout=10)
    resp.raise_for_status()
    return resp.json()


def _fmt_local_ts(value, fmt="%Y-%m-%d %H:%M:%S"):
    """把 Alertmanager 的 RFC3339(UTC) 时间串格式化成 TIME_ZONE 本地时间字符串。

    · 空值 / 解析失败 → 返回 ""
    · AM 对「尚未结束」的告警会返回 Go 零值 0001-01-01T00:00:00Z → 也返回 ""
    """
    if not value:
        return ""
    try:
        from datetime import datetime

        from django.utils import timezone

        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.year <= 1:
            return ""
        if timezone.is_aware(dt):
            dt = timezone.localtime(dt)
        return dt.strftime(fmt)
    except Exception:
        return str(value)


def render_alerts(payload):
    """把 Alertmanager webhook payload 渲染成纯文本（飞书/钉钉/企微/邮件通用）。

    对每条 alert：按 alertname 匹配告警规则，命中后用规则绑定的模板（AlertRule.template）
    渲染；规则未绑定模板时用 is_default=True 的兜底模板；都没有时回退到内置默认格式。
    """
    from dvadmin.alert.rendering import render_template

    from dvadmin.alert.models import AlertRule, AlertTemplate

    status = payload.get("status", "firing")
    alerts = payload.get("alerts", [])
    if not alerts:
        return f"[DevOps 告警] 0 条 {status}\n(空)"

    # 预加载涉及的规则（含绑定模板）与兜底模板，避免 N+1 查询
    alertnames = {a.get("labels", {}).get("alertname") for a in alerts if a.get("labels", {}).get("alertname")}
    rules_by_name = {
        r.name: r
        for r in AlertRule.objects.filter(enabled=True, name__in=alertnames).select_related("template")
    }
    default_tpl = AlertTemplate.objects.filter(enabled=True, is_default=True).first()


    def _default_block(a):
        labels = a.get("labels", {}) or {}
        annotations = a.get("annotations", {}) or {}
        severity = (labels.get("severity") or "info").upper()
        name = labels.get("alertname", "(未知告警)")
        a_status = a.get("status", "firing")
        summary = annotations.get("summary", "")
        desc = annotations.get("description", "")
        instance = labels.get("instance", "")
        starts = _fmt_local_ts(a.get("startsAt"))
        block = f"【{severity}】{name} ({a_status})"
        if summary:
            block += f"\n  摘要：{summary}"
        if desc:
            block += f"\n  描述：{desc}"
        if instance:
            block += f"\n  实例：{instance}"
        if starts:
            block += f"\n  起始：{starts}"
        return block

    blocks = []
    for a in alerts:
        labels = a.get("labels", {}) or {}
        alertname = labels.get("alertname", "")
        rule = rules_by_name.get(alertname)
        tpl = (rule.template if rule and rule.template_id else None) or default_tpl
        if tpl:
            annotations = a.get("annotations", {}) or {}
            ctx = {
                "alertname": alertname,
                "severity": labels.get("severity", "info"),
                "status": a.get("status", "firing"),
                "instance": labels.get("instance", ""),
                "summary": annotations.get("summary", ""),
                "description": annotations.get("description", ""),
                "startsAt": _fmt_local_ts(a.get("startsAt")),
                "endsAt": _fmt_local_ts(a.get("endsAt")),
                "value": str(a.get("value", "") or ""),
                "labels": labels,
            }
            try:
                blocks.append(render_template(tpl.body, ctx))
                continue
            except Exception:
                # 模板渲染失败时降级到默认格式
                pass
        blocks.append(_default_block(a))

    header = f"[DevOps 告警] {len(alerts)} 条 {status}"
    return header + "\n\n" + "\n\n".join(blocks)


def _clip_utf8(text, limit):
    """按 UTF-8 字节数截断，避免超出渠道上限（企微 markdown 4096 字节）导致整条消息发不出去。"""
    raw = str(text or "").encode("utf-8")
    if len(raw) <= limit:
        return text
    return raw[:limit].decode("utf-8", "ignore") + "\n\n…（内容过长已截断，完整告警请到平台查看）"


def send_feishu(webhook_url, content):
    """调用飞书自定义机器人 webhook 发送文本消息"""
    msg = {"msg_type": "text", "content": {"text": content}}
    resp = requests.post(webhook_url, json=msg, timeout=10)
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
    ok = resp.status_code == 200 and (data.get("StatusCode") == 0 or data.get("code") == 0)
    return ok, data


def send_dingtalk(webhook_url, content, secret=None):
    """调用钉钉自定义机器人 webhook 发送文本消息（支持加签）"""
    import base64
    import hashlib
    import hmac
    import time
    import urllib.parse

    url = webhook_url
    if secret:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"),
                             digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
    msg = {"msgtype": "text", "text": {"content": content}}
    resp = requests.post(url, json=msg, timeout=10)
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
    ok = data.get("errcode") == 0
    return ok, data


def send_wechat(webhook_url, content):
    """调用企业微信群机器人 webhook 发送 markdown 消息（支持标题与加粗）"""
    msg = {"msgtype": "markdown", "markdown": {"content": _clip_utf8(content, 4000)}}
    resp = requests.post(webhook_url, json=msg, timeout=10)
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
    ok = data.get("errcode") == 0
    return ok, data


def send_email(cfg, content):
    """通过 SMTP 发送告警邮件。cfg 含 smtp_host/smtp_port/username/password/to_addrs"""
    import smtplib
    from email.header import Header
    from email.mime.text import MIMEText

    host = cfg.get("smtp_host")
    port = int(cfg.get("smtp_port") or 465)
    username = cfg.get("username")
    password = cfg.get("password")
    to_addrs = cfg.get("to_addrs") or []
    if not host or not username or not to_addrs:
        return False, "缺少 smtp_host/username/to_addrs"

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = Header("[DevOps 告警] 告警通知", "utf-8")
    msg["From"] = username
    msg["To"] = ", ".join(to_addrs)

    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=10)
    else:
        server = smtplib.SMTP(host, port, timeout=10)
        server.starttls()
    try:
        server.login(username, password)
        server.sendmail(username, to_addrs, msg.as_string())
    finally:
        server.quit()
    return True, {"sent": len(to_addrs)}


def persist_alerts(payload):
    """把 Alertmanager webhook payload 持久化到 AlertEvent 表。

    firing：按 fingerprint upsert（已存在 firing 则更新，否则新建）。
    resolved：按 fingerprint 找到对应 firing 记录，置为 resolved 并写 ends_at；
             若找不到对应 firing 记录（如遗漏），也补录一条 resolved。
    返回 (created_count, updated_count)。
    """
    from datetime import datetime

    from django.utils import timezone

    from dvadmin.alert.models import AlertEvent, SEVERITY_CHOICES

    alerts = payload.get("alerts", [])
    created = 0
    updated = 0
    valid_severity = dict(SEVERITY_CHOICES)

    def _parse_ts(value):
        if not value:
            return None
        try:
            # Alertmanager 返回 RFC3339（UTC），如 2026-08-31T06:00:00.000Z
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if timezone.is_aware(dt):
                from django.conf import settings
                if not settings.USE_TZ:
                    dt = timezone.make_naive(timezone.localtime(dt))
            return dt
        except Exception:
            return None

    for a in alerts:
        labels = a.get("labels", {}) or {}
        annotations = a.get("annotations", {}) or {}
        fingerprint = a.get("fingerprint") or ""
        alertname = labels.get("alertname", "")
        status = a.get("status", "firing")
        severity = labels.get("severity", "warning")
        if severity not in valid_severity:
            severity = "warning"
        instance = labels.get("instance", "")
        summary = annotations.get("summary", "") or alertname
        description = annotations.get("description", "")
        starts_at = _parse_ts(a.get("startsAt"))
        ends_at = _parse_ts(a.get("endsAt"))

        if not fingerprint:
            # 无指纹时退化为按 alertname+instance 查找
            event = AlertEvent.objects.filter(alertname=alertname, instance=instance, status="firing").first()
        else:
            event = AlertEvent.objects.filter(fingerprint=fingerprint, status="firing").first()

        if status == "firing":
            if event:
                event.severity = severity
                event.summary = summary
                event.description = description
                event.labels = labels
                event.starts_at = starts_at or event.starts_at
                event.save(update_fields=["severity", "summary", "description", "labels", "starts_at"])
                updated += 1
            else:
                AlertEvent.objects.create(
                    fingerprint=fingerprint, alertname=alertname, status="firing",
                    severity=severity, instance=instance, summary=summary,
                    description=description, labels=labels, starts_at=starts_at, ends_at=None,
                )
                created += 1
        else:  # resolved
            if not event and fingerprint and starts_at:
                event = AlertEvent.objects.filter(fingerprint=fingerprint, status='resolved', starts_at=starts_at).first()
            if event:
                event.status = "resolved"
                event.ends_at = ends_at or timezone.now()
                event.save(update_fields=["status", "ends_at"])
                updated += 1
            else:
                AlertEvent.objects.create(
                    fingerprint=fingerprint, alertname=alertname, status="resolved",
                    severity=severity, instance=instance, summary=summary,
                    description=description, labels=labels,
                    starts_at=starts_at or ends_at or timezone.now(), ends_at=ends_at,
                )
                created += 1
    return created, updated


def dispatch_alerts(payload):
    """把 Alertmanager webhook payload 分发到对应渠道（按群组路由）
    规则有 group 时只发 group.channels；规则没 group 时发全部启用渠道（向后兼容）。"""
    from dvadmin.alert.models import AlertGroup, AlertRule, NotifyChannel

    alerts = payload.get('alerts', [])
    names = {a.get('labels', {}).get('alertname', '') for a in alerts}
    rules = {r.name: r for r in AlertRule.objects.filter(name__in=names).select_related('group')}
    channels = list(NotifyChannel.objects.filter(enabled=True))
    routed = {ch.id: [] for ch in channels}
    for alert in alerts:
        rule = rules.get(alert.get('labels', {}).get('alertname'))
        if rule and not rule.enabled:
            continue
        if rule and rule.group_id:
            ids = rule.group.channels.values_list('id', flat=True) if rule.group.enabled else []
        else:
            ids = routed.keys()
        for channel_id in ids:
            if channel_id in routed:
                routed[channel_id].append(alert)
    route_note = '按每条告警所属群组分发'

    results = []
    for ch in channels:
        if not routed[ch.id]:
            continue
        content = render_alerts({**payload, 'alerts': routed[ch.id]})
        from dvadmin.alert.secrets import decrypt_config
        try:
            cfg = decrypt_config(ch.config)
        except Exception:
            results.append({'channel': ch.name, 'ok': False, 'error': '渠道密钥读取失败'})
            continue
        if not isinstance(cfg, dict):
            results.append({
                "channel": ch.name, "type": ch.type, "ok": False,
                "reason": f"config 类型错误（{type(cfg).__name__}），应为 JSON 对象，请在通知渠道页编辑修正",
            })
            continue
        webhook = cfg.get("webhook", "")
        try:
            if ch.type == "feishu":
                if not webhook:
                    results.append({"channel": ch.name, "type": ch.type, "ok": False, "reason": "缺少 webhook"})
                    continue
                ok, resp = send_feishu(webhook, content)
            elif ch.type == "dingtalk":
                if not webhook:
                    results.append({"channel": ch.name, "type": ch.type, "ok": False, "reason": "缺少 webhook"})
                    continue
                ok, resp = send_dingtalk(webhook, content, cfg.get("secret"))
            elif ch.type == "wechat":
                if not webhook:
                    results.append({"channel": ch.name, "type": ch.type, "ok": False, "reason": "缺少 webhook"})
                    continue
                ok, resp = send_wechat(webhook, content)
            elif ch.type == "email":
                ok, resp = send_email(cfg, content)
            else:
                results.append({"channel": ch.name, "type": ch.type, "ok": False, "reason": f"未知渠道类型 {ch.type}"})
                continue
            results.append({"channel": ch.name, "type": ch.type, "ok": ok})
        except Exception as e:
            results.append({"channel": ch.name, "type": ch.type, "ok": False, "error": '发送失败，请检查配置和网络'})
    return route_note, results
