# -*- coding: utf-8 -*-
"""
堡垒机数据模型：凭据 / 会话记录 / 命令审计 / 命令下发
"""
from django.db import models

from dvadmin.cmdb.models import Server
from dvadmin.utils.models import CoreModel

from .crypto import decrypt, encrypt

AUTH_TYPE_CHOICES = (
    ("password", "密码"),
    ("private_key", "私钥"),
)

SESSION_STATUS_CHOICES = (
    ("active", "进行中"),
    ("closed", "已结束"),
)

DISPATCH_STATUS_CHOICES = (
    ("pending", "待执行"),
    ("running", "执行中"),
    ("success", "全部成功"),
    ("partial", "部分失败"),
    ("failed", "全部失败"),
)

ITEM_STATUS_CHOICES = (
    ("pending", "待执行"),
    ("success", "成功"),
    ("failed", "失败"),
    ("timeout", "超时"),
)

COMMAND_SOURCE_CHOICES = (
    ("session", "交互会话"),
    ("dispatch", "命令下发"),
)

# 高危命令关键词（命令下发 + 交互会话共用，命中则标记 is_dangerous）
DANGEROUS_PATTERNS = [
    'rm -rf', 'rm -fr', 'rm -r /', 'mkfs', 'fdisk', 'dd if=', 'dd of=/dev/sd',
    'drop table', 'drop database', 'truncate table', ':(){', 'shutdown', 'reboot',
    'halt', 'poweroff', 'init 0', 'init 6', 'chmod -R 777 /', '> /dev/sda',
    '> /dev/sdb', 'mv / ', 'curl', 'wget',
]


def is_dangerous_command(command: str) -> bool:
    """判断命令是否命中高危关键词"""
    return any(p in (command or '') for p in DANGEROUS_PATTERNS)


class Credential(CoreModel):
    """凭据：服务器账号密码/私钥，加密托管"""
    name = models.CharField(max_length=64, verbose_name="凭据名称", help_text="凭据名称")
    username = models.CharField(max_length=64, verbose_name="用户名", default="root", help_text="登录用户名")
    auth_type = models.CharField(max_length=20, choices=AUTH_TYPE_CHOICES, default="password",
                                 verbose_name="认证类型", help_text="认证类型")
    password = models.TextField(verbose_name="密码(密文)", null=True, blank=True, help_text="密码密文")
    private_key = models.TextField(verbose_name="私钥(密文)", null=True, blank=True, help_text="私钥密文")
    server = models.ForeignKey(to=Server, on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False,
                               verbose_name="关联服务器", help_text="关联到具体服务器，留空为通用凭据")

    class Meta:
        db_table = "bastion_credential"
        verbose_name = "凭据"
        verbose_name_plural = verbose_name

    def set_password(self, plain):
        self.password = encrypt(plain) if plain else ''

    def get_password(self):
        return decrypt(self.password)

    def set_private_key(self, plain):
        self.private_key = encrypt(plain) if plain else ''

    def get_private_key(self):
        return decrypt(self.private_key)


class SessionRecord(CoreModel):
    """会话记录（操作人为 CoreModel 的 creator 字段）"""
    server = models.ForeignKey(to=Server, on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False,
                               verbose_name="目标服务器", help_text="目标服务器")
    credential = models.ForeignKey(to=Credential, on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False,
                                   verbose_name="使用凭据", help_text="使用的凭据")
    username = models.CharField(max_length=64, verbose_name="登录用户名", null=True, blank=True, help_text="实际登录用户名")
    ip = models.CharField(max_length=64, verbose_name="目标IP", null=True, blank=True, help_text="目标服务器IP")
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="开始时间", help_text="开始时间")
    end_time = models.DateTimeField(verbose_name="结束时间", null=True, blank=True, help_text="结束时间")
    duration = models.IntegerField(default=0, verbose_name="持续时长(秒)", null=True, blank=True, help_text="持续时长")
    status = models.CharField(max_length=20, choices=SESSION_STATUS_CHOICES, default="active",
                              verbose_name="状态", help_text="状态")
    recording = models.CharField(max_length=512, verbose_name="录像文件路径", null=True, blank=True,
                                 help_text="asciinema 录像文件路径")

    class Meta:
        db_table = "bastion_session"
        verbose_name = "会话记录"
        verbose_name_plural = verbose_name
        ordering = ["-start_time"]


class CommandLog(CoreModel):
    """命令审计（交互会话 + 命令下发两种来源）"""
    session = models.ForeignKey(to=SessionRecord, on_delete=models.CASCADE, db_constraint=False,
                                null=True, blank=True, verbose_name="会话", help_text="所属会话（交互会话）")
    dispatch = models.ForeignKey(to='CommandDispatch', on_delete=models.CASCADE, db_constraint=False,
                                 null=True, blank=True, related_name='command_logs',
                                 verbose_name="下发任务", help_text="所属命令下发任务")
    command = models.TextField(verbose_name="命令", help_text="执行的命令")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="执行时间", help_text="执行时间")
    is_dangerous = models.BooleanField(default=False, verbose_name="高危命令", help_text="是否高危命令")
    source = models.CharField(max_length=20, choices=COMMAND_SOURCE_CHOICES, default="session",
                              verbose_name="来源", help_text="命令来源")
    ip = models.CharField(max_length=64, verbose_name="目标IP", null=True, blank=True,
                          help_text="目标服务器IP（命令下发时记录）")

    class Meta:
        db_table = "bastion_command_log"
        verbose_name = "命令审计"
        verbose_name_plural = verbose_name
        ordering = ["-timestamp"]


class CommandDispatch(CoreModel):
    """命令下发任务：堡垒机→多台目标并发执行同一命令"""
    name = models.CharField(max_length=128, verbose_name="任务名称", help_text="任务名称")
    command = models.TextField(verbose_name="命令", help_text="在每台目标上执行的命令")
    credential = models.ForeignKey(to=Credential, on_delete=models.SET_NULL, null=True, blank=True,
                                   db_constraint=False, verbose_name="凭据",
                                   help_text="任务级统一凭据")
    targets = models.JSONField(default=list, blank=True, verbose_name="目标列表",
                               help_text='JSON 数组：[{"server_id":1,"label":"...","ip":"x.x.x.x"}, ...]')
    timeout = models.IntegerField(default=30, verbose_name="单台超时(秒)", help_text="每台目标执行超时秒数")
    max_workers = models.IntegerField(default=10, verbose_name="并发数", help_text="同时执行的目标数（1-50）")
    status = models.CharField(max_length=20, choices=DISPATCH_STATUS_CHOICES, default="pending",
                              verbose_name="状态", help_text="任务状态")
    total = models.IntegerField(default=0, verbose_name="目标数", help_text="目标总数")
    success_count = models.IntegerField(default=0, verbose_name="成功数", help_text="执行成功数")
    failed_count = models.IntegerField(default=0, verbose_name="失败数", help_text="执行失败数")
    started_at = models.DateTimeField(verbose_name="开始执行时间", null=True, blank=True, help_text="实际开始执行时间")
    finished_at = models.DateTimeField(verbose_name="结束时间", null=True, blank=True, help_text="执行完成时间")
    last_error = models.TextField(verbose_name="最近错误", null=True, blank=True, help_text="执行异常信息")

    class Meta:
        db_table = "bastion_command_dispatch"
        verbose_name = "命令下发"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]


class CommandDispatchItem(CoreModel):
    """命令下发每台目标的执行结果"""
    dispatch = models.ForeignKey(to=CommandDispatch, on_delete=models.CASCADE, db_constraint=False,
                                 related_name="items", verbose_name="下发任务", help_text="所属下发任务")
    server = models.ForeignKey(to=Server, on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False,
                               verbose_name="目标服务器", help_text="CMDB 来源的目标")
    label = models.CharField(max_length=128, verbose_name="目标标签", blank=True, help_text="目标显示名")
    ip = models.CharField(max_length=64, verbose_name="目标IP", help_text="实际连接 IP")
    ssh_port = models.IntegerField(default=22, verbose_name="SSH端口", help_text="SSH 连接端口")
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default="pending",
                              verbose_name="状态", help_text="执行状态")
    stdout = models.TextField(verbose_name="标准输出", blank=True, help_text="命令标准输出")
    stderr = models.TextField(verbose_name="标准错误", blank=True, help_text="命令标准错误")
    exit_code = models.IntegerField(verbose_name="退出码", null=True, blank=True, help_text="命令退出码")
    duration = models.FloatField(verbose_name="耗时(秒)", null=True, blank=True, help_text="执行耗时")
    error = models.CharField(max_length=512, verbose_name="错误信息", blank=True, help_text="连接/认证/超时错误")

    class Meta:
        db_table = "bastion_command_dispatch_item"
        verbose_name = "命令下发结果"
        verbose_name_plural = verbose_name
        ordering = ["id"]