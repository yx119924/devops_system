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

from dvadmin.monitor.models import PrometheusSource, SOURCE_TYPE_CHOICES
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class PrometheusSourceSerializer(CustomModelSerializer):
    status_label = serializers.SerializerMethodField()
    source_type_label = serializers.SerializerMethodField()

    def get_status_label(self, obj):
        return dict(PrometheusSource._meta.get_field('status').choices).get(obj.status, obj.status)

    def get_source_type_label(self, obj):
        return dict(SOURCE_TYPE_CHOICES).get(obj.source_type, obj.source_type)

    class Meta:
        model = PrometheusSource
        fields = '__all__'
        read_only_fields = ["id"]


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
        try:
            if method == 'GET':
                resp = requests.get(url, params=data, timeout=timeout)
            else:
                resp = requests.post(url, data=data, timeout=timeout)
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
        """连通性测试：/-/healthy 返回纯文本（非 JSON），不走 _proxy"""
        source = self._get_source()
        base = (source.url or '').strip().rstrip('/')
        if not base:
            return ErrorResponse(msg="数据源地址为空")
        try:
            resp = requests.get(f"{base}/-/healthy", timeout=3)
        except requests.exceptions.Timeout:
            return ErrorResponse(msg=f"Prometheus 请求超时（3s）：{base}")
        except requests.exceptions.ConnectionError:
            return ErrorResponse(msg=f"无法连接 Prometheus：{base}")
        except requests.exceptions.RequestException as e:
            return ErrorResponse(msg=f"Prometheus 请求异常：{e}")
        if resp.status_code == 200 and 'Healthy' in resp.text:
            return DetailResponse(data={'status': 'ok', 'url': source.url}, msg="连接正常")
        return ErrorResponse(msg=f"Prometheus 不健康：HTTP {resp.status_code}，{resp.text[:100]}")

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
