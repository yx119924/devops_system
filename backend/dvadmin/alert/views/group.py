from rest_framework import serializers
from rest_framework.decorators import action

from dvadmin.alert.models import AlertGroup, NotifyChannel
from dvadmin.utils.json_response import DetailResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class AlertGroupSerializer(CustomModelSerializer):
    channels = serializers.PrimaryKeyRelatedField(
        many=True, queryset=NotifyChannel.objects.all(), required=False,
        help_text="关联的渠道 ID 列表"
    )
    channel_list = serializers.SerializerMethodField()

    def get_channel_list(self, obj):
        return [{"id": c.id, "name": c.name, "type": c.type} for c in obj.channels.all()]

    class Meta:
        model = AlertGroup
        fields = '__all__'
        read_only_fields = ["id"]


class AlertGroupViewSet(CustomModelViewSet):
    """告警群组（多个渠道的聚合，规则可关联群组实现按群组分发）"""
    queryset = AlertGroup.objects.all()
    serializer_class = AlertGroupSerializer
    search_fields = ['name', 'description']
    filter_fields = ['enabled']

    @action(methods=['GET'], detail=False, url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回全部启用群组"""
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(enabled=True).order_by('-create_datetime').values('id', 'name')
        return DetailResponse(data=data, msg="获取成功")