from django.core.management.base import BaseCommand

from dvadmin.monitor.models import PrometheusSource


class Command(BaseCommand):
    help = '初始化监控数据源（默认指向本机 Prometheus），可重复执行'

    def handle(self, *args, **options):
        PrometheusSource.objects.get_or_create(
            name='本机 Prometheus',
            defaults={'url': 'http://172.30.0.16:9090', 'status': 1, 'sort': 1},
        )
        self.stdout.write(self.style.SUCCESS('监控数据源初始化完成：本机 Prometheus (http://172.30.0.16:9090)'))
