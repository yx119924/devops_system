# -*- coding: utf-8 -*-
"""
AI 只读工具集 —— Agent 唯一能「动手」的地方。本功能的**执行层安全核心**。

四道闸，缺一不可
----------------
1. **开关闸** —— `AiGuardConfig.readonly_mode` / `enabled_tools`
   （两层：一个是命令执行总开关，一个是"允不允许碰服务器"）
2. **命令闸** —— `guard.check_command()`：分段校验、元字符拦截、白/黑名单、敏感路径
3. **授权闸** —— `bastion.access.require_access(user, server, credential, 'dispatch')`
   「AI 能操作什么」== 「你在『命令下发』里能操作什么」，**不引入第二套授权口径**。
   把 AI 的权限面绑到一个已经上线、已经有审计的口径上，是这次设计里最省心的决定。
4. **脱敏闸** —— 输出先脱敏、再截断，然后才回灌给大模型

★ 工具只收 `server_id`，**不收裸 IP**
  否则模型可以把命令直接打到 CMDB 之外的机器上，第 3 道闸形同虚设。
  这是这类"AI 运维助手"最容易漏的一个口子 —— 参数表里只要出现 `host`/`ip`，
  就等于把 SSH 通道对模型敞开了。

★ 被拒绝的调用也要写台账
  审计关心的是「AI 想干什么、被什么拦住」。只管成功调用，
  就永远看不出有人在用 AI 试探读 /etc/shadow。
"""
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from dvadmin.aiagent import desensitize
from dvadmin.aiagent.guard import check_command

logger = logging.getLogger(__name__)

# 单条命令的长度上限（防护栏被超长字符串刷爆）
MAX_COMMAND_CHARS = 1024
# 台账里保留的输出片段长度（比回灌给模型的 max_output_chars 更短 —— 台账是给人看的）
LEDGER_EXCERPT_CHARS = 2000


# ============================================================
# 工具声明（OpenAI function calling 格式）
# ============================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_servers",
            "description": (
                "列出你有权限操作的服务器（来自 CMDB）。不知道要在哪台机器上排查时，"
                "先用这个工具查。可按主机名 / IP / 标签模糊搜索。"
                "返回的 id 就是后续 run_readonly_command 要用的 server_id。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string",
                                "description": "模糊匹配主机名、IP、标签；留空表示不过滤"},
                    "limit": {"type": "integer",
                              "description": "最多返回多少台，默认 20，最大 50"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_readonly_command",
            "description": (
                "在一台或多台服务器上执行一条**只读**命令并拿到输出。"
                "★ 严格限制：只允许白名单内的只读命令（uptime/df/free/ss/ps/docker ps/"
                "journalctl/systemctl status 等），"
                "禁止任何写操作、重定向（> <）、命令拼接（; && || |）、命令替换（$( )）。"
                "被拒绝时会告诉你原因，换一条合规的命令重试即可，不要反复试同一条。"
                "★ 一次不要查太多台，先 1~2 台验证思路，再扩大范围。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "server_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "目标服务器 id 列表（来自 list_servers，不是 IP）",
                    },
                    "command": {"type": "string",
                                "description": "要执行的只读命令，例如 free -m、df -hT、ss -s"},
                    "purpose": {"type": "string",
                                "description": "为什么跑这条命令（会写进审计台账，必填）"},
                },
                "required": ["server_ids", "command", "purpose"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_alerts",
            "description": (
                "查询平台已落库的历史告警（数据来自 Alertmanager webhook）。"
                "可按告警名/摘要/实例模糊搜索、按状态和级别过滤、按时间范围回溯。\n"
                "★ 回答「这条告警为什么触发」「这告警是不是反复响」这类问题，**必须先用它拿到告警原始记录**，"
                "不要凭常识猜原因。告警的规则名、实例、级别、摘要都在这里。\n"
                "★ 返回的 instance 可能是 URL 形式（如 http://192.168.0.5:8819），"
                "要定位是哪台机器，请自己提取其中的 IP 再用 list_servers 查。\n"
                "★ 每条带两个计数，**不要混用**：`occurrences_in_range` = 在你指定的时间范围内"
                "出现过几次（回答「这个月几次」「最近一周几次」用这个）；"
                "`occurrences_all_time` = 历史上总共几次（判断是不是老问题用这个）。\n"
                "★ 记录只覆盖「已落库」的告警；若查不到，可能该告警未通过 webhook 落库，如实说明即可。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string",
                                "description": "模糊匹配告警名称、摘要、实例、描述；留空表示不过滤"},
                    "status": {"type": "string", "enum": ["firing", "resolved"],
                               "description": "告警状态；留空表示全部"},
                    "severity": {"type": "string", "enum": ["critical", "warning", "info"],
                                 "description": "告警级别；留空表示全部"},
                    "hours": {"type": "integer",
                              "description": "回溯最近 N 小时（1~8760）。与 since/until 二选一，优先用这个"},
                    "since": {"type": "string",
                              "description": "起始时间，格式 YYYY-MM-DD HH:MM[:SS]，如 2026-11-04 11:50"},
                    "until": {"type": "string",
                              "description": "结束时间，格式同上"},
                    "limit": {"type": "integer",
                              "description": "最多返回多少条，默认 20，最大 50"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_logs",
            "description": (
                "检索 Elasticsearch 里的历史日志（filebeat 采集进来的业务/系统日志）。\n"
                "★ 回答「昨天这个时间报了什么错」「为什么 502」「当时有没有异常日志」这类问题用它。"
                "告警告诉你「发生了什么」，日志才告诉你「为什么」。\n"
                "★ keyword 走 ES query_string 语法，支持 `error AND timeout`、`\"connection refused\"` 这类组合。\n"
                "★ 必须先给出时间范围（hours 或 since/until），不给时默认最近 24 小时 —— "
                "日志量很大，不限定时间会超时。\n"
                "★ 返回的是日志片段，不是结论。要基于 message 原文判断，不要脑补没看到的内容。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string",
                                "description": "ES query_string 语法，如 502、error AND timeout；留空表示不限"},
                    "level": {"type": "string",
                              "description": "日志级别，如 error / warn / info；留空表示不限"},
                    "hours": {"type": "integer",
                              "description": "回溯最近 N 小时（1~720），未给 since 时默认 24"},
                    "since": {"type": "string", "description": "起始时间 YYYY-MM-DD HH:MM[:SS]"},
                    "until": {"type": "string", "description": "结束时间 YYYY-MM-DD HH:MM[:SS]"},
                    "index": {"type": "string",
                              "description": "索引模式，如 nginx-*；留空用数据源默认配置"},
                    "source_id": {"type": "integer", "description": "ES 数据源 id；只有一个时可不填"},
                    "size": {"type": "integer",
                             "description": "返回条数，默认 20，最大 100"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_metrics",
            "description": (
                "查询 Prometheus 指标（PromQL）。\n"
                "★ 用来确认「那个时间点 CPU/内存/连接数/磁盘有没有异常拐点」，"
                "是判断资源类故障的第一手证据。\n"
                "★ 只给 query 走即时查询（看当前值）；同时给 range_minutes 走范围查询（看趋势与拐点）。\n"
                "★ PromQL 要写窄一些：带上明确的指标名和标签过滤，例如 "
                "`node_memory_MemAvailable_bytes{instance=\"192.168.0.5:9100\"}`；"
                "禁止用 `{__name__=~\".*\"}` 这类全匹配，会被拒绝。\n"
                "★ 返回的是时间序列原始值，不要直接下结论；先看有没有拐点，再和告警时间对齐。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "PromQL 表达式，必填"},
                    "range_minutes": {"type": "integer",
                                      "description": "给这个值就走范围查询，回溯最近 N 分钟（1~10080）"},
                    "step": {"type": "string",
                             "description": "范围查询的步长，如 60s、5m；不填按范围自动取"},
                    "source_id": {"type": "integer", "description": "Prometheus 数据源 id；只有一个时可不填"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_jobs",
            "description": (
                "列出你可以看到的 Jenkins Job（含嵌套目录，按角色授权过滤）。\n"
                "★ 用户说「XX job 构建失败了」但没给完整路径时，先用它定位 full_path，"
                "**不要猜 job 名**。嵌套目录的 full_path 形如 `dev/backend`。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string",
                                "description": "按 job 路径模糊过滤；留空列出全部（最多 100 个）"},
                    "source_id": {"type": "integer", "description": "Jenkins 服务器 id；只有一个时可不填"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_builds",
            "description": (
                "列出某个 Job 的最近构建（编号、结果、开始时间、耗时、构建参数）。\n"
                "★ 回答「这个 job 为什么构建失败」时，必须**先**用它拿到具体构建编号，"
                "再用 get_build_log 拉那一次的日志。\n"
                "★ 构建参数很有价值：能看出是谁用什么参数触发的。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job": {"type": "string",
                            "description": "Job 的 full_path，如 dev/backend（来自 list_jobs）"},
                    "limit": {"type": "integer", "description": "返回最近几次，默认 5，最大 20"},
                    "source_id": {"type": "integer", "description": "Jenkins 服务器 id；只有一个时可不填"},
                },
                "required": ["job"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_build_log",
            "description": (
                "拉取某一次构建的日志，并自动抽取失败现场（锚点前后几十行）。\n"
                "★ build 参数**必填且必须是数字编号**，不接受 lastBuild —— "
                "用户问的可能是历史上某一次失败，拿最后一次会答非所问。\n"
                "★ 返回的是**片段**：`truncated=true` 时禁止断言「整个构建没有其他错误」。\n"
                "★ 判断失败原因要看 `anchor_text` 和片段原文，不要凭 job 名猜。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job": {"type": "string", "description": "Job 的 full_path（来自 list_jobs）"},
                    "build": {"type": "integer",
                              "description": "构建编号（来自 list_builds），必须是数字"},
                    "source_id": {"type": "integer", "description": "Jenkins 服务器 id；只有一个时可不填"},
                },
                "required": ["job", "build"],
            },
        },
    },
]


# ============================================================
# 上下文与工具函数
# ============================================================
class ToolContext(object):
    """一次提问的执行上下文。由 agent 构造，贯穿所有工具调用。"""

    def __init__(self, user, session, rules, round_index=0):
        self.user = user
        self.session = session
        self.rules = rules or {}
        self.round_index = round_index
        self.keywords = desensitize.parse_keywords(self.rules.get("desensitize_keywords"))

    def mask(self, text):
        """按护栏配置对某段文本脱敏。返回 (文本, 命中标签串)。"""
        if not self.rules.get("desensitize", True):
            return text or "", ""
        out, hits = desensitize.mask(text, self.keywords)
        return out, "、".join(hits)


def _clamp(value, low, high, default):
    try:
        num = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, num))


def _truncate(text, limit):
    """截断但保留首尾：排障时**开头**是现象、**结尾**往往是结论。"""
    text = text or ""
    if len(text) <= limit:
        return text
    head = int(limit * 0.7)
    tail = limit - head
    return "%s\n…（此处省略 %d 字符）…\n%s" % (text[:head], len(text) - limit, text[-tail:])


def _dump(obj):
    return json.dumps(obj, ensure_ascii=False)


def _fail(msg):
    return _dump({"ok": False, "error": msg})


def _write_ledger(ctx, **fields):
    """写一行工具调用台账。审计主表 —— 任何失败都不能影响主流程。"""
    from dvadmin.aiagent.models import AiToolCall

    try:
        row = AiToolCall(session=ctx.session

                         , owner=ctx.user,
                         round_index=ctx.round_index, **fields)
        row.save()
        return row
    except Exception:
        # 台账写不进去也不能让对话失败；但要留日志，否则审计会静默缺口
        logger.exception("写 AI 工具调用台账失败")
        return None


def _credential_payload(credential):
    return {
        "username": credential.username or "root",
        "auth_type": credential.auth_type or "password",
        "password": credential.get_password() if credential.auth_type == "password" else None,
        "private_key": credential.get_private_key() if credential.auth_type == "private_key" else None,
    }


# ============================================================
# 工具 1：list_servers
# ============================================================
def tool_list_servers(args, ctx):
    from django.db.models import Q

    from dvadmin.bastion.access import is_asset_admin, writable_server_ids
    from dvadmin.cmdb.models import Server

    keyword = (args.get("keyword") or "").strip()
    limit = _clamp(args.get("limit"), 1, 50, 20)

    qs = Server.objects.all()
    if not is_asset_admin(ctx.user):
        # 和「命令下发」同一个可见集合：能操作才列出来
        qs = qs.filter(pk__in=(writable_server_ids(ctx.user) or []))

    if keyword:
        qs = qs.filter(Q(hostname__icontains=keyword)
                       | Q(ip__icontains=keyword)
                       | Q(tags__icontains=keyword))

    total = qs.count()
    rows = list(qs.order_by("ip").values(
        "id", "hostname", "ip", "extra_ips", "status", "os",
        "environment__name", "idc__name", "business_line__name")[:limit])

    servers = [{
        "server_id": r["id"],
        "hostname": r["hostname"],
        "ip": r["ip"],
        "extra_ips": r["extra_ips"] or "",
        "status": r["status"],
        "os": r["os"] or "",
        "environment": r["environment__name"] or "",
        "idc": r["idc__name"] or "",
        "business_line": r["business_line__name"] or "",
    } for r in rows]

    out = {"ok": True, "total_matched": total, "returned": len(servers), "servers": servers}
    if not total:
        out["hint"] = ("没有匹配的服务器。若你确信该机器存在，说明当前账号还没有它的资产授权，"
                       "请让运维在「CMDB → 服务器授权」里配置。"
                       "★ 不要猜测 IP 直接下单 —— 工具只接受 server_id。")
    elif total > len(servers):
        out["hint"] = "结果被 limit 截断了，可用更精确的 keyword 缩小范围。"
    return _dump(out)


# ============================================================
# 工具 2：run_readonly_command
# ============================================================
def tool_run_readonly_command(args, ctx):
    from dvadmin.cmdb.models import Server

    rules = ctx.rules
    max_servers = _clamp(rules.get("max_servers"), 1, 50, 5)

    # ---- 参数校验 ----
    raw_ids = args.get("server_ids")
    if isinstance(raw_ids, (int, str)):
        raw_ids = [raw_ids]
    if not isinstance(raw_ids, (list, tuple)) or not raw_ids:
        return _fail("server_ids 必须是非空数组，元素是 list_servers 返回的 server_id")

    ids, seen = [], set()
    for item in raw_ids:
        try:
            sid = int(item)
        except (TypeError, ValueError):
            return _fail("server_ids 里出现了非整数：%r" % (item,))
        if sid not in seen:
            seen.add(sid)
            ids.append(sid)
    if len(ids) > max_servers:
        return _fail("一次最多操作 %d 台服务器，你给了 %d 台。请分批查。" % (max_servers, len(ids)))

    command = (args.get("command") or "").strip()
    if not command:
        return _fail("command 不能为空")
    if len(command) > MAX_COMMAND_CHARS:
        return _fail("命令过长（%d 字符，上限 %d）" % (len(command), MAX_COMMAND_CHARS))

    purpose = (args.get("purpose") or "").strip()
    if not purpose:
        # 强制写理由：没有理由的调用在审计里等于没有价值
        return _fail("purpose 必填：一句话说明为什么要跑这条命令（会写进审计台账）")

    # ---- 先把目标解析出来，让台账里能带上真实的主机名 ----
    found = {s.pk: s for s in Server.objects.filter(pk__in=ids)}
    items = []
    for sid in ids:
        server = found.get(sid)
        if server is None:
            items.append({"sid": sid, "server": None,
                          "label": "server_id=%s" % sid, "ip": "",
                          "err": "CMDB 里没有 id=%s 的服务器" % sid})
        else:
            items.append({"sid": sid, "server": server,
                          "label": server.hostname or server.ip, "ip": server.ip,
                          "err": ""})

    base = {"tool_name": "run_readonly_command", "command": command, "purpose": purpose[:255]}

    # ---- 闸 1：开关 ----
    if not rules.get("enabled_tools", True):
        reason = ("管理员已关闭「允许调用只读工具」，AI 当前不能连服务器。"
                  "请让管理员到「模型配置 → 安全护栏」开启。")
        _reject_all(ctx, items, base, reason, "blocked")
        return _dump({"ok": False, "error": reason,
                      "targets": [{"server_id": it["sid"], "server": it["label"],
                                   "result": "blocked"} for it in items]})

    if not rules.get("readonly_mode", True):
        reason = ("「只读模式」已被管理员关闭，AI 当前不执行任何命令（含只读命令）。"
                  "这是应急刹车：请让管理员确认后再开启。")
        _reject_all(ctx, items, base, reason, "blocked")
        return _dump({"ok": False, "error": reason,
                      "targets": [{"server_id": it["sid"], "server": it["label"],
                                   "result": "blocked"} for it in items]})

    # ---- 闸 2：命令护栏 ----
    ok, reason, segments = check_command(
        command, rules.get("allowed") or [], rules.get("denied") or [],
        rules.get("denied_paths") or [])
    if not ok:
        _reject_all(ctx, items, base, reason, "rejected")
        return _dump({
            "ok": False,
            "error": reason,
            "command": command,
            "segments": segments,
            "how_to_fix": ("换成白名单内的**单条只读命令**。注意：不允许 `;` `&&` `||` `|` 拼接、"
                           "不允许 `> <` 重定向、不允许 `$( )`。"
                           "需要多个信息时，分多次调用，每次一条命令。"),
        })

    # ---- 闸 3：资产授权（逐台）----
    from dvadmin.bastion.access import require_access

    credential = ctx.session.credential
    if credential is None:
        reason = "本会话没有选定凭据，无法建立 SSH 连接。请新建会话时选一条凭据。"
        _reject_all(ctx, items, base, reason, "blocked")
        return _dump({"ok": False, "error": reason, "targets": _targets(items)})

    runnable = []
    for it in items:
        if it["server"] is None:
            _write_ledger(ctx, server=None, server_label=it["label"], ip="",
                          status="error", reject_reason=it["err"], **base)
            it["res"] = {"server_id": it["sid"], "server": it["label"], "ip": "",
                         "status": "error", "error": it["err"]}
            continue
        try:
            require_access(ctx.user, it["server"], credential, "dispatch")
        except PermissionDenied as exc:
            detail = getattr(exc, "detail", None)
            msg = str(detail[0]) if isinstance(detail, (list, tuple)) and detail else str(exc)
            _write_ledger(ctx, server=it["server"], server_label=it["label"],
                          ip=it["ip"], status="blocked", reject_reason=msg[:500], **base)
            it["res"] = {"server_id": it["sid"], "server": it["label"], "ip": it["ip"],
                         "status": "blocked", "error": msg}
            continue
        runnable.append(it)

    # ---- 执行（闸 4 脱敏在 _run_on_server 内）----
    if runnable:
        payload = _credential_payload(credential)
        timeout = _clamp(rules.get("command_timeout"), 5, 300, 30)
        workers = _clamp(rules.get("max_workers"), 1, 20, 4)
        max_chars = _clamp(rules.get("max_output_chars"), 500, 100000, 8000)
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(runnable)))) as pool:
            futures = [pool.submit(_run_on_server, it, command, payload, timeout,
                                   ctx, max_chars, purpose) for it in runnable]
            for fut in futures:
                fut.result()          # 异常已在 _run_on_server 内吃掉

    targets = _targets(items)
    done = [t for t in targets if t["status"] in ("success", "empty")]
    return _dump({
        "ok": bool(done),
        "command": command,
        "summary": {"success": len(done), "total": len(targets)},
        "targets": targets,
        "note": ("输出已脱敏（凭据类内容替换为 ***）并截断。"
                 "只根据实际输出下结论，不要补没看到的内容。"),
    })


# ============================================================
# 工具 3：query_alerts
#
# 数据语义（改这里前必读）
# ------------------------
#   AlertEvent 的一行 = **一次完整的告警生命周期**（firing 时创建，resolved 时把同一行改状态）。
#   `persist_alerts()` 在 firing 阶段按 fingerprint 做 upsert，所以同一 fingerprint
#   再次告警时会**新建一行**。⇒ 按 fingerprint 计数 = 「这条告警历史上响过几次」。
#
#   `USE_TZ=False`，库里全是 naive datetime。时间比较必须用 naive，
#   否则 `starts_at__gte=<aware>` 会抛 RuntimeError。
# ============================================================
_ALERT_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
)


def _parse_alert_time(value):
    """宽松解析时间字符串 → naive datetime；解析不了返回 None。

    模型给的格式五花八门（"2026-11-04 11:50"、"2026-11-04T11:50:00"、ISO 带 Z），
    这里都兜一遍。**绝不抛异常** —— 时间格式错误不该让整次查询失败，
    应该退化成分时段查询，并在结果里告诉模型「时间没解析上」。
    """
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in _ALERT_TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        from django.utils.dateparse import parse_datetime

        dt = parse_datetime(text)
        if dt is None:
            return None
        if timezone.is_aware(dt):
            # settings.USE_TZ=True 时库里的也是 aware，直接用；否则转 naive
            from django.conf import settings as _settings
            if _settings.USE_TZ:
                return dt
            return timezone.make_naive(dt, timezone.get_current_timezone())
        return dt
    except Exception:
        return None


def _resolve_alert_window(args):
    """把 hours / since+until 归一成 (since, until, 人类可读说明)。

    `hours` 优先：模型判断「昨天」这种相对时间容易错，但算「最近 24 小时」很稳。
    """
    now = timezone.now()          # USE_TZ=False ⇒ naive，可直接与库里字段比
    since = until = None
    note = ""

    raw_hours = args.get("hours")
    if raw_hours not in (None, ""):
        try:
            hours = int(raw_hours)
        except (TypeError, ValueError):
            hours = 0
        if hours > 0:
            hours = max(1, min(hours, 8760))     # 上限一年，防模型传个天文数字
            since = now - timedelta(hours=hours)
            note = "最近 %d 小时（%s 起）" % (hours, since.strftime("%m-%d %H:%M"))

    if since is None:
        since = _parse_alert_time(args.get("since"))
        until = _parse_alert_time(args.get("until"))
        if since and until:
            note = "%s ~ %s" % (since.strftime("%m-%d %H:%M"), until.strftime("%m-%d %H:%M"))
        elif since:
            note = "%s 之后" % since.strftime("%m-%d %H:%M")
        elif until:
            note = "%s 之前" % until.strftime("%m-%d %H:%M")
        # 给了时间字符串但解析失败 ⇒ 明确告诉模型，别让它以为筛过了
        if not since and not until and (args.get("since") or args.get("until")):
            note = "★ 时间参数没解析成功，本次未按时间过滤（请改用 hours 或 YYYY-MM-DD HH:MM）"

    return since, until, note


def _fmt_dt(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _format_alert_row(row, n_in_range, n_all):
    """把一行 AlertEvent 压成给模型看的 dict。labels 要截断，否则一条就几千字符。

    ★ 两个计数必须分开传：「本次时间范围内几次」和「历史总共几次」是两个不同的问题，
      合并成一个字段一定会让模型答错（它分不清你问的是哪个）。
    """
    labels = row.labels or {}
    if isinstance(labels, dict):
        label_text = json.dumps(labels, ensure_ascii=False, separators=(",", ":"))
    else:
        label_text = str(labels)
    if len(label_text) > 600:
        label_text = label_text[:600] + "…（已截断）"

    duration = None
    if row.starts_at:
        end = row.ends_at or timezone.now()
        try:
            duration = int((end - row.starts_at).total_seconds() // 60)
        except Exception:
            duration = None

    return {
        "alertname": row.alertname or "",
        "instance": row.instance or "",
        "status": row.status,
        "severity": row.severity,
        "summary": (row.summary or "")[:300],
        "description": (row.description or "")[:400],
        "starts_at": _fmt_dt(row.starts_at),
        "ends_at": _fmt_dt(row.ends_at),
        "duration_minutes": duration,
        "fingerprint": row.fingerprint or "",
        "occurrences_in_range": n_in_range,
        "occurrences_all_time": n_all,
        "labels": label_text,
    }


def tool_query_alerts(args, ctx):
    """查历史告警。只读，不涉及任何机器操作，所以不走命令/授权那两道闸。"""
    from django.db.models import Count, Q

    from dvadmin.alert.models import AlertEvent

    limit = _clamp(args.get("limit"), 1, 50, 20)

    qs = AlertEvent.objects.all()

    keyword = (args.get("keyword") or "").strip()
    if keyword:
        qs = qs.filter(Q(alertname__icontains=keyword)
                       | Q(summary__icontains=keyword)
                       | Q(instance__icontains=keyword)
                       | Q(description__icontains=keyword))

    status = (args.get("status") or "").strip().lower()
    if status in ("firing", "resolved"):
        qs = qs.filter(status=status)

    severity = (args.get("severity") or "").strip().lower()
    if severity in ("critical", "warning", "info"):
        qs = qs.filter(severity=severity)

    since, until, window_note = _resolve_alert_window(args)
    if since:
        qs = qs.filter(starts_at__gte=since)
    if until:
        qs = qs.filter(starts_at__lte=until)

    total = qs.count()
    if not total:
        return _dump({
            "ok": True,
            "total_matched": 0,
            "returned": 0,
            "alerts": [],
            "time_window": window_note,
            "hint": ("没有匹配的告警。常见原因：① 时间范围不对；"
                     "② 该告警只推了通知、没走 webhook 落库；③ 关键词不匹配。"
                     "★ 不要因为查不到就推测原因，如实告诉用户「告警库里没有这条记录」，"
                     "并建议他放宽时间范围或换关键词。"),
        })

    rows = list(qs.order_by("-starts_at", "-id")[:limit])

    # ---- 同指纹计数：必须区分「时间窗内」与「全部历史」----
    # ★ 曾踩的坑：只按 fingerprint 数全库，模型问「这个月几次」会拿到历史总数，
    #   然后理直气壮地答一个错数字 —— 比答不出更糟。
    # 计数**只应用时间过滤**，不应用 keyword/status/severity：
    #   「这条告警这个月响了几次」与你有没有筛 firing 无关。
    fps = {r.fingerprint for r in rows if r.fingerprint}
    in_range, all_time = {}, {}
    if fps:
        q_in = AlertEvent.objects.filter(fingerprint__in=fps)
        if since:
            q_in = q_in.filter(starts_at__gte=since)
        if until:
            q_in = q_in.filter(starts_at__lte=until)
        for item in q_in.values("fingerprint").annotate(n=Count("id")):
            in_range[item["fingerprint"]] = item["n"]
        for item in (AlertEvent.objects.filter(fingerprint__in=fps)
                     .values("fingerprint").annotate(n=Count("id"))):
            all_time[item["fingerprint"]] = item["n"]

    alerts = [_format_alert_row(r, in_range.get(r.fingerprint, 1),
                                all_time.get(r.fingerprint, 1)) for r in rows]

    out = {
        "ok": True,
        "total_matched": total,
        "returned": len(alerts),
        "time_window": window_note,
        "alerts": alerts,
    }
    hints = []
    if total > len(alerts):
        hints.append("共匹配 %d 条，只返回最近 %d 条；可用更精确的时间或关键词缩小范围。"
                     % (total, len(alerts)))
    if any(a["occurrences_in_range"] > 1 for a in alerts):
        hints.append("有告警在本次时间范围内重复出现（occurrences_in_range > 1），"
                     "结论里要明确指出「反复发生」而不是孤立事件。")
    if any(a["occurrences_all_time"] > a["occurrences_in_range"] for a in alerts):
        hints.append("部分告警在本次时间范围之外也发生过（occurrences_all_time 更大），"
                     "说明它是老问题，不是这次才出现的。")
    if any("://" in a["instance"] for a in alerts):
        hints.append("instance 是 URL 形式，定位机器请提取其中的 IP 再用 list_servers 查。")
    if hints:
        out["hint"] = " ".join(hints)
    return _dump(out)


# ============================================================
# 工具 4/5 的共用：通用时间窗
# ============================================================
def _resolve_time_window(args, default_hours=24, max_hours=720):
    """hours 优先 → since/until → 回落到 default_hours（0 表示不限）。

    与 `_resolve_alert_window` 的差别：这个支持「默认窗口」。
    日志量极大，不限定时间会直接把 ES 打超时，所以它默认 24 小时。
    """
    now = timezone.now()
    since = until = None
    note = ""

    raw_hours = args.get("hours")
    if raw_hours not in (None, ""):
        try:
            hours = int(raw_hours)
        except (TypeError, ValueError):
            hours = 0
        if hours > 0:
            hours = max(1, min(hours, max_hours))
            since = now - timedelta(hours=hours)
            note = "最近 %d 小时" % hours

    if since is None:
        since = _parse_alert_time(args.get("since"))
        until = _parse_alert_time(args.get("until"))
        if since and until:
            note = "%s ~ %s" % (_fmt_dt(since), _fmt_dt(until))
        elif since:
            note = "%s 之后" % _fmt_dt(since)
        elif until:
            note = "%s 之前" % _fmt_dt(until)
        elif args.get("since") or args.get("until"):
            note = "时间参数没解析成功，已回落到默认窗口"

    if since is None and until is None and default_hours:
        since = now - timedelta(hours=default_hours)
        note = (note + "；" if note else "") + "未指定时间，默认最近 %d 小时" % default_hours

    return since, until, note


def _es_ts(dt):
    """naive datetime → ES 认的 ISO 串。

    ★ 刻意**不加时区**：必须与 `log/views/source.py:_norm_ts` 完全同口径。
      日志检索页就是这么传的（前端本地时间字符串直接透传），
      这里若自作聪明补 +08:00，AI 查到的时间窗会和日志页对不上 —— 那更难排查。
      时区问题是既有系统的既有口径，要改就两边一起改，不在这里单方面改。
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%S") if dt else None


# ============================================================
# 工具 4：query_logs
# ============================================================
def tool_query_logs(args, ctx):
    """检索 ES 日志。只读；不涉及机器操作。"""
    import requests as _requests

    from dvadmin.log.models import ElasticsearchSource
    # 复用日志模块的解析函数，保证字段口径与「日志检索」页面完全一致
    from dvadmin.log.views.source import (
        TOTAL_HIT_CAP, _extract_level, _pick, _safe_index,
    )

    size = _clamp(args.get("size"), 1, 100, 20)
    since, until, window_note = _resolve_time_window(args, default_hours=24, max_hours=720)

    # ---- 选数据源 ----
    qs = ElasticsearchSource.objects.filter(status=1)
    source_id = args.get("source_id")
    if source_id:
        source = qs.filter(pk=source_id).first()
        if source is None:
            return _fail("没有 id=%s 的启用中 ES 数据源。可用数据源请在「日志 → 数据源」里查看。"
                         % source_id)
    else:
        source = qs.order_by("sort", "id").first()
        if source is None:
            return _fail("平台还没有启用中的 Elasticsearch 数据源。"
                         "请先让管理员在「日志 → 数据源」里添加，否则查不了日志。")

    # ---- 索引：模型给的要过白名单，防它拼出跨全库的表达式 ----
    raw_index = (args.get("index") or "").strip()
    if raw_index and not _safe_index(raw_index):
        return _fail("索引模式不合法：%s（只允许字母、数字、下划线、连字符、逗号、星号）" % raw_index)
    index = _safe_index(raw_index) or (source.index_pattern or "").strip().strip("/")
    if not index:
        return _fail("索引模式为空：数据源没配默认索引，请在参数里指定，如 nginx-*")

    # ---- 构建 DSL ----
    must, filters = [], []
    keyword = (args.get("keyword") or "").strip()
    if keyword:
        must.append({"query_string": {"query": keyword}})

    rng = {}
    if since:
        rng["gte"] = _es_ts(since)
    if until:
        rng["lte"] = _es_ts(until)
    if rng:
        filters.append({"range": {"@timestamp": rng}})

    level = (args.get("level") or "").strip().lower()
    if level:
        # 与检索页一致：三种 level 字段 + 正文兜底，命中任一即可
        should = [
            {"term": {"level": level}},
            {"term": {"log_level": level}},
            {"term": {"severity": level}},
            {"match_phrase": {"message": level.upper()}},
        ]
        filters.append({"bool": {"should": should, "minimum_should_match": 1}})

    dsl = {
        "size": size,
        "track_total_hits": TOTAL_HIT_CAP,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {"bool": {}},
    }
    if must:
        dsl["query"]["bool"]["must"] = must
    if filters:
        dsl["query"]["bool"]["filter"] = filters

    base = (source.url or "").strip().rstrip("/")
    if not base:
        return _fail("ES 数据源地址为空")
    url = "%s/%s/_search" % (base, index)

    try:
        resp = _requests.post(url, json=dsl, auth=source.get_auth(), timeout=20)
    except _requests.exceptions.Timeout:
        return _fail("ES 请求超时（20s）。多半是时间范围太大或索引太多："
                     "请缩小 hours，或在 index 里指定更精确的前缀。")
    except _requests.exceptions.ConnectionError:
        return _fail("无法连接 ES：%s" % base)
    except _requests.exceptions.RequestException as exc:
        return _fail("ES 请求异常：%s" % exc)

    if resp.status_code == 404:
        return _fail("索引不存在：%s。可能这个前缀没被 filebeat 采集，或索引名写错了。" % index)
    if resp.status_code in (401, 403):
        return _fail("ES 认证失败或账号无权限，请让管理员检查数据源的用户名密码。")
    if resp.status_code != 200:
        return _fail("ES 返回 HTTP %s：%s" % (resp.status_code, resp.text[:300]))

    try:
        data = resp.json()
    except ValueError:
        return _fail("ES 返回非 JSON 响应")

    hits = (data.get("hits") or {}).get("hits", [])
    total_raw = (data.get("hits") or {}).get("total", 0)
    if isinstance(total_raw, dict):
        total = total_raw.get("value", 0)
        total_exact = total_raw.get("relation") == "eq"
    else:
        total, total_exact = (total_raw or 0), True

    logs = []
    for h in hits:
        src = h.get("_source") or {}
        message = str(_pick(src, ("message", "msg", "log_message")) or "")
        logs.append({
            "timestamp": _pick(src, ("@timestamp", "timestamp", "time")) or "",
            "level": _pick(src, ("level", "log_level", "severity")) or _extract_level(message),
            "host": _pick(src, ("host", "hostname", "server_ip", "ip"),
                          ("host.name", "agent.hostname")) or "",
            "service": _pick(src, ("service", "app", "service_name", "container_name")) or "",
            # 单条截断：一次 100 条 × 全文会把上下文预算吃光
            "message": message[:1500],
        })

    out = {
        "ok": True,
        "index": index,
        "source": source.name,
        "time_window": window_note,
        "total_matched": total,
        "total_exact": total_exact,
        "returned": len(logs),
        "logs": logs,
    }
    hints = []
    if not total:
        hints.append("没有匹配的日志。可能是：① 这个时间窗内确实没有；"
                     "② 这台主机/这个路径没被 filebeat 采集；③ 关键词写法不匹配。"
                     "★ 如实说明查不到，不要编造日志内容。")
    if total and not total_exact:
        hints.append("真实总数超过 ES 统计上限（%d），total_matched 只是下限。" % TOTAL_HIT_CAP)
    if total > len(logs):
        hints.append("只返回最近 %d 条；要更多证据请缩小时间窗或加关键词。" % len(logs))
    if hints:
        out["hint"] = " ".join(hints)
    return _dump(out)


# ============================================================
# 工具 5：query_metrics
# ============================================================
# PromQL 滥用防护：这些写法会瞬间拉爆 Prometheus（或让 django 等到超时），直接拒绝
_PROMQL_MAX_RANGE_HOURS = 24          # 单个 range selector 上限
_PROMQL_MAX_LOOKBACK_MIN = 10080      # 范围查询最多回溯 7 天
_PROMQL_MAX_SERIES = 100              # 返回序列数上限


def _check_promql(query):
    """返回 (ok, reason)。只挡「明显会打爆」的写法，不做完整语法校验。

    ★ 为什么必须挡：PromQL 是图灵完备到能拖垮 TSDB 的查询语言，
      模型一句 `{__name__=~\".+\"}` 就能让 Prometheus OOM。
      这不是防恶意，是防幻觉 —— 模型不知道你的数据量有多大。
    """
    import re as _re

    q = (query or "").strip()
    if not q:
        return False, "query 不能为空"
    if len(q) > 2000:
        return False, "PromQL 过长（上限 2000 字符）"

    # 全匹配：{__name__=~".*"} / {__name__=~".+"} 这类
    if _re.search(r'__name__\s*=~\s*"[\^\.\*\+\?]*"', q):
        return False, ("禁止用 __name__ 全匹配（如 {__name__=~\".*\"}），"
                       "它会扫描整个 TSDB。请写明确指标名，"
                       "如 node_cpu_seconds_total、up。")

    # 通配 metric 名：{__name__=~"node_.*"} 也挡（仍然太宽）
    m = _re.search(r'__name__\s*=~\s*"([^"]+)"', q)
    if m and any(ch in m.group(1) for ch in (".*", ".+", "^", "$")):
        return False, ("禁止用正则匹配指标名。请写明确的指标名，"
                       "不确定有哪些指标时先问用户或用已知的 node_*/up。")

    # range selector 过长：[30d]、[1000h]
    for val, unit in _re.findall(r'\[\s*(\d+)\s*([smhdwy])\s*\]', q):
        try:
            n = int(val)
        except ValueError:
            continue
        hours = {"s": n / 3600.0, "m": n / 60.0, "h": float(n),
                 "d": n * 24.0, "w": n * 168.0, "y": n * 8760.0}[unit]
        if hours > _PROMQL_MAX_RANGE_HOURS:
            return False, ("时间窗口过长（[%s%s] ≈ %.0f 小时，上限 %d 小时）。"
                           "排查故障用 [5m]/[1h] 就够，窗口越大越慢。"
                           % (val, unit, hours, _PROMQL_MAX_RANGE_HOURS))

    return True, ""


def tool_query_metrics(args, ctx):
    """查 Prometheus。只读；不做任何机器操作。"""
    import requests as _requests

    from dvadmin.monitor.models import PrometheusSource

    query = (args.get("query") or "").strip()
    ok, reason = _check_promql(query)
    if not ok:
        return _fail(reason)

    # ---- 选数据源 ----
    qs = PrometheusSource.objects.filter(status=1, source_type="prometheus")
    source_id = args.get("source_id")
    if source_id:
        source = qs.filter(pk=source_id).first()
        if source is None:
            return _fail("没有 id=%s 的启用中 Prometheus 数据源。" % source_id)
    else:
        source = qs.order_by("sort", "id").first()
        if source is None:
            return _fail("平台还没有启用中的 Prometheus 数据源。"
                         "请先让管理员在「监控 → 数据源」里添加。")

    base = (source.url or "").strip().rstrip("/")
    if not base:
        return _fail("Prometheus 数据源地址为空")

    range_minutes = args.get("range_minutes")
    is_range = range_minutes not in (None, "")
    if is_range:
        try:
            minutes = int(range_minutes)
        except (TypeError, ValueError):
            return _fail("range_minutes 必须是整数（分钟）")
        minutes = max(1, min(minutes, _PROMQL_MAX_LOOKBACK_MIN))
        now = timezone.now()
        start = now - timedelta(minutes=minutes)
        step = (args.get("step") or "").strip() or "%ds" % max(15, int(minutes * 60 / 200))
        payload = {"query": query, "start": start.timestamp(), "end": now.timestamp(), "step": step}
        path = "/api/v1/query_range"
    else:
        payload = {"query": query}
        path = "/api/v1/query"

    try:
        resp = _requests.post("%s%s" % (base, path), data=payload, timeout=15,
                              auth=source.get_auth(), headers=source.get_headers())
    except _requests.exceptions.Timeout:
        return _fail("Prometheus 请求超时（15s）。查询可能太重：请缩小时间范围或加标签过滤。")
    except _requests.exceptions.ConnectionError:
        return _fail("无法连接 Prometheus：%s" % base)
    except _requests.exceptions.RequestException as exc:
        return _fail("Prometheus 请求异常：%s" % exc)

    if resp.status_code != 200:
        return _fail("Prometheus 返回 HTTP %s：%s" % (resp.status_code, resp.text[:300]))

    try:
        body = resp.json()
    except ValueError:
        return _fail("Prometheus 返回非 JSON 响应")

    if body.get("status") != "success":
        err = body.get("error") or body.get("errorType") or "未知错误"
        return _fail("PromQL 执行失败：%s。请检查指标名和标签是否正确。" % err)

    data = body.get("data") or {}
    result = data.get("result") or []
    series_count = len(result)
    truncated = series_count > _PROMQL_MAX_SERIES
    if truncated:
        result = result[:_PROMQL_MAX_SERIES]

    # 精简：只留指标标签 + 值，别把整坨原始 JSON 灌给模型
    series = []
    for item in result:
        metric = item.get("metric") or {}
        keep = {k: v for k, v in metric.items() if k in ("__name__", "instance", "job", "device", "mountpoint", "mode")}
        if is_range:
            values = [[v[0], v[1]] for v in (item.get("values") or [])]
        else:
            v = item.get("value") or []
            values = [v] if v else []
        series.append({"metric": keep, "points": values[-200:]})

    out = {
        "ok": True,
        "source": source.name,
        "query": query,
        "mode": "range" if is_range else "instant",
        "series_count": series_count,
        "returned": len(series),
        "result_type": data.get("resultType") or "",
        "series": series,
    }
    if is_range:
        out["range_minutes"] = minutes
        out["step"] = step
    hints = []
    if not series:
        hints.append("没有返回任何序列。可能是：① 指标名不对；② 标签过滤太严；"
                     "③ 这段时间该指标没有采集。先确认指标名，再放宽标签。")
    if truncated:
        hints.append("序列数 %d 超过上限，已只返回前 %d 条；请加标签过滤缩小范围。"
                     % (series_count, _PROMQL_MAX_SERIES))
    if is_range:
        hints.append("points 是 [时间戳, 值] 数组；判断拐点请对比告警 starts_at，不要说「一直很高」这种没依据的话。")
    if hints:
        out["hint"] = " ".join(hints)
    return _dump(out)


# ============================================================
# 工具 6/7/8：Jenkins（list_jobs / list_builds / get_build_log）
#
# 与 jenkins/views 的分工：那边是给人点的页面，这边是给模型用的工具。
# 权限口径**必须**与页面一致 —— 复用 JenkinsRolePermission 的三态语义：
#   无记录 → 默认拒绝 ｜ allowed_paths=[] → 全部 ｜ 否则前缀匹配
# 自己另立一套口径 = 模型能看到你在页面上藏起来的 job。
# ============================================================
def _jenkins_source(args):
    """选 Jenkins 服务器。返回 (source, err_msg)。"""
    from dvadmin.jenkins.models import JenkinsServer

    qs = JenkinsServer.objects.filter(status=1)
    sid = args.get("source_id")
    if sid:
        source = qs.filter(pk=sid).first()
        if source is None:
            return None, "没有 id=%s 的启用中 Jenkins 服务器。" % sid
        return source, None
    source = qs.order_by("sort", "id").first()
    if source is None:
        return None, ("平台还没有启用中的 Jenkins 服务器。"
                      "请先让管理员在「发布 → Jenkins」里添加。")
    return source, None


def _jenkins_allowed_paths(user, source):
    """返回 None=全部 / []=无权限 / list=前缀列表。口径同 jenkins/views。"""
    from dvadmin.jenkins.models import JenkinsRolePermission

    if getattr(user, "is_superuser", False):
        return None
    role_ids = list(user.role.values_list("id", flat=True))
    if not role_ids:
        return []
    perms = JenkinsRolePermission.objects.filter(server=source, role_id__in=role_ids)
    if not perms.exists():
        return []
    allowed = set()
    for p in perms:
        paths = p.allowed_paths or []
        if not paths:          # 空列表 = 全部
            return None
        allowed.update(paths)
    return list(allowed)


def _jenkins_job_path(full_path):
    """'dev/backend' → 'dev/job/backend'（嵌套 folder 每层都要 /job/）。"""
    parts = str(full_path).split("/")
    if any(p in ("", ".", "..") or "\\" in p for p in parts):
        raise ValueError("Job 路径包含非法路径段")
    return "/job/".join(parts)


def _jenkins_path_matches(full_path, prefix):
    pc = prefix.rstrip("/")
    return full_path == pc or full_path.startswith(pc + "/")


def _jenkins_denied_reason(ctx, source, job):
    """校验当前用户能否操作该 job。返回 None=可操作，否则返回中文原因。"""
    try:
        _jenkins_job_path(job)
    except ValueError as exc:
        return str(exc)
    allowed = _jenkins_allowed_paths(ctx.user, source)
    if allowed is None:
        return None
    if not allowed:
        return ("当前账号没有任何 Jenkins 目录授权。请让管理员在「发布 → Jenkins → 角色授权」里配置。")
    if not any(_jenkins_path_matches(str(job), p) for p in allowed):
        return "当前账号没有 Job「%s」的授权（可见范围：%s）。" % (job, "、".join(allowed))
    return None


def _jenkins_get(source, path, params=None, timeout=30):
    """GET Jenkins，返回 (status_code, body, resp)。body 对 JSON 已解码。"""
    import requests as _requests

    from dvadmin.jenkins.views.jenkins import jenkins_auth

    base = (source.url or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("Jenkins 地址为空")
    resp = _requests.get(base + path, auth=jenkins_auth(source), params=params,
                         timeout=timeout, allow_redirects=False)
    ctype = resp.headers.get("Content-Type", "")
    if "json" in ctype:
        try:
            return resp.status_code, resp.json(), resp
        except ValueError:
            pass
    return resp.status_code, resp.text, resp


def _jenkins_fetch_jobs(source, path="", depth=0, max_depth=3, out=None):
    """递归拉 job 树（含 folder）。深度上限 3，节点上限 500 —— 防某个大 Jenkins 拖死。"""
    if out is None:
        out = []
    if depth > max_depth or len(out) >= 500:
        return out
    url_path = "/api/json"
    if path:
        url_path = "/job/%s/api/json" % _jenkins_job_path(path)
    try:
        code, body, _ = _jenkins_get(
            source, url_path, params={"tree": "jobs[name,url,color,_class]"}, timeout=30)
    except Exception:
        return out
    if code != 200 or not isinstance(body, dict):
        return out
    for j in (body.get("jobs") or []):
        name = j.get("name") or ""
        if not name:
            continue
        full = "%s/%s" % (path, name) if path else name
        jclass = j.get("_class") or ""
        is_folder = ("Folder" in jclass) or (not j.get("color"))
        out.append({
            "name": name,
            "full_path": full,
            "is_folder": is_folder,
            "color": j.get("color") or "",
            "url": j.get("url") or "",
        })
        if is_folder:
            _jenkins_fetch_jobs(source, full, depth + 1, max_depth, out)
        if len(out) >= 500:
            break
    return out


def tool_list_jobs(args, ctx):
    """列出 Jenkins job（按角色授权过滤）。"""
    source, err = _jenkins_source(args)
    if err:
        return _fail(err)

    try:
        jobs = _jenkins_fetch_jobs(source)
    except Exception as exc:
        return _fail("拉取 Jenkins Job 列表失败：%s" % exc)

    allowed = _jenkins_allowed_paths(ctx.user, source)
    if allowed is not None:
        if not allowed:
            return _fail("当前账号没有任何 Jenkins 目录授权，看不到任何 Job。"
                         "请让管理员在「发布 → Jenkins → 角色授权」里配置。")
        jobs = [j for j in jobs if any(_jenkins_path_matches(j["full_path"], p) for p in allowed)]

    keyword = (args.get("keyword") or "").strip().lower()
    if keyword:
        jobs = [j for j in jobs if keyword in j["full_path"].lower()]

    jobs_only = [j for j in jobs if not j["is_folder"]]
    out = {
        "ok": True,
        "source": source.name,
        "total": len(jobs_only),
        "returned": min(len(jobs_only), 100),
        "jobs": [{"full_path": j["full_path"], "color": j["color"]}
                 for j in jobs_only[:100]],
    }
    if not jobs_only:
        out["hint"] = ("没有匹配的 Job。若你确信存在，可能是当前账号没有该目录的授权，"
                       "如实告知用户即可，不要猜 Job 名。")
    return _dump(out)


def tool_list_builds(args, ctx):
    """列某个 Job 的最近构建。"""
    source, err = _jenkins_source(args)
    if err:
        return _fail(err)

    job = (args.get("job") or "").strip()
    if not job:
        return _fail("job 必填：先用 list_jobs 找到目标 Job 的 full_path，再查它的构建历史")
    denied = _jenkins_denied_reason(ctx, source, job)
    if denied:
        return _fail(denied)

    limit = _clamp(args.get("limit"), 1, 20, 5)
    tree = ("builds[number,result,timestamp,duration,displayName,building,description,"
            "actions[parameters[name,value]]]{0,%d}" % limit)
    try:
        code, body, _ = _jenkins_get(
            source, "/job/%s/api/json" % _jenkins_job_path(job),
            params={"tree": tree}, timeout=30)
    except Exception as exc:
        return _fail("获取构建历史失败：%s" % exc)

    if code == 404:
        return _fail("Job 不存在：%s。请先用 list_jobs 确认 full_path（嵌套目录要用 a/b 形式）。" % job)
    if code != 200 or not isinstance(body, dict):
        return _fail("获取构建历史失败 HTTP %s" % code)

    builds = []
    for b in (body.get("builds") or []):
        ts = b.get("timestamp")
        params = {}
        for act in (b.get("actions") or []):
            for p in (act.get("parameters") or []):
                nm = p.get("name")
                if nm:
                    params[nm] = p.get("value")
        builds.append({
            "number": b.get("number"),
            "result": b.get("result") or ("BUILDING" if b.get("building") else ""),
            "started_at": (datetime.fromtimestamp(ts / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
                           if isinstance(ts, (int, float)) else ""),
            "duration_seconds": int((b.get("duration") or 0) / 1000),
            "display_name": b.get("displayName") or "",
            "parameters": params,
        })

    out = {
        "ok": True,
        "job": job,
        "returned": len(builds),
        "builds": builds,
    }
    if not builds:
        out["hint"] = "该 Job 还没有构建记录，或构建已被清理。"
    elif any(b["result"] in ("FAILURE", "ABORTED") for b in builds):
        out["hint"] = ("存在失败构建。要分析原因，用 get_build_log 拉取**具体那次**的日志"
                       "（build 参数必填，不要用最后一次代替）。")
    return _dump(out)


# ============================================================
# 工具 8：get_build_log —— 核心是「裁剪」，不是「拉取」
#
# 为什么要裁剪：一个 Maven 构建的 console 有 5~50 MB、几万行，
# 而关键信息只集中在末尾那 20 行。整坨塞给模型有两个后果：
#   ① 上下文预算被一次调用吃光；② 关键行被几万行 INFO 淹没 ⇒ 模型开始编。
# 所以这里是**工具层做信息压缩**，而不是让模型自己翻。
# ============================================================
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# 失败锚点：按「越靠后越有可能是真因」倒序找最后一个命中
_BUILD_ANCHORS = (
    "BUILD FAILURE", "BUILD FAILED", "BUILD UNSTABLE",
    "Failed to execute goal", "Compilation failure",
    "ERROR:", "error:", "FAILURE:", "FAILED:",
    "Exception", "Traceback (most recent call last)",
    "fatal:", "npm ERR!", "error TS", "Non-zero exit code",
    "returned exit code", "command not found", "Permission denied",
)

# 噪音行：只删「明确无信息量」的，宁可多留不可错删
_BUILD_NOISE = (
    "Downloading from", "Downloaded from", "Progress (",
    "Downloading:", "Retrieving document", "Download complete",
)


def _is_build_noise(line):
    s = line.strip()
    if not s:
        return False
    return any(m in s for m in _BUILD_NOISE)


def _trim_build_log(text, max_lines=220, context=60, max_chars=8000):
    """把构建日志压成「失败现场」。

    返回的 `truncated` 语义是 **「这份日志不完整」**，不是「被截断了尾巴」——
    模型必须知道自己在看片段，否则会断言「整个构建没有别的错误」。
    """
    raw = text or ""
    total_bytes = len(raw.encode("utf-8", "ignore"))
    clean = _ANSI_RE.sub("", raw).replace("\r\n", "\n").replace("\r", "\n")
    lines = clean.split("\n")
    total_lines = len(lines)

    # ---- 定位最后一个失败锚点（失败信息几乎总在末尾）----
    anchor_idx = None
    for i in range(total_lines - 1, -1, -1):
        if any(a in lines[i] for a in _BUILD_ANCHORS):
            anchor_idx = i
            break

    if anchor_idx is None:
        lo = max(0, total_lines - max_lines)
        hi = total_lines
    else:
        lo = max(0, anchor_idx - context)
        hi = min(total_lines, anchor_idx + context + 1)
        if hi - lo > max_lines:
            hi = lo + max_lines

    snippet = lines[lo:hi]

    # ---- 去噪 + 压连续空行 ----
    filtered = []
    for line in snippet:
        if _is_build_noise(line):
            continue
        if not line.strip():
            if filtered and not filtered[-1].strip():
                continue
            filtered.append("")
            continue
        filtered.append(line)
    while filtered and not filtered[-1].strip():
        filtered.pop()

    body = "\n".join(filtered)
    cut_by_chars = len(body) > max_chars
    trimmed = body[:max_chars]

    return {
        "total_bytes": total_bytes,
        "total_lines": total_lines,
        "returned_lines": len(filtered),
        "returned_range": ("第 %d-%d 行" % (lo + 1, hi)) if hi > lo else "",
        "anchor_line": (anchor_idx + 1) if anchor_idx is not None else None,
        "anchor_text": (lines[anchor_idx].strip()[:200] if anchor_idx is not None else ""),
        "truncated": bool(lo > 0 or hi < total_lines or cut_by_chars),
        "log": trimmed,
    }


def _jenkins_fetch_log(source, job, build, max_bytes=4 * 1024 * 1024, max_rounds=8):
    """增量拉构建日志，累计上限 max_bytes。返回 (text, hit_cap)。

    ★ 不用 lastBuild：用户问的往往是历史上某一次失败，拿最后一次会答非所问。
    """
    chunks, start, hit_cap = [], 0, False
    path = "/job/%s/%s/logText/progressiveText" % (_jenkins_job_path(job), build)
    for _ in range(max_rounds):
        code, body, resp = _jenkins_get(source, path, params={"start": start}, timeout=60)
        if code == 404:
            raise RuntimeError("构建不存在：%s #%s（请用 list_builds 确认编号）" % (job, build))
        if code != 200:
            raise RuntimeError("获取日志失败 HTTP %s" % code)

        text = body if isinstance(body, str) else str(body)
        chunks.append(text)

        size_hdr = resp.headers.get("X-Text-Size")
        try:
            start = int(size_hdr) if size_hdr else start + len(text.encode("utf-8"))
        except (TypeError, ValueError):
            start = start + len(text.encode("utf-8"))

        more = (resp.headers.get("X-More-Data") or "false").lower() == "true"
        if not more:
            break
        if start >= max_bytes:
            hit_cap = True
            break
    return "".join(chunks), hit_cap


def tool_get_build_log(args, ctx):
    """拉某次构建的日志并裁剪。"""
    source, err = _jenkins_source(args)
    if err:
        return _fail(err)

    job = (args.get("job") or "").strip()
    if not job:
        return _fail("job 必填：先用 list_jobs 找到 full_path")

    build = str(args.get("build") or "").strip()
    if not build:
        return _fail("build 必填：必须显式给出构建编号（先用 list_builds 拿到）。"
                     "不要用 lastBuild 代替 —— 用户问的可能是历史上某一次失败。")
    if not build.isdigit():
        return _fail("build 必须是数字编号，收到：%s" % build)

    denied = _jenkins_denied_reason(ctx, source, job)
    if denied:
        return _fail(denied)

    try:
        text, hit_cap = _jenkins_fetch_log(source, job, build)
    except Exception as exc:
        return _fail("拉取构建日志失败：%s" % exc)

    trimmed = _trim_build_log(text)
    out = {
        "ok": True,
        "job": job,
        "build": build,
        "source": source.name,
        "fetch_hit_cap": hit_cap,
    }
    out.update(trimmed)

    if out["truncated"] or hit_cap:
        out["note"] = ("★ 你看到的是**片段**，不是完整日志。"
                       "禁止基于它断言「整个构建没有其他错误」。")
    else:
        out["note"] = "这是完整日志。"
    if out["anchor_line"] is None:
        out["note"] += " 未找到失败锚点，已取日志尾部（失败信息通常就在末尾）。"
    return _dump(out)


def _targets(items):
    return [it.get("res") or {"server_id": it["sid"], "server": it["label"],
                              "ip": it["ip"], "status": "error",
                              "error": it.get("err") or "未执行"}
            for it in items]


def _reject_all(ctx, items, base, reason, status):
    """命令被拦 / 开关关闭 / 无凭据时，为每个目标写一行台账。

    审计要看得见「AI 想干什么、被什么拦住」—— 只记成功调用的台账没有价值。
    """
    for it in items:
        _write_ledger(ctx, server=it["server"], server_label=it["label"], ip=it["ip"],
                      status=status, reject_reason=reason[:500], **base)
        it["res"] = {"server_id": it["sid"], "server": it["label"], "ip": it["ip"],
                     "status": status, "error": reason}


def _run_on_server(item, command, payload, timeout, ctx, max_chars, purpose):
    """单台执行 → 脱敏 → 截断 → 台账。异常一律吃掉（结果写进 item['res']）。"""
    server = item["server"]
    common = {"server": server, "server_label": item["label"], "ip": item["ip"],
              "tool_name": "run_readonly_command", "command": command,
              "purpose": (purpose or "")[:255]}
    try:
        from dvadmin.bastion.ssh_client import ssh_exec

        res = ssh_exec(
            host=server.ip,
            port=server.ssh_port or 22,
            username=payload.get("username") or "root",
            auth_type=payload.get("auth_type") or "password",
            password=payload.get("password"),
            private_key=payload.get("private_key"),
            command=command,
            timeout=timeout,
        )
    except Exception as exc:                     # 连接 / 认证 / 超时
        msg = str(exc) or exc.__class__.__name__
        _write_ledger(ctx, status="failed", reject_reason=msg[:500], **common)
        item["res"] = {"server_id": item["sid"], "server": item["label"],
                       "ip": item["ip"], "status": "failed", "error": msg}
        return

    # ★ 顺序：先脱敏、再截断。反过来的话，跨越截断点的密钥会被切成两半，前半截照样出境。
    stdout, hits_out = ctx.mask(res.get("stdout") or "")
    stderr, hits_err = ctx.mask(res.get("stderr") or "")
    exit_code = res.get("exit_code")
    err = res.get("error") or ""

    if err:
        status = "failed"
    elif exit_code == 0:
        status = "success" if (stdout.strip() or stderr.strip()) else "empty"
    else:
        status = "failed"

    _write_ledger(
        ctx, status=status, exit_code=exit_code, duration=res.get("duration"),
        stdout_excerpt=_truncate(stdout, LEDGER_EXCERPT_CHARS),
        stderr_excerpt=_truncate(stderr, LEDGER_EXCERPT_CHARS),
        desensitized="、".join([h for h in (hits_out, hits_err) if h])[:255],
        reject_reason=err[:500], **common)

    item["res"] = {
        "server_id": item["sid"],
        "server": item["label"],
        "ip": item["ip"],
        "status": status,
        "exit_code": exit_code,
        "duration": res.get("duration"),
        "stdout": _truncate(stdout, max_chars),
        "stderr": _truncate(stderr, max_chars),
    }
    if err:
        item["res"]["error"] = err


# ============================================================
# 分发
# ============================================================
REGISTRY = {
    "list_servers": tool_list_servers,
    "run_readonly_command": tool_run_readonly_command,
    "query_alerts": tool_query_alerts,
    "query_logs": tool_query_logs,
    "query_metrics": tool_query_metrics,
    "list_jobs": tool_list_jobs,
    "list_builds": tool_list_builds,
    "get_build_log": tool_get_build_log,
}


def execute_tool(name, args, ctx):
    """执行工具，返回**回灌给模型**的字符串。任何异常都转成可读中文，不抛给上层。"""
    func = REGISTRY.get(name)
    if func is None:
        return _fail("未知工具「%s」。可用工具：%s" % (name, "、".join(sorted(REGISTRY))))
    if not isinstance(args, dict):
        return _fail("工具参数必须是 JSON 对象")
    try:
        return func(args, ctx)
    except Exception as exc:
        logger.exception("AI 工具执行异常：%s", name)
        return _fail("工具「%s」执行出错：%s" % (name, str(exc)[:300]))
