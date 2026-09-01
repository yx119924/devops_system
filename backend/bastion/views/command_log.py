from rest_framework import serializers

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
    """命令审计"""
    queryset = CommandLog.objects.all()
    serializer_class = CommandLogSerializer
    search_fields = ['command', 'ip']
    filter_fields = ['is_dangerous', 'session', 'source', 'dispatch', 'ip']
