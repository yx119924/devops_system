# -*- coding: utf-8 -*-
"""
ES 日志数据源管理 + 日志检索代理
端点：
  search  -> POST {url}/{index}/_search   日志检索（时间/关键字/级别筛选，索引可覆盖）
  indices -> GET  {url}/_cat/indices      索引模式列表（滚动索引自动归并成通配模式）
  test    -> GET  {url}/                  连通性测试
  all     -> GET                          下拉选项
"""
import re

import requests
from rest_framework import serializers
from rest_framework.decorators import action

from dvadmin.log.models import ElasticsearchSource
from dvadmin.bastion.crypto import encrypt
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet

# 合法索引名/模式：ES 索引名允许字母数字下划线短横点，模式额外允许 * , +
_INDEX_RE = re.compile(r'^[A-Za-z0-9_\-.*,+]+$')

# 滚动索引后缀（-2026.09.19 / -2026-09-19 / -20260919 / -000001 / -01 / -1）
# sep 单独捕获并在拼模式时保留，保证 myapp-log-* 而不是 myapp-log*
_ROLLING_RE = re.compile(
    r'^(?P<base>.+?)(?P<sep>[-_.])'
    r'(?:'
    r'\d{4}(?:[-_.]\d{2}(?:[-_.]\d{2})?)?'
    r'|\d{6,}'
    r'|\d{2,5}'
    r'|\d'
    r')$'
)

# 不展示的系统/监控索引前缀
_SKIP_PREFIX = ('.', 'monitoring-', 'ilm-history', 'security-', 'deprecation-', 'apm-')

# 命中总数统计上限：ES 默认 10000，超了只返回 relation=gte；放宽到 10 万兼顾准确与性能
TOTAL_HIT_CAP = 100000


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


_SIZE_UNITS = {'b': 1, 'kb': 1024, 'mb': 1024 ** 2, 'gb': 1024 ** 3, 'tb': 1024 ** 4, 'pb': 1024 ** 5}


def _parse_size(value):
    """把 ES _cat 的 '1.2gb' / '128mb' 解析成字节数"""
    m = re.match(r'^([\d.]+)\s*([kmgtp]?b)$', (value or '').strip().lower())
    if not m:
        return 0
    return int(float(m.group(1)) * _SIZE_UNITS.get(m.group(2), 1))


def _dig(src, path):
    """按 'a.b.c' 从嵌套 dict 安全取值"""
    cur = src
    for key in path.split('.'):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _pick(src, keys=(), paths=()):
    """按候选字段名/路径依次取值，取到第一个非空的标量值。

    跳过 dict/list —— 例如 filebeat 的 `log` / `host` 是对象而非字符串，
    直接取会把整个对象塞进展示字段。
    """
    for k in keys:
        v = src.get(k)
        if v is not None and v != '' and not isinstance(v, (dict, list)):
            return v
    for p in paths:
        v = _dig(src, p)
        if v is not None and v != '' and not isinstance(v, (dict, list)):
            return v
    return ''


# 没有独立 level 字段的索引（filebeat 原样采集），级别藏在正文里：
#   2026-09-16 22:06:05.024 [hutool-cron-8565] [INFO ][cn.edu...] - xxx      <- [INFO ] 形式
#   2026-09-19 12:57:16.617 [redisson-netty-1-16] DEBUG org.redisson...      <- 独立词形式
_LEVEL_RE = re.compile(
    r'\[(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\s*\]'
    r'|\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b',
    re.I,
)
# 前端下拉用的级别名 -> 正文里可能出现的写法
_LEVEL_SEARCH_ALIAS = {
    'warning': ('WARN', 'WARNING'),
    'critical': ('FATAL', 'CRITICAL'),
    'error': ('ERROR', 'FATAL'),
}
_LEVEL_NORMALIZE = {'warn': 'warning', 'fatal': 'critical', 'err': 'error'}


def _extract_level(text):
    """从日志正文提取级别；只看前 200 字符，避免正文里偶然出现的单词造成误判"""
    m = _LEVEL_RE.search((text or '')[:200])
    if not m:
        return ''
    lv = (m.group(1) or m.group(2) or '').lower()
    return _LEVEL_NORMALIZE.get(lv, lv)


def _safe_index(value):
    """校验索引名/模式，防止拼接进 URL 造成注入；不合法返回空串"""
    v = (value or '').strip().strip('/')
    if not v or not _INDEX_RE.match(v):
        return ''
    return v


def _merge_index(name):
    """把滚动索引（xxx-2026.09.19）归并成通配模式（xxx-*），保留原分隔符"""
    m = _ROLLING_RE.match(name)
    if m and m.group('base'):
        return f"{m.group('base')}{m.group('sep')}*"
    return name


class ElasticsearchSourceSerializer(CustomModelSerializer):
    status_label = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()

    def get_has_password(self, obj):
        return bool(obj.password)

    def validate(self, attrs):
        password = attrs.pop('password', None)
        if password:
            attrs['password'] = encrypt(password)
        return super().validate(attrs)

    def get_status_label(self, obj):
        return dict(ElasticsearchSource._meta.get_field('status').choices).get(obj.status, obj.status)

    class Meta:
        model = ElasticsearchSource
        fields = '__all__'
        read_only_fields = ["id"]
        # password 密文不进前端展示，前端用 has_password 标记是否已配置
        extra_kwargs = {"password": {"write_only": True}}


class ElasticsearchSourceViewSet(CustomModelViewSet):
    """ES 日志数据源"""
    queryset = ElasticsearchSource.objects.all()
    serializer_class = ElasticsearchSourceSerializer
    search_fields = ['name', 'url']
    filter_fields = ['status']

    @action(methods=['GET'], detail=True, url_path='test')
    def test(self, request, pk=None):
        """连通性测试：GET / 返回 ES 基本信息"""
        source = self.get_object()
        base = (source.url or '').strip().rstrip('/')
        if not base:
            return ErrorResponse(msg="数据源地址为空")
        try:
            resp = requests.get(base, auth=source.get_auth(), timeout=5)
        except requests.exceptions.Timeout:
            return ErrorResponse(msg=f"ES 请求超时（5s）：{base}")
        except requests.exceptions.ConnectionError:
            return ErrorResponse(msg=f"无法连接 ES：{base}")
        except requests.exceptions.RequestException as e:
            return ErrorResponse(msg=f"ES 请求异常：{e}")
        if resp.status_code == 200:
            return DetailResponse(data={'status': 'ok', 'url': source.url}, msg="连接正常")
        if resp.status_code in (401, 403):
            return ErrorResponse(msg='ES 认证失败或账号无权限，请检查用户名与密码')
        return ErrorResponse(msg=f"ES 返回 HTTP {resp.status_code}：{resp.text[:150]}")

    @action(methods=['GET'], detail=True, url_path='indices')
    def indices(self, request, pk=None):
        """索引模式列表：读 _cat/indices，把按天滚动的索引归并成通配模式供前端筛选。

        query: keyword=模糊过滤模式名
        返回: {list: [{pattern, count, docs, samples, current}], total, indices}
        """
        source = self.get_object()
        base = (source.url or '').strip().rstrip('/')
        if not base:
            return ErrorResponse(msg="数据源地址为空")

        try:
            resp = requests.get(
                f"{base}/_cat/indices",
                params={'format': 'json', 'h': 'index,docs.count,store.size', 's': 'index:asc'},
                auth=source.get_auth(), timeout=15,
            )
        except requests.exceptions.Timeout:
            return ErrorResponse(msg=f"ES 请求超时（15s）：{base}")
        except requests.exceptions.ConnectionError:
            return ErrorResponse(msg=f"无法连接 ES：{base}")
        except requests.exceptions.RequestException as e:
            return ErrorResponse(msg=f"ES 请求异常：{e}")

        if resp.status_code in (401, 403):
            return ErrorResponse(msg='ES 认证失败或账号无权限，请检查用户名与密码')
        if resp.status_code != 200:
            return ErrorResponse(msg=f"ES 返回 HTTP {resp.status_code}：{resp.text[:200]}")

        try:
            rows = resp.json()
        except ValueError:
            return ErrorResponse(msg="ES 返回非 JSON 响应")

        current = (source.index_pattern or '').strip()
        groups = {}
        valid = 0
        for row in rows or []:
            name = (row.get('index') or '').strip()
            if not name or name.startswith(_SKIP_PREFIX):
                continue
            valid += 1
            pattern = _merge_index(name)
            g = groups.setdefault(pattern, {'pattern': pattern, 'count': 0, 'docs': 0, 'size': 0,
                                            'samples': [], 'oldest': name, 'newest': name})
            g['count'] += 1
            g['docs'] += _to_int(row.get('docs.count'))
            g['size'] += _parse_size(row.get('store.size'))
            if len(g['samples']) < 3:
                g['samples'].append(name)
            # 索引名按字典序 ≈ 时间序，用于展示时间跨度
            if name < g['oldest']:
                g['oldest'] = name
            if name > g['newest']:
                g['newest'] = name

        data = sorted(groups.values(), key=lambda x: x['pattern'].lower())
        for g in data:
            g['current'] = (g['pattern'] == current)

        # 数据源配的模式可能暂时没有数据（ES 里查不到），补一条保证一定能选回默认值
        if current and not any(g['pattern'] == current for g in data):
            data.insert(0, {'pattern': current, 'count': 0, 'docs': 0, 'size': 0,
                            'samples': [], 'oldest': '', 'newest': '', 'current': True})

        keyword = (request.query_params.get('keyword') or '').strip().lower()
        if keyword:
            data = [g for g in data if keyword in g['pattern'].lower()]

        return DetailResponse(
            data={'list': data, 'total': len(data), 'indices': valid, 'current': current},
            msg="获取成功",
        )

    @action(methods=['POST'], detail=True, url_path='search')
    def search(self, request, pk=None):
        """日志检索：body {index, keyword, level, from, to, size, from_offset}
        index 优先于数据源上配置的「索引模式」，用于在检索页临时切换索引。
        """
        source = self.get_object()
        body = request.data or {}

        raw_index = (body.get('index') or '').strip()
        if raw_index and not _safe_index(raw_index):
            return ErrorResponse(msg=f"索引模式不合法：{raw_index}")

        keyword = (body.get('keyword') or '').strip()
        level = (body.get('level') or '').strip()
        from_ts = body.get('from') or None
        to_ts = body.get('to') or None
        try:
            size = max(1, min(int(body.get('size', 50)), 200))
        except (TypeError, ValueError):
            size = 50
        try:
            offset = max(0, int(body.get('from_offset', 0)))
        except (TypeError, ValueError):
            offset = 0

        # 构建 ES DSL（字段名按常见约定：@timestamp / level）
        must = []
        if keyword:
            must.append({"query_string": {"query": keyword}})
        filters = []
        if from_ts or to_ts:
            rng = {}
            if from_ts:
                rng['gte'] = from_ts
            if to_ts:
                rng['lte'] = to_ts
            filters.append({"range": {"@timestamp": rng}})
        if level:
            lv = level.strip().lower()
            # 有的索引有独立 level 字段，有的（filebeat 原样采集）级别只在正文里，
            # 这里用 should 同时兜住两种情况，minimum_should_match=1 命中任一即可
            should = [
                {"term": {"level": lv}},
                {"term": {"log_level": lv}},
                {"term": {"severity": lv}},
            ]
            for token in _LEVEL_SEARCH_ALIAS.get(lv, (lv.upper(),)):
                should.append({"match_phrase": {"message": token}})
            filters.append({"bool": {"should": should, "minimum_should_match": 1}})

        dsl = {
            "size": size,
            "from": offset,
            # ES 默认 total 只统计到 10000 就返回 relation=gte，这里放宽到 10 万
            "track_total_hits": TOTAL_HIT_CAP,
            "sort": [{"@timestamp": {"order": "desc"}}],
            "query": {"bool": {}},
        }
        if must:
            dsl["query"]["bool"]["must"] = must
        if filters:
            dsl["query"]["bool"]["filter"] = filters

        base = (source.url or '').strip().rstrip('/')
        if not base:
            return ErrorResponse(msg="数据源地址为空")
        index = _safe_index(raw_index) or (source.index_pattern or '').strip().strip('/')
        if not index:
            return ErrorResponse(msg="索引模式为空，请在数据源或检索页指定")
        url = f"{base}/{index}/_search"
        try:
            resp = requests.post(url, json=dsl, auth=source.get_auth(), timeout=20)
        except requests.exceptions.Timeout:
            return ErrorResponse(msg=f"ES 请求超时（20s）：{base}")
        except requests.exceptions.ConnectionError:
            return ErrorResponse(msg=f"无法连接 ES：{base}")
        except requests.exceptions.RequestException as e:
            return ErrorResponse(msg=f"ES 请求异常：{e}")

        if resp.status_code == 404:
            return ErrorResponse(msg=f"索引不存在或没有匹配的索引：{index}")
        if resp.status_code in (401, 403):
            return ErrorResponse(msg='ES 认证失败或账号无权限，请检查用户名与密码')
        if resp.status_code != 200:
            return ErrorResponse(msg=f"ES 返回 HTTP {resp.status_code}：{resp.text[:300]}")

        try:
            data = resp.json()
        except ValueError:
            return ErrorResponse(msg="ES 返回非 JSON 响应")

        hits = (data.get('hits') or {}).get('hits', [])
        total_raw = (data.get('hits') or {}).get('total', 0)
        # ES 7+ total 是 {value, relation}；relation=gte 表示真实总数超过统计上限
        if isinstance(total_raw, dict):
            total = total_raw.get('value', 0)
            total_exact = total_raw.get('relation') == 'eq'
        else:
            total = total_raw or 0
            total_exact = True

        logs = []
        for h in hits:
            src = h.get('_source') or {}
            message = str(_pick(src, ('message', 'msg', 'log_message')) or '')
            # 统一补充 _id / _index 便于定位
            logs.append({
                "id": h.get('_id'),
                "index": h.get('_index'),
                "timestamp": _pick(src, ('@timestamp', 'timestamp', 'time')) or '',
                # 没有独立 level 字段的索引（如 filebeat 原样采集），从正文里提取
                "level": _pick(src, ('level', 'log_level', 'severity')) or _extract_level(message),
                "message": message,
                "host": _pick(src, ('host', 'hostname', 'server_ip', 'ip'),
                              ('host.name', 'agent.hostname')) or '',
                "service": _pick(src, ('service', 'app', 'service_name', 'container_name'),
                                 ('dissect.service_name', 'container.name',
                                  'kubernetes.container.name')) or '',
                "env": _pick(src, ('env_name', 'env', 'environment')) or '',
                "file": _dig(src, 'log.file.path') or '',
                "_source": src,
            })

        return DetailResponse(
            data={"total": total, "total_exact": total_exact, "logs": logs, "index": index},
            msg="查询成功",
        )

    @action(methods=['GET'], detail=False, url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回启用数据源"""
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(status=1).order_by('sort').values('id', 'name', 'url', 'index_pattern')
        return DetailResponse(data=list(data), msg="获取成功")
