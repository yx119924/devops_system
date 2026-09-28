# -*- coding: utf-8 -*-
"""
命令护栏 —— 本功能的**安全核心**。

设计要点（很重要，改动前先读）：
1. **默认拒绝**：不在白名单内的命令一律拒绝，不是"黑名单拦截"。
2. **分段校验**：整条命令先按 shell 连接符（`;` `&&` `||` `|`）切成段，
   **每一段都要单独过关**。否则 `uptime; rm -rf /` 会因为 `uptime` 命中白名单而整体放行。
3. **元字符拦截**：`>` `<` 反引号 `$(` `${` 一律拒绝（写文件 / 命令替换）。
4. **路径黑名单**：即使命令本身在白名单内（如 `grep`、`tail`），
   只要参数里出现凭据类路径，一样拒绝。
5. 黑名单优先于白名单。

任何一条被拒都会把原因返回给大模型，让它换一条命令，而不是中断对话。
"""
import re

# shell 连接符：用来把复合命令切段
_SEPARATOR_RE = re.compile(r"\|{2}|&&|;|\|")

# 危险元字符：重定向 / 命令替换。单个 $ 不算（awk 里常见），只拦 $( 和 ${
_META_RE = re.compile(r"[><`]|\$\(|\$\{")

# 排版用：把连续空白折成一个空格，便于前缀匹配
_WS_RE = re.compile(r"\s+")


def split_command(command):
    """把复合命令切成独立段（丢弃空段）。"""
    if not command:
        return []
    return [seg.strip() for seg in _SEPARATOR_RE.split(command) if seg and seg.strip()]


def parse_rules(text):
    """把「一行一条」的规则文本解析成规则列表。

    去空行、去 `#` 注释、折叠空白、按原顺序去重。
    """
    rules, seen = [], set()
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = _WS_RE.sub(" ", line)
        if line not in seen:
            seen.add(line)
            rules.append(line)
    return rules


def _match_prefix(segment, rule):
    """前缀匹配 + 边界判断。

    边界：规则后必须接空格或正好结束，否则白名单里的 `cat` 会错误放行 `catalog`。

    例外：规则以 `-` 结尾时（如黑名单 `hostnamectl set-`），
    后面直接接字母数字也算命中 —— 否则 `hostnamectl set-hostname x` 会漏网（实测踩过）。
    """
    if segment == rule:
        return True
    if not segment.startswith(rule):
        return False
    nxt = segment[len(rule)]
    if nxt == " ":
        return True
    return rule.endswith("-") and (nxt.isalnum() or nxt == "-")


def check_command(command, allowed, denied, denied_paths):
    """校验一条命令是否可以执行。

    :param command: 模型给出的原始命令
    :param allowed: 白名单规则列表（parse_rules 的结果）
    :param denied: 黑名单规则列表
    :param denied_paths: 敏感路径列表（子串匹配）
    :return: (ok: bool, reason: str, segments: list[str])
    """
    segments = split_command(command)
    if not segments:
        return False, "命令为空", []

    if _META_RE.search(command):
        return False, "命令包含重定向或命令替换（>、<、反引号、$()），已拒绝", segments

    for seg in segments:
        for rule in denied:
            # 黑名单用**纯前缀**、不要求边界：目的是"宁可多拦"。
            # 这样 `journalctl --vacuum-size=100M`、`date --set=2020-01-01`
            # 这类「长选项带值」的写法才会被 `--vacuum` / `--set` 覆盖到
            # （白名单反过来要求边界，防止 `cat` 放行 `catalog`）。
            if seg.startswith(rule):
                return False, "命中危险命令黑名单「%s」，已拒绝：%s" % (rule, seg), segments

        for path in denied_paths:
            if path and path in seg:
                return False, "命中敏感路径黑名单「%s」，已拒绝：%s" % (path, seg), segments

        if not any(_match_prefix(seg, rule) for rule in allowed):
            return False, "不在只读白名单内，已拒绝：%s" % seg, segments

    return True, "", segments


def load_guard_rules():
    """从 AiGuardConfig 读出已解析的规则。供 agent / tools 调用。

    ★ 这是护栏的**唯一读入口**：agent 与 tools 都从这里拿，
      避免两处各自 `AiGuardConfig.load()` 后口径跑偏（比如只在一处读 enabled_tools）。
    """
    from dvadmin.aiagent.models import AiGuardConfig

    cfg = AiGuardConfig.load()
    return {
        "allowed": parse_rules(cfg.allowed_commands),
        "denied": parse_rules(cfg.denied_commands),
        "denied_paths": parse_rules(cfg.denied_paths),
        # 两层开关
        "readonly_mode": cfg.readonly_mode,
        "enabled_tools": cfg.enabled_tools,
        # 数据外发边界
        "desensitize": cfg.desensitize,
        "desensitize_keywords": cfg.desensitize_keywords,
        # 运行参数
        "command_timeout": cfg.command_timeout,
        "max_servers": cfg.max_servers,
        "max_workers": cfg.max_workers,
        "max_rounds": cfg.max_rounds,
        "max_output_chars": cfg.max_output_chars,
        "chat_timeout": cfg.chat_timeout,
        "daily_round_limit": cfg.daily_round_limit,
        "daily_token_limit": cfg.daily_token_limit,
    }
