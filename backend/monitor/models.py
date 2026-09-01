# -*- coding: utf-8 -*-
"""
监控告警数据模型：Prometheus 数据源
"""
from django.db import models

from dvadmin.utils.models import CoreModel

STATUS_CHOICES = (
    (1, "启用"),
    (0, "停用"),
)


class PrometheusSource(CoreModel):
    """Prometheus 数据源配置"""
    name = models.CharField(max_length=64, verbose_name="数据源名称", help_text="数据源名称")
    url = models.CharField(max_length=255, verbose_name="Prometheus 地址", help_text="如 http://172.30.0.16:9090")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态", help_text="状态")
    sort = models.IntegerField(default=1, verbose_name="显示排序", null=True, blank=True, help_text="显示排序")

    class Meta:
        db_table = "monitor_prometheus_source"
        verbose_name = "Prometheus 数据源"
        verbose_name_plural = verbose_name
        ordering = ["sort", "-create_datetime"]
