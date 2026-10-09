# -*- coding: utf-8 -*-
"""发布流水线（可视化流水线）—— 数据模型

它要解决的缺口
--------------
平台此前只有「Jenkins 转发层」：选 Jenkins 服务器 → 列 Job 树 → 点构建 → 看日志。
**发布目标由 Jenkins Job 自己的参数决定**，平台既不参与编排，也选不了「发到哪几台机器」。

本模块引入平台自己的流水线概念：

    Pipeline            流水线（编排定义 + 默认凭据）
      └ PipelineNode    节点（顺序列表，支持上移/下移）
            └ PipelineRun      一次执行（含本次实际参数）
                  └ PipelineNodeRun  每个节点在这次执行里的逐台结果

★ 与 Jenkins 的关系：**「构建」节点复用 Jenkins**（编译环境/私服/缓存已在那边治理好，
  自建只会重踩一遍坑），其余节点（参数化/命令/检查/上传/通知）全部自建
  ⇒ 编排、部署、通知都不再受 Jenkins 约束。

可逆性
------
全部是**新建表**，不改任何现有表结构。停用菜单即隐身，删表即彻底消失。

★ 目标地址口径（与命令下发/日志采集完全一致）
------------------------------------------------
`config['targets']` 里存的 `ip/ssh_port` 只是**快照**，用于编排页回显；
真正连接时 `engine.py` 会**回读 CMDB 的最新 ip/ssh_port** 覆盖它。
库里存的地址在服务器换网段后会过期，照它连就是「改了资产却还在往旧 IP 发」。
"""
from django.db import models

from dvadmin.utils.models import CoreModel

STATUS_CHOICES = (
    (1, "启用"),
    (0, "停用"),
)

# 节点类型（MVP 六种，见 `deploy/日志采集与可视化流水线-方案设计.md` §3.2）
NODE_TYPE_CHOICES = (
    ("param", "参数化"),
    ("command", "执行命令"),
    ("check", "环境检查"),
    ("upload", "上传制品"),
    ("build", "构建"),
    ("notify", "通知"),
)

# 节点失败后的走向
#
# ★ 刻意**只有 stop / continue**，不做 `goto:<节点id>` 分支指针：
#   分支指针要引入「环检测 + 最大跳转次数」，而一旦漏了环检测，
#   一次误配就是**无限重跑发布的自动化事故**（比"发布失败"严重得多）。
#   顺序编排已经覆盖了「失败即停 / 失败继续」这两种真实诉求；
#   真需要分支时再连 `pos_x/pos_y` 一起升级自由画布，那时一并做环检测。
ON_FAILURE_CHOICES = (
    ("stop", "失败即停止"),
    ("continue", "失败继续"),
)

RUN_STATUS_CHOICES = (
    ("pending", "待执行"),
    ("running", "执行中"),
    ("success", "全部成功"),
    ("partial", "部分失败"),
    ("failed", "失败"),
    ("aborted", "已中止"),
)

# 终态：到达后不再接受 advance
#
# ★ `partial` 是刻意加的一档，不是"failed 的别名"：
#   节点被配置成「失败继续」时，后面几个节点会照跑完 —— 此时如果报 `success`，
#   页面上是一条绿色的"发布成功"，而实际上某一步是失败的。
#   发布链路上「看起来成功」比「明确报错」危险得多，所以单开一档。
RUN_FINAL_STATUS = ("success", "partial", "failed", "aborted")

NODE_RUN_STATUS_CHOICES = (
    ("pending", "待执行"),
    ("running", "执行中"),
    ("success", "成功"),
    ("failed", "失败"),
)

TRIGGER_TYPE_CHOICES = (
    ("manual", "手动触发"),
    ("schedule", "定时触发"),
)

# 单节点超时上限：命令/检查节点
MAX_NODE_TIMEOUT = 300
# 「构建」节点等待 Jenkins 出结果的上限（秒）
MAX_BUILD_WAIT = 600
# 单个节点最多操作的服务器数（与命令下发的量级一致）
MAX_TARGETS_PER_NODE = 50


class Pipeline(CoreModel):
    """流水线：一条编排定义。

    `params` 是**运行时参数定义**（启动流水线时让用户填版本号/环境等），
    形如 ``[{"key":"version","label":"版本号","default":"","required":true}]``。
    这些值会被节点配置用 ``{{version}}`` 之类的占位符引用。

    ★ 只做「一层」占位符替换，不引入任何表达式求值 —— 发布链路上
      "用户可控的文本参与代码求值"是绝对不能开的口子。
    """

    name = models.CharField(max_length=64, verbose_name="流水线名称", help_text="如 myapp 生产发布")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态", help_text="状态")
    params = models.JSONField(default=list, blank=True, verbose_name="运行时参数",
                              help_text='JSON 数组：[{"key":"version","label":"版本号","default":"","required":true}]')
    credential = models.ForeignKey(to="bastion.Credential", on_delete=models.SET_NULL, null=True, blank=True,
                                   db_constraint=False, verbose_name="默认凭据",
                                   help_text="连接目标机的默认凭据（节点可覆盖）；复用堡垒机凭据，已加密")

    class Meta:
        db_table = "release_pipeline"
        verbose_name = "发布流水线"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]

    def param_defs(self):
        """把 `params` 归一成 ``[{key,label,default,required}]``，丢掉非法项。

        ★ 归一放在模型层而不是序列化器：`engine` 建 run 时也要用同一份口径，
          两处各写一遍迟早会出现"页面能填、引擎认不出"的错位。
        """
        out, seen = [], set()
        for item in (self.params or []):
            if not isinstance(item, dict):
                continue
            key = str(item.get('key') or '').strip()
            # 参数名要能安全地做占位符替换：只允许字母数字下划线
            if not key or key in seen or not key.replace('_', '').isalnum():
                continue
            seen.add(key)
            out.append({
                'key': key,
                'label': str(item.get('label') or key)[:64],
                'default': '' if item.get('default') is None else str(item.get('default')),
                'required': bool(item.get('required')),
            })
        return out

    def node_count(self):
        return self.nodes.count()

    def __str__(self):
        return self.name


class PipelineNode(CoreModel):
    """流水线节点（顺序编排的一个步骤）。

    ``config`` 按 ``node_type`` 各存各的：

    ==========  ================================================================
    param       ``{}``（值从 Pipeline.params 取，节点只是个可视化占位）
    command     ``{command, targets, credential, timeout, on_failure_hint}``
    check       ``{command, targets, credential, timeout}``（退出码非 0 即失败）
    upload      ``{local_path, remote_path, targets, credential}``
    build       ``{jenkins_server_id, job, parameters, wait_timeout}``
    notify      ``{channel_id, title, content, on}``  on = always/success/failure
    ==========  ================================================================
    """

    pipeline = models.ForeignKey(to=Pipeline, on_delete=models.CASCADE, db_constraint=False,
                                 related_name="nodes", verbose_name="流水线", help_text="所属流水线")
    name = models.CharField(max_length=64, verbose_name="节点名称", help_text="如 上传制品 / 重启服务")
    node_type = models.CharField(max_length=20, choices=NODE_TYPE_CHOICES, default="command",
                                 verbose_name="节点类型", help_text="节点类型")
    config = models.JSONField(default=dict, blank=True, verbose_name="节点配置",
                              help_text="各类型自己的配置，见 models.py 的字段说明")
    seq = models.IntegerField(default=0, verbose_name="顺序号", help_text="编排顺序（由小到大执行）")
    on_failure = models.CharField(max_length=20, choices=ON_FAILURE_CHOICES, default="stop",
                                  verbose_name="失败处理", help_text="该节点失败后：停止整条流水线 / 继续下一个节点")
    # ★ 预留自由画布：现在不渲染，但先存着 —— 将来升级画布不用改数据模型
    pos_x = models.IntegerField(default=0, verbose_name="画布X", help_text="预留：自由画布坐标")
    pos_y = models.IntegerField(default=0, verbose_name="画布Y", help_text="预留：自由画布坐标")

    class Meta:
        db_table = "release_pipeline_node"
        verbose_name = "流水线节点"
        verbose_name_plural = verbose_name
        ordering = ["seq", "id"]

    def target_list(self):
        """节点配置里的目标（只保留能取到 server_id 的项）。"""
        out = []
        for t in (self.config or {}).get('targets') or []:
            if not isinstance(t, dict):
                continue
            try:
                sid = int(t.get('server_id'))
            except (TypeError, ValueError):
                continue
            item = {'server_id': sid}
            item['label'] = str(t.get('label') or '')
            item['ip'] = str(t.get('ip') or '')
            try:
                item['ssh_port'] = int(t.get('ssh_port') or 22)
            except (TypeError, ValueError):
                item['ssh_port'] = 22
            out.append(item)
        return out

    def __str__(self):
        return "%s[%s] %s" % (self.pipeline_id, self.seq, self.name)


class PipelineRun(CoreModel):
    """一次流水线执行。

    ``pipeline`` 用 ``SET_NULL`` + ``pipeline_name`` 快照：流水线被删掉之后，
    **执行历史仍然完整可查**（审计记录不能因为编排被删就消失）。
    """

    pipeline = models.ForeignKey(to=Pipeline, on_delete=models.SET_NULL, null=True, blank=True,
                                 db_constraint=False, related_name="runs",
                                 verbose_name="流水线", help_text="所属流水线（可能已被删除）")
    pipeline_name = models.CharField(max_length=64, verbose_name="流水线名称", null=True, blank=True,
                                     help_text="发起时的名称快照")
    status = models.CharField(max_length=20, choices=RUN_STATUS_CHOICES, default="pending",
                              verbose_name="状态", help_text="执行状态")
    params = models.JSONField(default=dict, blank=True, verbose_name="本次参数",
                              help_text="本次执行实际填入的参数值")
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE_CHOICES, default="manual",
                                    verbose_name="触发方式", help_text="触发方式")

    total_nodes = models.IntegerField(default=0, verbose_name="节点总数", help_text="节点总数")
    done_nodes = models.IntegerField(default=0, verbose_name="已完成节点", help_text="已结束（成功或失败）的节点数")
    failed_nodes = models.IntegerField(default=0, verbose_name="失败节点", help_text="失败的节点数")
    current_node_id = models.IntegerField(verbose_name="当前节点ID", null=True, blank=True,
                                          help_text="正在执行/最近执行的节点 id")

    started_at = models.DateTimeField(verbose_name="开始时间", null=True, blank=True, help_text="开始时间")
    finished_at = models.DateTimeField(verbose_name="结束时间", null=True, blank=True, help_text="结束时间")
    last_error = models.TextField(verbose_name="最近错误", null=True, blank=True, help_text="失败节点的错误摘要")

    class Meta:
        db_table = "release_pipeline_run"
        verbose_name = "流水线执行"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]

    @property
    def is_final(self):
        return self.status in RUN_FINAL_STATUS

    def __str__(self):
        return "%s #%s %s" % (self.pipeline_name, self.pk, self.status)


class PipelineNodeRun(CoreModel):
    """节点在一次执行里的结果。

    ``node`` 用 ``SET_NULL``，同时把 ``node_name/node_type/on_failure/config`` 快照下来 ——
    编排页改一个字就重跑，历史记录不该跟着变（否则审计记录会被"追改"）。
    """

    run = models.ForeignKey(to=PipelineRun, on_delete=models.CASCADE, db_constraint=False,
                            related_name="node_runs", verbose_name="执行记录", help_text="所属执行记录")
    node = models.ForeignKey(to=PipelineNode, on_delete=models.SET_NULL, null=True, blank=True,
                             db_constraint=False, verbose_name="节点", help_text="对应节点（可能已被删除）")
    node_name = models.CharField(max_length=64, verbose_name="节点名称", null=True, blank=True,
                                 help_text="节点名称快照")
    node_type = models.CharField(max_length=20, choices=NODE_TYPE_CHOICES, default="command",
                                 verbose_name="节点类型", help_text="节点类型快照")
    seq = models.IntegerField(default=0, verbose_name="顺序号", help_text="执行顺序")
    on_failure = models.CharField(max_length=20, choices=ON_FAILURE_CHOICES, default="stop",
                                  verbose_name="失败处理", help_text="失败处理快照")
    config = models.JSONField(default=dict, blank=True, verbose_name="节点配置快照",
                              help_text="发起时固化的节点配置")

    status = models.CharField(max_length=20, choices=NODE_RUN_STATUS_CHOICES, default="pending",
                              verbose_name="状态", help_text="节点状态")
    targets_result = models.JSONField(default=list, blank=True, verbose_name="逐台结果",
                                      help_text='JSON 数组：[{"label":..,"ip":..,"ok":..,"stdout":..,"exit_code":..}]')
    message = models.CharField(max_length=512, verbose_name="结果摘要", null=True, blank=True,
                               help_text="成功或失败的摘要")
    started_at = models.DateTimeField(verbose_name="开始时间", null=True, blank=True, help_text="开始时间")
    finished_at = models.DateTimeField(verbose_name="结束时间", null=True, blank=True, help_text="结束时间")
    duration = models.FloatField(verbose_name="耗时(秒)", null=True, blank=True, help_text="耗时（秒）")

    class Meta:
        db_table = "release_pipeline_node_run"
        verbose_name = "流水线节点执行"
        verbose_name_plural = verbose_name
        ordering = ["seq", "id"]

    def __str__(self):
        return "run=%s seq=%s %s" % (self.run_id, self.seq, self.status)
