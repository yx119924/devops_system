# -*- coding: utf-8 -*-
"""
告警管理视图：活跃告警 + Alertmanager 静默 + 路由收敛
这些是 Alertmanager 的代理接口，数据不落本地库，实时透传。
"""
from datetime import datetime, timedelta, timezone

import requests
import yaml
from rest_framework.decorators import api_view

from dvadmin.alert.services import ALERTMANAGER_URL
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

AM_ALERTS = f"{ALERTMANAGER_URL}/api/v2/alerts"
AM_SILENCES = f"{ALERTMANAGER_URL}/api/v2/silences"
AM_STATUS = f"{ALERTMANAGER_URL}/api/v2/status"


@api_view(["GET"])
def active_alerts(request):
    """活跃告警列表：透传 Alertmanager /api/v2/alerts，规整为前端易用结构"""
    try:
        resp = requests.get(AM_ALERTS, timeout=10)
        resp.raise_for_status()
        items = []
        for a in resp.json():
            labels = a.get("labels", {}) or {}
            annotations = a.get("annotations", {}) or {}
            status = a.get("status", {}) or {}
            items.append({
                "fingerprint": a.get("fingerprint"),
                "alertname": labels.get("alertname"),
                "severity": labels.get("severity"),
                "instance": labels.get("instance"),
                "job": labels.get("job"),
                "state": status.get("state"),
                "silenced": len(status.get("silencedBy", [])) > 0,
                "inhibited": len(status.get("inhibitedBy", [])) > 0,
                "startsAt": a.get("startsAt"),
                "endsAt": a.get("endsAt"),
                "summary": annotations.get("summary"),
                "description": annotations.get("description"),
                "labels": labels,
                "receivers": [r.get("name") for r in (a.get("receivers") or [])],
            })
        return DetailResponse(data=items, msg="获取成功")
    except requests.exceptions.RequestException as e:
        return ErrorResponse(msg=f"查询活跃告警失败：{e}")
    except Exception as e:
        return ErrorResponse(msg=f"查询活跃告警失败：{e}")


@api_view(["GET", "POST"])
def silence_list_create(request):
    """静默管理：GET 返回静默列表；POST 创建静默（body: matchers + comment + duration_minutes）"""
    if request.method == "GET":
        try:
            resp = requests.get(AM_SILENCES, timeout=10)
            resp.raise_for_status()
            return DetailResponse(data=resp.json(), msg="获取成功")
        except requests.exceptions.RequestException as e:
            return ErrorResponse(msg=f"查询静默失败：{e}")
        except Exception as e:
            return ErrorResponse(msg=f"查询静默失败：{e}")

    # POST 创建静默
    body = request.data or {}
    matchers = body.get("matchers")
    if not matchers or not isinstance(matchers, list):
        return ErrorResponse(msg="缺少 matchers（匹配标签列表）")

    duration = int(body.get("duration_minutes") or 60)
    now = datetime.now(timezone.utc)
    starts_at = body.get("startsAt") or now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    ends_at = body.get("endsAt") or (now + timedelta(minutes=duration)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    payload = {
        "matchers": matchers,
        "startsAt": starts_at,
        "endsAt": ends_at,
        "createdBy": body.get("createdBy") or "xwops",
        "comment": body.get("comment") or "",
    }
    try:
        resp = requests.post(AM_SILENCES, json=payload, timeout=10)
        if resp.status_code in (200, 201):
            return DetailResponse(data=resp.json(), msg="静默已创建")
        return ErrorResponse(msg=f"创建静默失败：HTTP {resp.status_code} {resp.text[:200]}")
    except requests.exceptions.RequestException as e:
        return ErrorResponse(msg=f"创建静默失败：{e}")
    except Exception as e:
        return ErrorResponse(msg=f"创建静默失败：{e}")


@api_view(["DELETE"])
def silence_delete(request, silence_id):
    """删除静默：DELETE /api/alert/manage/silences/{silence_id}/"""
    try:
        # Alertmanager 删除端点是单数 /api/v2/silence/{id}
        url = f"{ALERTMANAGER_URL}/api/v2/silence/{silence_id}"
        resp = requests.delete(url, timeout=10)
        if resp.status_code == 200:
            return DetailResponse(msg="静默已删除")
        return ErrorResponse(msg=f"删除静默失败：HTTP {resp.status_code} {resp.text[:200]}")
    except requests.exceptions.RequestException as e:
        return ErrorResponse(msg=f"删除静默失败：{e}")
    except Exception as e:
        return ErrorResponse(msg=f"删除静默失败：{e}")


@api_view(["GET"])
def route_summary(request):
    """路由收敛概览：解析 Alertmanager route + receivers，展示告警如何收敛/分发"""
    try:
        resp = requests.get(AM_STATUS, timeout=10)
        resp.raise_for_status()
        original = (resp.json().get("config") or {}).get("original", "")
        parsed = yaml.safe_load(original) or {}
        route = parsed.get("route", {}) or {}
        receivers = parsed.get("receivers", []) or []

        # 规整 receivers：只保留名字 + 启用的集成类型
        recv_view = []
        for r in receivers:
            types = [k for k, v in (r or {}).items() if isinstance(v, list) and v]
            recv_view.append({"name": r.get("name"), "integrations": types})

        return DetailResponse(data={
            "route": {
                "receiver": route.get("receiver"),
                "group_by": route.get("group_by") or [],
                "group_wait": route.get("group_wait"),
                "group_interval": route.get("group_interval"),
                "repeat_interval": route.get("repeat_interval"),
            },
            "receivers": recv_view,
        }, msg="获取成功")
    except requests.exceptions.RequestException as e:
        return ErrorResponse(msg=f"查询路由配置失败：{e}")
    except Exception as e:
        return ErrorResponse(msg=f"查询路由配置失败：{e}")
