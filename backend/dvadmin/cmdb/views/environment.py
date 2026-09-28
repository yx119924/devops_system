from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.cmdb.models import Environment
from dvadmin.utils.json_response import DetailResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class EnvironmentSerializer(CustomModelSerializer):
    class Meta:
        model = Environment
        fields = '__all__'
        read_only_fields = ["id"]


class EnvironmentViewSet(CustomModelViewSet):
    """环境管理"""
    queryset = Environment.objects.all()
    serializer_class = EnvironmentSerializer
    search_fields = ['name', 'code']
    filter_fields = ['status']

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回全部启用环境"""
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(status=1).order_by('sort').values('name', 'id')
        return DetailResponse(data=data, msg="获取成功")
