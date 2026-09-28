# -*- coding: utf-8 -*-
"""日志采集通道：生成 / 下发 / 停止 filebeat 配置片段，并检测目标机环境。

调用链
------
``views/collect.py``  →  ``log/collector.py``  →  ``bastion/ssh_client.ssh_exec``

设计约束（改这个文件前先读完，每条都是踩过的坑）
-------------------------------------------------
1. **不自己写采集器**。offset / 文件轮转 / 多行合并 / 背压 / at-least-once
   全部交给 filebeat；平台只做「生成配置 → 下发 → 回显」。自己实现这些
   在日志量面前一定会撞天花板（内网 myapp 一天 2.3 亿条 / 57GB）。

2. **★ RE2 兼容性必须前置拦截**。filebeat 用 Go 的 RE2，**不支持**
   ``(?=...)`` / ``(?!...)`` / ``(?<=...)`` / ``(?<!...)`` / ``\\1`` 反向引用 /
   原子组 / 递归。这些正则在 Python 里能编译通过 —— 于是「规则试跑」会显示
   一切正常，下发后 filebeat 却**起不来**（配置解析失败）。
   所以：``check_re2_compatible()`` 在**试跑和下发的两个入口都要跑**，
   宁可在这里拦住，也不要在目标机上把 filebeat 弄挂。

3. **★ 不谎称能控制索引名**。filebeat 的 ``index`` 是 **output 级**配置，
   在主配置 ``filebeat.yml`` 里，片段改不动它。所以本模块：
   · 把 ``index_prefix`` 随每条事件作为 fields 带下去（便于 ES 侧路由/排查）；
   · 由 ``detect_environment()`` 把目标机**实际的 output hosts 与 index 读回来**；
   · 页面据此告知用户"日志实际落到哪个索引"，而不是假装我们说了算。

4. **一切拼接进 shell 的字符串都要过白名单**。路径只允许
   ``/A-Za-z0-9_.-/*[]``（见 ``models.PATH_PATTERN_RE``），片段文件名由主键生成，
   **不接受任何用户输入直接进命令**；文件内容走 base64 传输（字符集安全，
   不引号、不转义、不 heredoc）。

5. **不依赖 PyYAML**。解析目标机 ``filebeat.yml`` 用逐行文本解析 ——
   不能假设目标机/平台装了 yaml 库。解析结果标注为"仅供参考"。

6. **★ 「只采新增」只有 ``log`` input 的 ``tail_files`` 能保证**（用户拍板项）。
   filestream **无**等价项：``ignore_older`` / ``ignore_inactive`` 的「从未采集过的文件，
   offset 设为末尾」只在文件 mtime 早于阈值时成立，而线上应用日志秒级持续写入、
   mtime 一直在变 ⇒ 判定恒为「不忽略」，仍会从头读。
   ⇒ ``tail_new_only=True`` 且探测到 filestream 时**降级用 log input**，
     并由 ``render_tail_note()`` 把「为什么退、退成什么」讲给用户：不静默、不谎称。
"""
import base64
import re
import time

from dvadmin.bastion.ssh_client import ssh_exec

HERE_TAG = "XwOps"

# filebeat ≥ 7.9 才有 filestream input；低于此版本退回 log input
FILESTREAM_MIN_VERSION = (7, 9)

# 片段加载需要主配置里有这一段（检测不到就提示用户补）
MAIN_PATCH_TEMPLATE = """\
# ---- XwOps 日志采集：加载配置片段 ----
# ★ 追加到目标机 /etc/filebeat/filebeat.yml 末尾后重启 filebeat
#   （追加前请先备份原文件；本段不修改任何已有配置项）
filebeat.config.inputs:
  enabled: true
  path: %(dir)s/*.yml
  reload.enabled: true
  reload.period: 10s
"""

# shell 元字符 —— 双保险，白名单之外再拦一层
_UNSAFE_SHELL = re.compile(r"[;|&$`<>(){}\\'\"\n\r\t=~^]")
# 路径穿越
_DOTDOT = re.compile(r"(^|/)\.\.(/|$)")

# RE2（Go regexp）不支持的结构 —— Python re 能编译，filebeat 会挂
_RE2_UNSUPPORTED = (
    (re.compile(r"\(\?="), "正向预查 (?=...)"),
    (re.compile(r"\(\?!"), "负向预查 (?!...)"),
    (re.compile(r"\(\?<="), "正向回顾 (?<=...)"),
    (re.compile(r"\(\?<!"), "负向回顾 (?<!...)"),
    (re.compile(r"\(\?P="), "命名组反向引用 (?P=name)"),
    (re.compile(r"\(\?>"), "原子组 (?>...)"),
    (re.compile(r"\(\?R\)"), "递归 (?R)"),
    (re.compile(r"\(\?[aiLmsux-]+:"), "内联 flag 组 (?i:...)（应写成 (?i) 前缀）"),
    (re.compile(r"\\K"), "\\K"),
)


# ===========================================================================
# 校验
# ===========================================================================
def check_re2_compatible(pattern):
    """检查正则是否 RE2 兼容。返回 ``(ok, reason)``。

    ★ 这是整个模块最重要的一道闸：Python 与 Go 的正则方言不同，
    差异点恰好集中在"负向条件"这类**过滤规则最爱用**的语法上。
    """
    if not pattern:
        return True, ""
    for rx, label in _RE2_UNSUPPORTED:
        if rx.search(pattern):
            return False, "filebeat 使用 Go RE2 正则，不支持 %s" % label
    # 数字反向引用 \1 \2（\0 是八进制，允许）
    i = 0
    while i < len(pattern) - 1:
        if pattern[i] == "\\":
            nxt = pattern[i + 1]
            if nxt.isdigit() and nxt != "0":
                return False, "filebeat 使用 Go RE2 正则，不支持数字反向引用 \\%s" % nxt
            i += 2
            continue
        i += 1
    try:
        re.compile(pattern)
    except re.error as exc:
        return False, "正则语法错误：%s" % exc
    return True, ""


# ---- 附加字段的保留名 -------------------------------------------------------
# ★ 这些名字要么被 input 结构占用、要么被 filebeat 约定占用。
#   用户填进 extra_fields 会覆盖掉平台写入的值或破坏 input 结构，
#   而且是"静默生效"—— 采不到日志却看不出原因。所以直接在保存时拒绝。
RESERVED_EXTRA_FIELDS = {
    "xwops_task_id", "xwops_task_name", "index_prefix",
    "message", "paths", "fields", "fields_under_root", "processors",
    "type", "enabled", "id", "multiline", "parsers", "ignore_older",
}
RESERVED_EXTRA_PREFIX = "xwops_"


# ---- ECS 顶层「对象型」字段 -------------------------------------------------
# ★★ 为什么必须有这张表（2026-09-24 真机自测挖出的、本模块最严重的一个坑）
#
#   filebeat 首次连上 ES 时会安装一份 ECS 索引模板。该模板把**绝大多数 ECS
#   顶层字段声明为 object**（`service.name` / `host.name` / `agent.version` …）。
#   用户往「附加字段」里填这么一个名字、给一个标量值，事件顶到根层就变成：
#
#       "service": "xwops-selftest"        ← 字符串
#
#   而模板要求这个位置是对象，ES 直接拒收该条文档：
#
#       HTTP 400  mapper_parsing_exception
#       object mapping for [service] tried to parse field [service] as object,
#       but found a concrete value
#
#   filebeat 拿到 400 的处理是**丢弃事件**（不重试）：
#       WARN [elasticsearch] elasticsearch/client.go:416
#            Cannot index event (status=400): dropping event!
#
#   ⇒ 结果是「三边全绿、一条数据都没有」：
#       · 平台侧    ：`filebeat test config` 通过，下发报「成功」
#       · filebeat 侧：harvester 正常运行，metrics 里 events.total 一路在涨
#       · ES 侧     ：server log 干净（文档级错误不进 server log）
#     这正是本模块最想防的那类静默失败 ⇒ 必须在**保存时**就拒绝。
#
#   ★ 清单来源：**不靠记忆**。`deploy/tools/_probe_ecs_objects.py` 从目标机
#     `GET /_index_template/<filebeat 装的模板>` 解析得到。
#     实测（filebeat 7.17.29 + ES 7.17.10）：顶层字段 122 个，
#     其中 object/nested **115 个**；标量只有 7 个：
#       @timestamp / fields / labels / message / metadata / stream / tags
#     换 filebeat 大版本后**重跑该探针**更新此表。
#
#   实测证据（同机同刻，只换字段名）：
#     {"message":"x"}                        → 201 created
#     {"message":"x","service":"s"}          → 400 mapper_parsing_exception
#     {"message":"x","service":{"name":"s"}} → 201 created
#     {"message":"x","host":"h"}             → 400（host 同样是 object）
#     {"message":"x","env_name":"e"}         → 201 created（非 ECS 名，动态映射）
ECS_OBJECT_FIELDS = frozenset({
    "activemq", "agent", "apache", "as", "auditd", "aws", "aws-cloudwatch",
    "azure", "bucket", "cef", "checkpoint", "cisco", "client", "cloud",
    "code_signature", "container", "coredns", "crowdstrike", "cyberarkpas",
    "data_stream", "destination", "dll", "dns", "docker", "ecs",
    "elasticsearch", "elf", "envoyproxy", "error", "event", "file", "fileset",
    "forcepoint", "fortinet", "gcp", "geo", "google_workspace", "group",
    "gsuite", "haproxy", "hash", "host", "http", "ibmmq", "icinga", "icmp",
    "igmp", "iis", "input", "interface", "iptables", "jolokia", "juniper",
    "kafka", "kibana", "kubernetes", "log", "logstash", "microsoft", "misp",
    "mongodb", "mssql", "mysql", "mysqlenterprise", "nats", "netflow",
    "network", "nginx", "o365", "object", "observer", "okta", "oracle",
    "orchestrator", "organization", "os", "osquery", "package", "panw", "pe",
    "pensando", "postgresql", "process", "rabbitmq", "redis", "registry",
    "related", "rsa", "rule", "santa", "server", "service", "snyk", "sophos",
    "source", "span", "suricata", "syslog", "system", "threat", "threatintel",
    "timeseries", "tls", "trace", "traefik", "transaction", "url", "user",
    "user_agent", "vlan", "vulnerability", "x509", "zeek", "zookeeper", "zoom",
})


def check_extra_fields(extra):
    """校验附加字段的**名字与取值**。返回 ``(ok, reason)``。

    三道拦截，都在**保存时**（不是下发时）拒绝：

      ① 名字撞了 filebeat input 结构 / 平台保留名
         → 会静默破坏采集配置本身；
      ② 名字是 ECS 的**对象型**顶层字段（`service` / `host` / `agent` / `log` …）
         → ES 报 400 并**丢弃每一条**日志（详见 ``ECS_OBJECT_FIELDS`` 上面那段），
           三边全绿却零数据，是排查成本最高的一种失败；
      ③ 值是 dict / list
         → 生成器只会把它 ``str()`` 成一个字符串塞进 YAML，既不是用户想要的
           嵌套结构、又同样会被 ES 拒收。宁可在保存时讲清楚。
    """
    if not extra:
        return True, ""
    if not isinstance(extra, dict):
        return False, "附加字段必须是 JSON 对象"
    for key in extra:
        k = str(key)
        if not k.replace("_", "").isalnum():
            return False, "字段名只允许字母数字下划线：%s" % k
        if k in RESERVED_EXTRA_FIELDS:
            return False, "字段名 %s 是保留名，请换一个（避免覆盖采集配置本身）" % k
        if k.startswith(RESERVED_EXTRA_PREFIX):
            return False, "字段名不能以 %s 开头（平台保留前缀）" % RESERVED_EXTRA_PREFIX
        if k in ECS_OBJECT_FIELDS:
            return False, (
                "字段名 %s 是 ECS 的**对象型**顶层字段（ES 索引模板里 %s 下面还有 "
                "name/version 等子字段），不能直接填一个值：ES 会以 HTTP 400 "
                "（mapper_parsing_exception）拒收该任务的**每一条**日志，"
                "而 filebeat 只会静默丢弃、平台侧看不出异常。"
                "请改用自定义名，如 %s_name / app_name / env_name。"
                % (k, k, k))
        val = extra[key]
        if isinstance(val, (dict, list)):
            return False, (
                "字段 %s 的值必须是标量（字符串/数字/布尔），当前是 %s。"
                "需要嵌套结构时请换成扁平的自定义字段名。"
                % (k, type(val).__name__))
    return True, ""


def validate_path_pattern(path):
    """校验日志路径：必须是绝对路径、无 shell 元字符、无路径穿越。"""
    from dvadmin.log.models import PATH_PATTERN_RE
    p = (path or "").strip()
    if not p:
        return False, "日志路径不能为空"
    if not p.startswith("/"):
        return False, "日志路径必须是绝对路径（以 / 开头）"
    if _DOTDOT.search(p):
        return False, "日志路径不能包含 .. 路径穿越"
    if not re.match(PATH_PATTERN_RE, p):
        return False, "日志路径含非法字符（只允许字母数字 _ - . / * [ ]）"
    return True, ""


def validate_remote_dir(path):
    """校验片段目录：绝对路径、无通配、无元字符。"""
    p = (path or "").strip()
    if not p.startswith("/"):
        return False, "片段目录必须是绝对路径"
    if _DOTDOT.search(p) or _UNSAFE_SHELL.search(p):
        return False, "片段目录含非法字符"
    if not re.match(r"^/[A-Za-z0-9_.\-/]{1,254}$", p):
        return False, "片段目录格式不合法"
    return True, ""


def validate_index_prefix(prefix):
    """索引前缀必须是 ES 合法索引名开头（小写、字母数字开头）。"""
    from dvadmin.log.models import INDEX_PREFIX_RE
    p = (prefix or "").strip()
    if not p:
        return False, "索引前缀不能为空"
    if not re.match(INDEX_PREFIX_RE, p):
        return False, "索引前缀只允许小写字母、数字、下划线、短横、点，且需以字母或数字开头"
    return True, ""


def validate_task(task):
    """下发/试跑前的整体校验。返回 ``(ok, [错误信息])``。"""
    errors = []

    ok, msg = validate_index_prefix(getattr(task, "index_prefix", ""))
    if not ok:
        errors.append(msg)

    ok, msg = validate_path_pattern(getattr(task, "path_pattern", ""))
    if not ok:
        errors.append(msg)

    ok, msg = validate_remote_dir(getattr(task, "remote_dir", "") or "")
    if not ok:
        errors.append(msg)

    ok, msg = check_extra_fields(getattr(task, "extra_fields", None) or {})
    if not ok:
        errors.append("附加字段：%s" % msg)

    for field, label in (("include_regex", "包含规则"),
                         ("exclude_regex", "排除规则"),
                         ("multiline_start", "多行起始正则"),
                         ("time_regex", "时间提取正则")):
        val = getattr(task, field, "") or ""
        if not val:
            continue
        ok, msg = check_re2_compatible(val)
        if not ok:
            errors.append("%s：%s" % (label, msg))

    t_regex = (getattr(task, "time_regex", "") or "").strip()
    t_layout = (getattr(task, "time_layout", "") or "").strip()
    if t_regex and not t_layout:
        errors.append("填了「时间提取正则」就必须填「时间格式」，否则 @timestamp 不会被改写")
    if t_layout and not t_regex:
        errors.append("填了「时间格式」就必须填「时间提取正则」")
    if t_regex and "log_time" not in t_regex:
        errors.append("时间提取正则必须包含命名组 (?P<log_time>...)，否则取不到时间")

    if not (task.targets or []):
        errors.append("至少需要选择一台目标服务器")

    return (not errors), errors


# ===========================================================================
# YAML 生成
# ===========================================================================
def yaml_sq(value):
    """YAML 单引号标量。

    ★ 单引号里的反斜杠是**字面量**，所以正则里的 ``\\d`` ``\\b`` 原样保留，
    不需要二次转义；只需要把单引号自身翻倍。
    """
    return "'" + str(value).replace("'", "''") + "'"


def _yaml_list(items, indent):
    pad = " " * indent
    return "\n".join("%s- %s" % (pad, yaml_sq(i)) for i in items)


def _reindent(text, base, default=6):
    """把"按 default 列起写"的块整体平移 ``base - default`` 列。

    ★ 为什么不手改每一行的空格数：块内部的**相对**缩进就是 YAML 结构本身，
      手改很容易差一两格 → 又变成"能解析但结构不对"的静默失败
      （这一轮就是被这种失败坑了整整两遍）。这里只动基准列，相对结构原样保留。
    """
    delta = base - default
    if delta == 0:
        return text
    out = []
    for line in text.splitlines():
        if not line.strip():
            out.append(line)
        elif delta > 0:
            out.append(" " * delta + line)
        else:
            cut = min(-delta, len(line) - len(line.lstrip()))
            out.append(line[cut:])
    return "\n".join(out)


def validate_fragment_shape(content):
    """校验配置片段的**形状**（不是语法）。返回 ``(ok, 错误信息)``。

    ★★ 为什么必须有它（2026-09-24 真机自测揪出的最隐蔽的一个 bug）：

      `filebeat.config.inputs` 引用的片段文件，**内容本身就是"输入列表"** ——
      整个文件解析出来是一个 YAML **数组**，数组元素才是 input。
      平台初版生成的是带 `filebeat.inputs:` 键的**映射**，于是真机上：

          DEBUG cfgfile/cfgfile.go:193  Load config from file: .../xwops-task-3.yml
          DEBUG cfgfile/reload.go:213   Number of module configs found: 0
          INFO  beater/crawler.go:106   Enabled inputs: 0

      **文件被读了、YAML 也合法**（`filebeat test config -c <片段>` 能过，
      因为那个检查只看"能否解析成一个完整 beat 配置"），
      但 reloader 从中提取出 **0 个配置** ⇒ 永不采集。
      而平台对每台目标机都报"下发成功"。

      这是静默失败里最难查的一种：**所有检查全绿，就是没数据**。
      实测对照（同机同刻、只换片段形状）：
          带 `filebeat.inputs:` 键 → configs=0，harvester 不启动，ES 0 条
          裸数组                  → configs=1，harvester 启动，  ES 有数据
      ⇒ 所以这里做**真结构校验**（真 YAML 解析器，不是字符串猜形状）。

    解析器不可用时**返回失败并说明原因**，绝不静默放行 ——
    一个"因为没检查所以通过"的门禁，比没有门禁更危险。
    """
    try:
        import yaml
    except Exception as exc:                                     # noqa: BLE001
        return False, ("平台侧没有可用的 YAML 解析器（%s），无法校验片段形状；"
                       "宁可不发，也不发一个 filebeat 读不懂的片段" % exc)
    try:
        doc = yaml.safe_load(content)
    except Exception as exc:                                     # noqa: BLE001
        return False, "配置片段不是合法 YAML：%s" % exc

    if not isinstance(doc, list):
        return False, (
            "配置片段必须是**输入列表**（YAML 数组），当前解析出来是 %s。"
            "最常见的错法是在片段里又套了一层 `filebeat.inputs:` —— "
            "`filebeat.config.inputs` 引用的文件，内容**本身就是**那个列表。"
            % type(doc).__name__)
    if not doc:
        return False, "配置片段是空列表，里面没有任何 input"
    for idx, item in enumerate(doc):
        if not isinstance(item, dict):
            return False, "配置片段第 %d 项不是映射（应写成 `- type: ...`）" % (idx + 1)
        if not str(item.get("type") or "").strip():
            return False, "配置片段第 %d 项缺少 `type`" % (idx + 1)
    return True, ""


def dropped_level_condition(task):
    """生成"丢弃低于 min_level 的日志"条件块（RE2 安全写法）。

    为什么用「丢弃低级别」而不是「保留高级别」：
      保留要写成 ``not: {or: [...]}``，条件嵌套更深、更易写错；
      而且"列出要丢的"与 ``min_level`` 的语义方向一致。
    """
    regexes = task.level_regexes()
    if not regexes:
        return ""
    lines = ["      - drop_event:", "          when:", "            or:"]
    for rx in regexes:
        # (?i) 是 RE2 支持的内联 flag，避免大小写差异漏过滤
        lines.append("              - regexp:")
        lines.append("                  message: %s" % yaml_sq("(?i)" + rx))
    return "\n".join(lines)


def build_processors(task, server_ip, base=6):
    """按顺序生成 processors 列表。

    顺序即语义（filebeat 顺序执行），与 ``apply_filters()`` 的 Python 复现**必须一致**：
      ① 排除规则 → ② 包含规则 → ③ 最低级别 → ④ 时间提取 → ⑤ 补字段

    ``base``：列表项 `-` 所在的列。默认 6 对应"嵌套在 filebeat.inputs 里的 input"，
    而当前片段是**顶级数组**（见 `render_config`），所以调用方传 4。
    """
    blocks = []

    # ① 排除
    if (task.exclude_regex or "").strip():
        blocks.append("\n".join([
            "      - drop_event:",
            "          when:",
            "            regexp:",
            "              message: %s" % yaml_sq(task.exclude_regex.strip()),
        ]))

    # ② 包含（"不匹配就丢" —— 用 not 而不是负向预查，RE2 不支持后者）
    if (task.include_regex or "").strip():
        blocks.append("\n".join([
            "      - drop_event:",
            "          when:",
            "            not:",
            "              regexp:",
            "                message: %s" % yaml_sq(task.include_regex.strip()),
        ]))

    # ③ 最低级别
    lv = dropped_level_condition(task)
    if lv:
        blocks.append(lv)

    # ④ 时间提取：把日志正文时间写进 @timestamp
    #    （内网现网踩过的坑：@timestamp 记成采集时刻 → 时间范围检索全乱）
    if (task.time_regex or "").strip() and (task.time_layout or "").strip():
        blocks.append("\n".join([
            "      - regex:",
            "          field: message",
            "          pattern: %s" % yaml_sq(task.time_regex.strip()),
            "          ignore_failure: true",
            "      - timestamp:",
            "          field: log_time",
            "          layouts:",
            "            - %s" % yaml_sq(task.time_layout.strip()),
            "          ignore_failure: true",
            "      - drop_fields:",
            "          fields: [log_time]",
            "          ignore_missing: true",
        ]))

    # ⑤ 补 server_ip：多台目标共用一份规则，只有这里逐台不同
    blocks.append("\n".join([
        "      - add_fields:",
        "          target: ''",
        "          fields:",
        "            server_ip: %s" % yaml_sq(server_ip),
    ]))

    # ★ 只平移基准列，块内部的相对缩进（= YAML 结构）原样保留
    return _reindent("\n".join(blocks), base)


def effective_input_type(task, detected_beat_type):
    """由「探测到的 filebeat 类型」推出**实际会写进片段的 input 类型**。

    ★ 为什么要有这么一个函数（2026-09-24 真机自测踩到的坑）：
      降级判断原先只写在 ``render_config`` 内部，而给用户看的
      ``render_tail_note(task, detected)`` 收到的是**降级前**的类型。
      于是出现割裂：目标机片段里明明是 ``type: log``（S6-2 可证），
      用户拿到的说明却是 filestream 那两句 —— 既没说 tail_files 的保证，
      更没提它「已被采过的文件会按 registry 续读」这条边界。
      ⇒ 判断只能有一处来源：``render_config`` 与 ``render_tail_note``
        都调本函数，谁都不许自己重写一遍条件。
    """
    tail = bool(getattr(task, "tail_new_only", True))
    if tail and detected_beat_type != "log":
        return "log"
    return detected_beat_type or "filestream"


def render_config(task, server_ip, beat_type="filestream"):
    """生成 filebeat 配置片段（写入目标机 ``<remote_dir>/xwops-task-<id>.yml``）。

    beat_type: ``filestream``（filebeat ≥ 7.9）或 ``log``（更老的版本）。

    ★ 「只采新增」（``task.tail_new_only``，用户拍板项）**只有 log input 的
      ``tail_files`` 能真正保证**。filebeat 官方文档里 filestream 没有等价项：
      ``ignore_older`` / ``ignore_inactive`` 的「从未采集过的文件，offset 设为文件末尾」
      只在文件**最后修改时间**早于阈值时成立 —— 而线上应用日志是秒级持续写入的，
      mtime 一直在变，判定恒为「不忽略」⇒ 仍然从头读。
      实测结论（社区以 filebeat 源码 isFileIgnored 为依据的验证）也是如此：
      持续读写的大日志首次接入会让吞吐短时飙升。
      ⇒ 开启「只采新增」且探测到 filestream 时，**降级用 log input** 承载。
        宁可用一个 deprecated 的输入类型（8.x 仍完整支持），
        也不能把目标机几个月的历史日志灌进 ES。
    """
    task_id = task.pk if task.pk else "new"
    ver_tag = "# 由 %s 平台生成 · 任务 #%s · 请勿手工修改（下次下发会覆盖）" % (HERE_TAG, task_id)

    tail = bool(getattr(task, "tail_new_only", True))
    # ★ 降级判断走 effective_input_type（与 render_tail_note 同源），
    #   避免「配置用了 log、说明讲了 filestream」这种割裂再次发生。
    beat_type = effective_input_type(task, beat_type)

    # ★★★ 片段**顶层必须是数组**（文件内容本身就是"输入列表"），
    #     不能写成 `filebeat.inputs:` 下面再挂列表。
    #
    #     为什么会这样：目标机主配置里是
    #         filebeat.config.inputs:
    #           enabled: true
    #           path: /etc/filebeat/inputs.d/*.yml
    #           reload.enabled: true
    #     reloader 读取每个片段文件后，把**文件解析结果**当作 input 列表。
    #     写成带 `filebeat.inputs:` 键的映射时，reloader 提取出 0 个配置：
    #         DEBUG cfgfile/cfgfile.go:193  Load config from file: .../xwops-task-3.yml
    #         DEBUG cfgfile/reload.go:213   Number of module configs found: 0
    #         INFO  beater/crawler.go:106   Enabled inputs: 0
    #     ⇒ 文件被读了、YAML 也合法（`filebeat test config -c <片段>` 照样能过），
    #       但**永不采集**，而平台每台都报"下发成功" —— 最坏的一类静默失败。
    #
    #     2026-09-24 真机对照实测（同机同刻，只换形状）：
    #       带键 → configs=0，harvester 不启动，ES 0 条
    #       裸数组 → configs=1，harvester 启动，  ES 有数据
    #     `validate_fragment_shape()` 就是钉这条不变量的门禁。
    if beat_type == "log":
        # 老版本 / 「只采新增」：processors 直接挂在 input 下；多行用 input 级 multiline
        head = [
            ver_tag,
            "- type: log",
            "  enabled: true",
        ]
        if tail:
            head += [
                "# ★ 只采新增（tail_files）：从文件**末尾**开始读，",
                "#   接入前已有的历史日志不会被采集。仅 log input 提供该选项。",
                "  tail_files: true",
            ]
        head += [
            "  paths:",
            _yaml_list([task.path_pattern], 4),
            "  fields:",
            "    xwops_task_id: %s" % task_id,
            "    xwops_task_name: %s" % yaml_sq(task.name or ""),
            "    index_prefix: %s" % yaml_sq(task.index_prefix or ""),
        ]
        # ★★ 附加字段必须留在 `fields:` 块**内部** —— 排在 `fields_under_root: true`
        #    之后就会被解析成"布尔值底下的子键"，是**非法 YAML**：
        #      fields_under_root: true
        #        service: 'x'          ← yaml: mapping values are not allowed in this context
        #    2026-09-24 真机自测撞上：filebeat 直接拒收整个片段 →
        #    「一条日志都采不到，平台却回报下发成功」的静默失败。
        for k, v in sorted((task.extra_fields or {}).items()):
            head.append("    %s: %s" % (k, yaml_sq(v)))
        head.append("  fields_under_root: true")
        if (task.multiline_start or "").strip():
            head += [
                "  multiline:",
                "    pattern: %s" % yaml_sq(task.multiline_start.strip()),
                "    negate: true",
                "    match: after",
            ]
    else:
        head = [
            ver_tag,
            "- type: filestream",
            "  id: xwops-task-%s" % task_id,
            "  enabled: true",
            "  paths:",
            _yaml_list([task.path_pattern], 4),
            "  fields:",
            "    xwops_task_id: %s" % task_id,
            "    xwops_task_name: %s" % yaml_sq(task.name or ""),
            "    index_prefix: %s" % yaml_sq(task.index_prefix or ""),
        ]
        # ★ 同上：附加字段必须在 ``fields:`` 块内、``fields_under_root`` 之前
        for k, v in sorted((task.extra_fields or {}).items()):
            head.append("    %s: %s" % (k, yaml_sq(v)))
        head.append("  fields_under_root: true")
        if (task.multiline_start or "").strip():
            head += [
                "  parsers:",
                "    - multiline:",
                "        pattern: %s" % yaml_sq(task.multiline_start.strip()),
                "        negate: true",
                "        match: after",
            ]

    # ★ base=4：片段是**顶级数组**，列表项 `-` 在列 4（`processors:` 键在列 2）
    procs = build_processors(task, server_ip, base=4)
    if procs:
        head.append("  processors:")
        head.append(procs)

    return "\n".join(head) + "\n"


def render_tail_note(task, detected_beat_type):
    """生成「只采新增」的**说明**，随检测/下发结果回给用户。

    ``detected_beat_type`` 是**探测到的**类型（``filestream`` / ``log``）；
    函数内部用 :func:`effective_input_type` 算出**实际会写进片段的**类型，
    再决定要给用户讲哪几句话。

    ★ 为什么不静默降级：用户拍板的是「不把历史日志灌进 ES」，而 filestream 做不到。
      如果我们悄悄换个 input 类型，用户下次看配置文件会一头雾水；
      如果装作 filestream 也能做到，那就是谎称。⇒ 讲清楚「为什么退、退成什么」。

    ★ 为什么还要把 tail_files 的**边界**写出来（2026-09-24 真机自测）：
      初版这里只写了「接入前的历史日志不会被采集」—— 这句话**说大了**。
      实测：`tail_files` 只对 **filebeat 还没见过的文件** 生效；
      文件一旦进过 registry（本任务之前下发过、或别的采集任务/探针采过它），
      filebeat 就复用旧 offset **续读**，于是把「上次采集之后到本次接入之前」
      那一小段新行也带了进来。E2E 的 S8 就是因此判红（好端端的一次反向验收
      变成了"产品说话不算数"）。而「续读」本身是**对的**：
      它避免出现数据空洞，比"严格从此刻开始"更重要。
      ⇒ 保证要改成准确的那句，边界要写出来。宁可用户读完说"原来如此"，
        也不要用户拿一句做不到的承诺去要求它。

    ★ ★★ 为什么降级场景必须**两份说明一起给**（2026-09-24 E2E S8-4 判红后修）：
      上一版把「为什么退」（解释 filestream 无 tail_files）和
      「退成什么 + 保证 + 边界」（tail_files 的两条）拆给了**两个入参分支**，
      可降级场景进来时带的仍是 ``detected_beat_type="filestream"`` ——
      于是只返回了「为什么退」那两句，用户**根本看不到**续读边界，
      而第一句还写着「改用 log input 承载，**以保证只采新增**」：
      配置确实换成 log 了，但这句"保证"却比实际能力大。
      ⇒ 判定实际类型后：只要是 log input 在采，tail_files 的保证与边界就必须跟出来。
    """
    tail = bool(getattr(task, "tail_new_only", True))
    if not tail:
        return ["本任务**未**开启「只采新增」：接入后会连同路径下已有的历史日志一起采集。"]

    # 只要最终是 log input 在采，这两条就**必须**给（保证 + 边界）。
    log_notes = [
        "只采新增：使用 log input 的 tail_files=true，**首次接入该文件**时从文件末尾开始读，"
        "接入前已有的历史日志不会被采集。",
        "★ 这条保证的准确边界（2026-09-24 真机自测确认）：tail_files 只对"
        "**filebeat 还没见过的文件**生效。如果该文件已经被 filebeat 采过"
        "（registry 里存着它的 offset —— 例如本任务之前下发过、或别的采集任务/实例采过它），"
        "filebeat 会从**上次的 offset 续读**，因此「上次采集之后、本次接入之前」"
        "这段新行也会被采进来。这不是故障：续读是为了不出现数据空洞。"
        "若要求「严格只从此刻起」，请改用未被采过的路径或文件名。",
    ]

    effective = effective_input_type(task, detected_beat_type)
    if detected_beat_type == "log":
        # 老版本（<7.9）本来就是 log：不必解释降级，直接给保证 + 边界。
        return list(log_notes)

    # 探测到 filestream、但「只采新增」使实际输入降级为 log：
    # 先讲「为什么退」，再讲「退成什么」以及随之而来的保证与边界（顺序即阅读顺序）。
    downgrade_notes = [
        "只采新增：目标机 filebeat ≥ 7.9（默认 filestream input），但 filestream "
        "**没有** tail_files 等价项 —— ignore_older / ignore_inactive 只对「最后修改时间早于阈值」"
        "的冷文件生效，而持续写入的活跃日志 mtime 一直在变，判定恒为「不忽略」⇒ 仍会从头读。",
        "因此本片段已**改用 log input**（filebeat 8.x 仍完整支持，官方标注 deprecated）承载，"
        "以保证只采新增。若你希望改用 filestream（例如团队规范要求），"
        "可关闭任务的「只采新增」后重新下发 —— 代价是历史日志会被一并采集。",
    ]
    assert effective == "log", "降级场景下实际类型必然是 log，判断已与 render_config 同源"
    return downgrade_notes + list(log_notes)


def build_main_patch(remote_dir):
    """生成需要追加到目标机 ``filebeat.yml`` 的片段加载配置。

    ★ 平台**不会自动写**这段 —— 它改的是主配置。页面上作为提示给出，
    要动的话用户显式点「应用主配置补丁」，且带备份与还原。
    """
    return MAIN_PATCH_TEMPLATE % {"dir": (remote_dir or "/etc/filebeat/inputs.d").rstrip("/")}


# ===========================================================================
# 规则过滤的 Python 复现（供「规则试跑」用，顺序必须与 build_processors 一致）
# ===========================================================================
def apply_filters(task, lines):
    """在平台侧复现 filebeat 的过滤行为，返回 ``(kept, dropped)``。

    ★ 这里**不追求 100% 等价**（filebeat 是流式的），而是给用户一个
    "规则大概会留下什么"的直观判断。差异点会在页面提示里说明。
    """
    kept, dropped = [], []

    def _search(pattern, text):
        try:
            return re.search(pattern, text, re.I) is not None
        except re.error:
            return False

    inc = (task.include_regex or "").strip()
    exc = (task.exclude_regex or "").strip()
    lo_aliases = task.dropped_levels()

    for ln in lines:
        text = ln.rstrip("\n")
        if not text.strip():
            continue
        if exc and _search(exc, text):
            dropped.append((text, "命中排除规则"))
            continue
        if inc and not _search(inc, text):
            dropped.append((text, "未命中包含规则"))
            continue
        if lo_aliases:
            hit = None
            for alias in lo_aliases:
                if re.search(r"\b%s\b" % re.escape(alias), text, re.I):
                    hit = alias
                    break
            if hit:
                dropped.append((text, "低于最低级别（%s）" % hit))
                continue
        kept.append(text)
    return kept, dropped


# ===========================================================================
# 目标机操作
# ===========================================================================
def _credential_payload(credential):
    """把 Credential 解成 ssh_exec 需要的参数。"""
    if credential is None:
        return {"username": "root", "auth_type": "password", "password": None, "private_key": None}
    return {
        "username": credential.username or "root",
        "auth_type": credential.auth_type,
        "password": credential.get_password() if credential.auth_type == "password" else None,
        "private_key": credential.get_private_key() if credential.auth_type == "private_key" else None,
    }


def _run(server, payload, command, timeout=30):
    """在目标机上跑一条命令。所有调用方都必须保证 command 里的动态部分过了白名单。"""
    started = time.time()
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
    if res.get("duration") is None:
        res["duration"] = round(time.time() - started, 3)
    return res


def _sh(path):
    """把已白名单校验过的路径安全地放进 shell（单引号包裹）。"""
    return "'" + str(path).replace("'", "'\\''") + "'"


# ---- 检测 -----------------------------------------------------------------
DETECT_SCRIPT = (
    "echo '---FILEBEAT---'; command -v filebeat 2>/dev/null || echo ''; "
    "echo '---VERSION---'; filebeat version 2>/dev/null || echo ''; "
    "echo '---ACTIVE---'; systemctl is-active filebeat 2>/dev/null || echo 'unknown'; "
    "echo '---MAINCFG---'; cat /etc/filebeat/filebeat.yml 2>/dev/null | head -120; "
    "echo '---INPUTSDIR---'; ls -1 %(dir)s 2>/dev/null || echo ''; "
    "echo '---ENDFILE---'"
)


def _parse_main_cfg(text):
    """逐行解析 filebeat.yml 的关键项（不依赖 PyYAML）。返回 dict。

    ★ 用**缩进栈**推导点分路径（``filebeat.config.inputs.path``），
      不假设缩进宽度。2026-09-24 真机自测踩过：旧版把 `indent <= 2` 当成
      "二级键"就 `continue`，而 filebeat 配置的惯例恰恰是 2 空格缩进 ——
      于是 `filebeat.config.inputs.path`、`output.elasticsearch.hosts`、
      `reload.enabled` **全部读成空字符串**，导致「环境检测」把一个
      **健康**的主配置报成"没有加载片段目录"。

      「把好的说成坏的」比「读不出来」更糟：用户会去改一个本来正确的配置。

    ★ 只做"够用的浅解析"：锚点/多文档等复杂 YAML 解析不准，但**检测是只读的**，
      读错不会造成后果，比硬引一个不确定存在的依赖划算。
    """
    out = {"es_hosts": "", "es_index": "", "inputs_path": "", "inputs_enabled": "",
           "reload_enabled": "", "raw_tail": ""}
    stack = []                      # [(indent, key), ...] 当前所在的映射层级
    list_owner = ""                 # 正在收集列表项的字段路径（hosts 可能是多行列表）
    lines = text.splitlines()
    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        stripped = raw.strip()
        # 列表项（如 hosts: 换行后写 - "http://..."）
        if stripped.startswith("- "):
            if list_owner == "output.elasticsearch.hosts":
                item = stripped[2:].strip().strip('"').strip("'")
                out["es_hosts"] = (out["es_hosts"] + "," + item).lstrip(",")
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        m = re.match(r"^[ \t]*([A-Za-z_][\w.\-]*)\s*:\s*(.*)$", raw)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        path = ".".join([k for _i, k in stack] + [key])
        stack.append((indent, key))
        list_owner = path if key == "hosts" else ""

        if path == "output.elasticsearch.hosts":
            out["es_hosts"] = val.strip("[]").strip('"').strip("'")
        elif path == "output.elasticsearch.index":
            out["es_index"] = val.strip('"').strip("'")
        elif path == "filebeat.config.inputs.path":
            out["inputs_path"] = val.strip('"').strip("'").lstrip("- ").strip()
        elif path == "filebeat.config.inputs.enabled":
            out["inputs_enabled"] = val
        elif path == "filebeat.config.inputs.reload.enabled":
            out["reload_enabled"] = val

    out["raw_tail"] = "\n".join(
        [l for l in lines if re.match(r"^\s*(output\.|output:|filebeat\.config|hosts:|index:|path:|reload)", l)][:20]
    )
    return out


def _parse_version(text):
    """从 ``filebeat version 8.6.2 (amd64), libbeat 8.6.2`` 里取 (8, 6, 2)。"""
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    if not m:
        return ()
    return tuple(int(x) for x in m.groups() if x is not None)


def detect_environment(server, credential):
    """只读检测目标机 filebeat 环境。返回 dict（绝不修改任何东西）。"""
    payload = _credential_payload(credential)
    dir_ok = True
    remote_dir = "/etc/filebeat/inputs.d"
    res = _run(server, payload, DETECT_SCRIPT % {"dir": remote_dir}, timeout=25)

    out = res.get("stdout") or ""
    err = res.get("error") or ""
    if err:
        return {"ok": False, "message": "连接失败：%s" % err}

    def _seg(name):
        m = re.search(r"---%s---\n(.*?)\n---" % name, out, re.S)
        return (m.group(1).strip() if m else "")

    fbin = _seg("FILEBEAT").splitlines()
    version_raw = _seg("VERSION").splitlines()
    version_txt = version_raw[0] if version_raw else ""
    active = _seg("ACTIVE").splitlines()
    main_cfg = _seg("MAINCFG")
    inputs_dir = [x for x in _seg("INPUTSDIR").splitlines() if x.strip()]

    installed = bool(fbin and fbin[0].startswith("/"))
    ver = _parse_version(version_txt)
    cfg = _parse_main_cfg(main_cfg)

    # 主配置是否已经会加载片段目录
    inputs_path = cfg.get("inputs_path", "")
    loads_dir = bool(inputs_path) and ("inputs.d" in inputs_path or inputs_path.rstrip("/").endswith("inputs"))
    reload_on = (cfg.get("reload_enabled", "").lower() == "true")

    beat_type = "filestream"
    if ver and ver < FILESTREAM_MIN_VERSION:
        beat_type = "log"

    warnings = []
    if not installed:
        warnings.append("目标机没有安装 filebeat（`command -v filebeat` 为空）")
    if installed and not loads_dir:
        warnings.append("主配置里没有加载片段目录 —— 需要补 filebeat.config.inputs 才能生效")
    if installed and (active[0] if active else "") != "active":
        warnings.append("filebeat 服务当前不是 active（%s）" % (active[0] if active else "unknown"))
    if ver and ver < FILESTREAM_MIN_VERSION:
        warnings.append("filebeat %s 较老，将使用 log input 而非 filestream" % version_txt)
    if cfg.get("es_hosts"):
        warnings.append("落库目标由目标机 output 决定：hosts=%s index=%s"
                        % (cfg.get("es_hosts"), cfg.get("es_index") or "(默认)"))

    return {
        "ok": True,
        "installed": installed,
        "binary": fbin[0] if fbin else "",
        "version": version_txt,
        "version_tuple": list(ver),
        "active": active[0] if active else "unknown",
        "beat_type": beat_type,
        "loads_inputs_dir": loads_dir,
        "reload_enabled": reload_on,
        "inputs_path": inputs_path,
        "es_hosts": cfg.get("es_hosts", ""),
        "es_index": cfg.get("es_index", ""),
        "existing_files": inputs_dir,
        "warnings": warnings,
        "raw": main_cfg[:4000],
        "main_patch": build_main_patch(remote_dir),
    }


def remote_dir_of(task):
    return (getattr(task, "remote_dir", "") or "/etc/filebeat/inputs.d").rstrip("/")


def remote_path_of(task):
    return "%s/xwops-task-%s.yml" % (remote_dir_of(task), task.pk)


# ---- 下发 -----------------------------------------------------------------
def apply_config(task, server, credential):
    """把配置片段下发到目标机并让 filebeat 重新加载。

    步骤（任一步失败即中止，**且发生在上线之前**）：
      ① 平台侧：``validate_task`` 校验规则合法性
      ② 平台侧：生成片段 → ``validate_fragment_shape`` 校验**形状**
         （必须是输入列表，不能套 `filebeat.inputs:`；见该函数 docstring）
      ③ 目标机：写 ``.incoming``（**绝不先动现场**）→ ``filebeat test config`` 校验语法
      ④ 目标机：备份已有同名片段（``.bak.<ts>``）→ ``mv`` 原子替换 → ``chmod``
      ⑤ 让 filebeat 生效：主配置开了 ``reload.enabled`` 就等热加载，
         否则 ``systemctl restart filebeat``
         （★ 不重启的话 filebeat 根本读不到新片段 —— 这点很容易漏）

    ★ 为什么校验要分"平台侧形状 + 目标机语法"两层，而不是只留一层：
      · 只留目标机 `filebeat test config`：对"带 filebeat.inputs 键"的错形状
        **会放行**（它语法合法），于是 filebeat 提取出 0 个 input 却不报错 ——
        这就是 2026-09-24 真机自测里"平台报成功、ES 一条没有"的根因。
      · 只留平台侧形状校验：挡不住 filebeat 版本差异带来的语法问题。
      ⇒ 两层都要，且**都在写现场之前**。
    """
    ok, errs = validate_task(task)
    if not ok:
        return {"ok": False, "message": "；".join(errs), "detail": ""}

    payload = _credential_payload(credential)
    remote_dir = remote_dir_of(task)
    path = remote_path_of(task)

    beat_type = "filestream"
    try:
        det = detect_environment(server, credential)
        if det.get("ok"):
            beat_type = det.get("beat_type") or "filestream"
    except Exception:                                              # noqa: BLE001
        det = {}

    content = render_config(task, server.ip, beat_type=beat_type)

    # ★★ 生成端先自检**形状**（不是语法）。
    #
    #   为什么单独需要这一步：`filebeat test config -c <片段>`（下面那层校验）
    #   对"带 filebeat.inputs: 键"这种错形状**是会放行的** —— 它只检查
    #   "能不能解析成一个完整 beat 配置"，而错形状本身语法完全合法。
    #   结果是 filebeat 从片段里提取出 0 个 input：不报错、不采集、平台报成功。
    #   ⇒ 语法校验 + 形状校验，两层都要有；缺任何一层都有洞。
    #   （详见 `validate_fragment_shape` 的 docstring）
    shape_ok, shape_msg = validate_fragment_shape(content)
    if not shape_ok:
        return {"ok": False,
                "message": "生成的配置片段形状不对，**已中止下发**（目标机未被改动）：%s"
                           % shape_msg,
                "detail": content,
                "server": server.hostname, "ip": server.ip,
                "shape_invalid": True}

    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    ts = time.strftime("%Y%m%d%H%M%S")
    incoming = path + ".incoming"

    # ★★ 下发前的**预校验**：让 filebeat 自己去解析这段 YAML。
    #
    #   为什么必须加（2026-09-24 真机自测的教训）：
    #   初版 render_config 把 extra_fields 排到了 `fields_under_root: true` 之后，
    #   生成的是**非法 YAML**。filebeat 加载时直接拒收该片段 →
    #   **一条日志都采不到，而平台回报"下发成功"**。这是最坏的失败形态：
    #   用户以为配好了，实际上什么都没发生，且不会有任何报错。
    #
    #   判据来自实测（deploy/tools/_probe_fragment_validate.py 固化）：
    #     · 合法片段（本就不含 output）→ `Exiting: no outputs are defined...` ⇒ 通过
    #       （output 由目标机的**主配置**提供，片段里本来就不该有）
    #     · 语法/结构错              → `Exiting: error loading config file: yaml: ...` ⇒ 拒绝
    #   校验不通过时**只删 .incoming，绝不碰已有配置** —— 宁可这次下发失败，
    #   也不能让一个跑得好好的采集任务因为一次误操作而停摆。
    validate = (
        "if command -v filebeat >/dev/null 2>&1; then "
        "VOUT=$(filebeat test config -c %s 2>&1 || true); "
        "case \"$VOUT\" in "
        "*\"no outputs are defined\"*) : ;; "
        "*\"Config OK\"*) : ;; "
        "*) echo __XWOPS_VALIDATE_FAIL__; echo \"$VOUT\"; rm -f %s; exit 9 ;; "
        "esac; "
        "fi"
    ) % (_sh(incoming), _sh(incoming))

    cmds = [
        "set -e",
        "mkdir -p %s" % _sh(remote_dir),
        # ③ 先写 .incoming（不碰现场）→ ④ 校验 → ⑤ 通过才原子替换
        "echo '%s' | base64 -d > %s" % (b64, _sh(incoming)),
        validate,
        "if [ -f %s ]; then cp -p %s %s.bak.%s; fi" % (_sh(path), _sh(path), _sh(path), ts),
        "mv -f %s %s" % (_sh(incoming), _sh(path)),
        "chmod 0644 %s" % _sh(path),
    ]
    if (det or {}).get("reload_enabled"):
        cmds.append("echo 'reload-enabled: 等 filebeat 自动加载（≤10s）'")
    else:
        cmds.append("systemctl restart filebeat")

    res = _run(server, payload, " ; ".join(cmds), timeout=60)

    if res.get("error"):
        return {"ok": False, "message": "下发失败：%s" % res["error"],
                "detail": content, "server": server.hostname, "ip": server.ip}
    # ★ 预校验失败必须**单独识别**并给出 filebeat 的原话，否则用户只能看到
    #   "退出码 9" 这种毫无信息量的东西，还得自己登机器去猜。
    if (res.get("exit_code") == 9
            or "__XWOPS_VALIDATE_FAIL__" in (res.get("stdout") or "")):
        vout = (res.get("stdout") or "").replace("__XWOPS_VALIDATE_FAIL__", "").strip()
        return {"ok": False,
                "message": "配置片段未通过 filebeat 校验，**已中止下发**（目标机现有配置未被改动）：%s"
                           % (vout.splitlines()[-1][:200] if vout else "原因未知"),
                "detail": (content + "\n\n--- filebeat test config 输出 ---\n" + vout),
                "stdout": res.get("stdout") or "",
                "server": server.hostname, "ip": server.ip,
                "validate_failed": True}
    if res.get("exit_code") != 0:
        return {"ok": False,
                "message": "下发命令退出码 %s：%s" % (res.get("exit_code"),
                                                    (res.get("stderr") or "").strip()[:300]),
                "detail": content + "\n\n--- stderr ---\n" + (res.get("stderr") or ""),
                "server": server.hostname, "ip": server.ip}

    return {"ok": True,
            "message": "已下发 %s（%s，且片段已通过 filebeat 校验）"
                       % (path, "热加载" if (det or {}).get("reload_enabled") else "已重启 filebeat"),
            "detail": content,
            "stdout": res.get("stdout") or "",
            "server": server.hostname, "ip": server.ip,
            "beat_type": beat_type,
            # ★ 注意这里传的是**探测到的** beat_type（render_config 内部可能已降级成 log），
            #   这样 render_tail_note 才能判断"是否需要向用户解释降级"。
            "tail_notes": render_tail_note(task, beat_type),
            "detect": det}


def stop_config(task, server, credential):
    """删除目标机上的配置片段并让 filebeat 重新加载（= 停止该任务的采集）。"""
    payload = _credential_payload(credential)
    remote_dir = remote_dir_of(task)
    path = remote_path_of(task)

    ok, msg = validate_remote_dir(remote_dir)
    if not ok:
        return {"ok": False, "message": msg, "detail": ""}

    det = {}
    try:
        det = detect_environment(server, credential)
    except Exception:                                              # noqa: BLE001
        pass

    cmds = [
        "set -e",
        "rm -f %s" % _sh(path),
    ]
    if (det or {}).get("reload_enabled"):
        cmds.append("echo 'reload-enabled: 等 filebeat 自动卸载（≤10s）'")
    else:
        cmds.append("systemctl restart filebeat")

    res = _run(server, payload, " ; ".join(cmds), timeout=60)
    if res.get("error"):
        return {"ok": False, "message": "停止失败：%s" % res["error"],
                "detail": "", "server": server.hostname, "ip": server.ip}
    if res.get("exit_code") != 0:
        return {"ok": False,
                "message": "停止命令退出码 %s：%s" % (res.get("exit_code"),
                                                    (res.get("stderr") or "").strip()[:300]),
                "server": server.hostname, "ip": server.ip}
    return {"ok": True, "message": "已删除 %s，该任务在 %s 上停止采集" % (path, server.hostname),
            "server": server.hostname, "ip": server.ip}


# ---- 规则试跑 -------------------------------------------------------------
def sample_and_filter(task, server, credential, lines=200):
    """在目标机抓样本行，用平台侧的规则复现跑一遍，返回过滤前后的对照。

    ★ 只读操作：``tail`` 不修改任何文件。路径已过白名单（无 shell 元字符），
    因此这里的通配 ``*`` 交由 shell 展开是安全的。
    """
    ok, errs = validate_task(task)
    if not ok:
        return {"ok": False, "message": "；".join(errs)}

    try:
        lines = max(1, min(int(lines or 200), 2000))
    except (TypeError, ValueError):
        lines = 200

    payload = _credential_payload(credential)
    # 路径已白名单（不含引号/元字符），故意不加引号以便 shell 展开通配
    cmd = "tail -q -n %d -- %s 2>/dev/null || true" % (lines, task.path_pattern)
    res = _run(server, payload, cmd, timeout=25)
    if res.get("error"):
        return {"ok": False, "message": "读取样本失败：%s" % res["error"]}

    raw = [l for l in (res.get("stdout") or "").splitlines() if l.strip()]
    if not raw:
        return {"ok": True, "total": 0, "kept": [], "dropped": [],
                "message": "没有读到内容：请确认路径存在（%s）、有日志文件、且账号有读权限"
                           % task.path_pattern}

    kept, dropped = apply_filters(task, raw)
    return {
        "ok": True,
        "total": len(raw),
        "kept_count": len(kept),
        "dropped_count": len(dropped),
        "kept": kept[:50],
        "dropped": [{"line": t, "reason": r} for t, r in dropped[:50]],
        "message": "样本 %d 行：保留 %d 行，过滤掉 %d 行" % (len(raw), len(kept), len(dropped)),
    }
