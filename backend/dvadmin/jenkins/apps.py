from django.apps import AppConfig


class JenkinsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dvadmin.jenkins'
    verbose_name = '发布管理'
