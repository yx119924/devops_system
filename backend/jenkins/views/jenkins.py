# -*- coding: utf-8 -*-
"""
Jenkins 服务器管理 + HTTP API 代理
代理端点（相对 Jenkins 根地址）：
  test       -> GET  {url}/api/json                          连通性测试
  jobs       -> GET  {url}/api/json?tree=jobs[...]           获取所有 Job
  build      -> POST {url}/job/{job}/build                   触发构建（自动带 crumb，支持参数）
  job_status -> GET  {url}/job/{job}/lastBuild/api/json      最近构建状态
  console    -> GET  {url}/job/{job}/{build}/logText/...     构建日志（增量）
"""
from urllib.parse import quote

import requests
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.jenkins.models import JenkinsServer
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class JenkinsServerSerializer(CustomModelSerializer):
    """Jenkins 服务器-序列化器：token 仅写入（不返回明文），读取返回是否已配置"""
    token = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True,
                                  help_text="API Token/密码明文（仅写入）")
    has_token = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    def get_has_token(self, obj):
        return bool(obj.token)

    def get_status_label(self, obj):
        return dict(JenkinsServer._meta.get_field('status').choices).get(obj.status, obj.status)

    class Meta:
        model = JenkinsServer
        fields = '__all__'
        read_only_fields = ["id"]

    def create(self, validated_data):
        plain_token = validated_data.pop('token', None)
        obj = super().create(validated_data)
        if plain_token:
            obj.set_token(plain_token)
        obj.save()
        return obj

    def update(self, instance, validated_data):
        plain_token = validated_data.pop('token', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        # 仅当传入新 token 才更新（留空表示不修改）
        if plain_token:
            instance.set_token(plain_token)
        instance.save()
        return instance


class JenkinsServerViewSet(CustomModelViewSet):
    """Jenkins 服务器管理 + 发布操作代理"""
    queryset = JenkinsServer.objects.all()
    serializer_class = JenkinsServerSerializer
    search_fields = ['name', 'url']
    filter_fields = ['status']

    # ------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------
    def _get_source(self):
        return self.get_object()

    def _auth(self, source):
        """返回 requests 的 auth 参数（Basic Auth）或 None（匿名）"""
        username = (source.username or '').strip()
        token = source.get_token()
        if username or token:
            return (username, token)
        return None

    def _request(self, source, path, method='GET', params=None, data=None, timeout=60):
        """代理 Jenkins HTTP 请求，返回 (status_code, body_text, resp)

        body_text 对 JSON 已解码、对纯文本原样返回（日志接口是纯文本）。
        """
        base = (source.url or '').strip().rstrip('/')
        if not base:
            raise RuntimeError("Jenkins 地址为空")
        url = f"{base}{path}"
        try:
            if method == 'GET':
                resp = requests.get(url, auth=self._auth(source), params=params, timeout=timeout)
            else:
                resp = requests.request(method, url, auth=self._auth(source), data=data, timeout=timeout)
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Jenkins 请求超时（>{timeout}s）")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"无法连接 Jenkins：{base}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Jenkins 请求异常：{e}")

        # JSON 优先，否则返回纯文本（日志接口）
        ctype = resp.headers.get('Content-Type', '')
        if 'json' in ctype:
            try:
                return resp.status_code, resp.json(), resp
            except ValueError:
                pass
        return resp.status_code, resp.text, resp

    def _get_crumb(self, source):
        """获取 CSRF crumb，返回 (field, value)；Jenkins 关闭 CSRF 时返回 None"""
        try:
            code, body, _ = self._request(source, '/crumbIssuer/api/json', method='GET', timeout=15)
        except Exception:
            return None
        if code == 200 and isinstance(body, dict):
            return body.get('crumbRequestField', 'Jenkins-Crumb'), body.get('crumb', '')
        return None

    # ------------------------------------------------------------
    # 连通性测试
    # ------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='test')
    def test(self, request, pk=None):
        source = self._get_source()
        try:
            code, body, _ = self._request(source, '/api/json', method='GET', timeout=15)
        except Exception as e:
            return ErrorResponse(msg=str(e))
        if code == 200:
            return DetailResponse(data={'status': 'ok', 'url': source.url}, msg="连接正常")
        return ErrorResponse(msg=f"Jenkins 返回 HTTP {code}：{str(body)[:200]}")

    # ------------------------------------------------------------
    # 获取所有 Job
    # ------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='jobs')
    def jobs(self, request, pk=None):
        source = self._get_source()
        tree = 'jobs[name,url,color,description]'
        try:
            code, body, _ = self._request(source, '/api/json', method='GET',
                                          params={'tree': tree}, timeout=30)
        except Exception as e:
            return ErrorResponse(msg=str(e))
        if code != 200:
            return ErrorResponse(msg=f"Jenkins 返回 HTTP {code}：{str(body)[:300]}")
        jobs = (body or {}).get('jobs', []) if isinstance(body, dict) else []
        return DetailResponse(data={'jobs': jobs}, msg="获取成功")

    # ------------------------------------------------------------
    # 触发构建
    # ------------------------------------------------------------
    @action(methods=['POST'], detail=True, url_path='build')
    def build(self, request, pk=None):
        """触发构建，body: {job, parameters?: {k:v}}"""
        source = self._get_source()
        job = (request.data or {}).get('job', '')
        parameters = (request.data or {}).get('parameters') or {}
        if not job:
            return ErrorResponse(msg="缺少 job 参数")
        job_path = quote(str(job), safe='')

        # 1. 尝试拿 crumb（Jenkins 开启 CSRF 时必需）
        crumb = self._get_crumb(source)
        headers = {}
        if crumb:
            headers[crumb[0]] = crumb[1]

        # 2. 触发构建（有参数走 buildWithParameters）
        try:
            if parameters:
                code, body, resp = self._request(source, f'/job/{job_path}/buildWithParameters',
                                                 method='POST', data=parameters, timeout=60)
            else:
                code, body, resp = self._request(source, f'/job/{job_path}/build',
                                                 method='POST', data=None, timeout=60)
        except Exception as e:
            return ErrorResponse(msg=str(e))

        if code in (200, 201):
            queue_url = resp.headers.get('Location', '')
            return DetailResponse(data={'status': 'ok', 'job': job, 'queue_url': queue_url},
                                  msg=f"已触发构建：{job}")
        # 403 且带了 crumb，可能是 crumb 失效，降级重试一次（不带 crumb）
        if code == 403 and crumb:
            try:
                if parameters:
                    code, body, resp = self._request(source, f'/job/{job_path}/buildWithParameters',
                                                     method='POST', data=parameters, timeout=60)
                else:
                    code, body, resp = self._request(source, f'/job/{job_path}/build',
                                                     method='POST', data=None, timeout=60)
            except Exception as e:
                return ErrorResponse(msg=str(e))
            if code in (200, 201):
                return DetailResponse(data={'status': 'ok', 'job': job}, msg=f"已触发构建：{job}")
        return ErrorResponse(msg=f"触发构建失败 HTTP {code}：{str(body)[:300]}")

    # ------------------------------------------------------------
    # 最近构建状态
    # ------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='job_status')
    def job_status(self, request, pk=None):
        source = self._get_source()
        job = request.query_params.get('job', '')
        if not job:
            return ErrorResponse(msg="缺少 job 参数")
        job_path = quote(str(job), safe='')
        try:
            code, body, _ = self._request(source, f'/job/{job_path}/lastBuild/api/json',
                                          method='GET', timeout=30)
        except Exception as e:
            return ErrorResponse(msg=str(e))
        if code == 200:
            return DetailResponse(data=body, msg="获取成功")
        if code == 404:
            return DetailResponse(data={'building': False, 'result': 'NOT_BUILT'},
                                  msg="该 Job 还没有构建记录")
        return ErrorResponse(msg=f"获取构建状态失败 HTTP {code}：{str(body)[:300]}")

    # ------------------------------------------------------------
    # 构建日志（增量）
    # ------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='console')
    def console(self, request, pk=None):
        """构建日志，参数: {job, build?, start?}；build 为空取 lastBuild"""
        source = self._get_source()
        job = request.query_params.get('job', '')
        build = request.query_params.get('build', 'lastBuild')
        start = request.query_params.get('start', '0')
        if not job:
            return ErrorResponse(msg="缺少 job 参数")
        job_path = quote(str(job), safe='')
        try:
            code, body, resp = self._request(
                source, f'/job/{job_path}/{build}/logText/progressiveText',
                method='GET', params={'start': start}, timeout=60)
        except Exception as e:
            return ErrorResponse(msg=str(e))
        if code != 200:
            return ErrorResponse(msg=f"获取日志失败 HTTP {code}：{str(body)[:300]}")
        more = (resp.headers.get('X-More-Data', 'false') or '').lower() == 'true'
        size = resp.headers.get('X-Text-Size', '0')
        return DetailResponse(data={'text': body or '', 'more': more, 'size': size}, msg="获取成功")

    # ------------------------------------------------------------
    # 下拉选项
    # ------------------------------------------------------------
    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回启用的 Jenkins 服务器"""
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(status=1).order_by('sort').values('id', 'name', 'url')
        return DetailResponse(data=list(data), msg="获取成功")
