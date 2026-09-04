from rest_framework import serializers
from rest_framework.decorators import action

import requests

from dvadmin.alert.models import AlertRule, SEVERITY_CHOICES
from dvadmin.alert.services import (
    _require_url,
    query_active_alerts,
    sync_rules,
    sync_rules_from_prometheus,
)
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class AlertRuleSerializer(CustomModelSerializer):
    severity_label = serializers.SerializerMethodField()
    group_name = serializers.CharField(source='group.name', read_only=True, default=None)
    template_name = serializers.CharField(source='template.name', read_only=True, default=None)

    def get_severity_label(self, obj):
        return dict(SEVERITY_CHOICES).get(obj.severity, obj.severity)

    class Meta:
        model = AlertRule
        fields = '__all__'
        read_only_fields = ["id"]


class AlertRuleViewSet(CustomModelViewSet):
    """告警规则管理"""
    queryset = AlertRule.objects.select_related('group', 'template').all()
    serializer_class = AlertRuleSerializer
    search_fields = ['name', 'expr', 'summary']
    filter_fields = ['enabled', 'severity', 'template']

    def filter_queryset(self, queryset):
        """前端按列搜索「规则名称/PromQL」传 name=/expr=，需手动 icontains 模糊匹配。
        其余字段（enabled/severity）走 django-filter 精确匹配。
        """
        q = self.request.query_params
        name = q.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        expr = q.get("expr")
        if expr:
            queryset = queryset.filter(expr__icontains=expr)
        summary = q.get("summary")
        if summary:
            queryset = queryset.filter(summary__icontains=summary)
        return super().filter_queryset(queryset)

    def perform_create(self, serializer):
        serializer.save()
        sync_rules()

    def perform_update(self, serializer):
        serializer.save()
        sync_rules()

    def perform_destroy(self, instance):
        instance.delete()
        sync_rules()

    @action(methods=['POST'], detail=False, url_path='reload')
    def reload_rules(self, request):
        """重新生成规则文件并热加载 Prometheus"""
        try:
            path, ok = sync_rules()
            if ok:
                return DetailResponse(data={'file': path}, msg="规则已同步并热加载")
            return ErrorResponse(msg="规则文件已生成，但 Prometheus reload 失败")
        except Exception as e:
            return ErrorResponse(msg=f"同步规则失败：{e}")

    @action(methods=['POST'], detail=False, url_path='preview')
    def preview(self, request):
        """预览表达式的即时查询结果，验证 PromQL 是否有效、是否有值"""
        expr = (request.data or {}).get('expr', '')
        if not expr:
            return ErrorResponse(msg="缺少 expr 参数")
        try:
            url = _require_url("prometheus", "Prometheus")
            resp = requests.post(f"{url}/api/v1/query", data={'query': expr}, timeout=15)
            resp.raise_for_status()
            return DetailResponse(data=resp.json(), msg="查询成功")
        except requests.exceptions.RequestException as e:
            return ErrorResponse(msg=f"表达式查询失败：{e}")

    @action(methods=['GET'], detail=False, url_path='active_alerts')
    def active_alerts(self, request):
        """查询 Alertmanager 当前活跃告警"""
        try:
            data = query_active_alerts()
            return DetailResponse(data=data, msg="获取成功")
        except Exception as e:
            return ErrorResponse(msg=f"查询活跃告警失败：{e}")

    @action(methods=['GET'], detail=False, url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回全部启用规则"""
        data = self.filter_queryset(self.get_queryset()).filter(enabled=True) \
            .order_by('severity', '-create_datetime').values('id', 'name', 'severity')
        return DetailResponse(data=data, msg="获取成功")

    @action(methods=['POST'], detail=False, url_path='sync_from_prom')
    def sync_from_prom(self, request):
        """从 Prometheus 反向同步 alerting 规则到 XwOps 库（可逆：仅改 XwOps 库，不动 Prom 资源）。

        前置：在「监控告警 → 数据源管理」添加 source_type=prometheus 的启用数据源。
        行为：按 alertname 匹配，命中则更新表达式/持续时间/级别/摘要/描述（保留 group/template/enabled），
              未命中则新建（enabled 初始按 Prom state 决定）。
        """
        try:
            result = sync_rules_from_prometheus()
            msg = (f"Prom 共有 {result['total_in_prom']} 条告警规则："
                   f"新建 {len(result['created'])} 条，"
                   f"更新 {len(result['updated'])} 条，"
                   f"跳过 {len(result['skipped'])} 条，"
                   f"错误 {len(result['errors'])} 条")
            return DetailResponse(data=result, msg=msg)
        except Exception as e:
            return ErrorResponse(msg=f"同步失败：{e}")
