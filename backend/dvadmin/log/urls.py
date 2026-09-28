from rest_framework import routers

from dvadmin.log.views.collect import LogCollectTaskViewSet
from dvadmin.log.views.source import ElasticsearchSourceViewSet

router = routers.SimpleRouter()
router.register(r'es', ElasticsearchSourceViewSet, basename='log_es')
# 日志采集配置（「日志管理 → 采集配置」）
# ★ 前端调用路径形如 /api/log/collect/；nginx 的 `rewrite ^/api/(.*)$ /$1 break`
#   会削掉最外层 /api，落到这里的 api/log/ 前缀上。
router.register(r'collect', LogCollectTaskViewSet, basename='log_collect')

urlpatterns = router.urls
