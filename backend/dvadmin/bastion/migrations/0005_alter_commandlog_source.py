# -*- coding: utf-8 -*-
"""给命令审计的「来源」加一档：流水线发布。

流水线的命令/检查节点会把执行写进 `CommandLog`（见 `release/engine.py::_audit`），
让「命令审计」页能把发布动作一起收进来 —— 运维查"这台机器上谁干了什么"
只会看那一个页面。

★ 只加一个枚举值，不新增/修改任何字段：对已有数据零影响。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bastion', '0004_commanddispatchitem_ssh_port'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commandlog',
            name='source',
            field=models.CharField(
                choices=[('session', '交互会话'), ('dispatch', '命令下发'), ('release', '流水线发布')],
                default='session', help_text='命令来源', max_length=20, verbose_name='来源'),
        ),
    ]
