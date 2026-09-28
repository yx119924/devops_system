from rest_framework import routers

from dvadmin.monitor.views.grafana import GrafanaProxyViewSet
from dvadmin.monitor.views.prometheus import PrometheusSourceViewSet

router = routers.SimpleRouter()
router.register(r'prometheus', PrometheusSourceViewSet, basename='monitor_prometheus')
router.register(r'grafana', GrafanaProxyViewSet, basename='monitor_grafana')

urlpatterns = router.urls
