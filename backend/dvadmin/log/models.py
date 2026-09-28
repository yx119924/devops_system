# -*- coding: utf-8 -*-
"""
ES 日志数据源模型：Elasticsearch 连接配置
密码复用堡垒机 Fernet 加密（密钥 CREDENTIAL_ENCRYPTION_KEY）
"""
from django.db import models

from dvadmin.bastion.crypto import decrypt, encrypt
from dvadmin.utils.models import CoreModel

STATUS_CHOICES = (
    (1, "启用"),
    (0, "停用"),
)


class ElasticsearchSource(CoreModel):
    """Elasticsearch 日志数据源配置"""
    name = models.CharField(max_length=64, verbose_name="数据源名称", help_text="数据源名称")
    url = models.CharField(max_length=255, verbose_name="ES 地址", help_text="如 http://192.168.1.100:9200")
    index_pattern = models.CharField(max_length=128, default="logs-*", verbose_name="索引模式",
                                     help_text="如 logs-* / app-*（支持通配）")
    username = models.CharField(max_length=64, verbose_name="用户名", null=True, blank=True,
                                help_text="Basic Auth 用户名（可选，匿名留空）")
    password = models.TextField(verbose_name="密码(密文)", null=True, blank=True,
                                help_text="Basic Auth 密码（可选，加密存储）")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态", help_text="状态")
    sort = models.IntegerField(default=1, verbose_name="显示排序", null=True, blank=True, help_text="显示排序")
    description = models.CharField(max_length=255, verbose_name="描述", null=True, blank=True, help_text="描述")

    class Meta:
        db_table = "log_es_source"
        verbose_name = "ES 数据源"
        verbose_name_plural = verbose_name
        ordering = ["sort", "-create_datetime"]

    def set_password(self, plain):
        self.password = encrypt(plain) if plain else ''

    def get_password(self):
        return decrypt(self.password) if self.password else ''

    def get_auth(self):
        """返回 requests 的 auth 参数：有用户名则 basic auth，否则 None"""
        if self.username:
            from requests.auth import HTTPBasicAuth
            return HTTPBasicAuth(self.username, self.get_password())
        return None


# ===========================================================================
# 日志采集配置（「日志管理 → 采集配置」）
# ===========================================================================
#
# 设计取舍（改之前先把这段读完）
# ------------------------------
# 采集通道 = **平台托管 filebeat 配置片段**（已拍板），不是平台主动拉取。因此：
#
#   · 平台**不写 ES**，也不管 offset —— 这两件事 filebeat 自己做，
#     断点续传 / 文件轮转 / 多行合并 / 背压都是它的成熟能力，不需要我们重写一遍。
#   · 平台只负责三件事：**生成片段 → 下发到目标机 → 回显状态**。
#   · 每个采集任务 = 目标机上的**一个独立文件**
#     `<remote_dir>/xwops-task-<id>.yml`，与存量 filebeat 配置物理隔离：
#     停止采集 = 删这个文件；任务删除 = 删这个文件。不会碰到别人的配置。
#   · ★ **主配置 `filebeat.yml` 默认不动**。但主配置必须包含
#     `filebeat.config.inputs.path` 才会加载片段目录 —— 这一点由「环境检测」
#     查出来并明确告诉用户，需要补主配置时给出**待补内容 + 备份 + 可还原**，
#     绝不静默改。
#   · ★ **落库索引**：filebeat 的 `index` 是 output 级配置（主配置里），
#     片段改不了它。所以平台**不谎称能控制索引名**，而是：
#     把 `index_prefix` 随事件作为 `fields` 带下去，
#     同时「环境检测」把目标机**实际的 output 与 index** 读回来给用户看；
#     任务详情里再给出「用实际索引名去检索」的入口。诚实 > 好看。
#
# 加密：本表的凭据走 `bastion.Credential`（已加密），这里不新增密钥字段。

COLLECT_MODE_CHOICES = (
    ("filebeat", "托管 filebeat 配置片段"),
)

# 采集任务在目标机上的落地状态
COLLECT_RUN_STATUS_CHOICES = (
    ("pending", "未下发"),
    ("applied", "已下发"),
    ("failed", "下发失败"),
    ("stopped", "已停止"),
)

# 最低级别：低于它的日志丢弃（在 filebeat 侧用 drop_event 实现）
COLLECT_LEVEL_CHOICES = (
    ("", "不限（全部采集）"),
    ("debug", "DEBUG 及以上"),
    ("info", "INFO 及以上"),
    ("warn", "WARN 及以上"),
    ("error", "ERROR 及以上"),
)

# 级别从低到高的序（用于推导「低于 min_level 的级别」）
LEVEL_ORDER = ("trace", "debug", "info", "warn", "error", "critical")

# 级别在日志正文里的常见写法（大小写不敏感，故只列大写基准）
LEVEL_ALIASES = {
    "trace": ("TRACE",),
    "debug": ("DEBUG",),
    "info": ("INFO",),
    "warn": ("WARN", "WARNING"),
    "error": ("ERROR", "FATAL"),
    "critical": ("CRITICAL", "FATAL"),
}

COLLECT_ACTION_CHOICES = (
    ("detect", "环境检测"),
    ("apply", "下发配置"),
    ("stop", "停止采集"),
    ("preview", "规则试跑"),
)

COLLECT_ACTION_STATUS_CHOICES = (
    ("success", "成功"),
    ("failed", "失败"),
)

# 索引前缀白名单：字母数字开头，只含小写字母/数字/下划线/短横/点
# （ES 索引名本身要求小写，且不允许 * ? " < > | 空格 逗号 # / \）
INDEX_PREFIX_RE = r"^[a-z0-9][a-z0-9_.\-]{0,63}$"

# 目标机日志路径白名单：只允许绝对路径 + 通配，禁止一切 shell 元字符
PATH_PATTERN_RE = r"^/[A-Za-z0-9_.\-/*\[\]]{1,254}$"

# filebeat 默认的片段目录（新版 filebeat 的 inputs.d 约定）
DEFAULT_REMOTE_DIR = "/etc/filebeat/inputs.d"


class LogCollectTask(CoreModel):
    """日志采集任务：把某几台服务器上指定路径的日志采进 Elasticsearch。

    一行 = 一个采集单元。多台目标共用同一份规则（规则相同、只有 `server_ip`
    字段按机器不同），下发时按目标逐台渲染。
    """

    name = models.CharField(max_length=64, verbose_name="任务名称",
                            help_text="如 myapp-prod 应用日志")
    source = models.ForeignKey(to=ElasticsearchSource, on_delete=models.SET_NULL, null=True, blank=True,
                               db_constraint=False, verbose_name="ES 数据源",
                               help_text="用于「环境检测」比对与跳转检索；落库目标由目标机 filebeat 的 output 决定")
    index_prefix = models.CharField(max_length=64, verbose_name="索引前缀",
                                    help_text="如 myapp（小写字母数字开头）；检索时用 myapp-* 通配")
    collect_mode = models.CharField(max_length=20, choices=COLLECT_MODE_CHOICES, default="filebeat",
                                    verbose_name="采集方式", help_text="当前仅支持托管 filebeat 配置片段")

    path_pattern = models.CharField(max_length=255, verbose_name="日志路径",
                                    help_text="绝对路径，支持通配，如 /var/log/myapp/*.log")
    include_regex = models.CharField(max_length=255, verbose_name="包含规则(正则)", null=True, blank=True,
                                     help_text="只采集匹配该正则的行；留空表示不限制")
    exclude_regex = models.CharField(max_length=255, verbose_name="排除规则(正则)", null=True, blank=True,
                                     help_text="丢弃匹配该正则的行，优先级高于包含规则")
    min_level = models.CharField(max_length=20, choices=COLLECT_LEVEL_CHOICES, default="",
                                 verbose_name="最低级别", help_text="低于该级别的日志直接丢弃")
    multiline_start = models.CharField(max_length=255, verbose_name="多行起始正则", null=True, blank=True,
                                       help_text="如 ^\\d{4}-\\d{2}-\\d{2}：堆栈/换行会被并进上一条")
    tail_new_only = models.BooleanField(default=True, verbose_name="只采新增",
                                        help_text="首次接入时从文件末尾开始，不把已有历史日志灌进 ES")

    time_regex = models.CharField(max_length=255, verbose_name="时间提取正则", null=True, blank=True,
                                  help_text="含命名组 log_time，如 ^(?P<log_time>\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})")
    time_layout = models.CharField(max_length=64, verbose_name="时间格式", null=True, blank=True,
                                   help_text="Go 时间布局，如 2006-01-02 15:04:05")

    extra_fields = models.JSONField(default=dict, blank=True, verbose_name="附加字段",
                                    help_text='JSON 对象，随每条日志写入。键请用自定义名（如 app_name / env_name）；不要用 service、host、agent、log 等 ECS 名，ES 会以 HTTP 400 拒收每一条日志')

    targets = models.JSONField(default=list, blank=True, verbose_name="目标服务器",
                               help_text='JSON 数组：[{"server_id":1,"label":"web-1","ip":"x.x.x.x","ssh_port":22}]')
    credential = models.ForeignKey(to="bastion.Credential", on_delete=models.SET_NULL, null=True, blank=True,
                                   db_constraint=False, verbose_name="凭据",
                                   help_text="连接目标机用的统一凭据（复用堡垒机凭据，已加密）")
    remote_dir = models.CharField(max_length=255, default=DEFAULT_REMOTE_DIR, verbose_name="片段目录",
                                  help_text="目标机上 filebeat 加载配置片段的目录")

    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态", help_text="状态")
    description = models.CharField(max_length=255, verbose_name="描述", null=True, blank=True, help_text="描述")

    run_status = models.CharField(max_length=20, choices=COLLECT_RUN_STATUS_CHOICES, default="pending",
                                  verbose_name="下发状态", help_text="目标机上的落地状态")
    last_action_at = models.DateTimeField(verbose_name="最近操作时间", null=True, blank=True, help_text="最近一次下发/停止的时间")
    last_message = models.CharField(max_length=512, verbose_name="最近结果", null=True, blank=True,
                                    help_text="最近一次操作的摘要（成功或失败原因）")

    class Meta:
        db_table = "log_collect_task"
        verbose_name = "日志采集任务"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]

    # ---- 派生属性（不落库，避免出现"两个真相"） ---------------------------

    @property
    def remote_filename(self):
        """目标机上的片段文件名。★ 由主键生成，不接受用户输入 —— 杜绝路径穿越。"""
        return "xwops-task-%s.yml" % (self.pk if self.pk else "new")

    @property
    def remote_path(self):
        return "%s/%s" % ((self.remote_dir or DEFAULT_REMOTE_DIR).rstrip("/"), self.remote_filename)

    @property
    def es_index_name(self):
        """片段里希望写入的索引名模板（filebeat 支持的日期写法）。"""
        return "%s-%%{+yyyy.MM.dd}" % (self.index_prefix or "")

    @property
    def es_index_pattern(self):
        """检索页用的通配模式（同时也是「跳转检索」预填的值）。"""
        return "%s-*" % (self.index_prefix or "")

    def dropped_levels(self):
        """按 min_level 推导出**要丢弃**的级别别名列表。

        ★ 刻意用「丢弃低级别」而不是「保留高级别」：
          filebeat 的 drop_event 条件里若要"保留"，就得写成
          `not: {regexp: ...}` 的并集，可读性差且容易写反；
          直接列出要丢的级别更直观，也不依赖 RE2 不支持的负向预查。
        """
        if not self.min_level or self.min_level not in LEVEL_ORDER:
            return []
        idx = LEVEL_ORDER.index(self.min_level)
        out = []
        for lv in LEVEL_ORDER[:idx]:
            out.extend(LEVEL_ALIASES.get(lv, ()))
        return out

    def level_regexes(self):
        """要丢弃的级别对应的正则（带词边界，避免 DEBUG 命中 DEBUGGING）。"""
        return [r"\b%s\b" % alias for alias in self.dropped_levels()]

    def get_target_count(self):
        return len(self.targets or [])

    def __str__(self):
        return "%s → %s" % (self.name, self.path_pattern)


class LogCollectRecord(CoreModel):
    """采集任务的操作台账：每次「检测 / 下发 / 停止 / 试跑」都留一行。

    ★ 为什么连失败的也记：这个功能的失败几乎都发生在**目标机侧**
      （filebeat 没装、systemd 单元名不对、目录不存在、权限不足），
      只把失败提示在页面一闪而过，事后根本没法复盘是哪台机、什么错。
    """

    task = models.ForeignKey(to=LogCollectTask, on_delete=models.CASCADE, db_constraint=False,
                             related_name="records", verbose_name="采集任务", help_text="所属采集任务")
    action = models.CharField(max_length=20, choices=COLLECT_ACTION_CHOICES, verbose_name="操作", help_text="操作类型")
    status = models.CharField(max_length=20, choices=COLLECT_ACTION_STATUS_CHOICES, verbose_name="结果",
                              help_text="成功 / 失败")
    target_label = models.CharField(max_length=128, verbose_name="目标", null=True, blank=True,
                                    help_text="命中的目标机（多台时逐台记一行）")
    ip = models.CharField(max_length=64, verbose_name="目标IP", null=True, blank=True, help_text="目标IP")
    message = models.CharField(max_length=512, verbose_name="摘要", null=True, blank=True, help_text="结果摘要")
    detail = models.TextField(verbose_name="详情", null=True, blank=True,
                              help_text="生成的配置片段 / 命令输出 / 错误堆栈")
    duration = models.FloatField(verbose_name="耗时(秒)", null=True, blank=True, help_text="操作耗时")

    class Meta:
        db_table = "log_collect_record"
        verbose_name = "日志采集台账"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]

    def __str__(self):
        return "%s %s %s" % (self.task_id, self.action, self.status)
