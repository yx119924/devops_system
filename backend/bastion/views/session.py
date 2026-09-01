from rest_framework import serializers

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
    """会话记录"""
    queryset = SessionRecord.objects.all()
    serializer_class = SessionRecordSerializer
    search_fields = ['username', 'ip', 'creator__username', 'creator__name']
    filter_fields = ['status', 'server', 'creator']
