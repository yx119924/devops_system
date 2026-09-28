# -*- coding: utf-8 -*-
"""
CMDB 资产管理数据模型
机房 / 环境 / 业务线 三个维度字典 + 服务器资产主体
"""
from django.db import models

from dvadmin.utils.models import CoreModel

# 维度字典通用状态
STATUS_CHOICES = (
    (1, "启用"),
    (0, "停用"),
)

# 服务器状态
SERVER_STATUS_CHOICES = (
    ("online", "在线"),
    ("offline", "离线"),
    ("maintenance", "维护中"),
    ("offline_shelf", "已下架"),
)


class Idc(CoreModel):
    """机房（命名可自定义，如 1号机房 / 2号机房）"""
    name = models.CharField(max_length=64, verbose_name="机房名称", help_text="机房名称")
    code = models.CharField(max_length=32, verbose_name="机房编码", null=True, blank=True, help_text="机房编码")
    location = models.CharField(max_length=128, verbose_name="位置", null=True, blank=True, help_text="机房位置")
    sort = models.IntegerField(default=1, verbose_name="显示排序", null=True, blank=True, help_text="显示排序")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态", help_text="状态")

    class Meta:
        db_table = "cmdb_idc"
        verbose_name = "机房"
        verbose_name_plural = verbose_name


class Environment(CoreModel):
    """环境（生产 / 测试 / 开发，可扩展）"""
    name = models.CharField(max_length=64, verbose_name="环境名称", help_text="环境名称")
    code = models.CharField(max_length=32, verbose_name="环境编码", null=True, blank=True, help_text="环境编码")
    sort = models.IntegerField(default=1, verbose_name="显示排序", null=True, blank=True, help_text="显示排序")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态", help_text="状态")

    class Meta:
        db_table = "cmdb_environment"
        verbose_name = "环境"
        verbose_name_plural = verbose_name


class BusinessLine(CoreModel):
    """业务线（devops 等，对内）"""
    name = models.CharField(max_length=64, verbose_name="业务线名称", help_text="业务线名称")
    code = models.CharField(max_length=32, verbose_name="业务线编码", null=True, blank=True, help_text="业务线编码")
    owner = models.CharField(max_length=64, verbose_name="负责人", null=True, blank=True, help_text="负责人")
    sort = models.IntegerField(default=1, verbose_name="显示排序", null=True, blank=True, help_text="显示排序")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态", help_text="状态")

    class Meta:
        db_table = "cmdb_business_line"
        verbose_name = "业务线"
        verbose_name_plural = verbose_name


class Server(CoreModel):
    """服务器资产"""
    hostname = models.CharField(max_length=64, verbose_name="主机名", help_text="主机名")
    ip = models.CharField(max_length=64, db_index=True, verbose_name="主管理IP", help_text="主管理IP（堡垒机连接用）")
    extra_ips = models.CharField(max_length=255, verbose_name="其他内网IP", null=True, blank=True,
                                 help_text="多网卡时的其他内网IP，逗号分隔")
    os = models.CharField(max_length=128, verbose_name="操作系统", null=True, blank=True, help_text="操作系统")
    cpu = models.IntegerField(default=0, verbose_name="CPU核数", null=True, blank=True, help_text="CPU核数")
    memory = models.IntegerField(default=0, verbose_name="内存(GB)", null=True, blank=True, help_text="内存大小(GB)")
    disk = models.CharField(max_length=255, verbose_name="磁盘", null=True, blank=True, help_text="磁盘信息")
    deploy_content = models.CharField(max_length=255, verbose_name="部署内容", null=True, blank=True,
                                      help_text="部署的应用/服务，如 nginx / mysql")
    serial_number = models.CharField(max_length=64, verbose_name="设备序列号", null=True, blank=True, help_text="设备序列号")
    purchase_date = models.DateField(verbose_name="采购日期", null=True, blank=True, help_text="采购日期")
    warranty_expiry = models.DateField(verbose_name="维保到期", null=True, blank=True, help_text="维保到期时间")
    ssh_port = models.IntegerField(default=22, verbose_name="SSH端口", help_text="SSH端口")
    status = models.CharField(max_length=20, choices=SERVER_STATUS_CHOICES, default="online", verbose_name="状态",
                              help_text="状态")
    tags = models.CharField(max_length=255, verbose_name="标签", null=True, blank=True, help_text="标签，逗号分隔")

    idc = models.ForeignKey(to=Idc, on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False,
                            verbose_name="机房", help_text="所属机房")
    environment = models.ForeignKey(to=Environment, on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False,
                                    verbose_name="环境", help_text="所属环境")
    business_line = models.ForeignKey(to=BusinessLine, on_delete=models.SET_NULL, null=True, blank=True, db_constraint=False,
                                      verbose_name="业务线", help_text="所属业务线")

    class Meta:
        db_table = "cmdb_server"
        verbose_name = "服务器"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]


# 资产授权级别
GRANT_LEVEL_CHOICES = (
    ("read", "只读"),
    ("write", "可操作"),
)

# 级别排序权重（一台服务器命中多条授权时取最高）
GRANT_LEVEL_RANK = {"read": 1, "write": 2}


class ServerGrant(CoreModel):
    """服务器资产授权：把某台服务器的访问权授予一个角色或一个用户。

设计取舍
--------
DVAdmin 自带的 `RoleMenuButtonPermission.data_range` 只能表达"按**创建者部门**过滤"
（`filters.py` 最后是 `queryset.filter(dept_belong_id__in=dept_list)`），而
`CoreModel.dept_belong_id` 是 `CoreModelManager.create` 写入的**创建人 dept_id（单值审计戳）**。
两者叠加的后果是：

- 一台服务器只能"归属"一个部门，做不到"生产机同时给运维和开发看"
- 想放开就得把 `data_range` 设成 3（全部数据），又变成"谁都能看全部"

所以资产的可访问范围必须独立建模。本表就是那个模型：**多对多 + 级别**。

级别语义
--------
- ``read``  ：能看（列表 / 详情 / 首页统计），**不能**下发命令、**不能** Web SSH
- ``write`` ：能看 + 能下发命令 + 能 Web SSH

判定优先级（见 ``dvadmin/bastion/access.py``）
------------------------------------------------
1. 超级管理员 → 全部服务器，``write``
2. 资产运营者（持有 ``server:Create`` / ``server:Update`` / ``server:Delete`` 任一按钮权限，
   即"运维 / 管理员"角色）→ 全部服务器，``write``
3. 其余用户 → 只认本表记录：``role`` 命中（用户所属任一角色）或 ``user`` 命中；
   同一台服务器有多条授权时取**最高**级别
4. 无任何命中 → 看不到、做不了（**fail closed**）

字段说明
--------
``role`` / ``user`` 至少填一个（由 ``ServerGrantSerializer.validate`` 保证）。
MySQL 下 NULL 不参与唯一约束，所以"同一 server+role 不重复"也在序列化器里校验。
"""

    server = models.ForeignKey(
        to=Server, on_delete=models.CASCADE, db_constraint=False,
        related_name="grants", verbose_name="服务器",
        help_text="被授权的服务器资产",
    )
    role = models.ForeignKey(
        to="system.Role", on_delete=models.CASCADE, db_constraint=False,
        null=True, blank=True, related_name="server_grants", verbose_name="授权角色",
        help_text="授予该角色的全体用户；与「授权用户」至少填一个",
    )
    user = models.ForeignKey(
        to="system.Users", on_delete=models.CASCADE, db_constraint=False,
        null=True, blank=True, related_name="server_grants", verbose_name="授权用户",
        help_text="授予该用户本人；与「授权角色」至少填一个",
    )
    level = models.CharField(
        max_length=8, choices=GRANT_LEVEL_CHOICES, default="read",
        verbose_name="授权级别", help_text="只读=仅可查看；可操作=可查看并下发命令/Web SSH",
    )

    class Meta:
        db_table = "cmdb_server_grant"
        verbose_name = "服务器资产授权"
        verbose_name_plural = verbose_name
        ordering = ["server_id", "id"]
        indexes = [
            models.Index(fields=["role"], name="cmdb_grant_role_idx"),
            models.Index(fields=["user"], name="cmdb_grant_user_idx"),
        ]

    def __str__(self):
        who = self.role.name if self.role_id else (
            (self.user.name or self.user.username) if self.user_id else "?")
        return "%s → %s (%s)" % (self.server.hostname if self.server_id else "?", who, self.level)
