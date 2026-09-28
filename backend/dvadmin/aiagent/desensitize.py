# -*- coding: utf-8 -*-
"""
外发前脱敏 —— 命令输出 / 用户提问在**离开本机之前**先把凭据抹掉。

为什么必须有这一层
------------------
「智能问答」会把命令输出（`docker inspect` 的环境变量、`env`、配置文件片段、
`ss -p` 的进程名 …）拼进 prompt 发给外部大模型厂商。运维排查时这些输出里
**经常**夹着密码、Token、连接串 —— `docker inspect` 会原样回显容器的
`MYSQL_ROOT_PASSWORD`，这是最常见的泄漏路径。
一旦外发就收不回来，所以过滤必须发生在**出境之前**，不能事后补。

★ 脱敏发生在「入库时」而不是「发送时」
   用户提问与工具输出都是**先脱敏、再写进会话**。好处有两个：
     1. 会话表里永远不落明文凭据（出事时"我们存过什么"是干净的）
     2. 每轮请求不用对整段历史重复扫一遍，开销恒定
   代价是用户在页面上看到自己输入里的敏感值也变成 `***` —— 这是刻意接受的。

两层规则
--------
1. **内置形态**（本文件的 `_RULES`）：云厂商 AK、`sk-` 密钥、GitHub/GitLab/Slack
   token、JWT、Bearer、PEM 私钥块、`KEY=value` 键值对、`scheme://user:pass@host`。
   这些是「通用凭据形态」，与业务无关，恒定生效。
2. **自定义关键词**（页面上维护，`AiGuardConfig.desensitize_keywords`）：一行一个，
   纯**子串**匹配。★ 刻意不用正则 —— 页面上写错一个正则会让整条链路 500，
   而子串写错最坏只是不命中。少于 3 个字符的关键词会被忽略（`a` / `1` 这类会误伤一切）。

设计取向：**宁可多抹**。多抹一行的代价是模型少一点上下文；漏抹一个密码的代价不可逆。
"""
import re

MASK = "***"

# 自定义关键词的最短长度：太短会误伤（例如把 "id" 抹成 ***）
MIN_KEYWORD_LEN = 3

# 需要打码的键名特征（键名保留，只抹值 —— 让模型仍然看得出"这里有个密码字段"）
_KEY_HINT = (r"[A-Za-z0-9_]*(?:"
             r"pass(?:word|wd)?|passphrase|pwd|secret|token|api[_-]?key|access[_-]?key|"
             r"private[_-]?key|credential|auth"
             r")[A-Za-z0-9_]*")


def _build_rules():
    """构建 (标签, 正则, 替换串) 列表。正则写坏时跳过该条，不影响其它规则。

    ★ 顺序**有语义**：先跑「凭据形态」再跑「键值对」。
      反例（实盘踩过）：`Authorization: Bearer eyJ...` 若先跑键值对，`auth` 命中键名、
      把值 `Bearer` 当成口令抹掉，真正的 token 原样留在后面出境。
      ⇒ 形态规则在前，键值对在后兜底。
    """
    rules = []

    def add(label, pattern, repl):
        try:
            rules.append((label, re.compile(pattern, re.I | re.S), repl))
        except re.error:
            # 内置规则写坏是我们的问题，但不该让整个功能不可用 —— 跳过并继续
            pass

    # ---------- 第一组：凭据「形态」识别（不依赖键名） ----------

    # 1) PEM 私钥块：整块抹掉（可能跨多行，依赖 re.S）
    add("私钥块",
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
        MASK)

    # 2) URL 内嵌口令：mysql://root:Passw0rd@10.0.0.1:3306/db
    #    保留协议与用户名，只抹口令 —— 让模型知道"这是个带认证的连接串"
    add("URL 内嵌口令",
        r"([a-zA-Z][a-zA-Z0-9+.\-]*://[^/\s:@]{1,64}):([^/\s@]{1,128})@",
        r"\1:" + MASK + "@")

    # 3) 各家 Token / AccessKey 形态
    add("云厂商 AccessKey", r"\b(?:AKIA|ASIA|LTAI|AKID)[A-Za-z0-9]{12,}", MASK)
    add("sk- 密钥", r"\bsk-[A-Za-z0-9_\-]{16,}", MASK)
    add("GitHub Token", r"\bgh[pousr]_[A-Za-z0-9]{20,}", MASK)
    add("GitLab Token", r"\bglpat-[A-Za-z0-9_\-]{16,}", MASK)
    add("Slack Token", r"\bxox[baprs]-[A-Za-z0-9\-]{10,}", MASK)
    # 三段式 JWT（`eyJ` 开头的 header.payload.signature）
    add("JWT", r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}", MASK)
    # HTTP 认证头：Bearer / Basic。★ 长度不设下限 ——
    #   `Bearer abc123` 这种短 token 同样是凭据，而 "Bearer" 这个词在只读命令输出里
    #   几乎不会以别的语义出现，抹掉没有误伤风险。
    add("Bearer 头", r"\bBearer\s+[A-Za-z0-9._\-]+", "Bearer " + MASK)
    add("Basic 头", r"\bBasic\s+[A-Za-z0-9+/=]{8,}", "Basic " + MASK)

    # ---------- 第二组：键值对兜底 ----------

    # 4) 键值对：MYSQL_ROOT_PASSWORD=xxx / "password": "xxx" / redis_pass: xxx
    #    ★ 键名两侧允许下划线，所以不能用 \b（MYSQL_ROOT_PASSWORD 里 PASSWORD
    #      前面是下划线，\b 不成立，会漏掉 —— 这是最常见的那个漏点）
    #    ★ 键名两侧还允许引号（JSON 里的 "DB_PASSWORD"），否则 JSON 全漏
    #    ★ 值不能是 Bearer/Basic/Digest 这类「认证方案词」本身：
    #      `Authorization: Bearer xxx` 的值是 Bearer，抹它等于放走后面的 token
    add("键值对口令",
        r"([\"']?" + _KEY_HINT + r"[\"']?\s*[:=]\s*)(?P<q>[\"']?)"
        r"(?!(?:Bearer|Basic|Digest|Token|Apikey)\b)"
        r"([^\s\"',;}]{3,})(?P=q)",
        r"\1\g<q>" + MASK + r"\g<q>")

    return rules


_RULES = _build_rules()


def parse_keywords(text):
    """把页面上「一行一个」的关键词文本解析成列表（去空行、去注释、去重）。"""
    out, seen = [], set()
    for raw in (text or "").splitlines():
        kw = raw.strip()
        if not kw or kw.startswith("#"):
            continue
        if kw not in seen:
            seen.add(kw)
            out.append(kw)
    return out


def mask(text, extra_keywords=None):
    """脱敏。返回 ``(脱敏后文本, [命中的规则标签])``。

    :param text: 待脱敏文本（None 安全）
    :param extra_keywords: 额外的**子串**关键词列表（来自护栏配置）
    """
    if not text:
        return text or "", []
    out = text
    hits = []
    for label, rx, repl in _RULES:
        out, n = rx.subn(repl, out)
        if n:
            hits.append("%s×%d" % (label, n))
    for kw in (extra_keywords or []):
        kw = (kw or "").strip()
        if len(kw) < MIN_KEYWORD_LEN:
            continue
        if kw in out:
            cnt = out.count(kw)
            out = out.replace(kw, MASK)
            hits.append("自定义:%s×%d" % (kw, cnt))
    return out, hits


def mask_or_keep(text, enabled=True, extra_keywords=None):
    """带开关的便捷入口。``enabled=False`` 时原样返回（仍返回空 hits）。"""
    if not enabled:
        return text or "", []
    return mask(text, extra_keywords)
