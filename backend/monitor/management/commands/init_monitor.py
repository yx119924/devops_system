from django.core.management.base import BaseCommand

from dvadmin.monitor.models import PrometheusSource


class Command(BaseCommand):
    help = '初始化监控数据源（Prometheus + Alertmanager 各一条，占位地址），可重复执行'

    def handle(self, *args, **options):
        defaults = [
            ('本机 Prometheus', 'prometheus', 'http://127.0.0.1:9090', 1),
            ('本机 Alertmanager', 'alertmanager', 'http://127.0.0.1:9093', 2),
        ]
        for name, source_type, url, sort in defaults:
            obj, created = PrometheusSource.objects.get_or_create(
                name=name,
                source_type=source_type,
                defaults={'url': url, 'status': 1, 'sort': sort},
            )
            flag = '新增' if created else '已存在'
            self.stdout.write(f'  [{flag}] {name} ({source_type}) -> {obj.url}')
        self.stdout.write(self.style.SUCCESS('监控数据源初始化完成，请到「监控告警 → 数据源管理」把地址改成实际值'))
