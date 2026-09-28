from rest_framework import serializers

from dvadmin.bastion.access import is_asset_admin, restrict_command_log
from dvadmin.bastion.models import CommandLog
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class CommandLogSerializer(CustomModelSerializer):
    dispatch_name = serializers.CharField(source='dispatch.name', read_only=True, default=None)
    source_name = serializers.SerializerMethodField()

    def get_source_name(self, obj):
        return dict(CommandLog._meta.get_field('source').choices).get(obj.source, obj.source)

    class Meta:
        model = CommandLog
        fields = '__all__'
        read_only_fields = ["id"]


class CommandLogViewSet(CustomModelViewSet):
    """命令审计

    可见范围（与「会话记录 / 命令下发」刻意不同，因为本页是**审计**视角）：

    - 超级管理员 / 资产运营者（运维、管理员）：全部
    - 其余用户：**被授权服务器上发生过的全部命令**（按目标 IP 裁剪），不只是自己发的。
      这样"我负责的机器上跑了什么高危命令"是能看到的，符合审计需求；
      而别人的机器上跑什么，看不到。
    """
    queryset = CommandLog.objects.all()
    serializer_class = CommandLogSerializer
    search_fields = ['command', 'ip']
    filter_fields = ['is_dangerous', 'session', 'source', 'dispatch', 'ip']
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_asset_admin(user):
            return qs
        return restrict_command_log(qs, user)
