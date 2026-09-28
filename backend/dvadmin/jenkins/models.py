# -*- coding: utf-8 -*-
"""
Jenkins 发布管理模型：Jenkins 服务器连接配置 + 角色 Job 可见权限
token 复用堡垒机凭据加密（Fernet，密钥 CREDENTIAL_ENCRYPTION_KEY）
"""
from django.db import models

from dvadmin.bastion.crypto import decrypt, encrypt
from dvadmin.system.models import Role
from dvadmin.utils.models import CoreModel

STATUS_CHOICES = (
    (1, "启用"),
    (0, "停用"),
)


class JenkinsServer(CoreModel):
    """Jenkins 服务器配置：连接地址 + 认证凭据（token 加密存储）"""
    name = models.CharField(max_length=64, verbose_name="服务器名称", help_text="服务器名称")
    url = models.CharField(max_length=255, verbose_name="Jenkins 地址", help_text="如 http://192.168.1.100:8080")
    username = models.CharField(max_length=64, verbose_name="用户名", default="", blank=True,
                                help_text="认证用户名（可为空，用匿名）")
    token = models.TextField(verbose_name="API Token/密码(密文)", null=True, blank=True,
                             help_text="API Token 或密码，加密存储")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态", help_text="状态")
    sort = models.IntegerField(default=1, verbose_name="显示排序", null=True, blank=True, help_text="显示排序")

    class Meta:
        db_table = "jenkins_server"
        verbose_name = "Jenkins 服务器"
        verbose_name_plural = verbose_name
        ordering = ["sort", "-create_datetime"]

    def set_token(self, plain):
        self.token = encrypt(plain) if plain else ''

    def get_token(self):
        return decrypt(self.token)


class JenkinsRolePermission(CoreModel):
    """角色对 Jenkins Job 的可见权限：allowed_paths 前缀列表
    - allowed_paths = []（空）→ 该角色可见全部 Job（管理员/普通运维）
    - allowed_paths = ["dev/", "pre/", "test/"] → 只可见这些路径前缀开头的 Job
    - 某角色没有权限记录 → 无权限（默认拒绝，安全）
    """
    server = models.ForeignKey(to=JenkinsServer, on_delete=models.CASCADE, db_constraint=False,
                               related_name="role_permissions", verbose_name="Jenkins 服务器",
                               help_text="关联的 Jenkins 服务器")
    role = models.ForeignKey(to=Role, on_delete=models.CASCADE, db_constraint=False,
                             verbose_name="角色", help_text="可见性角色")
    allowed_paths = models.JSONField(default=list, blank=True, verbose_name="允许路径前缀",
                                     help_text='JSON 数组，如 ["dev/","pre/","test/"]；空数组=全部')

    class Meta:
        db_table = "jenkins_role_permission"
        verbose_name = "Jenkins 角色权限"
        verbose_name_plural = verbose_name
        ordering = ["id"]

    def __str__(self):
        return f"{self.server.name} / {self.role.name} / {self.allowed_paths}"
