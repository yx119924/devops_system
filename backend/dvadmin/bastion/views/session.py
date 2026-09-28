from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from django.conf import settings
from django.http import FileResponse
from pathlib import Path

from dvadmin.bastion.access import is_asset_admin
from dvadmin.bastion.models import SessionRecord
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class SessionRecordSerializer(CustomModelSerializer):
    server_name = serializers.CharField(source='server.hostname', read_only=True, default=None)
    credential_name = serializers.CharField(source='credential.name', read_only=True, default=None)
    operator_name = serializers.CharField(source='creator.name', read_only=True, default=None)
    operator_username = serializers.CharField(source='creator.username', read_only=True, default=None)
    status_label = serializers.SerializerMethodField()

    def get_status_label(self, obj):
        return dict(SessionRecord._meta.get_field('status').choices).get(obj.status, obj.status)

    class Meta:
        model = SessionRecord
        fields = '__all__'
        read_only_fields = ["id"]


class SessionRecordViewSet(CustomModelViewSet):
    """会话记录

    可见范围：超级管理员 / 资产运营者（运维、管理员）看全部；其余用户只看**自己发起**的会话，
    避免别人的登录过程、录像、命令流互相可见。录像下载接口 ``recording`` 走 ``get_object()``，
    因此同样受本条裁剪保护。
    """
    queryset = SessionRecord.objects.all()
    serializer_class = SessionRecordSerializer
    search_fields = ['username', 'ip', 'creator__username', 'creator__name']
    filter_fields = ['status', 'server', 'creator']
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_asset_admin(user):
            return qs
        return qs.filter(creator=user)

    @action(detail=True, methods=['get'])
    def recording(self, request, pk=None):
        session = self.get_object()
        path = Path(settings.MEDIA_ROOT) / 'sessions' / f'{session.pk}.cast'
        if not path.is_file():
            raise NotFound('录像不存在')
        response = FileResponse(path.open('rb'), content_type='application/octet-stream')
        response['Cache-Control'] = 'no-store'
        return response
