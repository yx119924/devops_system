# -*- coding: utf-8 -*-
"""
ES 日志数据源管理 + 日志检索代理
端点：
  search  -> POST {url}/{index}/_search   日志检索（时间/关键字/级别筛选，索引可覆盖）
  indices -> GET  {url}/_cat/indices      索引模式列表（滚动索引自动归并成通配模式）
  test    -> GET  {url}/                  连通性测试
  all     -> GET                          下拉选项
"""
import logging
import re
import time
from datetime import datetime, timedelta, timezone as dt_timezone

import requests
from rest_framework import serializers
from rest_framework.decorators import action

from dvadmin.log.models import ElasticsearchSource
from dvadmin.bastion.crypto import encrypt
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet

logger = logging.getLogger(__name__)

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


# ★ 时间戳格式：前端 el-date-picker 的 `value-format="YYYY-MM-DD HH:mm:ss"` 是**空格**分隔，
#   而 ES 的 @timestamp 默认 format 是 `strict_date_optional_time`，只认 ISO 8601 的 **`T`** 分隔。
#   2026-10-09 实测（nginx-log-* / aichem-service-log-* 同 ES）：
#     `{"range":{"@timestamp":{"gte":"2026-10-09 11:34:05"}}}` -> HTTP 400
#     `{"range":{"@timestamp":{"gte":"2026-10-09T11:34:05"}}}` -> HTTP 200
#   ⇒ 不做归一化的话，用户在检索页**一旦选了时间范围，查询必然 400**。
_TS_SPACE_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})$')

# 检索页展示的时间格式
_TS_OUT_FMT = '%Y-%m-%d %H:%M:%S'


def _local_tz():
    """项目时区。

    ★ 不用 ``django.utils.timezone.localtime()``：本项目 ``USE_TZ = False``，
      该函数对 aware datetime 的处理依赖 USE_TZ，在不同配置下表现不一致。
      直接取 ``settings.TIME_ZONE`` 构造 ZoneInfo 最可控（取不到时退回 UTC+8）。
    """
    try:
        from zoneinfo import ZoneInfo

        from django.conf import settings
        return ZoneInfo(getattr(settings, 'TIME_ZONE', None) or 'Asia/Shanghai')
    except Exception:                                                   # noqa: BLE001
        return dt_timezone(timedelta(hours=8))


def _fmt_ts(value):
    """把 ES 的时间值格式化成项目时区的可读字符串（``YYYY-MM-DD HH:mm:ss``）。

    ★ 为什么在服务端转、不在前端转（2026-11-06 用户反馈「时间少 8 小时」）：
      ES 返回的 ``@timestamp`` 是 UTC，形如 ``2026-11-06T01:01:02.658Z``。
      前端若用 ``new Date()`` 渲染，会按**客户端时区**显示 —— 同一条日志，
      在公司看是 09:01、在别的时区连 VPN 看就是另一个数，两个人截图对不上。
      统一在服务端按 ``settings.TIME_ZONE`` 转，显示口径只有一处。

    ★ 认不出来的格式**原样返回**，不返回空 —— 宁可显示一个怪字符串，
      也不要让一条本该有时间的日志看起来像「没有时间」。
    """
    if value in (None, ''):
        return ''
    # 数字：可能是 epoch 秒，也可能是毫秒（不同采集端写法不同）
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        secs = float(value)
        if secs > 1e11:                                                 # 毫秒
            secs /= 1000.0
        try:
            dt = datetime.fromtimestamp(secs, tz=dt_timezone.utc)
        except (OverflowError, OSError, ValueError):
            return str(value)
        return dt.astimezone(_local_tz()).strftime(_TS_OUT_FMT)

    s = str(value).strip()
    if not s:
        return ''
    # Python 3.11 之前的 fromisoformat 不认结尾的 Z
    iso = s[:-1] + '+00:00' if s.endswith('Z') else s
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return s
    if dt.tzinfo is None:
        # ES 的 @timestamp 默认就是 UTC；没有时区后缀时按 UTC 解释
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(_local_tz()).strftime(_TS_OUT_FMT)


def _norm_ts(value):
    """把前端传来的**本地时间**归一化成 ES 能精确理解的 UTC ISO 8601。

    ★ 两步都不能少（2026-11-06 修）：
      ① 空格 → ``T``：ES 的 ``strict_date_optional_time`` 不认空格（见上一条注释）
      ② **补时区并转 UTC**：``2026-11-06T09:00:00`` 这种**无时区**字符串，
         ES 一律按 **UTC** 解释。而用户在检索页选的是**北京时间** 09:00，
         直接发过去就变成 UTC 09:00 = 北京 17:00，查询窗口整整偏 8 小时。
         表现是「选了最近 1 小时，一条都没有」，而日志其实是有的 ——
         这种偏差极难往「时区」上想，所以宁可在这里显式转一次。
      其余形式（已带时区 / ``now-1d`` 日期数学）原样透传。
    """
    s = str(value or '').strip()
    if not s:
        return None
    m = _TS_SPACE_RE.match(s)
    if m:
        naive = datetime.strptime(s, _TS_OUT_FMT)
        aware = naive.replace(tzinfo=_local_tz())
        return aware.astimezone(dt_timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return s


def _merge_index(name):
    """把滚动索引（xxx-2026.09.19）归并成通配模式（xxx-*），保留原分隔符"""
    m = _ROLLING_RE.match(name)
    if m and m.group('base'):
        return f"{m.group('base')}{m.group('sep')}*"
    return name


# 多选筛选项最多接受多少个（防止构造超长 terms 查询）
_FACET_MAX_ITEMS = 200


def _as_list(value):
    """把前端传来的多选参数归一成去重后的字符串列表。

    ★ 为什么要容三种形态（2026-11-05）：前端 el-select 多选给的是 list，
      但手工用 curl / 脚本调接口时常传 `hosts=a,b` 或单个字符串。
      若直接 `for x in value`，字符串会**按字符拆开** —— "web" 变成 "w"/"e"/"b"，
      于是 filters 里塞进三个单字母，查出来恒为 0 条**且不报错**，极难排查。
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        raw = str(value).split(',')
    out = []
    for item in raw:
        s = str(item or '').strip()
        if s and s not in out:
            out.append(s)
        if len(out) >= _FACET_MAX_ITEMS:
            break
    return out


# 检索页要聚合的两个字段（采集侧口径：server_ip 由平台注入，service_name 由附加字段写入）
_AGG_FIELDS = ('server_ip', 'service_name')


def _agg_field_plan(base, index, auth, fields=_AGG_FIELDS):
    """探测每个字段在目标索引里的**可聚合形态**。

    返回 ``(usable, blocked)``：
      usable[field] = 真正该拿去聚合的字段名
        · ``server_ip``          —— 本身就是 keyword
        · ``server_ip.keyword``  —— text + keyword 子字段的老索引，用子字段照样能聚
      blocked[field] = 不可用的原因（给用户看的中文短语）

    ★ 为什么不「先聚合，失败再看错误文案」（2026-11-05 真机踩到，第二次）：
      ES 7 的报错是 ``Text fields are not optimised for operations that require
      per-document field data...``，而 ES 6 是 ``Fielddata is disabled on text fields``。
      按文案分支必然漏掉一个版本 —— 漏掉的表现是把**整段英文 JSON 弹给用户**。
      探测字段能力是版本无关的，才是正解。

    ★ 为什么不「字段不存在就直接跳过」：老索引的 text 字段多半带 ``.keyword`` 子字段，
      其实完全可以聚合，只是要换成子字段名。用 _field_caps 才能区分「不能聚」和「要换名字聚」。
    """
    try:
        resp = requests.get(f"{base}/{index}/_field_caps",
                            params={'fields': ','.join(fields)}, auth=auth, timeout=10)
    except requests.exceptions.RequestException as e:
        return {}, {f: '字段探测失败（%s）' % e for f in fields}

    if resp.status_code == 404:
        return {}, {f: '索引不存在' for f in fields}
    if resp.status_code != 200:
        return {}, {f: '字段探测失败（HTTP %s）' % resp.status_code for f in fields}

    try:
        caps = (resp.json() or {}).get('fields') or {}
    except ValueError:
        return {}, {f: '字段探测返回非 JSON' for f in fields}

    usable, blocked = {}, {}
    for f in fields:
        info = caps.get(f)
        if not info:
            blocked[f] = '在该索引里没有这个字段'
            continue
        kw = info.get('keyword') or {}
        # 本身是 keyword：没有 text 兄弟节点，且可聚合
        if kw and 'text' not in info and kw.get('aggregatable', True):
            usable[f] = f
            continue
        # text + keyword 子字段：改用子字段
        if kw and kw.get('aggregatable', True):
            usable[f] = f + '.keyword'
            continue
        blocked[f] = '是 text 且没有 keyword 子字段（不能聚合）'
    return usable, blocked


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
        """日志检索：body {index, keyword, level, hosts, services, from, to, size, from_offset}
        index 优先于数据源上配置的「索引模式」，用于在检索页临时切换索引。
        hosts / services 是多选筛选（list 或逗号分隔字符串均可）。
        """
        source = self.get_object()
        body = request.data or {}

        raw_index = (body.get('index') or '').strip()
        if raw_index and not _safe_index(raw_index):
            return ErrorResponse(msg=f"索引模式不合法：{raw_index}")

        keyword = (body.get('keyword') or '').strip()
        level = (body.get('level') or '').strip()
        # ★ 必须归一化：前端 el-date-picker 的 value-format 是「空格」分隔，
        #   而 ES 的 @timestamp 只认 ISO 8601 的「T」分隔 —— 不转就是 HTTP 400（见 _norm_ts）
        from_ts = _norm_ts(body.get('from'))
        to_ts = _norm_ts(body.get('to'))
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

        # ★ 主机 / 服务筛选（2026-11-05 新增）
        #   字段名口径必须与采集侧严格一致：
        #     server_ip     —— 平台下发片段时逐台注入（collector.py:721-727 的 add_fields）
        #     service_name  —— 任务的「附加字段」写入
        #   ★ 绝不能写成 service：那是 ECS 的 object 字段，采集侧填标量会被 ES 拒收，
        #     这里查它只会命中 service.name 之类的子路径，恒为 0 条。
        #   ★ 两个字段都要求是 keyword（索引模板里声明）。若被动态映射成 text，
        #     terms 查询不会报错、只会返回 0 条 —— 用 facets 接口能看出这个差异。
        hosts = _as_list(body.get('hosts'))
        services = _as_list(body.get('services'))
        if hosts:
            filters.append({"terms": {"server_ip": hosts}})
        if services:
            filters.append({"terms": {"service_name": services}})

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
        # ★ 计时埋点（2026-10-09 加）：
        #   排「大索引检索 5s 超时」时得到一个反常事实 —— 在同一台 ES 上直连复刻该 DSL
        #   只要 **0.65s**，而 `GetEsIndices`（同一个 5s 前端超时、同一个 ES 地址）也能成功，
        #   即 django→ES 这条路是通的。也就是说「5s 到底被谁吃掉」当时**没有任何数据能区分**
        #   「ES 那一步慢」还是「django/网络慢」，只能靠猜。
        #   这行日志把 **ES 往返耗时** 单独打出来，下次再超时，`docker logs dvadmin3-django`
        #   里比对 es=xxxms 与请求总耗时，一眼就能分清是谁的问题。
        _t0 = time.monotonic()
        try:
            resp = requests.post(url, json=dsl, auth=source.get_auth(), timeout=20)
        except requests.exceptions.Timeout:
            logger.warning("[log.search] ES 自身超时(20s) source=%s index=%s 已耗时=%.0fms url=%s",
                           source.id, index, (time.monotonic() - _t0) * 1000, url)
            return ErrorResponse(msg=f"ES 请求超时（20s）：{base}")
        except requests.exceptions.ConnectionError:
            logger.warning("[log.search] ES 连接失败 source=%s index=%s 已耗时=%.0fms url=%s",
                           source.id, index, (time.monotonic() - _t0) * 1000, url)
            return ErrorResponse(msg=f"无法连接 ES：{base}")
        except requests.exceptions.RequestException as e:
            logger.warning("[log.search] ES 请求异常 source=%s index=%s 已耗时=%.0fms err=%s",
                           source.id, index, (time.monotonic() - _t0) * 1000, e)
            return ErrorResponse(msg=f"ES 请求异常：{e}")

        logger.info("[log.search] source=%s index=%s level=%s size=%s offset=%s range=%s..%s "
                    "-> es=%.0fms http=%s bytes=%d",
                    source.id, index, level or '-', size, offset, from_ts or '-', to_ts or '-',
                    (time.monotonic() - _t0) * 1000, resp.status_code, len(resp.content))

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
                # ★ 统一转成项目时区再返回（ES 给的是 UTC，直接用会少 8 小时）
                "timestamp": _fmt_ts(_pick(src, ('@timestamp', 'timestamp', 'time'))),
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

    # ★ detail=True 不能改成 False（2026-11-05 踩过）：
    #   detail=False 注册出来的是集合级路由 `/log/es/facets/`，
    #   而检索页请求的是 `/log/es/{id}/facets/` ⇒ 一路 404「接口路径找不到」，
    #   且响应里不会告诉你「正确路径是什么」。
    #   路由对不对，可用 print(get_resolver().url_patterns) 或 DRF 的 router.urls 验证。
    @action(methods=['GET'], detail=True, url_path='facets')
    def facets(self, request, pk=None):
        """检索页的筛选项：主机 IP / 服务名（terms 聚合）。

        GET ?index=<索引模式>
        返回 {hosts: [{value, count}], services: [...], notes: [...]}

        ★ 为什么从 ES 聚合、而不是从 CMDB 或写死：
          下拉要的是「**当前索引里真实出现过**哪些主机、哪些服务」。
          从 CMDB 取会多出「有机器但没日志」的项，写死则会漏掉新增服务 ——
          两者都会让用户选中一个永远查不到结果的值，却看不出哪里错了。
        """
        source = self.get_object()
        raw_index = (request.query_params.get('index') or '').strip()
        if raw_index and not _safe_index(raw_index):
            return ErrorResponse(msg=f"索引模式不合法：{raw_index}")
        index = _safe_index(raw_index) or (source.index_pattern or '').strip().strip('/')
        if not index:
            return ErrorResponse(msg='索引模式为空，无法获取筛选项')

        base = (source.url or '').strip().rstrip('/')
        if not base:
            return ErrorResponse(msg='数据源地址为空')

        # ★ 先探测字段能力，再决定聚合什么（见 _agg_field_plan 的注释）
        usable, blocked = _agg_field_plan(base, index, source.get_auth())
        notes = ['%s %s' % (f, why) for f, why in sorted(blocked.items())]

        agg_body = {}
        if 'server_ip' in usable:
            agg_body['hosts'] = {"terms": {"field": usable['server_ip'], "size": _FACET_MAX_ITEMS}}
        if 'service_name' in usable:
            agg_body['services'] = {"terms": {"field": usable['service_name'], "size": _FACET_MAX_ITEMS}}

        if not agg_body:
            # 这个索引本来就没有这两个字段（例如 nginx-log-* 这类非本平台采集的索引）。
            # 不报错：切到别的索引看一眼是正常操作，弹红框属于打扰。
            both_missing = (len(blocked) == len(_AGG_FIELDS)
                            and all('没有这个字段' in v for v in blocked.values()))
            if both_missing:
                notes = ['该索引没有 server_ip / service_name 字段（可能不是本平台采集的索引），'
                         '主机 / 服务筛选对它不可用']
            return DetailResponse(
                data={"hosts": [], "services": [],
                      "notes": notes or ['该索引没有 server_ip / service_name 字段']},
                msg="该索引没有可聚合的主机/服务字段")

        dsl = {"size": 0, "track_total_hits": False, "aggs": agg_body}
        url = f"{base}/{index}/_search"
        _t0 = time.monotonic()
        try:
            resp = requests.post(url, json=dsl, auth=source.get_auth(), timeout=20)
        except requests.exceptions.Timeout:
            return ErrorResponse(msg=f"ES 请求超时（20s）：{base}")
        except requests.exceptions.ConnectionError:
            return ErrorResponse(msg=f"无法连接 ES：{base}")
        except requests.exceptions.RequestException as e:
            return ErrorResponse(msg=f"ES 请求异常：{e}")

        logger.info("[log.facets] source=%s index=%s fields=%s -> es=%.0fms http=%s",
                    source.id, index, ','.join(sorted(usable.values())),
                    (time.monotonic() - _t0) * 1000, resp.status_code)

        if resp.status_code == 404:
            # 索引还不存在 = 采集还没落第一条。不是错误，返回空选项让页面照常可用。
            return DetailResponse(
                data={"hosts": [], "services": [],
                      "notes": notes + ["索引还不存在：%s（确认采集已下发、且之后有新日志写入）" % index]},
                msg="索引不存在")
        if resp.status_code in (401, 403):
            return ErrorResponse(msg='ES 认证失败或账号无权限，请检查用户名与密码')
        if resp.status_code == 400:
            # ★ 不按错误文案分支（ES 6/7/8 措辞各不相同），统一降级成可读提示，
            #   绝不能把整段英文 JSON 弹给用户。
            return DetailResponse(
                data={"hosts": [], "services": [],
                      "notes": notes + ["ES 拒绝聚合（HTTP 400）：server_ip / service_name 可能不是 keyword。"
                                        "按 LOG-COLLECT.md 第 11 章建索引模板后重写数据。"]},
                msg="字段类型不支持聚合")
        if resp.status_code != 200:
            return ErrorResponse(msg=f"ES 返回 HTTP {resp.status_code}：{resp.text[:300]}")

        try:
            data = resp.json()
        except ValueError:
            return ErrorResponse(msg="ES 返回非 JSON 响应")

        resp_aggs = data.get('aggregations') or {}

        def _buckets(name):
            return [{"value": b.get('key'), "count": b.get('doc_count', 0)}
                    for b in ((resp_aggs.get(name) or {}).get('buckets') or [])
                    if b.get('key') not in (None, '')]

        hosts = _buckets('hosts')
        services = _buckets('services')
        if not hosts and not services:
            notes.append("当前索引里没有 server_ip / service_name 的值："
                         "确认采集任务的「附加字段」填了 service_name，且日志是下发之后新写入的")
        return DetailResponse(data={"hosts": hosts, "services": services, "notes": notes},
                              msg="获取成功")

    @action(methods=['GET'], detail=False, url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回启用数据源"""
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(status=1).order_by('sort').values('id', 'name', 'url', 'index_pattern')
        return DetailResponse(data=list(data), msg="获取成功")
