# -*- coding: utf-8 -*-
"""
Jenkins 服务器管理 + HTTP API 代理
代理端点（相对 Jenkins 根地址）：
  test       -> GET  {url}/api/json                          连通性测试
  jobs       -> GET  {url}/api/json?tree=jobs[...]           获取所有 Job
  job_params -> GET  {url}/job/{job}/api/json?...            参数定义 + 候选值（下拉/多选数据源）
  build      -> POST {url}/job/.../build 或 /buildWithParameters  触发构建（参数化 job 自动切换端点）
  job_status -> GET  {url}/job/{job}/lastBuild/api/json      最近构建状态
  console    -> GET  {url}/job/{job}/{build}/logText/...     构建日志（增量）
"""
import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import requests
from django.db import transaction
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated

from dvadmin.jenkins.models import JenkinsServer, JenkinsRolePermission
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet

# ★ 「角色可见目录」的候选清单**不再写死**，改为实时读取该台 Jenkins 的目录树。
#
# 起因：早先这里预置了 ['dev/', 'test/', 'pre/', 'prod/'] 作为下拉候选，但真实
# Jenkins 的顶层是「开发环境 / 测试环境 / 灰度环境 / 生产环境 / 灵境开物-* /
# 定时任务 …」外加一批**根级 Job**（myapp-cloud-service、备份、离子液体 …），
# 预置项跟实际完全对不上，管理员只能手工敲。现在直接拉真实目录树，
# 并且**根级 Job 也列为可授权项**——前缀语义对同名根级 Job 同样成立
# （``_path_matches('备份', '备份/')`` 为 True）。
#
# 失败时**绝不伪造列表**（那正是本次要修掉的问题）：降级为「已授权目录的并集」，
# 并回一条 ``folders_error``；select 本来就支持手工输入，不影响保存。
FOLDER_CACHE_TTL = 300          # 目录结构变更不频繁，缓存 5 分钟
_FOLDER_CACHE = {}
# ★ 单台拉取超时必须远小于前端 request() 的 5000ms 默认超时，
#   否则 Jenkins 一慢，整个授权面板会跟着 5s 超时报错、连现有配置都保存不了。
FOLDER_FETCH_TIMEOUT = 3.0
_MAX_FOLDER_OPTIONS = 400       # 防御：异常庞大的目录树不往前端灌
MAX_PATH_LEN = 200              # 单个授权前缀的长度上限

# ---------------------------------------------------------------
# Job 树拉取：一次深树查询 + 进程内缓存
#
# 旧实现是「每遇到一个 folder 就发一次 HTTP」的递归爬取，实测这台 Jenkins
# 上有 250 个 Job，superadmin 要发 **22 次**请求、耗时 1.7~6.9s（受单次抖动放大）；
# 而前端 ``request()`` 的真实超时是 **5s**（见 web/src/utils/service.ts 的
# ``createRequestFunction``，那里的 ``configDefault.timeout = 5000`` 会覆盖
# axios 实例上的 20000），于是「偶尔 timeout of 5000ms exceeded」。
#
# 改用 Jenkins 的嵌套 ``tree`` 参数一次取回 TREE_DEPTH 层，实测 **1 次请求 / 0.4s**。
# 超过该深度仍是 folder 的分支再用递归补齐（正常目录结构下不会触发）。
# ---------------------------------------------------------------
TREE_DEPTH = 4
TREE_CACHE_TTL = 60
_TREE_CACHE = {}

_JOB_FIELDS = 'name,url,color,description,_class'


def _tree_expr(depth):
    """构造 Jenkins tree 查询表达式：``jobs[<fields>,jobs[<fields>,...]]``"""
    if depth <= 0:
        return None
    inner = _tree_expr(depth - 1)
    if inner:
        return 'jobs[%s,%s]' % (_JOB_FIELDS, inner)
    return 'jobs[%s]' % _JOB_FIELDS


def _flatten_tree(nodes, path='', depth=0, out=None):
    """把嵌套 tree 响应展开成扁平列表（folder 在前，其子节点紧随其后）"""
    if out is None:
        out = []
    for j in nodes or []:
        if not isinstance(j, dict):
            continue
        name = j.get('name', '')
        full_path = '%s/%s' % (path, name) if path else name
        jclass = j.get('_class', '') or ''
        # folder 没有 color 字段；普通 Job 即使未构建过也有 'notbuilt'/'disabled'
        is_folder = 'Folder' in jclass or not j.get('color')
        out.append({
            'full_path': full_path, 'name': name, 'is_folder': is_folder,
            'color': j.get('color'), 'description': j.get('description'),
            'url': j.get('url'), 'depth': depth,
        })
        if isinstance(j.get('jobs'), list):
            _flatten_tree(j['jobs'], full_path, depth + 1, out)
    return out


def norm_grant_path(raw):
    """把用户/前端传来的目录前缀规范化为 ``"dev/"`` 这种形式。"""
    p = str(raw or '').strip().strip('/')
    if not p:
        return ''
    if len(p) > MAX_PATH_LEN:
        raise ValueError('目录前缀过长')
    if '\\' in p or '//' in p or any(seg in ('', '.', '..') for seg in p.split('/')):
        raise ValueError('目录前缀「%s」包含非法路径段' % raw)
    return p + '/'


# ---------------------------------------------------------------
# 「可授权目录」候选清单：从真实 Job 树汇总（模块级，供两个 ViewSet 复用）
# ---------------------------------------------------------------
_JENKINS_SESSION = requests.Session()


def jenkins_auth(source):
    """Basic Auth 参数，与 ``JenkinsServerViewSet._auth`` 同口径。"""
    username = (source.username or '').strip()
    token = source.get_token()
    if username or token:
        return (username, token)
    return None


def fetch_tree_nodes(source, timeout=FOLDER_FETCH_TIMEOUT):
    """一次深树查询取回扁平化 Job 树。**仅**供目录清单使用。

    刻意不复用 ``JenkinsServerViewSet._fetch_full_tree``：那个版本还会对超过
    ``TREE_DEPTH`` 的 folder 递归补齐（多次 HTTP），而目录清单只需要各层
    folder 的名字，深度不足的分支漏掉也不影响授权（前缀始终可手工输入）。
    这里固定只发 1 次请求，把耗时压在几百毫秒内。
    """
    base = (source.url or '').strip().rstrip('/')
    if not base:
        raise RuntimeError('Jenkins 地址为空')
    try:
        resp = _JENKINS_SESSION.get(
            base + '/api/json', auth=jenkins_auth(source),
            params={'tree': _tree_expr(TREE_DEPTH)},
            timeout=timeout, allow_redirects=False)
    except requests.exceptions.Timeout:
        raise RuntimeError('Jenkins 请求超时（>%ss）' % timeout)
    except requests.exceptions.ConnectionError:
        raise RuntimeError('无法连接 Jenkins：%s' % base)
    except requests.exceptions.RequestException as e:
        raise RuntimeError('Jenkins 请求异常：%s' % e)
    if resp.status_code != 200:
        raise RuntimeError('Jenkins 返回 HTTP %s' % resp.status_code)
    try:
        body = resp.json()
    except ValueError:
        raise RuntimeError('Jenkins 返回了非 JSON 内容')
    if not isinstance(body, dict):
        raise RuntimeError('Jenkins 返回了非 JSON 内容')
    return _flatten_tree(body.get('jobs', []))


def build_folder_options(nodes):
    """把扁平 Job 树汇总成「可授权前缀」清单，返回 ``(top, options)``。

    * ``top``     —— 顶层项的值列表（字符串数组，如 ``['开发环境/', '备份/']``）。
                     保持旧字段结构，给提示语/兼容取值用。
    * ``options`` —— 结构化选项，供前端分组下拉::

                      {'value': '生产环境/', 'label': '生产环境/',
                       'depth': 0, 'kind': 'folder'}

      ``depth == 0`` 包含**根级 Job**（``kind='job'``）；``depth > 0`` 只收 folder
      （子目录里具体的 Job 不再单列——授权到目录即可，下层默认可见）。
      ``value`` 一律带尾部 ``/``，与 :func:`norm_grant_path` 的输出对齐。
    """
    top, options, seen = [], [], set()
    for n in sorted(nodes or [], key=lambda x: (x['depth'], x['full_path'])):
        is_top = n['depth'] == 0
        if not is_top and not n['is_folder']:
            continue
        val = n['full_path'] + '/'
        if val in seen:
            continue
        seen.add(val)
        if is_top:
            top.append(val)
        options.append({
            'value': val,
            'label': n['full_path'],
            'depth': int(n['depth']),
            'kind': 'folder' if n['is_folder'] else 'job',
        })
        if len(options) >= _MAX_FOLDER_OPTIONS:
            break
    return top, options


def folder_options_for(source, force=False):
    """取某台 Jenkins 的「可授权前缀」清单（TTL 缓存；**失败不抛异常**）。

    返回 ``(top, options, error)``。``error`` 非空即拉取失败，调用方必须降级——
    绝不允许回退到一份编造的目录列表（那正是这次要修掉的问题）。
    """
    now = time.time()
    hit = _FOLDER_CACHE.get(source.pk)
    if not force and hit and now - hit[0] < FOLDER_CACHE_TTL:
        return hit[1], hit[2], ''
    try:
        top, options = build_folder_options(fetch_tree_nodes(source))
    except Exception as e:                       # noqa: BLE001 —— 任何异常都只降级
        return [], [], str(e)
    _FOLDER_CACHE[source.pk] = (now, top, options)
    return top, options, ''


def folder_options_many(sources):
    """并发取多台服务器的目录清单，返回 ``{server_pk: (top, options, error)}``。

    必须并发：前端 ``request()`` 默认超时只有 5s，若串行等 N 台、每台最多
    ``FOLDER_FETCH_TIMEOUT`` 秒，服务器一多就会把整个授权面板拖超时。
    """
    sources = list(sources)
    if not sources:
        return {}
    if len(sources) == 1:
        return {sources[0].pk: folder_options_for(sources[0])}
    out = {}
    with ThreadPoolExecutor(max_workers=min(4, len(sources))) as ex:
        futs = {ex.submit(folder_options_for, s): s for s in sources}
        for fut in as_completed(futs):
            srv = futs[fut]
            try:
                out[srv.pk] = fut.result()
            except Exception as e:               # 双保险，理论上不会走到
                out[srv.pk] = ([], [], str(e))
    return out


def granted_union(paths_lists):
    """已授权目录的并集 —— 拉取失败时的兜底候选，保证管理员至少能看到当前配置。"""
    out = []
    for paths in paths_lists or []:
        for p in paths or []:
            if p and p not in out:
                out.append(p)
    return sorted(out)


def fallback_options(paths):
    """由一组已授权目录构造结构化选项（兜底用）。"""
    return [{'value': p, 'label': p.rstrip('/'), 'depth': 0, 'kind': 'folder'}
            for p in paths]


def _apply_grant_input(perms, servers_qs, role_id, role_label='角色'):
    """把前端提交的授权列表校验成可入库的行（供两个 ViewSet 复用）。

    - ``allow_all: true``                → ``allowed_paths=[]``（全部可见）
    - ``allowed_paths: []``（且非全开）  → **跳过**（不建记录 = 默认拒绝）
    - 未出现在 ``perms`` 里的对象         → 由调用方整体覆盖时删除

    返回 ``(rows, error_msg)``，``error_msg`` 非空表示校验失败。
    """
    if perms is None:
        return None, '缺少 perms 字段（传空数组表示收回全部授权）'
    if not isinstance(perms, list):
        return None, 'perms 必须是数组'

    rows, seen = [], set()
    for i, item in enumerate(perms):
        idx = i + 1
        if not isinstance(item, dict):
            return None, '第 %d 项格式错误：应为对象' % idx
        try:
            server_id = int(item.get('server'))
        except (TypeError, ValueError):
            return None, '第 %d 项缺少合法的 server' % idx
        if not servers_qs.filter(pk=server_id).exists():
            return None, '第 %d 项 Jenkins 服务器不存在：%s' % (idx, server_id)
        if server_id in seen:
            continue
        seen.add(server_id)

        if item.get('allow_all'):
            paths = []                       # 空列表 = 全部可见
        else:
            paths = item.get('allowed_paths') or []
            if not isinstance(paths, list):
                return None, '第 %d 项 allowed_paths 必须是数组' % idx
            try:
                paths = [p for p in dict.fromkeys(norm_grant_path(x) for x in paths) if p]
            except ValueError as e:
                return None, '第 %d 项 %s' % (idx, e)
            # 关键：``allowed_paths=[]`` 在模型里表示"全部可见"。若前端想表达
            # "这个 %s 不给权限"，传的也是空数组——必须在这里**跳过**（= 不建记录 =
            # 默认拒绝），否则会把"取消授权"写成"授权全部"，是最危险的误授。
            if not paths:
                continue

        rows.append({'server_id': server_id, 'role_id': role_id,
                     'allowed_paths': paths})
    return rows, ''


# ---------------------------------------------------------------
# 参数化构建：候选值解析
#
# 实测这台 Jenkins 上 229 个 Job / 836 个参数，候选值有三处来源：
#   ① Jenkins JSON API 的 parameterDefinitions[].choices   → 605 个静态下拉
#   ② job config.xml 里 Active Choices 脚本的静态列表        → 27 个
#      （含 23 个 PT_CHECKBOX 复选框多选、2 个级联）
#   ③ 构建历史里实际用过的值                                 → 4 个（脚本实时查 GitLab 分支）
#
# ★ ``tree`` 绝不能写 ``[*]``：写 ``[*]`` 时 ``defaultParameterValue`` 只返回
#   ``_class``、不返回 ``value``（实测 834 个默认值全部丢失），必须把字段显式列全。
# ★ Active Choices 的候选值只能解析 config.xml —— 三条捷径实测全部走不通：
#   · ``descriptorByName/.../fillItems`` 在 uno-choice@2.8.10 上 404
#     （已用同类描述符做对照实验，确认 URL 模式本身是对的）
#   · ``GET /buildWithParameters`` 405（只收 POST，而 POST 会真触发构建）
#   · ``POST /scriptler/run/{id}`` 只绑定脚本自身声明的参数，``script=`` 替代脚本
#     会被"Script not approved yet"以 403 挡掉
# ---------------------------------------------------------------
PARAM_TREE = ('property[parameterDefinitions['
              'name,type,_class,description,choices,defaultParameterValue[value]]]')
PARAM_CACHE_TTL = 600
_PARAM_CACHE = {}

# Jenkins 参数类名 → 前端控件类型
_CLASS_TO_TYPE = {
    'ChoiceParameterDefinition': 'choice',
    'TextParameterDefinition': 'text',
    'StringParameterDefinition': 'string',
    'BooleanParameterDefinition': 'boolean',
    'PasswordParameterDefinition': 'password',
}
# Active Choices 的参数类名（候选值不在 JSON 里，要去 config.xml 解析）
_UNOCHOICE_CLASSES = {
    'ChoiceParameter', 'CascadeChoiceParameter', 'DynamicReferenceParameter',
}
# Active Choices 的 choiceType → 前端控件类型。
# ★ 取值是 PT_ 前缀（PT_SINGLE_SELECT / PT_MULTI_SELECT / PT_RADIO / PT_CHECKBOX），
#   不是直觉上的 MULTI_SELECT —— 实测配置里 MULTI_SELECT 出现 0 次，
#   生产环境的多选是 PT_CHECKBOX（复选框）。
_CHOICE_TYPE_TO_UI = {
    'PT_SINGLE_SELECT': 'choice',
    'PT_MULTI_SELECT': 'choice',    # 前端用 el-select multiple
    'PT_RADIO': 'radio',
    'PT_CHECKBOX': 'checkbox',
}
_UI_WITH_CHOICES = ('choice', 'checkbox', 'radio')

_UNOCHOICE_RE = re.compile(
    r'<(org\.biouno\.unochoice\.[A-Za-z]+)(?:\s+plugin="[^"]*")?\s*>(.*?)</\1>', re.S)
# ★ 只能取 <secureScript>，不能顺带取 <secureFallbackScript>
#   （它的内容是 return ['加载失败']），否则错误文案会被当成候选值。
_SECURE_SCRIPT_RE = re.compile(r'<secureScript[^>]*>\s*<script>(.*?)</script>', re.S)
_IF_BLOCK_RE = re.compile(r'if\s*\(([^)]*)\)\s*\{(.*?)\}', re.S)
_ELSE_BLOCK_RE = re.compile(r'else\s*\{(.*?)\}', re.S)
_RETURN_LIST_RE = re.compile(r'return\s*\[(.*?)\]', re.S)
_LITERAL_RE = re.compile(r"""['"]([^'"]*)['"]""")


def _xml_tag(block, tag):
    """取 XML 块里某个标签的文本，并做 HTML 反转义（config.xml 里 ' 存成 &apos;）"""
    m = re.search(r'<%s[^>]*>(.*?)</%s>' % (tag, tag), block, re.S)
    return html.unescape(m.group(1)).strip() if m else ''


def _list_literals(text):
    """从 ``return [ 'a', 'b' ]`` 里抠出字符串字面量列表"""
    m = _RETURN_LIST_RE.search(text or '')
    if not m:
        return []
    return [v for v in _LITERAL_RE.findall(m.group(1)) if v.strip()]


def parse_config_params(xml_text):
    """解析 job config.xml，返回 Active Choices 参数表 ``{参数名: {...}}``

    每条含：``ui_type``（决定控件）、静态候选值、级联规则
    （``if (X == "a" || X == "b") { return [...] } else { return [...] }``）。
    非 Active Choices 的参数不会出现在结果里。
    """
    out = {}
    for m in _UNOCHOICE_RE.finditer(xml_text or ''):
        blk = m.group(2)
        name = _xml_tag(blk, 'name')
        if not name:
            continue
        choice_type = _xml_tag(blk, 'choiceType') or 'PT_SINGLE_SELECT'
        refs = [x for x in re.split(r'[,\s]+', _xml_tag(blk, 'referencedParameters')) if x]
        ss = _SECURE_SCRIPT_RE.search(blk)
        body = html.unescape(ss.group(1)) if ss else ''

        rules, else_choices, flat = [], [], []
        if body:
            flat = _list_literals(body)
            if 'if' in body:
                for cm in _IF_BLOCK_RE.finditer(body):
                    when = {}
                    for var, val in re.findall(r'(\w+)\s*==\s*[\'"]([^\'"]*)[\'"]', cm.group(1)):
                        when.setdefault(var, []).append(val)
                    choices = _list_literals(cm.group(2))
                    if when and choices:
                        rules.append({'when': when, 'choices': choices})
                em = _ELSE_BLOCK_RE.search(body)
                if em:
                    else_choices = _list_literals(em.group(1))

        # 兜底候选：所有出现过的值（级联分支里的也并进来），供前端在
        # 当前级联条件都没命中时使用
        fallback = list(dict.fromkeys(
            flat + else_choices + [v for r in rules for v in r['choices']]))
        is_multi = choice_type in ('PT_CHECKBOX', 'PT_MULTI_SELECT')
        out[name] = {
            'ui_type': _CHOICE_TYPE_TO_UI.get(choice_type, 'choice'),
            'choice_type': choice_type,
            'referenced': refs,
            'choices': flat if not rules else fallback,
            'cascade_rules': rules,
            'cascade_else': else_choices,
            'fallback_choices': fallback,
            'multiple': is_multi,
        }
    return out


def extract_history_values(builds):
    """从构建历史里提取每个参数**实际用过的值**（新的在前，已去重）

    Jenkins 每次构建都会把参数写进 ``actions[].parameters[]``，这是唯一
    不需要任何凭据就能拿到的"真实候选值"来源，用来兜住那些脚本里算不出来的
    参数（例如实时查 GitLab 分支的 BRANCH_CHEM）。
    """
    seen = {}
    for b in builds or []:
        if not isinstance(b, dict):
            continue
        for act in (b.get('actions') or []):
            if not isinstance(act, dict):
                continue
            for pm in (act.get('parameters') or []):
                if not isinstance(pm, dict):
                    continue
                name, val = pm.get('name'), pm.get('value')
                if not name or val in (None, ''):
                    continue
                if not isinstance(val, str):
                    val = json.dumps(val, ensure_ascii=False)
                lst = seen.setdefault(name, [])
                if val not in lst:
                    lst.append(val)
    return seen


class JenkinsGrantAdminPermission(BasePermission):
    """谁能配置 Jenkins 目录授权。

    两条路：运维 / 管理员（``jenkinsServer:Create|Update|Delete``，在 Jenkins 服务器页配），
    或**能配角色权限的人**（``role:SetMenu``，在角色管理页配）。

    不复用 ``CustomPermission``：本 ViewSet 的自定义 action 路径没有登记 MenuButton，
    ``CustomPermission`` 的 URL+method 反查必然落空（403），而这里要判的是
    "这个人是不是运维/管理员"，跟具体接口无关。
    """

    message = '仅运维或管理员可配置 Jenkins 目录授权'

    def has_permission(self, request, view):
        user = request.user
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'is_superuser', False):
            return True
        try:
            from dvadmin.utils.perm_helper import has_button
        except Exception:
            return False
        return has_button(
            user,
            'jenkinsServer:Create', 'jenkinsServer:Update', 'jenkinsServer:Delete',
            'role:SetMenu',
        )


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
        """取当前 URL 里的 Jenkins 服务器。

        同样走 ``_get_server_raw`` 而不是 ``self.get_object()``——``test`` / ``jobs`` /
        ``build`` / ``job_status`` / ``console`` 这五个 action 的接口层权限由
        ``CustomPermission`` 按 ``jenkinsJob:*`` / ``jenkinsServer:Test`` 按钮把守，
        数据层可见性由 ``_get_allowed_paths``（角色目录授权）决定，
        不应该再叠加一层与它们无关的部门 ``data_range`` 过滤。
        """
        from rest_framework.exceptions import NotFound

        server = self._get_server_raw(self.kwargs.get('pk'))
        if server is None:
            raise NotFound('Jenkins 服务器不存在')
        return server

    @staticmethod
    def _get_server_raw(pk):
        """直接按 pk 取 Jenkins 服务器，**不走** ``filter_queryset``。

        为什么要绕开：框架的 ``DataLevelPermissionsFilter`` 是拿 ``request.path``
        去 ``MenuButton`` 表反查按钮权限的。本 ViewSet 的 ``role_permissions`` /
        ``set_role_permissions`` 是新增的 action，路径从未登记过 MenuButton，
        于是 ``dataScope_list`` 为空 → 最终落到 ``dept_belong_id__in=[]`` →
        对任何非超管都返回空集 → ``self.get_object()`` 直接 404。
        授权配置对本 ViewSet 而言是"辅助数据"，可见性由 ``JenkinsGrantAdminPermission``
        在代码层判定，不依赖框架的 data_range。
        """
        try:
            return JenkinsServer.objects.get(pk=pk)
        except (JenkinsServer.DoesNotExist, ValueError, TypeError):
            return None

    def _auth(self, source):
        """返回 requests 的 auth 参数（Basic Auth）或 None（匿名）"""
        username = (source.username or '').strip()
        token = source.get_token()
        if username or token:
            return (username, token)
        return None

    def _request(self, source, path, method='GET', params=None, data=None, timeout=60, headers=None):
        """代理 Jenkins HTTP 请求，返回 (status_code, body_text, resp)

        body_text 对 JSON 已解码、对纯文本原样返回（日志接口是纯文本）。
        """
        base = (source.url or '').strip().rstrip('/')
        if not base:
            raise RuntimeError("Jenkins 地址为空")
        url = f"{base}{path}"
        try:
            if not hasattr(self, '_jenkins_session'):
                self._jenkins_session = requests.Session()
            resp = self._jenkins_session.request(
                method, url, auth=self._auth(source), params=params, data=data,
                headers=headers, timeout=timeout, allow_redirects=False,
            )
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
    # 获取所有 Job（递归 folder + 按角色权限过滤）
    # ------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='jobs')
    def jobs(self, request, pk=None):
        """Job 列表。

        参数 ``refresh=1`` 可强制跳过缓存（前端「刷新 Job 列表」按钮用）。
        返回值里 ``cached`` 仅用于排查，无业务含义。
        """
        source = self._get_source()
        allowed = self._get_allowed_paths(request, source)
        force = str(request.query_params.get('refresh', '')).lower() in ('1', 'true', 'yes')
        try:
            nodes, cached = self._get_full_tree(source, force=force)
        except Exception as e:
            return ErrorResponse(msg=str(e))
        items = self._filter_nodes(nodes, allowed)
        return DetailResponse(
            data={
                'jobs': items,
                # restricted=False → 不受限（超管，或该角色 allowed_paths 为空=全部）
                'restricted': allowed is not None,
                'allowed_paths': allowed if allowed is not None else None,
                'total': len(items),
                'cached': cached,
            },
            msg="获取成功",
        )

    # ------------------------------------------------------------
    # Job 树：拉取 / 缓存 / 过滤
    # ------------------------------------------------------------
    def _get_full_tree(self, source, force=False):
        """取（**未过滤**的）完整 Job 树，带 TTL 缓存。

        缓存的是"全量树"而不是"某个用户过滤后的结果"——这样不同角色的请求
        共享同一份缓存，也避免把某个受限角色的可见集误发给别人。
        返回 ``(nodes, cached)``。
        """
        now = time.time()
        hit = _TREE_CACHE.get(source.pk)
        if not force and hit and now - hit[0] < TREE_CACHE_TTL:
            return hit[1], True
        nodes = self._fetch_full_tree(source)
        _TREE_CACHE[source.pk] = (now, nodes)
        return nodes, False

    def _fetch_full_tree(self, source):
        """一次深树查询取回整棵树；深度不足的分支再递归补齐。"""
        code, body, _ = self._request(
            source, '/api/json', method='GET',
            params={'tree': _tree_expr(TREE_DEPTH)}, timeout=30)
        if code != 200:
            raise RuntimeError('获取 Job 列表失败：Jenkins 返回 HTTP %s' % code)
        if not isinstance(body, dict):
            raise RuntimeError('获取 Job 列表失败：Jenkins 返回了非 JSON 内容')
        nodes = _flatten_tree(body.get('jobs', []))
        # 出现在最深一层的 folder 说明它下面还有内容没取到，逐个补齐
        deep = [n for n in nodes if n['is_folder'] and n['depth'] >= TREE_DEPTH]
        for n in deep:
            nodes.extend(self._fetch_jobs_tree(source, n['full_path'], n['depth'] + 1, 12, None))
        return nodes

    @classmethod
    def _filter_nodes(cls, nodes, allowed):
        """按角色可见目录过滤（``allowed=None`` 表示不受限）。

        返回**新的** dict，不修改缓存里的对象，否则会污染其他角色的结果。
        """
        if allowed is None:
            return [dict(n) for n in nodes]
        if not allowed:
            return []
        out = []
        for n in nodes:
            fp = n['full_path']
            if n['is_folder']:
                # folder 命中前缀，或某前缀落在该 folder 之内 → 保留（否则子项也到不了）
                if any(cls._path_matches(fp, p) or cls._path_matches(p, fp) for p in allowed):
                    out.append(dict(n))
            elif any(cls._path_matches(fp, p) for p in allowed):
                out.append(dict(n))
        return out

    def _get_allowed_paths(self, request, source):
        """返回允许的路径前缀列表；None=全部允许；[]=无权限

        注意：判定依据必须是 role 多对多（user.role），**不能用 current_role**。
        current_role 是登录时写入的单个 FK（current_role_id），历史用户或直接改库
        的用户该字段可能是 NULL，会导致"所有 Job 一律默认拒绝"。
        多对多并集也与 CustomPermission 的判定口径一致。
        """
        if getattr(request.user, 'is_superuser', False):
            return None
        role_ids = list(request.user.role.values_list('id', flat=True))
        if not role_ids:
            return []
        perms = JenkinsRolePermission.objects.filter(server=source, role_id__in=role_ids)
        if not perms.exists():
            return []  # 默认拒绝
        allowed = set()
        for p in perms:
            paths = p.allowed_paths or []
            if not paths:  # 空列表 = 全部
                return None
            allowed.update(paths)
        return list(allowed)

    @staticmethod
    def _path_matches(full_path, prefix):
        """判断路径是否命中前缀（前缀如 "dev/" 或 "dev/backend"），按路径段精确匹配"""
        pc = prefix.rstrip('/')
        return full_path == pc or full_path.startswith(pc + '/')

    @staticmethod
    def _jenkins_path(full_path):
        """把展示用的 full_path（如 'dev/中心/backend'）转成 Jenkins URL 路径（'dev/job/中心/job/backend'）

        Jenkins 嵌套 folder 的 API 路径是 /job/父/job/子/...，每层都要用 /job/ 分隔，
        而不是直接 / 拼接。
        """
        parts = str(full_path).split('/')
        if any(part in ('', '.', '..') or '\\' in part for part in parts):
            raise ValueError('Job 路径包含非法路径段')
        return '/job/'.join(parts)

    def _check_job_allowed(self, request, source, job):
        """校验用户是否有权操作某 job（供 build/job_status/console 复用）"""
        try:
            self._jenkins_path(job)
        except ValueError:
            return False
        allowed = self._get_allowed_paths(request, source)
        if allowed is None:
            return True
        if not allowed:
            return False
        return any(self._path_matches(str(job), p) for p in allowed)

    def _fetch_jobs_tree(self, source, path='', depth=0, max_depth=12, allowed=None):
        """递归爬取顶层 jobs，返回扁平列表（含 folder + job，带 full_path/depth/is_folder）"""
        tree = 'jobs[name,url,color,description,_class]'
        if path:
            url_path = f'/job/{quote(self._jenkins_path(path), safe="/")}/api/json'
        else:
            url_path = '/api/json'
        code, body, _ = self._request(source, url_path, method='GET', params={'tree': tree}, timeout=60)
        if code != 200:
            return []
        items = (body or {}).get('jobs', []) if isinstance(body, dict) else []
        result = []
        for j in items:
            jname = j.get('name', '')
            full_path = f"{path}/{jname}" if path else jname
            jclass = j.get('_class', '') or ''
            is_folder = 'Folder' in jclass or not j.get('color')
            node = {
                'full_path': full_path, 'name': jname, 'is_folder': is_folder,
                'color': j.get('color'), 'description': j.get('description'),
                'url': j.get('url'), 'depth': depth,
            }
            if is_folder:
                if allowed is None:
                    drill = True
                else:
                    # folder 下钻：folder 命中某前缀，或某前缀落在 folder 之内
                    drill = any(
                        self._path_matches(full_path, p) or self._path_matches(p, full_path)
                        for p in allowed
                    )
                if drill and depth < max_depth:
                    sub = self._fetch_jobs_tree(source, full_path, depth + 1, max_depth, allowed)
                    result.append(node)      # folder 行总是显示（即使为空）
                    result.extend(sub)
                elif allowed is None:
                    result.append(node)
            else:
                if allowed is None or any(self._path_matches(full_path, p) for p in allowed):
                    result.append(node)
        return result

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
        if not self._check_job_allowed(request, source, job):
            return ErrorResponse(msg="无权限操作该 Job")
        job_path = quote(self._jenkins_path(job), safe='/')

        # 1. 尝试拿 crumb（Jenkins 开启 CSRF 时必需）
        crumb = self._get_crumb(source)
        headers = {}
        if crumb:
            headers[crumb[0]] = crumb[1]

        # 2. 选择触发端点：显式带参数走 buildWithParameters；无参数先试 /build，
        #    参数化 job（含 Jenkinsfile 定义参数）走 /build 会 400 "Nothing is submitted"，
        #    此时降级改用 buildWithParameters（使用默认参数值）
        endpoint = 'buildWithParameters' if parameters else 'build'

        def _post(ep):
            return self._request(source, f'/job/{job_path}/{ep}', method='POST',
                                 data=parameters or None, timeout=60, headers=headers)

        # 3. 触发构建
        try:
            code, body, resp = _post(endpoint)
        except Exception as e:
            return ErrorResponse(msg=str(e))

        # 参数化 job 走了 /build → 400，降级重试 buildWithParameters
        if code == 400 and endpoint == 'build':
            try:
                code, body, resp = _post('buildWithParameters')
            except Exception as e:
                return ErrorResponse(msg=str(e))

        if code in (200, 201):
            queue_url = resp.headers.get('Location', '')
            return DetailResponse(data={'status': 'ok', 'job': job, 'queue_url': queue_url},
                                  msg=f"已触发构建：{job}")
        # Refresh crumb in the same session so the cookie and crumb stay paired.
        if code == 403 and crumb:
            headers.clear()
            refreshed = self._get_crumb(source)
            if refreshed:
                headers[refreshed[0]] = refreshed[1]
            try:
                code, body, resp = _post(endpoint)
            except Exception as e:
                return ErrorResponse(msg=str(e))
            if code in (200, 201):
                return DetailResponse(data={'status': 'ok', 'job': job}, msg=f"已触发构建：{job}")
        return ErrorResponse(msg=f"触发构建失败 HTTP {code}：{str(body)[:300]}")

    # ------------------------------------------------------------
    # 参数化构建：取参数定义 + 候选值（前端弹窗的数据源）
    #
    # 刻意用 ``IsAuthenticated`` + 内部自行校验，**不走** ``CustomPermission``：
    # 本 action 的路径没有登记 MenuButton，而 ``CustomPermission`` 是**带 ``$``
    # 的精确匹配**（``ValidationApi`` 才是不带 ``$`` 的前缀匹配），未登记的路径
    # 对非超管一律拒绝。这里真正要判的是"这个人能不能构建这个 Job"，
    # 所以复用目录授权 ``_check_job_allowed`` + 按钮 ``jenkinsJob:Build``。
    # ------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='job_params',
            permission_classes=[IsAuthenticated])
    def job_params(self, request, pk=None):
        """取 Job 的参数定义与候选值。

        参数 ``job``（full_path）必填，``refresh=1`` 可跳过缓存。
        返回值里的 ``source`` 标注每个参数候选值的来路（便于排查）：
        ``json_api`` / ``config_static`` / ``cascade_static`` / ``build_history``。
        """
        source = self._get_source()
        job = request.query_params.get('job', '')
        if not job:
            return ErrorResponse(msg="缺少 job 参数")
        if not self._check_job_allowed(request, source, job):
            return ErrorResponse(msg="无权限操作该 Job")
        if not getattr(request.user, 'is_superuser', False):
            try:
                from dvadmin.utils.perm_helper import has_button
            except Exception:
                # 与 bastion/access.py、本文件 JenkinsGrantAdminPermission 一致：取不到
                # 判定依据就拒绝，不默认放行。
                return ErrorResponse(msg="无权限查看构建参数")
            if not has_button(request.user, 'jenkinsJob:Build', 'jenkinsJob:Params'):
                return ErrorResponse(msg="无权限查看构建参数")

        force = str(request.query_params.get('refresh', '')).lower() in ('1', 'true', 'yes')
        key = (source.pk, job)
        hit = _PARAM_CACHE.get(key)
        if not force and hit and time.time() - hit[0] < PARAM_CACHE_TTL:
            return DetailResponse(data=hit[1], msg="获取成功")
        try:
            data = self._build_job_params(source, job)
        except Exception as e:
            return ErrorResponse(msg=str(e))
        _PARAM_CACHE[key] = (time.time(), data)
        return DetailResponse(data=data, msg="获取成功")

    def _build_job_params(self, source, job):
        """组装一个 Job 的参数定义与候选值

        按需请求 Jenkins，最多三次（都是只读）：
          ① 参数定义（总是）
          ② config.xml（仅当存在 Active Choices 参数）
          ③ 构建历史（仅当仍有参数拿不到候选值）
        """
        job_path = quote(self._jenkins_path(job), safe='/')
        code, body, _ = self._request(
            source, f'/job/{job_path}/api/json', method='GET',
            params={'tree': PARAM_TREE}, timeout=30)
        if code != 200 or not isinstance(body, dict):
            raise RuntimeError('获取参数定义失败：Jenkins 返回 HTTP %s' % code)

        defs = []
        for prop in (body.get('property') or []):
            if isinstance(prop, dict) and isinstance(prop.get('parameterDefinitions'), list):
                defs.extend(prop['parameterDefinitions'])

        params = []
        for d in defs:
            if not isinstance(d, dict) or not d.get('name'):
                continue
            cls = str(d.get('_class') or d.get('type') or '').split('.')[-1]
            raw_default = (d.get('defaultParameterValue') or {}).get('value')
            default = '' if raw_default is None else (
                raw_default if isinstance(raw_default, str)
                else json.dumps(raw_default, ensure_ascii=False))
            choices = [c for c in (d.get('choices') or []) if isinstance(c, str)]
            params.append({
                'name': d.get('name'),
                'type': _CLASS_TO_TYPE.get(cls, 'string'),
                'jenkins_type': cls,
                'description': d.get('description') or '',
                'default': default,
                'choices': choices,
                'source': 'json_api' if choices else 'unknown',
                'multiple': False,
                'degraded': False,
            })

        # ② Active Choices：候选值写在参数脚本里，只能解析 config.xml
        if any(p['jenkins_type'] in _UNOCHOICE_CLASSES for p in params):
            code, xml, resp = self._request(
                source, f'/job/{job_path}/config.xml', method='GET', timeout=30)
            # 固定按 UTF-8 解码字节，不用 resp.text。
            # 实测 config.xml 的 Content-Type 是 `application/xml`（**不带 charset**），
            # 此时 requests 会走字符集自动探测——内容里中英混排时探测有可能猜错（乱码），
            # 而且它是"逐响应"的，等于给每个 Job 埋一颗随机雷。这里直接指定编码，
            # Jenkins 的 config.xml 声明就是 UTF-8，确定性的。
            xml_text = None
            if code == 200:
                raw = getattr(resp, 'content', None)
                if isinstance(raw, bytes):
                    xml_text = raw.decode('utf-8', 'replace')
                elif isinstance(xml, str):
                    xml_text = xml
            sub = parse_config_params(xml_text) if xml_text is not None else {}
            for p in params:
                info = sub.get(p['name'])
                if not info:
                    continue
                p['type'] = info['ui_type']
                p['multiple'] = info['multiple']
                if info['referenced']:
                    # 级联参数：候选值随被引用参数变化，前端本地重算
                    p['cascade_on'] = info['referenced']
                    p['cascade_rules'] = info['cascade_rules']
                    p['cascade_else'] = info['cascade_else']
                    p['fallback_choices'] = info['fallback_choices']
                    p['choices'] = info['fallback_choices']
                    p['source'] = 'cascade_static' if info['cascade_rules'] else 'unknown'
                elif info['choices']:
                    p['choices'] = info['choices']
                    p['source'] = 'config_static'

        # ③ 仍然没有候选值（脚本实时查 GitLab 分支之类）→ 用构建历史里用过的值
        need = [p for p in params
                if p['type'] in _UI_WITH_CHOICES and not p['choices']]
        if need:
            code, hist_body, _ = self._request(
                source, f'/job/{job_path}/api/json', method='GET',
                params={'tree': 'builds[number,result,timestamp,'
                                'actions[parameters[name,value]]]{0,30}'},
                timeout=40)
            hist = (extract_history_values(hist_body.get('builds'))
                    if code == 200 and isinstance(hist_body, dict) else {})

            def _vals_of(p):
                vals = hist.get(p['name']) or []
                if p['multiple']:
                    # 多选参数在构建记录里是逗号拼接的，拆开再合并
                    vals = [v for raw in vals for v in str(raw).split(',') if v.strip()]
                return list(dict.fromkeys(vals))

            for p in need:
                vals = _vals_of(p)
                if vals:
                    p['recent'] = vals[:10]
                    p['choices'] = vals
                    p['source'] = 'build_history'
                # 允许自由输入：候选值只是"最近用过的"，可能要填新分支
                p['allow_create'] = True
                if not p['choices']:
                    p['degraded'] = True

            # 纯文本参数（TAG / 版本号这类）顺手带上历史值，前端只拿来当
            # 「上次填了 xxx」的提示，**不改控件类型、不动 source** —— 否则会
            # 给一个没有候选列表的文本框挂上"最近用过"的角标，名不副实。
            # 历史已经拿到了，这里不再多发请求。
            for p in params:
                if p['type'] in ('text', 'string'):
                    vals = _vals_of(p)
                    if vals:
                        p['recent'] = vals[:10]

        return {
            'job': job,
            'has_params': bool(params),
            'params': params,
        }

    def finalize_response(self, request, response, *args, **kwargs):
        if hasattr(self, '_jenkins_session'):
            self._jenkins_session.close()
        return super().finalize_response(request, response, *args, **kwargs)

    # ------------------------------------------------------------
    # 最近构建状态
    # ------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='job_status')
    def job_status(self, request, pk=None):
        source = self._get_source()
        job = request.query_params.get('job', '')
        if not job:
            return ErrorResponse(msg="缺少 job 参数")
        if not self._check_job_allowed(request, source, job):
            return ErrorResponse(msg="无权限操作该 Job")
        job_path = quote(self._jenkins_path(job), safe='/')
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
        if not self._check_job_allowed(request, source, job):
            return ErrorResponse(msg="无权限操作该 Job")
        job_path = quote(self._jenkins_path(job), safe='/')
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
        """下拉选项：返回启用的 Jenkins 服务器。

        刻意**不**调用 ``self.filter_queryset()``：``/api/jenkins/server/all/`` 虽然
        登记了 ``jenkinsJob:ServerList`` 按钮，但一旦有人把它的 ``data_range`` 改回小值，
        下拉就会莫名其妙变空。服务器列表属辅助数据，可见性由
        ``_get_allowed_paths``（按角色目录授权）在 ``jobs`` 里体现。
        """
        data = JenkinsServer.objects.filter(status=1).order_by('sort').values('id', 'name', 'url')
        return DetailResponse(data=list(data), msg="获取成功")

    # ------------------------------------------------------------
    # 角色可见目录授权（JenkinsRolePermission）
    #
    # 语义回顾（见 models.JenkinsRolePermission）：
    #   无记录            → 默认拒绝（看不到任何 Job）
    #   allowed_paths=[]  → 全部可见
    #   allowed_paths=[…] → 只可见这些前缀开头的 Job/folder，下层自动可见
    # ------------------------------------------------------------
    @staticmethod
    def _norm_path(raw):
        """把用户/前端传来的目录前缀规范化为 ``"dev/"`` 这种形式。"""
        return norm_grant_path(raw)

    @action(methods=['GET'], detail=True, url_path='role_permissions',
            permission_classes=[JenkinsGrantAdminPermission])
    def role_permissions(self, request, pk=None):
        """某台 Jenkins 服务器上「角色 × 可见目录」的当前配置。

        返回**全部启用角色**（含未配置的），前端据此直接渲染一张勾选表——
        只返回已配置的记录会导致前端没地方勾"新开一个角色"。

        ``configured=False`` → 无记录 → 默认拒绝；``allow_all=True`` → 全部可见。
        """
        server = self._get_server_raw(pk)
        if server is None:
            return ErrorResponse(msg='Jenkins 服务器不存在')

        from dvadmin.system.models import Role

        cur = {p.role_id: p for p in JenkinsRolePermission.objects.filter(server=server)}
        roles = []
        for role in Role.objects.filter(status=1).order_by('id'):
            perm = cur.get(role.id)
            paths = list(perm.allowed_paths or []) if perm is not None else []
            roles.append({
                'role': role.id,
                'role_name': role.name,
                'role_key': role.key,
                'configured': perm is not None,
                'allow_all': bool(perm is not None and not paths),
                'allowed_paths': paths,
            })
        # 候选目录 = 该台 Jenkins 的真实顶层目录/Job（实时拉取，带缓存）
        top, options, err = folder_options_for(server)
        if err:
            # 拉不到就退化为「已授权目录的并集」：至少让管理员看见现有配置，
            # 而不是回退到写死的 dev/test/pre/prod。
            top = granted_union([r['allowed_paths'] for r in roles])
            options = fallback_options(top)
        return DetailResponse(
            data={
                'server_id': server.pk,
                'roles': roles,
                'folders': top,
                'folder_options': options,
                'folders_error': err,
            },
            msg='获取成功',
        )

    @action(methods=['POST'], detail=True, url_path='set_role_permissions',
            permission_classes=[JenkinsGrantAdminPermission])
    @transaction.atomic
    def set_role_permissions(self, request, pk=None):
        """整体覆盖某台服务器的角色目录授权。

        请求体::

            {"perms": [
                {"role": 4, "allow_all": true},
                {"role": 6, "allowed_paths": ["dev/", "test/"]},
                {"role": 7, "allowed_paths": ["test/"]}
            ]}

        - ``allow_all: true``            → 写一条 ``allowed_paths=[]``（全部可见）
        - ``allowed_paths: []``（且非 allow_all）→ **删除**该角色记录（默认拒绝）
        - **未出现在 ``perms`` 里的角色 → 一并删除**（整体覆盖语义）

        整体覆盖而非逐条增删：前端是"勾完一次保存"的交互，逐条 diff 需要前端自己
        算差异，任一步失败都会留下半套授权。这里在事务里一次性重建。
        """
        server = self._get_server_raw(pk)
        if server is None:
            return ErrorResponse(msg='Jenkins 服务器不存在')

        raw = request.data.get('perms')
        if raw is None:
            return ErrorResponse(msg='缺少 perms 字段（传空数组表示收回全部授权）')
        if not isinstance(raw, list):
            return ErrorResponse(msg='perms 必须是数组')

        from dvadmin.system.models import Role

        rows, seen = [], set()
        for i, item in enumerate(raw):
            idx = i + 1
            if not isinstance(item, dict):
                return ErrorResponse(msg='第 %d 项格式错误：应为对象' % idx)
            try:
                role_id = int(item.get('role'))
            except (TypeError, ValueError):
                return ErrorResponse(msg='第 %d 项缺少合法的 role' % idx)
            if not Role.objects.filter(pk=role_id).exists():
                return ErrorResponse(msg='第 %d 项角色不存在：%s' % (idx, role_id))
            if role_id in seen:
                continue
            seen.add(role_id)

            if item.get('allow_all'):
                paths = []                       # 空列表 = 全部可见
            else:
                paths = item.get('allowed_paths') or []
                if not isinstance(paths, list):
                    return ErrorResponse(msg='第 %d 项 allowed_paths 必须是数组' % idx)
                try:
                    paths = [p for p in dict.fromkeys(self._norm_path(x) for x in paths) if p]
                except ValueError as e:
                    return ErrorResponse(msg='第 %d 项 %s' % (idx, e))
                # 关键：``allowed_paths=[]`` 在模型里表示"全部可见"。若前端想表达
                # "这个角色不给权限"，传的也是空数组——必须在这里**跳过**（= 不建记录 =
                # 默认拒绝），否则会把"取消授权"写成"授权全部"，是最危险的误授。
                if not paths:
                    continue

            rows.append({'server_id': server.pk, 'role_id': role_id,
                         'allowed_paths': paths})

        JenkinsRolePermission.objects.filter(server=server).delete()
        if rows:
            JenkinsRolePermission.objects.bulk_create(
                [JenkinsRolePermission(**r) for r in rows])

        saved = JenkinsRolePermission.objects.select_related('role').filter(server=server)
        return DetailResponse(
            data={'server_id': server.pk, 'count': len(rows), 'roles': [
                {'role': p.role_id, 'role_name': p.role.name,
                 'allow_all': not (p.allowed_paths or []),
                 'allowed_paths': list(p.allowed_paths or [])}
                for p in saved
            ]},
            msg='授权已保存（%d 个角色；未列出的角色一律不可见）' % len(rows),
        )


class JenkinsRoleGrantViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """「角色管理」页里的 Jenkins 目录授权面板（**角色视角**）。

    与 :class:`JenkinsServerViewSet` 的 ``role_permissions`` / ``set_role_permissions``
    （服务器视角：一台服务器 × 所有角色）互补——本接口是"一个角色 × 所有服务器"，
    正好对应角色管理页里点开某个角色后要看到的那张表。

    路径 ``/api/jenkins/role_grant/`` 刻意与 ``/api/jenkins/server/`` 分开：
    ``/api/jenkins/server/`` 前缀上的 ``jenkinsServer:Search``（bid=152）是连
    开发 / 测试都有的按钮，挂在那下面会让普通开发也能读到全公司的目录授权表。
    本 ViewSet 只暴露 ``list`` + ``set``，权限一律由 ``JenkinsGrantAdminPermission`` 把守。
    """

    queryset = JenkinsServer.objects.all()
    permission_classes = [IsAuthenticated, JenkinsGrantAdminPermission]

    @staticmethod
    def _role_of(request):
        from dvadmin.system.models import Role

        try:
            role_id = int(request.query_params.get('role_id') or (request.data or {}).get('role_id'))
        except (TypeError, ValueError):
            return None
        return Role.objects.filter(pk=role_id).first()

    def list(self, request, *args, **kwargs):
        """某角色在所有 Jenkins 服务器上的目录授权。"""
        from dvadmin.system.models import Role

        role = self._role_of(request)
        if role is None:
            try:
                rid = int(request.query_params.get('role_id'))
            except (TypeError, ValueError):
                return ErrorResponse(msg='缺少合法的 role_id')
            if not Role.objects.filter(pk=rid).exists():
                return ErrorResponse(msg='角色不存在：%s' % rid)
            return ErrorResponse(msg='缺少合法的 role_id')

        cur = {p.server_id: p for p in JenkinsRolePermission.objects.filter(role_id=role.pk)}
        srvs = list(JenkinsServer.objects.all().order_by('sort', 'id'))
        # 每台 Jenkins 的目录结构可能不同（尤其存在多台时），所以候选目录**逐台**取；
        # 并发拉取，避免串行等待把前端 5s 超时耗光。
        folder_map = folder_options_many(srvs)
        servers = []
        all_top = []
        for srv in srvs:
            perm = cur.get(srv.pk)
            paths = list(perm.allowed_paths or []) if perm is not None else []
            top, options, err = folder_map.get(srv.pk, ([], [], ''))
            if err:
                top = granted_union([paths])
                options = fallback_options(top)
            for t in top:
                if t not in all_top:
                    all_top.append(t)
            servers.append({
                'server': srv.pk,
                'server_name': srv.name,
                'url': srv.url,
                'status': srv.status,
                'configured': perm is not None,
                'allow_all': bool(perm is not None and not paths),
                'allowed_paths': paths,
                # 逐台候选（前端每个下拉用自己的那一份）
                'folders': top,
                'folder_options': options,
                'folders_error': err,
            })
        return DetailResponse(
            data={
                'role_id': role.pk,
                'role_name': role.name,
                'servers': servers,
                'folders': sorted(all_top),
                'folder_options': fallback_options(sorted(all_top)),
            },
            msg='获取成功',
        )

    @action(methods=['POST'], detail=False, url_path='set')
    @transaction.atomic
    def set_grants(self, request, *args, **kwargs):
        """整体覆盖某角色在所有 Jenkins 服务器上的目录授权。

        请求体::

            {"role_id": 6, "perms": [
                {"server": 2, "allow_all": false, "allowed_paths": ["dev/"]}
            ]}

        **只处理``perms``里出现的服务器**（未出现的服务器保持原样）——角色管理页的
        交互是"改哪台保存哪台"，与服务器页的"整台覆盖"语义不同，不能误删别的服务器授权。
        某台服务器传 ``allowed_paths: []`` 且非 ``allow_all`` → 收回该服务器的授权。
        """
        role = self._role_of(request)
        if role is None:
            return ErrorResponse(msg='缺少合法的 role_id')

        perms = request.data.get('perms')
        if perms is None:
            return ErrorResponse(msg='缺少 perms 字段（传空数组表示不做修改）')
        if not isinstance(perms, list):
            return ErrorResponse(msg='perms 必须是数组')

        rows, err = _apply_grant_input(perms, JenkinsServer.objects.all(), role.pk,
                                       role_label='角色')
        if err:
            return ErrorResponse(msg=err)

        # 本次提交里出现过的服务器（含被"收回授权"而没进 rows 的），只动这些
        submitted = set()
        for item in perms:
            if not isinstance(item, dict):
                continue
            try:
                submitted.add(int(item.get('server')))
            except (TypeError, ValueError):
                continue

        if submitted:
            JenkinsRolePermission.objects.filter(
                role_id=role.pk, server_id__in=submitted).delete()
        if rows:
            JenkinsRolePermission.objects.bulk_create(
                [JenkinsRolePermission(**r) for r in rows])

        # 缓存里存的是**全量树**、过滤发生在每次请求上，所以授权变更本就即时生效；
        # 清一次只是让下次请求顺便拿到最新的目录结构（folder 候选清单同理）。
        _TREE_CACHE.clear()
        _FOLDER_CACHE.clear()

        saved = JenkinsRolePermission.objects.select_related('server').filter(role_id=role.pk)
        return DetailResponse(
            data={
                'role_id': role.pk,
                'count': len(rows),
                'servers': [
                    {'server': p.server_id, 'server_name': p.server.name,
                     'allow_all': not (p.allowed_paths or []),
                     'allowed_paths': list(p.allowed_paths or [])}
                    for p in saved
                ],
            },
            msg='授权已保存（%d 台服务器；未列出的服务器不可见）' % len(rows),
        )
