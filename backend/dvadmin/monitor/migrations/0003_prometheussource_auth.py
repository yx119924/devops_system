# -*- coding: utf-8 -*-
"""监控数据源增加访问凭据字段（Basic Auth / Grafana API Token）"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitor", "0002_alter_prometheussource_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="prometheussource",
            name="username",
            field=models.CharField(
                blank=True,
                help_text="Basic Auth 用户名（可选，匿名留空）",
                max_length=64,
                null=True,
                verbose_name="用户名",
            ),
        ),
        migrations.AddField(
            model_name="prometheussource",
            name="password",
            field=models.TextField(
                blank=True,
                help_text="Basic Auth 密码；Grafana 也可只填 API Token（加密存储）",
                null=True,
                verbose_name="密码(密文)",
            ),
        ),
    ]
