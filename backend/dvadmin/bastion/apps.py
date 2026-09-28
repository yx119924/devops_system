from django.apps import AppConfig


class BastionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dvadmin.bastion'
    verbose_name = '堡垒机'

    def ready(self):
        from django.db.models.signals import pre_save
        from .redaction import redact_operation_log
        pre_save.connect(redact_operation_log, dispatch_uid='xwops.redact_operation_log', weak=False)
