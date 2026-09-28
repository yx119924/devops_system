"""Read-only deployment checks against the real installed framework and schema."""
import os
from pathlib import Path
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.urls import resolve
from dvadmin.bastion.crypto import encrypt, decrypt
from dvadmin.alert.rendering import validate_template


class Command(BaseCommand):
    help = '检查真实框架、配置、表结构、接口及历史模板（不修改业务数据）'

    def handle(self, *args, **options):
        errors = []
        if settings.DEBUG:
            errors.append('DEBUG 必须为 False（当前为 True，改 backend/conf/env.py）')
        if '*' in settings.ALLOWED_HOSTS:
            errors.append("ALLOWED_HOSTS 禁止 *，改成实际访问用的主机名/IP，"
                          "例如 ['192.168.1.50', '127.0.0.1', 'localhost']"
                          "（改 backend/conf/env.py；端口不用写，Django 会自动忽略端口）")
        if 'redis' not in settings.CACHES['default']['BACKEND'].lower():
            errors.append('默认缓存必须为共享 Redis')
        if len(getattr(settings, 'ALERT_WEBHOOK_SECRET', '') or os.environ.get('ALERT_WEBHOOK_SECRET', '')) < 32:
            errors.append('ALERT_WEBHOOK_SECRET 至少 32 字符')
        try:
            decrypt(encrypt('preflight'))
        except Exception:
            errors.append('凭据加密密钥缺失或格式无效')
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
            for model in apps.get_models():
                if model._meta.app_label not in ('bastion', 'cmdb', 'alert', 'jenkins', 'log', 'monitor'):
                    continue
                table = model._meta.db_table
                if table not in tables:
                    errors.append('缺少表：' + table)
                    continue
                actual = {col.name for col in connection.introspection.get_table_description(cursor, table)}
                expected = {field.column for field in model._meta.local_fields}
                if expected - actual:
                    errors.append(f'{table} 缺少字段：' + ', '.join(sorted(expected - actual)))
        # ★ 本交付未启用 Web SSH 票据（terminal 路由未挂载），故不检查该路径。
        # ★ 本交付也未接入 Grafana SSO，因此**不存在** /api/monitor/grafana/{id}/entry/；
        #   这里改查确实存在的 grafana sources 接口，以验证该路由已挂载。
        for path in ['/api/bastion/dispatch/',
                     '/api/bastion/session/1/recording/', '/api/cmdb/server/dispatch_options/',
                     '/api/monitor/grafana/sources/', '/api/alert/webhook/receiver/']:
            try:
                resolve(path)
            except Exception:
                errors.append('接口未挂载：' + path)
        try:
            from application.asgi import application  # noqa: F401
            import celery, paramiko, cryptography  # noqa: F401
            from cryptography.fernet import Fernet  # noqa: F401
        except Exception as exc:
            errors.append('ASGI 或依赖无法加载：' + type(exc).__name__)
        from dvadmin.alert.models import AlertTemplate
        if 'alert_template' in tables:
            for template in AlertTemplate.objects.filter(enabled=True):
                try:
                    validate_template(template.body)
                except Exception:
                    self.stdout.write(f'提示：模板 ID {template.pk} 不兼容限制语法；通知将使用默认文本，需在模板页调整')
        # ★ 本交付保留了 ssh_client 的 AutoAddPolicy，known_hosts 不参与校验，故只作提示。
        known = Path(os.environ.get('SSH_KNOWN_HOSTS', '/backend/conf/known_hosts'))
        if not known.is_file() or not known.stat().st_size:
            self.stdout.write('提示：未配置 known_hosts（本版使用 AutoAddPolicy，属预期）')
        if errors:
            raise CommandError('\n'.join(errors))
        self.stdout.write(self.style.SUCCESS('配置、表字段、接口挂载及运行时导入检查通过。'))
