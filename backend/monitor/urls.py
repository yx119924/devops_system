from rest_framework import routers

from dvadmin.monitor.views.prometheus import PrometheusSourceViewSet

router = routers.SimpleRouter()
router.register(r'prometheus', PrometheusSourceViewSet, basename='monitor_prometheus')

urlpatterns = router.urls
