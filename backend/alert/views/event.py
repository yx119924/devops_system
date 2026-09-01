# -*- coding: utf-8 -*-
"""
告警事件 ViewSet：历史告警查询（只读）
"""
from rest_framework import serializers

from dvadmin.alert.models import AlertEvent, ALERT_STATUS_CHOICES, SEVERITY_CHOICES
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class AlertEventSerializer(CustomModelSerializer):
    severity_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    def get_severity_label(self, obj):
        return dict(SEVERITY_CHOICES).get(obj.severity, obj.severity)

    def get_status_label(self, obj):
        return dict(ALERT_STATUS_CHOICES).get(obj.status, obj.status)

    class Meta:
        model = AlertEvent
        fields = '__all__'
        read_only_fields = ["id"]


class AlertEventViewSet(CustomModelViewSet):
    """历史告警查询（只读，数据由 Alertmanager webhook 写入）"""
    queryset = AlertEvent.objects.all()
    serializer_class = AlertEventSerializer
    search_fields = ['alertname', 'instance', 'summary', 'description']
    filter_fields = ['status', 'severity', 'alertname', 'instance']

    # 历史告警只读，禁止增删改
    def create(self, request, *args, **kwargs):
        return self._not_allowed()

    def update(self, request, *args, **kwargs):
        return self._not_allowed()

    def destroy(self, request, *args, **kwargs):
        return self._not_allowed()

    def _not_allowed(self):
        from dvadmin.utils.json_response import ErrorResponse
        return ErrorResponse(msg="历史告警由系统采集，不支持手动增删改")
