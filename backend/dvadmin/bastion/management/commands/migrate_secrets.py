"""Idempotent encryption migration; no secrets are printed."""
from cryptography.fernet import InvalidToken
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from dvadmin.alert.models import NotifyChannel
from dvadmin.alert.secrets import PREFIX, SECRET_FIELDS
from dvadmin.bastion.crypto import decrypt, encrypt
from dvadmin.log.models import ElasticsearchSource


class Command(BaseCommand):
    help = '校验并迁移历史渠道/ES 密钥；默认只检查，--apply 才写入'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--redact-history', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        changed = 0
        # Validate the configured key before touching rows.
        decrypt(encrypt('key-check'))
        for channel in NotifyChannel.objects.select_for_update():
            cfg = dict(channel.config or {})
            dirty = False
            for key in SECRET_FIELDS:
                value = cfg.get(key)
                if not value:
                    continue
                if value.startswith(PREFIX):
                    try:
                        decrypt(value[len(PREFIX):])
                    except InvalidToken:
                        raise CommandError(f'渠道 {channel.pk} 解密失败；请恢复原密钥')
                else:
                    cfg[key] = PREFIX + encrypt(value)
                    dirty = True
            if dirty:
                changed += 1
                if options['apply']:
                    channel.config = cfg
                    channel.save(update_fields=['config'])
        for source in ElasticsearchSource.objects.select_for_update().exclude(password__in=['', None]):
            if not source.password:
                continue
            try:
                decrypt(source.password)
            except InvalidToken:
                if source.password.startswith('gAAAA'):
                    raise CommandError(f'ES {source.pk} 疑似旧密文但解密失败；停止，禁止二次加密')
                changed += 1
                if options['apply']:
                    source.set_password(source.password)
                    source.save(update_fields=['password'])
        # Verify other encrypted credentials too, to detect accidental key changes.
        from dvadmin.bastion.models import Credential
        from dvadmin.jenkins.models import JenkinsServer
        for model, fields in [(Credential, ('password', 'private_key')), (JenkinsServer, ('token',))]:
            for row in model.objects.all():
                for field in fields:
                    if getattr(row, field):
                        try:
                            decrypt(getattr(row, field))
                        except InvalidToken:
                            raise CommandError(f'{model.__name__} {row.pk} 解密失败，请检查原密钥')
        if options['redact_history']:
            model = next((m for m in apps.get_models() if m._meta.db_table == 'dvadmin_system_operation_log'), None)
            if model is None:
                raise CommandError('没有找到操作日志模型')
            self.stdout.write(f'历史日志待脱敏：{model.objects.count()} 行')
            if options['apply']:
                model.objects.all().update(request_body='[REDACTED]', json_result='[REDACTED]', request_msg='[REDACTED]')
        self.stdout.write(f'需迁移密钥记录：{changed}；模式：' + ('已应用' if options['apply'] else '只检查'))
