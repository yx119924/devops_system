# -*- coding: utf-8 -*-
"""
告警管理视图：活跃告警 + Alertmanager 静默 + 路由收敛
这些是 Alertmanager 的代理接口，数据不落本地库，实时透传。
"""
import re
from datetime import datetime, timedelta, timezone

import requests
import yaml
from rest_framework.decorators import api_view

from dvadmin.alert.services import _require_url
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

# 静默时长上限（分钟）：30 天，防止误填出「永久静默」
MAX_DURATION_MINUTES = 60 * 24 * 30


def _matcher_list(raw):
    """规整前端传来的匹配条件列表。

    只保留「标签名 + 标签值」都非空的项，并补全 isRegex / isEqual，
    避免前端漏传字段导致 Alertmanager 400。
    """
    out = []
    if not isinstance(raw, list):
        return out
    for m in raw:
        if not isinstance(m, dict):
            continue
        name = str(m.get("name") or "").strip()
        value = "" if m.get("value") is None else str(m.get("value")).strip()
        if not name or value == "":
            continue
        out.append({
            "name": name,
            "value": value,
            "isRegex": bool(m.get("isRegex")),
            "isEqual": bool(m.get("isEqual", True)),
        })
    return out


def _validate_matchers(matchers):
    """正则类 matcher 先在 Python 侧编译校验，把「静默建成功但永不命中」挡在提交前。

    注意：Alertmanager 用的是 Go RE2，语法与 Python re 大体一致；
    这里只做基本合法性检查，真正的编译以 AM 侧为准。
    """
    for m in matchers:
        if m["isRegex"]:
            try:
                re.compile(m["value"])
            except re.error as e:
                return f"正则不合法（{m['name']}=~{m['value']}）：{e}"
    return ""


def _creator_name(user):
    """静默创建人：优先中文名，退回用户名；无登录态时用 xwops（兼容脚本/自动化调用）"""
    if not user or not getattr(user, "is_authenticated", False):
        return "xwops"
    return getattr(user, "name", "") or getattr(user, "username", "") or "xwops"


def _am_url(path):
    """拼 Alertmanager 接口地址。

    注意：地址来自数据库（数据源管理页），必须在请求时动态取，
    不能像旧版那样在模块 import 时拼成常量——否则改了页面配置也不生效。
    """
    return f"{_require_url('alertmanager', 'Alertmanager')}{path}"


@api_view(["GET"])
def active_alerts(request):
    """活跃告警列表：透传 Alertmanager /api/v2/alerts，规整为前端易用结构"""
    try:
        resp = requests.get(_am_url("/api/v2/alerts"), timeout=10)
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
            resp = requests.get(_am_url("/api/v2/silences"), timeout=10)
            resp.raise_for_status()
            return DetailResponse(data=resp.json(), msg="获取成功")
        except requests.exceptions.RequestException as e:
            return ErrorResponse(msg=f"查询静默失败：{e}")
        except Exception as e:
            return ErrorResponse(msg=f"查询静默失败：{e}")

    # POST 创建静默
    body = request.data or {}
    matchers = _matcher_list(body.get("matchers"))
    if not matchers:
        return ErrorResponse(msg="请至少填写一个有效的匹配条件（标签名 + 标签值都不能为空）")

    invalid = _validate_matchers(matchers)
    if invalid:
        return ErrorResponse(msg=invalid)

    try:
        duration = int(body.get("duration_minutes") or 60)
    except (TypeError, ValueError):
        duration = 60
    duration = max(1, min(duration, MAX_DURATION_MINUTES))

    now = datetime.now(timezone.utc)
    starts_at = body.get("startsAt") or now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    ends_at = body.get("endsAt") or (now + timedelta(minutes=duration)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    payload = {
        "matchers": matchers,
        "startsAt": starts_at,
        "endsAt": ends_at,
        "createdBy": body.get("createdBy") or _creator_name(getattr(request, "user", None)),
        "comment": body.get("comment") or "",
    }
    try:
        resp = requests.post(_am_url("/api/v2/silences"), json=payload, timeout=10)
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
        url = _am_url(f"/api/v2/silence/{silence_id}")
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
        resp = requests.get(_am_url("/api/v2/status"), timeout=10)
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
