# -*- coding: utf-8 -*-
"""
告警管理数据模型：告警规则
"""
from django.db import models

from dvadmin.utils.models import CoreModel

SEVERITY_CHOICES = (
    ("critical", "严重"),
    ("warning", "警告"),
    ("info", "提示"),
)


class AlertRule(CoreModel):
    """告警规则（对应 Prometheus alerting rule）"""
    name = models.CharField(max_length=128, verbose_name="规则名称", help_text="告警名称，需唯一")
    expr = models.TextField(verbose_name="PromQL 表达式", help_text="触发告警的 PromQL 表达式，如 up == 0")
    duration = models.CharField(max_length=16, default="1m", verbose_name="持续时间",
                                help_text="条件持续多久才触发，如 30s / 1m / 5m")
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="warning",
                                verbose_name="告警级别", help_text="告警级别")
    summary = models.CharField(max_length=255, verbose_name="告警摘要", null=True, blank=True,
                               help_text="告警标题摘要")
    description = models.CharField(max_length=512, verbose_name="告警描述", null=True, blank=True,
                                   help_text="告警详细描述")
    enabled = models.BooleanField(default=True, verbose_name="是否启用", help_text="停用后规则不参与评估")
    group = models.ForeignKey(to="AlertGroup", on_delete=models.SET_NULL, null=True, blank=True,
                              db_constraint=False, verbose_name="告警群组",
                              help_text="关联告警群组后，触发时只发群组内的渠道；不选则按所有启用渠道发送")
    template = models.ForeignKey(to="AlertTemplate", on_delete=models.SET_NULL, null=True, blank=True,
                                 db_constraint=False, related_name="rules",
                                 verbose_name="通知模板",
                                 help_text="触发后使用该模板渲染通知内容；不选则用默认模板（is_default）或内置格式")

    class Meta:
        db_table = "alert_rule"
        verbose_name = "告警规则"
        verbose_name_plural = verbose_name
        ordering = ["severity", "-create_datetime"]


CHANNEL_TYPE_CHOICES = (
    ("feishu", "飞书"),
    ("dingtalk", "钉钉"),
    ("wechat", "企业微信"),
    ("email", "邮箱"),
)


class NotifyChannel(CoreModel):
    """通知渠道（飞书/钉钉/企业微信/邮箱 webhook 配置）"""
    name = models.CharField(max_length=64, verbose_name="渠道名称", help_text="渠道名称")
    type = models.CharField(max_length=16, choices=CHANNEL_TYPE_CHOICES, verbose_name="渠道类型",
                             help_text="渠道类型")
    config = models.JSONField(default=dict, verbose_name="渠道配置", blank=True,
                              help_text='JSON 配置：飞书/企微填 {"webhook":"..."}；钉钉填 {"webhook":"...","secret":"..."}；'
                                        '邮箱填 {"smtp_host":"","smtp_port":465,"username":"","password":"","to_addrs":["..."]}')
    enabled = models.BooleanField(default=True, verbose_name="是否启用", help_text="是否启用")
    description = models.CharField(max_length=255, verbose_name="描述", null=True, blank=True,
                                   help_text="描述")

    class Meta:
        db_table = "alert_channel"
        verbose_name = "通知渠道"
        verbose_name_plural = verbose_name
        ordering = ["type", "-create_datetime"]


class AlertGroup(CoreModel):
    """告警群组：聚合多个通知渠道，告警规则关联群组后只发群组内的渠道"""
    name = models.CharField(max_length=64, verbose_name="群组名称", help_text="群组名称")
    description = models.CharField(max_length=255, verbose_name="描述", null=True, blank=True,
                                   help_text="描述")
    enabled = models.BooleanField(default=True, verbose_name="是否启用", help_text="是否启用")
    channels = models.ManyToManyField(to=NotifyChannel, blank=True, db_constraint=False,
                                       related_name="groups",
                                       verbose_name="通知渠道", help_text="群组包含的通知渠道")

    class Meta:
        db_table = "alert_group"
        verbose_name = "告警群组"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]


ALERT_STATUS_CHOICES = (
    ("firing", "告警中"),
    ("resolved", "已恢复"),
)


class AlertEvent(CoreModel):
    """告警事件：Alertmanager webhook 持久化存储的历史告警"""
    fingerprint = models.CharField(max_length=64, verbose_name="告警指纹", db_index=True,
                                   help_text="Alertmanager 告警唯一指纹（labels 哈希）")
    alertname = models.CharField(max_length=128, verbose_name="告警名称", db_index=True,
                                 help_text="告警名称（labels.alertname）")
    status = models.CharField(max_length=16, choices=ALERT_STATUS_CHOICES, default="firing",
                              verbose_name="状态", help_text="告警状态")
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="warning",
                                verbose_name="告警级别", help_text="告警级别")
    instance = models.CharField(max_length=128, verbose_name="实例", null=True, blank=True,
                                help_text="触发告警的实例（labels.instance）")
    summary = models.CharField(max_length=512, verbose_name="告警摘要", null=True, blank=True,
                               help_text="告警摘要（annotations.summary）")
    description = models.CharField(max_length=1024, verbose_name="告警描述", null=True, blank=True,
                                   help_text="告警描述（annotations.description）")
    labels = models.JSONField(default=dict, verbose_name="标签", blank=True,
                              help_text="告警完整 labels")
    starts_at = models.DateTimeField(verbose_name="开始时间", null=True, blank=True,
                                     help_text="告警开始时间")
    ends_at = models.DateTimeField(verbose_name="恢复时间", null=True, blank=True,
                                   help_text="告警恢复时间")

    class Meta:
        db_table = "alert_event"
        verbose_name = "告警事件"
        verbose_name_plural = verbose_name
        ordering = ["-starts_at", "-create_datetime"]


class AlertTemplate(CoreModel):
    """告警模板：Jinja2 模板，由告警规则引用（AlertRule.template）渲染通知内容。
    is_default=True 时作为兜底模板，未指定模板的规则触发时使用。
    """
    name = models.CharField(max_length=64, unique=True, verbose_name="模板名称",
                            help_text="模板名称，全局唯一")
    description = models.CharField(max_length=255, null=True, blank=True,
                                   verbose_name="模板描述")
    body = models.TextField(verbose_name="模板内容（Jinja2）",
                            help_text="可用变量：alertname / severity / status / instance / "
                                      "summary / description / startsAt / endsAt / value / labels")
    variables = models.JSONField(default=list, blank=True, verbose_name="模板变量",
                                 help_text="自动从 body 中提取的变量名（只读）")
    is_default = models.BooleanField(default=False, verbose_name="默认模板",
                                     help_text="True 时作为兜底模板，未指定模板的规则触发时使用")
    enabled = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = "alert_template"
        verbose_name = "告警模板"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]
