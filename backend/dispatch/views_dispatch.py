# -*- coding: utf-8 -*-
"""
命令下发 ViewSet：
- list/retrieve/create/update/destroy 由 CustomModelViewSet 提供
- execute action: 触发并发执行（同步阻塞，返回最终结果）
- items 子资源：detail 路由下读 items
"""
from rest_framework import serializers
from rest_framework.decorators import action

from dvadmin.bastion.executor import execute_dispatch
from dvadmin.bastion.models import CommandDispatch, CommandDispatchItem
from dvadmin.utils.json_response import SuccessResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class CommandDispatchItemSerializer(CustomModelSerializer):
    server_name = serializers.CharField(source='server.hostname', read_only=True, default=None)

    class Meta:
        model = CommandDispatchItem
        fields = '__all__'
        read_only_fields = ['id']


class CommandDispatchSerializer(CustomModelSerializer):
    items = CommandDispatchItemSerializer(many=True, read_only=True)
    credential_name = serializers.CharField(source='credential.name', read_only=True, default=None)
    target_count = serializers.SerializerMethodField()

    def get_target_count(self, obj):
        return len(obj.targets or [])

    class Meta:
        model = CommandDispatch
        fields = '__all__'
        read_only_fields = ['id', 'status', 'total', 'success_count', 'failed_count',
                            'started_at', 'finished_at', 'last_error']


class CommandDispatchViewSet(CustomModelViewSet):
    """命令下发"""
    queryset = CommandDispatch.objects.all().order_by('-create_datetime')
    serializer_class = CommandDispatchSerializer

    def perform_create(self, serializer):
        dispatch = serializer.save()
        items = []
        for t in (dispatch.targets or []):
            items.append(CommandDispatchItem(
                dispatch=dispatch,
                server_id=t.get('server_id') or None,
                label=t.get('label') or t.get('ip') or '',
                ip=t.get('ip') or '',
                ssh_port=int(t.get('ssh_port') or 22),
                status='pending',
            ))
        CommandDispatchItem.objects.bulk_create(items)

    @action(detail=True, methods=['post'], url_path='execute')
    def execute(self, request, pk=None):
        """触发执行（同步等所有目标返回）。retry=True 只重跑失败项"""
        max_workers = request.data.get('max_workers') or None
        retry = bool(request.data.get('retry'))
        dispatch = execute_dispatch(pk, max_workers=max_workers, retry_failed=retry)
        ser = self.get_serializer(dispatch)
        return SuccessResponse(data=ser.data, msg='执行完成')

    @action(detail=True, methods=['get'], url_path='items')
    def items(self, request, pk=None):
        """查看每台目标的执行结果"""
        qs = CommandDispatchItem.objects.filter(dispatch_id=pk).order_by('id')
        return SuccessResponse(data=CommandDispatchItemSerializer(qs, many=True).data)