from rest_framework import routers

from dvadmin.release.views.pipeline import (
    PipelineNodeToolViewSet,
    PipelineRunViewSet,
    PipelineViewSet,
)

router = routers.SimpleRouter()
# 发布流水线（「发布管理 → 流水线编排 / 执行记录」）
# ★ 前端调用路径形如 /api/release/pipeline/；nginx 的 `rewrite ^/api/(.*)$ /$1 break`
#   会削掉最外层 /api，落到这里的 api/release/ 前缀上。
router.register(r'pipeline', PipelineViewSet, basename='release_pipeline')
router.register(r'run', PipelineRunViewSet, basename='release_run')
# 节点工具（预检）。只有一个 detail=False 的 POST 动作 ⇒ SimpleRouter 会跳过
# 空映射的 list/retrieve 路由，只留 `/api/release/node/preview/`。
router.register(r'node', PipelineNodeToolViewSet, basename='release_node')

urlpatterns = router.urls
