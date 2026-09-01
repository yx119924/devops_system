from django.core.management.base import BaseCommand

from dvadmin.cmdb.models import BusinessLine, Environment, Idc


class Command(BaseCommand):
    help = '初始化 CMDB 基础数据（环境/业务线/机房），可重复执行'

    def handle(self, *args, **options):
        environments = [
            ('生产', 'prod', 1),
            ('测试', 'test', 2),
            ('开发', 'dev', 3),
        ]
        for name, code, sort in environments:
            Environment.objects.get_or_create(name=name, defaults={'code': code, 'sort': sort})
        self.stdout.write(self.style.SUCCESS('环境初始化完成：生产/测试/开发'))

        business_lines = [
            ('devops', 'devops', 1),
        ]
        for name, code, sort in business_lines:
            BusinessLine.objects.get_or_create(name=name, defaults={'code': code, 'sort': sort})
        self.stdout.write(self.style.SUCCESS('业务线初始化完成：devops'))

        idcs = [
            ('1号机房', 'idc1', '1号机房', 1),
            ('2号机房', 'idc2', '2号机房', 2),
        ]
        for name, code, location, sort in idcs:
            Idc.objects.get_or_create(name=name, defaults={'code': code, 'location': location, 'sort': sort})
        self.stdout.write(self.style.SUCCESS('机房初始化完成：1号机房/2号机房'))
