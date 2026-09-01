from rest_framework import routers

from dvadmin.cmdb.views.business_line import BusinessLineViewSet
from dvadmin.cmdb.views.environment import EnvironmentViewSet
from dvadmin.cmdb.views.idc import IdcViewSet
from dvadmin.cmdb.views.server import ServerViewSet

router = routers.SimpleRouter()
router.register(r'idc', IdcViewSet, basename='cmdb_idc')
router.register(r'environment', EnvironmentViewSet, basename='cmdb_environment')
router.register(r'business_line', BusinessLineViewSet, basename='cmdb_business_line')
router.register(r'server', ServerViewSet, basename='cmdb_server')

urlpatterns = router.urls
