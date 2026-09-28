# -*- coding: utf-8 -*-
"""
命令下发 ViewSet：
- list/retrieve/create/update/destroy 由 CustomModelViewSet 提供
- execute action: 触发并发执行（同步阻塞，返回最终结果）
- items 子资源：detail 路由下读 items
"""
from rest_framework import serializers
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.exceptions import ValidationError
from dvadmin.bastion.access import is_asset_admin, require_access
from dvadmin.cmdb.models import Server

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

    def validate(self, attrs):
        user = self.context['request'].user
        credential = attrs.get('credential')
        targets = attrs.get('targets')
        if not credential or not isinstance(targets, list) or not 1 <= len(targets) <= 100:
            raise ValidationError('必须选择凭据及 1 到 100 个 CMDB 目标')
        normalized = []
        seen = set()
        for target in targets:
            if not isinstance(target, dict):
                raise ValidationError('目标格式错误')
            try:
                server = Server.objects.get(pk=int(target.get('server_id', 0)))
            except (Server.DoesNotExist, TypeError, ValueError):
                raise ValidationError('目标必须来自 CMDB；请先登记服务器')
            require_access(user, server, credential, 'dispatch')
            if server.pk in seen:
                continue
            seen.add(server.pk)
            normalized.append({'server_id': server.pk, 'ip': server.ip,
                               'ssh_port': server.ssh_port or 22, 'label': server.hostname})
        attrs['targets'] = normalized
        if not 1 <= attrs.get('timeout', 30) <= 300 or not 1 <= attrs.get('max_workers', 10) <= 20:
            raise ValidationError('超时应为 1–300 秒，并发应为 1–20')
        if not attrs.get('command', '').strip() or len(attrs['command']) > 16384:
            raise ValidationError('命令不能为空且不能超过 16384 字符')
        return super().validate(attrs)

    def get_target_count(self, obj):
        return len(obj.targets or [])

    class Meta:
        model = CommandDispatch
        fields = '__all__'
        read_only_fields = ['id', 'status', 'total', 'success_count', 'failed_count',
                            'started_at', 'finished_at', 'last_error']


class CommandDispatchViewSet(CustomModelViewSet):
    """命令下发

    权限三层：
    1. 接口层：``CustomPermission`` 按 ``dispatch:Create`` / ``:Execute`` 等按钮控制
    2. 目标层：``CommandDispatchSerializer.validate`` 对**每个目标服务器**调用
       ``require_access(..., 'dispatch')``——这是资产授权的真正关卡，
       前端下拉被绕过（手工构造 targets）也拦得住
    3. 可见层：本 ``get_queryset``
    """
    queryset = CommandDispatch.objects.all().order_by('-create_datetime')
    serializer_class = CommandDispatchSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # 资产运营者（运维/管理员）看全部任务，便于排障与审计
        return qs if is_asset_admin(user) else qs.filter(creator=user)

    @transaction.atomic
    def perform_create(self, serializer):
        dispatch = serializer.save(creator=self.request.user)
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
        obj = self.get_object()
        retry = request.data.get('retry', False)
        if not isinstance(retry, bool):
            raise ValidationError('retry 必须是布尔值')
        dispatch = execute_dispatch(obj.pk, retry_failed=retry, actor=request.user)
        ser = self.get_serializer(dispatch)
        return SuccessResponse(data=ser.data, msg='执行完成')

    @action(detail=True, methods=['get'], url_path='items')
    def items(self, request, pk=None):
        """查看每台目标的执行结果"""
        obj = self.get_object()
        qs = obj.items.order_by('id')
        return SuccessResponse(data=CommandDispatchItemSerializer(qs, many=True).data)

    @transaction.atomic
    def perform_destroy(self, instance):
        locked = CommandDispatch.objects.select_for_update().get(pk=instance.pk)
        if locked.status == 'running':
            raise ValidationError('执行中的任务不能删除')
        locked.delete()
