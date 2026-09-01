from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.cmdb.models import (
    BusinessLine,
    Environment,
    Idc,
    Server,
    SERVER_STATUS_CHOICES,
)
from dvadmin.utils.json_response import DetailResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class ServerSerializer(CustomModelSerializer):
    """列表/编辑-序列化器"""
    idc_name = serializers.CharField(source='idc.name', read_only=True, default=None)
    environment_name = serializers.CharField(source='environment.name', read_only=True, default=None)
    business_line_name = serializers.CharField(source='business_line.name', read_only=True, default=None)
    status_label = serializers.SerializerMethodField()

    def get_status_label(self, obj):
        return dict(SERVER_STATUS_CHOICES).get(obj.status, obj.status)

    class Meta:
        model = Server
        fields = '__all__'
        read_only_fields = ["id"]


class ImportServerSerializer(CustomModelSerializer):
    """Excel导入-序列化器：外键按名称匹配（slug_field='name'）"""
    idc = serializers.SlugRelatedField(slug_field='name', queryset=Idc.objects.all(), required=False, allow_null=True)
    environment = serializers.SlugRelatedField(slug_field='name', queryset=Environment.objects.all(), required=False, allow_null=True)
    business_line = serializers.SlugRelatedField(slug_field='name', queryset=BusinessLine.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Server
        fields = '__all__'
        read_only_fields = ["id"]


class ServerViewSet(CustomModelViewSet):
    """服务器管理"""
    queryset = Server.objects.all()
    serializer_class = ServerSerializer

    # Excel 导入
    import_serializer_class = ImportServerSerializer
    import_field_dict = {
        'hostname': '主机名',
        'ip': '主管理IP',
        'extra_ips': '其他内网IP',
        'idc': {'title': '机房', 'choices': {'queryset': Idc.objects.filter(status=1), 'values_name': 'name'}},
        'environment': {'title': '环境', 'choices': {'queryset': Environment.objects.filter(status=1), 'values_name': 'name'}},
        'business_line': {'title': '业务线', 'choices': {'queryset': BusinessLine.objects.filter(status=1), 'values_name': 'name'}},
        'deploy_content': '部署内容',
        'os': '操作系统',
        'cpu': 'CPU核数',
        'memory': '内存GB',
        'disk': '磁盘',
        'ssh_port': 'SSH端口',
        'status': {
            'title': '状态',
            'choices': {'data': {'online': '在线', 'offline': '离线', 'maintenance': '维护中', 'offline_shelf': '已下架'}},
        },
        'tags': '标签',
        'description': '描述',
    }

    search_fields = ['hostname', 'ip', 'extra_ips', 'deploy_content', 'tags']
    filter_fields = ['status', 'idc', 'environment', 'business_line']

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回全部在线服务器（供堡垒机凭据/会话关联选择）"""
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(status='online').order_by('hostname').values('hostname', 'id')
        return DetailResponse(data=data, msg="获取成功")

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='dispatch_options')
    def dispatch_options(self, request, *args, **kwargs):
        """下拉选项（命令下发专用）：返回 hostname/ip/ssh_port/id"""
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(status='online').order_by('hostname').values('id', 'hostname', 'ip', 'ssh_port')
        return DetailResponse(data=data, msg="获取成功")