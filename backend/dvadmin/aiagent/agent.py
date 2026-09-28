# -*- coding: utf-8 -*-
"""
智能问答 —— Agent 主循环。

一次提问的完整过程
------------------
   配额门禁 → 脱敏用户提问 → 组装 messages → [模型 ↔ 工具] 循环 → 收敛回答 → 落库

设计取舍（改动前先读）
----------------------
1. **同步执行，不用 Celery / SSE**
   本项目「命令下发」的 execute 就是同步阻塞返回最终结果，这里沿用同一套惯例：
   前端发一个请求、转圈、拿完整回答。少一个任务表、少一个轮询接口、少一套状态机。
   代价是单次请求较长 —— 所以有 `chat_timeout` 上限（默认 90s），
   而网关的 `proxy_read_timeout` 是 600s，余量足够。
   真到了感觉慢的规模，再换 Celery + 轮询，接口形状不用变。
2. **无工具可用时不下发 tools**
   `enabled_tools=False` 时直接不带 tools 参数 —— 让模型**没有机会**发起工具调用，
   而不是发起后我们再拒绝。前者在 prompt 里就没有越权的想象力。
3. **轮次/时长都到上限时，再要一次"无工具"的收尾回答**
   否则用户会看到"达到上限了但没有结论"。多花一次调用换一个可用的结论，值。
4. **消息里存的是脱敏后的内容**
   见 desensitize.py 的说明：入库即脱敏，会话表永远不落明文凭据。
"""
import json
import logging
import time

from django.db.models import F
from django.utils import timezone

from dvadmin.aiagent import tools as ai_tools
from dvadmin.aiagent.guard import load_guard_rules
from dvadmin.aiagent.providers.base import ProviderError
from dvadmin.aiagent.providers.openai_compat import get_provider
from dvadmin.aiagent.tools import ToolContext, execute_tool

logger = logging.getLogger(__name__)

# 上下文预算：messages 里所有 content 的总字符数超过它就裁剪最早的 tool 输出。
# 12 轮 × 每条命令最多 8000 字符 ≈ 10 万字符，正常用不到；这是防"模型一次要 20 台机器输出"的兜底。
PROMPT_CHAR_BUDGET = 240000
TRIMMED_MARK = "（早期输出已省略：为控制上下文长度）"

# 达到轮次/时长上限时追加的收尾指令（会留在 messages 里，审计能看到模型被告知了什么）
CONVERGE_HINT = ("（系统提示：本次排查已达到轮次或时长上限，"
                 "请立刻基于上面已有的命令输出给出当前结论与下一步建议，不要再调用工具。）")


class AgentError(Exception):
    """可以直接展示给用户的中文错误。"""


# ============================================================
# 提示词
# ============================================================
SYSTEM_PROMPT = """你是 XwOps 运维平台的「智能问答」助手，服务对象是运维工程师。

## 你的能力边界（硬性，不可协商）
1. 你**只能只读排查**：查 CMDB 资产清单，以及在被授权的服务器上执行白名单内的只读命令。
2. 你**没有任何写权限**：不能改配置、重启服务、装软件、删文件、改网络。
   用户要求这类操作时，直说"我没有写权限"，并给出他自己能执行的命令与注意事项。
3. 命令**一条一条来**：不允许用 `;` `&&` `||` `|` 拼接，不允许重定向 `>` `<`，
   不允许 `$( )`。被执行器拒绝时看拒绝原因换一条合规命令，**不要反复重试同一条**。
4. 你只能操作 `list_servers` 返回的服务器；工具只认 `server_id`，**不认 IP**。
   没授权的机器就直接说没权限，不要试图绕过。
5. 命令输出在回灌给你之前已被**脱敏**（凭据类内容会变成 `***`）。
   看到 `***` 说明这里原本是敏感值，**不要去猜、也不要提示用户把明文发给你**。

## 工作方式
1. **先弄清目标**：用户说"服务器很慢"时，先用 `list_servers` 定位机器；
   目标不明确就**问清楚**是哪台/哪个业务，不要随便挑一台就开干。
2. **先查后断**：每个结论都要有命令输出支撑。别凭经验断言"CPU 高、磁盘满"——先跑命令看真实数据。
3. **每步写清理由**：`purpose` 要说明这一步在验证什么假设，它会进审计台账。
4. **控制范围**：先 1~2 台验证思路，确认有效再扩大，一次别铺开太多台。
5. **绝不编造**：命令失败、输出为空、被拒绝，都如实说明。绝不虚构命令输出或编造数字。

## 回答格式（中文，简洁、可执行）
- **现象**：从输出里读到的客观事实（带具体数字）
- **判断**：最可能的原因 + 支撑它的证据；不确定就明说"不确定，需要再看 X"
- **建议**：下一步查什么 / 怎么处理（涉及写操作的，给出命令让人来执行）

不要输出 emoji，不要客套话，不要重复用户的问题。"""


def _wire_tool_call(call):
    """把 ToolCall 还原成 OpenAI 协议的 assistant.tool_calls 元素。"""
    return {
        "id": call.id or "",
        "type": "function",
        "function": {
            "name": call.name or "",
            "arguments": json.dumps(call.arguments or {}, ensure_ascii=False),
        },
    }


def build_system_prompt(user, session, rules, server_count):
    """在固定人格 prompt 后面追加本次运行时的环境事实。

    ★ 把"有几台机器、能不能跑命令"明确写进 prompt：模型据此在**第一轮**就知道
      自己该不该调工具，而不是先调一次被拒绝了再改口。
    """
    cred = session.credential
    cred_txt = "未选定凭据（无法建立 SSH 连接）" if cred is None else \
        "%s（登录用户名 %s，认证方式 %s）" % (
            cred.name, cred.username or "root",
            "密码" if cred.auth_type == "password" else "私钥")
    tools_ok = bool(rules.get("enabled_tools", True)) and bool(rules.get("readonly_mode", True))
    lines = [
        "",
        "## 本次会话的运行时环境",
        "- 提问用户：%s" % (getattr(user, "name", None) or getattr(user, "username", "")),
        "- 会话凭据：%s" % cred_txt,
        "- 你可操作的服务器：%s 台（只能操作这些；用 list_servers 查清单）" % server_count,
        "- 命令执行能力：%s" % ("可用（仅白名单内的只读命令）" if tools_ok
                            else "★ 当前不可用 —— 只能基于 CMDB 信息与常识作答，不要尝试调用工具"),
        "- 预算：本次最多 %s 次工具调用轮次、总时长 %s 秒" % (
            rules.get("max_rounds"), rules.get("chat_timeout")),
    ]
    return SYSTEM_PROMPT + "\n".join(lines)


# ============================================================
# 配额
# ============================================================
def _today():
    """今天的自然日（Asia/Shanghai）。

    ★★ 不要写 `timezone.localdate()`（09-23 线上事故，整个问答页打不开）：
      它内部就是 `localtime(now()).date()`，而 `localtime()` 是**只接受 aware 值**的，
      对 naive datetime 直接抛
      `ValueError: localtime() cannot be applied to a naive datetime`。
      本项目 `USE_TZ=False` → `timezone.now()` 返回 **naive** → 这一行**必然炸**。
      而 `check_quota()`/`bump_usage()`/`usage_snapshot()` 全走它，
      于是 `/api/aiagent/chat/options/` 500 → 前端只看到「获取配置失败」。

    ⇒ 正确写法：用 `now()` 取"当前时刻"，**只在它是 aware 时**才转本地时区。
      这样 `USE_TZ` 无论开还是关都对（关：now() 已是本地墙钟时间；开：now() 是 UTC，
      经 localtime() 换成 Asia/Shanghai，不会差一天）。
    """
    now = timezone.now()
    if timezone.is_aware(now):
        now = timezone.localtime(now)
    return now.date()


def check_quota(user, rules):
    """按人按天的配额门禁。超了就抛 AgentError（中文，可直接展示）。"""
    from dvadmin.aiagent.models import AiUsage

    limit_rounds = int(rules.get("daily_round_limit") or 0)
    limit_tokens = int(rules.get("daily_token_limit") or 0)
    used = AiUsage.objects.filter(owner=user, day=_today()).first()
    if used is None:
        return
    if limit_rounds and used.rounds >= limit_rounds:
        raise AgentError("你今天已经用满 %s 轮 AI 排查（当前 %s 轮），"
                         "明天再试。这个上限是为了防止模型调用把额度刷爆，"
                         "需要临时放宽请联系管理员。" % (limit_rounds, used.rounds))
    if limit_tokens and used.tokens >= limit_tokens:
        raise AgentError("你今天已经用满 %s token 的 AI 额度（当前 %s），"
                         "明天再试或联系管理员放宽。" % (limit_tokens, used.tokens))


def bump_usage(user, rounds, tokens):
    """累计今日用量。失败只记日志 —— 配额统计不该让一次正常问答失败。"""
    from dvadmin.aiagent.models import AiUsage

    try:
        obj, _created = AiUsage.objects.get_or_create(owner=user, day=_today())
        AiUsage.objects.filter(pk=obj.pk).update(
            rounds=F("rounds") + int(rounds or 0),
            tokens=F("tokens") + int(tokens or 0),
            requests=F("requests") + 1)
    except Exception:
        logger.exception("累计 AI 用量失败")


def usage_snapshot(user):
    """给前端显示"今天用了多少 / 上限多少"。"""
    from dvadmin.aiagent.models import AiUsage

    rules = load_guard_rules()
    used = AiUsage.objects.filter(owner=user, day=_today()).first()
    return {
        "day": str(_today()),
        "rounds": used.rounds if used else 0,
        "round_limit": rules.get("daily_round_limit"),
        "tokens": used.tokens if used else 0,
        "token_limit": rules.get("daily_token_limit"),
        "requests": used.requests if used else 0,
    }


# ============================================================
# 上下文裁剪
# ============================================================
def _total_chars(messages):
    return sum(len(m.get("content") or "") for m in messages)


def _trim_messages(messages, budget=PROMPT_CHAR_BUDGET):
    """超出预算时，从最早的 tool 输出开始替换成占位符。

    ★ 只动 `role == 'tool'` 的 content，**不删消息**：
      删掉会让 assistant.tool_calls 与 tool 消息失去配对，上游直接报协议错误。
    """
    if _total_chars(messages) <= budget:
        return messages
    for msg in messages:
        if _total_chars(messages) <= budget:
            break
        if msg.get("role") == "tool" and len(msg.get("content") or "") > len(TRIMMED_MARK):
            msg["content"] = TRIMMED_MARK
    return messages


# ============================================================
# 主循环
# ============================================================
def run_turn(session, question, user, rules=None):
    """跑一轮问答。返回 dict（回答 + 本轮统计）。失败抛 AgentError / ProviderError。

    :param session: AiChatSession 实例（已保存；messages 会被**原地更新并保存**）
    :param question: 用户本次输入（明文，函数内部先脱敏）
    :param user: 当前登录用户（必须 == session.owner）
    """
    from dvadmin.bastion.access import is_asset_admin, writable_server_ids

    rules = rules or load_guard_rules()

    # ---- 模型配置校验：只认本人的、启用中的配置 ----
    cfg = session.provider
    if cfg is None:
        raise AgentError("本次会话使用的模型配置已被删除。请到「模型配置」新建一条，"
                         "然后开启新会话。")
    if cfg.owner_id and cfg.owner_id != user.pk:
        # 理论上不可能（会话本身按人隔离），防御性检查
        raise AgentError("本次会话绑定的模型配置不属于当前用户，已拒绝调用")
    if not cfg.enabled:
        raise AgentError("本次会话使用的模型配置「%s」已被停用，"
                         "请到「模型配置」启用它，或换一条后新建会话。" % cfg.name)
    if not cfg.get_api_key():
        raise AgentError("模型配置「%s」还没填 API Key，请到「模型配置」补上。" % cfg.name)

    check_quota(user, rules)

    provider = get_provider(cfg)
    ctx = ToolContext(user, session, rules)
    max_rounds = max(1, min(int(rules.get("max_rounds") or 12), 30))
    chat_timeout = max(15, int(rules.get("chat_timeout") or 90))
    tools_enabled = bool(rules.get("enabled_tools", True)) and bool(rules.get("readonly_mode", True))

    # ---- 用户提问：先脱敏，再入库 ----
    masked_q, q_hits = ctx.mask(question)

    server_count = "全部" if is_asset_admin(user) else len(writable_server_ids(user) or [])

    messages = list(session.messages or [])
    if not messages:
        messages = [{"role": "system",
                     "content": build_system_prompt(user, session, rules, server_count)}]
    messages.append({"role": "user", "content": masked_q})

    started = time.time()
    rounds = 0
    used_tools = 0
    tokens = 0
    answer = ""
    stop_reason = "answered"
    tool_trace = []          # 给前端做「工具调用折叠展示」

    def _persist(status, last_error=""):
        """把本轮结果写回会话。★ 出错路径也要写 —— 否则用户的提问会凭空消失。"""
        session.messages = messages
        session.rounds = (session.rounds or 0) + rounds
        session.tool_count = (session.tool_count or 0) + used_tools
        session.total_tokens = (session.total_tokens or 0) + tokens
        session.status = status
        session.last_error = last_error
        if not session.title:
            session.title = masked_q[:40]
        session.save(update_fields=["messages", "rounds", "tool_count", "total_tokens",
                                    "status", "last_error", "title"])

    try:
        while True:
            if time.time() - started > chat_timeout:
                stop_reason = "timeout"
                break
            if rounds >= max_rounds:
                stop_reason = "max_rounds"
                break

            result = provider.chat(messages,
                                   tools=(ai_tools.TOOLS if tools_enabled else None))
            rounds += 1
            tokens += result.total_tokens or 0

            if not result.tool_calls:
                answer = (result.content or "").strip()
                messages.append({"role": "assistant", "content": result.content or ""})
                break

            messages.append({"role": "assistant", "content": result.content or "",
                             "tool_calls": [_wire_tool_call(c) for c in result.tool_calls]})
            ctx.round_index = rounds
            for call in result.tool_calls:
                out = execute_tool(call.name, call.arguments, ctx)
                used_tools += 1
                try:
                    parsed = json.loads(out)
                except ValueError:
                    parsed = {"raw": out}
                tool_trace.append({
                    "round": rounds, "tool": call.name,
                    "arguments": call.arguments,
                    "ok": bool(parsed.get("ok")),
                    "error": parsed.get("error") or "",
                    "command": parsed.get("command") or "",
                    "summary": parsed.get("summary") or None,
                    "targets": _trace_targets(parsed.get("targets") or []),
                })
                messages.append({"role": "tool", "tool_call_id": call.id or "",
                                 "name": call.name, "content": out})
            messages = _trim_messages(messages)

        # ---- 到上限了就再要一次"不带工具"的收尾回答 ----
        if not answer and stop_reason in ("timeout", "max_rounds"):
            messages.append({"role": "user", "content": CONVERGE_HINT})
            try:
                closing = provider.chat(messages, tools=None)
                rounds += 1
                tokens += closing.total_tokens or 0
                answer = (closing.content or "").strip()
                messages.append({"role": "assistant", "content": closing.content or ""})
            except ProviderError as exc:
                logger.warning("收尾回答失败：%s", exc)
            if not answer:
                answer = ("本次排查已用完 %s 次工具调用（%s），但还没能收敛出完整结论。"
                          "上面列出的命令输出就是当前掌握的线索，建议人工接着看；"
                          "也可以把问题拆小一点再问一次。"
                          % (max_rounds, "达到轮次上限" if stop_reason == "max_rounds"
                             else "达到时长上限"))
    except ProviderError as exc:
        # 调用大模型失败：保住提问上下文 + 记下原因，让用户能直接重试
        _persist("failed", str(exc)[:2000])
        raise

    _persist("active")
    bump_usage(user, rounds, tokens)

    return {
        "session_id": session.pk,
        "answer": answer,
        "rounds": rounds,
        "tools": used_tools,
        "tokens": tokens,
        "elapsed": round(time.time() - started, 2),
        "stop_reason": stop_reason,
        "desensitized": bool(q_hits),
        "tool_trace": tool_trace,
        "usage": usage_snapshot(user),
    }


# 前端「工具调用折叠展示」里每台机器的输出回显上限（完整片段在台账里看）
TRACE_CHARS = 1500


def _trace_targets(targets):
    """裁剪回给前端的 targets，避免响应体被命令输出撑爆。"""
    out = []
    for t in targets:
        if not isinstance(t, dict):
            continue
        item = dict(t)
        for key in ("stdout", "stderr"):
            val = item.get(key) or ""
            if len(val) > TRACE_CHARS:
                item[key] = val[:TRACE_CHARS] + "\n…（完整片段见「工具调用台账」）"
        out.append(item)
    return out
