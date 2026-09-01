# -*- coding: utf-8 -*-
"""告警模板管理：Jinja2 模板 CRUD + 预览"""
from rest_framework import serializers
from rest_framework.decorators import action

from jinja2 import Environment
from jinja2 import meta as jinja_meta
from jinja2.exceptions import TemplateError

from dvadmin.alert.models import AlertTemplate
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


def _extract_variables(body: str):
    """从 Jinja2 body 中提取所有未声明的变量名（按字母排序）。模板语法错误时返回 []"""
    if not body:
        return []
    try:
        env = Environment()
        ast = env.parse(body)
        return sorted(jinja_meta.find_undeclared_variables(ast))
    except Exception:
        return []


class AlertTemplateSerializer(CustomModelSerializer):
    class Meta:
        model = AlertTemplate
        fields = "__all__"
        read_only_fields = ["id"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # 列表展示时实时同步 variables（避免脏数据 + 让用户看到提取结果）
        ret["variables"] = _extract_variables(instance.body)
        return ret


class AlertTemplateViewSet(CustomModelViewSet):
    """告警模板：Jinja2 模板，由告警规则引用（AlertRule.template）渲染通知内容"""
    queryset = AlertTemplate.objects.all()
    serializer_class = AlertTemplateSerializer
    search_fields = ["name", "description"]
    filter_fields = ["enabled", "is_default"]

    def filter_queryset(self, queryset):
        """前端按列搜索「模板名称/描述」传的是 name=/description=，需手动做 icontains 模糊匹配。
        其余字段（enabled/is_default）走 django-filter 精确匹配，search= 走 SearchFilter。
        """
        q = self.request.query_params
        name = q.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        description = q.get("description")
        if description:
            queryset = queryset.filter(description__icontains=description)
        return super().filter_queryset(queryset)

    @action(methods=["GET"], detail=False, url_path="all")
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回全部启用模板（供告警规则「通知模板」下拉使用）"""
        data = self.filter_queryset(self.get_queryset()).filter(enabled=True) \
            .order_by("-is_default", "-create_datetime").values("id", "name", "is_default")
        return DetailResponse(data=data, msg="获取成功")

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.variables = _extract_variables(instance.body)
        instance.save(update_fields=["variables"])

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.variables = _extract_variables(instance.body)
        instance.save(update_fields=["variables"])

    @action(methods=["POST"], detail=False, url_path="preview")
    def preview(self, request):
        """用示例 alert 数据渲染模板，方便前端编辑时即时预览效果。
        入参：{"body": "<jinja2 文本>"}；返回：{"rendered": "...", "sample": {...}}
        """
        body = (request.data or {}).get("body", "")
        if not body:
            return ErrorResponse(msg="缺少 body 参数")
        sample = {
            "alertname": "HighCPUUsage",
            "severity": "warning",
            "status": "firing",
            "instance": "server-01:9100",
            "summary": "CPU 使用率超过 80%",
            "description": "5 分钟内 CPU 平均使用率 92%，请检查负载是否正常。",
            "startsAt": "2026-08-31T10:00:00Z",
            "endsAt": "",
            "value": "92",
            "labels": {
                "alertname": "HighCPUUsage",
                "severity": "warning",
                "instance": "server-01:9100",
            },
        }
        try:
            rendered = Environment().from_string(body).render(**sample)
            return DetailResponse(data={"rendered": rendered, "sample": sample}, msg="渲染成功")
        except TemplateError as e:
            return ErrorResponse(msg=f"模板语法错误：{e}")
        except Exception as e:
            return ErrorResponse(msg=f"渲染失败：{e}")