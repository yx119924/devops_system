from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.cmdb.models import BusinessLine
from dvadmin.utils.json_response import DetailResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class BusinessLineSerializer(CustomModelSerializer):
    class Meta:
        model = BusinessLine
        fields = '__all__'
        read_only_fields = ["id"]


class BusinessLineViewSet(CustomModelViewSet):
    """业务线管理"""
    queryset = BusinessLine.objects.all()
    serializer_class = BusinessLineSerializer
    search_fields = ['name', 'code', 'owner']
    filter_fields = ['status']

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回全部启用业务线"""
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(status=1).order_by('sort').values('name', 'id')
        return DetailResponse(data=data, msg="获取成功")
