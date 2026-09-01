# -*- coding: utf-8 -*-
"""
监控数据源模型：Prometheus / Alertmanager 统一管理
"""
from django.db import models

from dvadmin.utils.models import CoreModel

STATUS_CHOICES = (
    (1, "启用"),
    (0, "停用"),
)

SOURCE_TYPE_CHOICES = (
    ("prometheus", "Prometheus"),
    ("alertmanager", "Alertmanager"),
)


class PrometheusSource(CoreModel):
    """监控数据源配置（Prometheus / Alertmanager）"""
    name = models.CharField(max_length=64, verbose_name="数据源名称", help_text="数据源名称")
    source_type = models.CharField(
        max_length=16, choices=SOURCE_TYPE_CHOICES, default="prometheus",
        verbose_name="类型", help_text="数据类型：Prometheus / Alertmanager",
    )
    url = models.CharField(max_length=255, verbose_name="监控地址", help_text="如 http://192.168.1.100:9090")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态", help_text="状态")
    sort = models.IntegerField(default=1, verbose_name="显示排序", null=True, blank=True, help_text="显示排序")

    class Meta:
        db_table = "monitor_prometheus_source"
        verbose_name = "监控数据源"
        verbose_name_plural = verbose_name
        ordering = ["sort", "-create_datetime"]

    @classmethod
    def get_url(cls, source_type):
        """按类型取第一条启用的数据源地址，无则返回空串。"""
        row = (
            cls.objects.filter(status=1, source_type=source_type)
            .order_by("sort", "id")
            .values_list("url", flat=True)
            .first()
        )
        return (row or "").strip()
