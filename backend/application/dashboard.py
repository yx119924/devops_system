# -*- coding: utf-8 -*-
"""
Dashboard 聚合统计接口：首页智能化数据源
一次返回：服务器统计(含在线率) / 活跃告警(含级别分布) / 会话统计 / 命令下发统计 /
         高危命令统计 / Jenkins 概览 / 7 天告警趋势 / 最近告警 / 最近会话 / 操作动态流

权限说明（重要）
----------------
本接口是首页脚手架，**没有**对应的 MenuButton，所以不能用 `CustomPermission`
（它按 URL+method 反查按钮权限，查不到就 403）。它是裸 `@api_view`，也就**不会**
经过 `filter_queryset`，因此在改造前它是"任何登录用户都能拿到全系统统计"的泄漏点。

现在按两条独立的线裁剪：

1. **模块可见性（菜单级）** —— `user_menu_paths()` 拿到当前用户可见的菜单
   `web_path` 集合，逐块判断"这个人能不能进这个页面"。没有权限的板块直接返回空/0，
   前端据此隐藏面板与卡片，做到"首页显示什么"和"点进去能看到什么"一致，
   不会再出现"首页有数据、点过去 404"。
2. **数据范围（资产级）** —— 有权限的板块也不是无脑全表：服务器、会话、下发、
   高危命令都按 `ServerGrant` 资产授权的口径统计，与各自列表页的
   `get_queryset()` 完全一致（口径统一在 `dvadmin/bastion/access.py`）。
   所以开发看到的"服务器在线率"就是他被授权的那几台，而不是全公司服务器。

额外下发 `menus`（当前用户可见路径数组，超管为 null 表示不受限）与 `access`
（各板块布尔开关）给前端，避免前端再发一次请求、也避免前后端两套判定跑偏。
"""
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from dvadmin.bastion.access import (
    is_asset_admin,
    restrict_command_log,
    visible_server_ids,
)
from dvadmin.utils.json_response import DetailResponse
from dvadmin.utils.perm_helper import has_any_path, user_menu_paths


def _fmt(dt):
    """datetime -> 'YYYY-MM-DD HH:MM:SS' 字符串（naive datetime 直接格式化）"""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """首页统计聚合：/api/dashboard/stats/"""
    from dvadmin.alert.models import AlertEvent
    from dvadmin.bastion.models import CommandDispatch, CommandLog, SessionRecord
    from dvadmin.cmdb.models import Server
    from dvadmin.jenkins.models import JenkinsServer

    user = request.user
    now = timezone.now()
    today = now.date()

    # ---------------- 0. 模块可见性 ----------------
    paths = user_menu_paths(user)
    vis = {
        "server": has_any_path(paths, "/server"),
        "alerts": has_any_path(paths, "/alertEvent", "/alertManage"),
        "sessions": has_any_path(paths, "/session"),
        "dispatch": has_any_path(paths, "/dispatch"),
        "danger": has_any_path(paths, "/commandLog"),
        "jenkins": has_any_path(paths, "/jenkins-job", "/jenkins-server"),
        "audit": has_any_path(paths, "/operationLog", "/loginLog"),
        "logs": has_any_path(paths, "/logSearch", "/logSource"),
        "grafana": has_any_path(paths, "/grafana"),
        "query": has_any_path(paths, "/query", "/source"),
    }

    asset_admin = is_asset_admin(user)

    # 1. 服务器统计（含在线率）——按资产授权口径
    if vis["server"]:
        server_qs = Server.objects.all()
        allowed_ids = visible_server_ids(user)
        if allowed_ids is not None:
            server_qs = server_qs.filter(pk__in=allowed_ids)
        server_total = server_qs.count()
        server_online = server_qs.filter(status="online").count()
        server_offline = server_qs.filter(status="offline").count()
        server_maintenance = server_qs.filter(status="maintenance").count()
    else:
        server_total = server_online = server_offline = server_maintenance = 0
    online_rate = round(server_online * 100.0 / server_total, 1) if server_total else 0.0

    # 2. 告警统计（活跃 + 近 7 天级别分布）——告警是"事件流"，有菜单即看全量
    start = now - timedelta(days=7)
    if vis["alerts"]:
        active_alerts = AlertEvent.objects.filter(status="firing").count()
        week_events = AlertEvent.objects.filter(starts_at__gte=start)
        week_total = week_events.count()
        critical_count = week_events.filter(severity="critical").count()
        warning_count = week_events.filter(severity="warning").count()
        info_count = week_events.filter(severity="info").count()
    else:
        active_alerts = week_total = 0
        critical_count = warning_count = info_count = 0

    # 3. 会话统计——与 SessionRecordViewSet.get_queryset 同口径
    session_qs = SessionRecord.objects.all()
    if not asset_admin:
        session_qs = session_qs.filter(creator=user)
    if vis["sessions"]:
        online_sessions = session_qs.filter(status="active").count()
        today_sessions = session_qs.filter(start_time__date=today).count()
    else:
        online_sessions = today_sessions = 0

    # 4. 命令下发统计（今日）——与 CommandDispatchViewSet.get_queryset 同口径
    dispatch_qs = CommandDispatch.objects.all()
    if not asset_admin:
        dispatch_qs = dispatch_qs.filter(creator=user)
    if vis["dispatch"]:
        today_dispatches = dispatch_qs.filter(create_datetime__date=today)
        dispatch_today = today_dispatches.count()
        dispatch_success = today_dispatches.filter(status="success").count()
        dispatch_failed = today_dispatches.filter(status__in=["failed", "partial"]).count()
    else:
        dispatch_today = dispatch_success = dispatch_failed = 0

    # 5. 高危命令统计（今日）——与 CommandLogViewSet.get_queryset 同口径
    if vis["danger"]:
        danger_qs = CommandLog.objects.filter(is_dangerous=True, timestamp__date=today)
        if not asset_admin:
            danger_qs = restrict_command_log(danger_qs, user)
        danger_commands = danger_qs.count()
    else:
        danger_commands = 0

    # 6. Jenkins 概览（本地配置，不实时调 Jenkins 避免拖慢首页）
    jenkins_count = JenkinsServer.objects.filter(status=1).count() if vis["jenkins"] else 0

    # 7. 7 天告警趋势（按 starts_at 日期分组）
    trend = []
    if vis["alerts"]:
        trend_qs = (
            AlertEvent.objects
            .filter(starts_at__gte=start)
            .annotate(day=TruncDate("starts_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        trend_map = {row["day"]: row["count"] for row in trend_qs}
    else:
        trend_map = {}

    # 生成连续 7 天序列（含今天），无数据的日期补 0
    for i in range(6, -1, -1):
        d = (now - timedelta(days=i)).date()
        trend.append({
            "date": d.strftime("%m-%d"),
            "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][d.weekday()],
            "count": trend_map.get(d, 0),
        })

    # 8. 最近告警（top 5，按开始时间倒序）
    if vis["alerts"]:
        recent_alerts = [
            {
                "alertname": a.alertname,
                "severity": a.severity,
                "status": a.status,
                "instance": a.instance or "",
                "summary": a.summary or "",
                "starts_at": _fmt(a.starts_at),
            }
            for a in AlertEvent.objects.order_by("-starts_at")[:5]
        ]
    else:
        recent_alerts = []

    # 9. 最近会话（top 5，按开始时间倒序）
    if vis["sessions"]:
        recent_sessions = [
            {
                "username": s.username or "",
                "ip": s.ip or "",
                "server_name": s.server.hostname if s.server else "",
                "status": s.status,
                "start_time": _fmt(s.start_time),
                "duration": s.duration or 0,
            }
            for s in session_qs.select_related("server").order_by("-start_time")[:5]
        ]
    else:
        recent_sessions = []

    # 10. 操作动态流（登录 + 操作日志合并，最近 8 条）——系统审计，有菜单才给
    activities = _build_activities(8) if vis["audit"] else []

    data = {
        "server": {
            "total": server_total,
            "online": server_online,
            "offline": server_offline,
            "maintenance": server_maintenance,
            "online_rate": online_rate,
        },
        "alerts": {
            "active": active_alerts,
            "week_total": week_total,
            "critical": critical_count,
            "warning": warning_count,
            "info": info_count,
        },
        "sessions": {
            "active": online_sessions,
            "today": today_sessions,
        },
        "dispatch": {
            "today": dispatch_today,
            "success": dispatch_success,
            "failed": dispatch_failed,
        },
        "danger": {
            "today_commands": danger_commands,
        },
        "jenkins": {
            "server_count": jenkins_count,
        },
        "trend": trend,
        "recent_alerts": recent_alerts,
        "recent_sessions": recent_sessions,
        "activities": activities,
        # 前端据此裁剪快捷入口 / 统计卡片 / 面板；None = 不受限（超管）
        "menus": sorted(paths) if paths is not None else None,
        "access": vis,
    }
    return DetailResponse(data=data, msg="获取成功")


def _build_activities(limit=8):
    """合并登录日志 + 操作日志，按时间倒序取最近 N 条，供首页操作动态流。
    日志表可能为空或字段存在差异，全程 try/except 兜底，避免首页 500。
    """
    items = []
    try:
        from dvadmin.system.models import LoginLog, OperationLog
    except Exception:
        return []

    # 登录日志
    try:
        for lg in LoginLog.objects.order_by("-create_datetime")[:limit]:
            items.append({
                "type": "login",
                "text": "%s 登录系统" % (lg.username or "未知用户"),
                "detail": "%s · %s" % (lg.ip or "-", lg.browser or "-"),
                "time": _fmt(lg.create_datetime),
                "ts": lg.create_datetime,
            })
    except Exception:
        pass

    # 操作日志
    try:
        for op in OperationLog.objects.select_related("creator").order_by("-create_datetime")[:limit]:
            user = ""
            try:
                user = op.creator.username if op.creator else ""
            except Exception:
                user = ""
            text = "%s %s" % (op.request_modular or "系统操作", op.request_method or "")
            items.append({
                "type": "op",
                "text": "%s · %s" % (user or "未知用户", text.strip()),
                "detail": "%s · 响应 %s" % (op.request_ip or "-", op.response_code or "-"),
                "time": _fmt(op.create_datetime),
                "ts": op.create_datetime,
            })
    except Exception:
        pass

    # 按时间倒序排序，取前 limit 条
    items.sort(key=lambda x: x["ts"], reverse=True)
    return items[:limit]
