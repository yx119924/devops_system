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
