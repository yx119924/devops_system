from rest_framework import routers

from dvadmin.jenkins.views.jenkins import JenkinsServerViewSet

router = routers.SimpleRouter()
router.register(r'server', JenkinsServerViewSet, basename='jenkins_server')

urlpatterns = router.urls
