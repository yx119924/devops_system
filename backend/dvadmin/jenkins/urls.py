from rest_framework import routers

from dvadmin.jenkins.views.jenkins import JenkinsRoleGrantViewSet, JenkinsServerViewSet

router = routers.SimpleRouter()
router.register(r'server', JenkinsServerViewSet, basename='jenkins_server')
# 「角色管理」页里的 Jenkins 目录授权面板（角色视角：一个角色 × 所有服务器）
router.register(r'role_grant', JenkinsRoleGrantViewSet, basename='jenkins_role_grant')

urlpatterns = router.urls
