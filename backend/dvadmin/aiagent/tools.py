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
from concurrent.futures import ThreadPoolExecutor

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
        row = AiToolCall(session=ctx.session, owner=ctx.user,
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
