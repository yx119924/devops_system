# -*- coding: utf-8 -*-
"""
堡垒机数据模型：凭据 / 会话记录 / 命令审计
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
    """命令审计"""
    session = models.ForeignKey(to=SessionRecord, on_delete=models.CASCADE, db_constraint=False,
                                verbose_name="会话", help_text="所属会话")
    command = models.TextField(verbose_name="命令", help_text="执行的命令")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="执行时间", help_text="执行时间")
    is_dangerous = models.BooleanField(default=False, verbose_name="高危命令", help_text="是否高危命令")

    class Meta:
        db_table = "bastion_command_log"
        verbose_name = "命令审计"
        verbose_name_plural = verbose_name
        ordering = ["-timestamp"]
