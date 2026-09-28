# -*- coding: utf-8 -*-
from django.apps import AppConfig


class LogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dvadmin.log"
    verbose_name = "日志管理"
