# -*- coding: utf-8 -*-
from django.apps import AppConfig


class ReleaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dvadmin.release"
    verbose_name = "发布流水线"
