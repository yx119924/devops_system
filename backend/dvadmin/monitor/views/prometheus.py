# -*- coding: utf-8 -*-
"""
Prometheus 数据源管理 + HTTP API 代理
代理端点：
  query       -> POST {url}/api/v1/query        即时查询
  query_range -> POST {url}/api/v1/query_range  范围查询
  alerts      -> GET  {url}/api/v1/alerts       告警
  targets     -> GET  {url}/api/v1/targets     采集目标状态
  test        -> GET  {url}/-/healthy           连通性测试
"""
import requests
from rest_framework import serializers
from rest_framework.decorators import action

from dvadmin.bastion.crypto import encrypt
from dvadmin.monitor.models import PrometheusSource, SOURCE_TYPE_CHOICES
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class PrometheusSourceSerializer(CustomModelSerializer):
    status_label = serializers.SerializerMethodField()
    source_type_label = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()

    def get_has_password(self, obj):
        return bool(obj.password)

    def validate(self, attrs):
        password = attrs.pop('password', None)
        if password:
            attrs['password'] = encrypt(password)
        return super().validate(attrs)

    def get_status_label(self, obj):
        return dict(PrometheusSource._meta.get_field('status').choices).get(obj.status, obj.status)

    def get_source_type_label(self, obj):
        return dict(SOURCE_TYPE_CHOICES).get(obj.source_type, obj.source_type)

    class Meta:
        model = PrometheusSource
        fields = '__all__'
        read_only_fields = ["id"]
        # password 密文不进前端展示，前端用 has_password 标记是否已配置
        extra_kwargs = {"password": {"write_only": True}}


class PrometheusSourceViewSet(CustomModelViewSet):
    """监控数据源（Prometheus / Alertmanager）"""
    queryset = PrometheusSource.objects.all()
    serializer_class = PrometheusSourceSerializer
    search_fields = ['name', 'url']
    filter_fields = ['status', 'source_type']

    def _get_source(self):
        return self.get_object()

    def _proxy(self, source, path, method='GET', data=None, timeout=15):
        """代理 Prometheus HTTP API，返回解析后的 JSON dict"""
        base = (source.url or '').strip().rstrip('/')
        if not base:
            raise ValueError("数据源地址为空")
        url = f"{base}{path}"
        auth, headers = source.get_auth(), source.get_headers()
        try:
            if method == 'GET':
                resp = requests.get(url, params=data, timeout=timeout, auth=auth, headers=headers)
            else:
                resp = requests.post(url, data=data, timeout=timeout, auth=auth, headers=headers)
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Prometheus 请求超时（>{timeout}s）")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"无法连接 Prometheus：{base}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Prometheus 请求异常：{e}")

        if resp.status_code != 200:
            raise RuntimeError(f"Prometheus 返回 HTTP {resp.status_code}：{resp.text[:300]}")
        return resp.json()

    @action(methods=['POST'], detail=True, url_path='query')
    def query(self, request, pk=None):
        """即时查询 PromQL，body: {query, time?}"""
        source = self._get_source()
        query = (request.data or {}).get('query', '')
        if not query:
            return ErrorResponse(msg="缺少 query 参数")
        data = {'query': query}
        if (request.data or {}).get('time'):
            data['time'] = request.data['time']
        try:
            result = self._proxy(source, '/api/v1/query', method='POST', data=data)
            return DetailResponse(data=result, msg="查询成功")
        except Exception as e:
            return ErrorResponse(msg=str(e))

    @action(methods=['POST'], detail=True, url_path='query_range')
    def query_range(self, request, pk=None):
        """范围查询，body: {query, start, end, step}"""
        source = self._get_source()
        body = request.data or {}
        query = body.get('query', '')
        if not query:
            return ErrorResponse(msg="缺少 query 参数")
        data = {'query': query}
        for key in ('start', 'end', 'step'):
            if body.get(key):
                data[key] = body[key]
        try:
            result = self._proxy(source, '/api/v1/query_range', method='POST', data=data)
            return DetailResponse(data=result, msg="查询成功")
        except Exception as e:
            return ErrorResponse(msg=str(e))

    @action(methods=['GET'], detail=True, url_path='alerts')
    def alerts(self, request, pk=None):
        """告警列表"""
        source = self._get_source()
        try:
            result = self._proxy(source, '/api/v1/alerts', method='GET')
            return DetailResponse(data=result, msg="获取成功")
        except Exception as e:
            return ErrorResponse(msg=str(e))

    @action(methods=['GET'], detail=True, url_path='targets')
    def targets(self, request, pk=None):
        """采集目标状态"""
        source = self._get_source()
        try:
            result = self._proxy(source, '/api/v1/targets', method='GET')
            return DetailResponse(data=result, msg="获取成功")
        except Exception as e:
            return ErrorResponse(msg=str(e))

    @action(methods=['GET'], detail=True, url_path='test')
    def test(self, request, pk=None):
        """连通性测试：/-/healthy 返回纯文本（非 JSON），不走 _proxy。

        Prometheus 返回 "Prometheus Server is Healthy."，Alertmanager 返回 "OK"，
        统一按 HTTP 200 判定健康；报错文案按数据源类型区分。
        """
        source = self._get_source()
        base = (source.url or '').strip().rstrip('/')
        if not base:
            return ErrorResponse(msg="数据源地址为空")
        stype = getattr(source, 'source_type', '') or ''
        label = {'alertmanager': 'Alertmanager', 'grafana': 'Grafana'}.get(stype, 'Prometheus')
        health_path = '/api/health' if stype == 'grafana' else '/-/healthy'
        try:
            resp = requests.get(f"{base}{health_path}", timeout=5,
                                auth=source.get_auth(), headers=source.get_headers())
        except requests.exceptions.Timeout:
            return ErrorResponse(msg=f"{label} 请求超时（5s）：{base}")
        except requests.exceptions.ConnectionError:
            return ErrorResponse(msg=f"无法连接 {label}：{base}")
        except requests.exceptions.RequestException as e:
            return ErrorResponse(msg=f"{label} 请求异常：{e}")
        if resp.status_code == 200:
            data = {'status': 'ok', 'url': source.url}
            # Grafana 的 /api/health 带版本号，回显给前端便于排查
            if stype == 'grafana':
                try:
                    data['version'] = resp.json().get('version', '')
                except Exception:
                    data['version'] = ''
            return DetailResponse(data=data, msg="连接正常")
        if resp.status_code in (401, 403):
            return ErrorResponse(msg=f"{label} 认证失败或账号无权限，请检查用户名与密码/Token")
        return ErrorResponse(msg=f"{label} 不健康：HTTP {resp.status_code}，{resp.text[:100]}")

    @action(methods=['GET'], detail=False, url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回启用数据源，默认只返回 Prometheus（查询页专用）。

        显式传 ?source_type=alertmanager 可获取 Alertmanager 列表。
        """
        queryset = self.filter_queryset(self.get_queryset())
        if not request.query_params.get('source_type'):
            queryset = queryset.filter(source_type='prometheus')
        data = queryset.filter(status=1).order_by('sort').values('id', 'name', 'url', 'source_type')
        return DetailResponse(data=list(data), msg="获取成功")
