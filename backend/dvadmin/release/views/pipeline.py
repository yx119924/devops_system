# -*- coding: utf-8 -*-
"""发布流水线 ViewSet。

端点清单（★ **每一个 @action 都要在 `backend/register_release.py` 里逐条登记
MenuButton** —— 后端 `CustomPermission` 是按 (api 模板, method 下标) 逐条匹配
`RoleMenuButtonPermission` 的，漏一条那条接口对非超管就恒返回业务码 4000）：

=========================================================  ================================================
``GET/POST/PUT/DELETE /api/release/pipeline/``              流水线 CRUD
``GET    /api/release/pipeline/all/``                       下拉
``GET    /api/release/pipeline/options/``                   页面下拉（凭据 / Jenkins / 节点类型 / 渠道）
``GET    /api/release/pipeline/{id}/nodes/``                读取编排
``POST   /api/release/pipeline/{id}/nodes/``                保存编排（整体替换 + 重排序号）
``POST   /api/release/pipeline/{id}/run/``                  发起一次执行
``POST   /api/release/node/preview/``                       节点预检（**不真执行**）
``GET    /api/release/run/``                                执行历史
``GET    /api/release/run/{id}/``                           执行详情（含各节点）
``POST   /api/release/run/{id}/advance/``                   推进一个节点
``POST   /api/release/run/{id}/abort/``                     中止
``POST   /api/release/run/{id}/retry/``                     重跑失败节点
=========================================================  ================================================

权限三层（与命令下发 / 日志采集同构）
-------------------------------------
1. 接口层：`CustomPermission` 按按钮权限控制
2. 目标层：**创建执行时**逐节点逐目标 `require_access(user, server, credential, 'dispatch')`
   —— 这是真正的关卡，前端下拉被绕过（手工构造 targets）也拦得住
3. 可见层：`get_queryset` —— 资产运营者看全部，其余人只看自己建的

★ 目标 IP 一律从 CMDB 重新读取，**不信任请求里带的 ip**
（照抄 `bastion/views/dispatch.py`，防止"凭据被发到前端指定的 IP"）。
"""
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from dvadmin.bastion.access import is_asset_admin, visible_credential_queryset
from dvadmin.cmdb.models import Server
from dvadmin.release import engine
from dvadmin.release.models import (
    MAX_BUILD_WAIT, MAX_NODE_TIMEOUT, MAX_TARGETS_PER_NODE, NODE_TYPE_CHOICES,
    ON_FAILURE_CHOICES, Pipeline, PipelineNode, PipelineNodeRun, PipelineRun,
    RUN_FINAL_STATUS,
)
from dvadmin.utils.json_response import DetailResponse, ErrorResponse, SuccessResponse
from dvadmin.utils.permission import CustomPermission
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet

# 通知节点可选的触发条件
NOTIFY_ON_CHOICES = (
    ("always", "总是通知"),
    ("success", "仅成功时"),
    ("failure", "仅失败时"),
)


# ===========================================================================
# 节点配置校验（**在保存时就拦住**，不要等执行到那一步才炸）
# ===========================================================================
def _detail_text(exc, field):
    """从 `ValidationError` 里取出人话。

    ★ DRF 的 `_get_error_details()` 对**字符串值**返回单个 `ErrorDetail`、
      对列表返回列表，两种都可能出现 —— 这里统一成字符串，
      否则前端会拿到一个 list（或更糟：见 `utils/exception.py` 里那段注释）。
    """
    detail = getattr(exc, 'detail', exc)
    value = detail.get(field) if isinstance(detail, dict) else detail
    if isinstance(value, (list, tuple)):
        return '；'.join(str(x) for x in value)
    return str(value)


def validate_node_config(node_type, config, label='节点'):
    """按节点类型做**结构**校验。返回归一后的 config。

    ★ 这里刻意**不做资产授权判定**（那件事在「发起执行」时统一做）。
      原因：编排保存时流水线的默认凭据可能还没选，此时判权会报「必须选择凭据」，
      用户会觉得莫名其妙。授权关卡放在按下"执行"的那一刻才合理。
    """
    if not isinstance(config, dict):
        raise ValidationError({'config': '%s 的配置必须是 JSON 对象' % label})

    def _targets(cfg):
        raw = cfg.get('targets')
        if raw in (None, ''):
            raw = []
        if not isinstance(raw, list):
            raise ValidationError({'config': '%s 的目标格式错误' % label})
        ids = []
        for item in raw:
            if not isinstance(item, dict):
                raise ValidationError({'config': '%s 的目标格式错误' % label})
            try:
                ids.append(int(item.get('server_id')))
            except (TypeError, ValueError):
                raise ValidationError({'config': '%s 的目标必须来自 CMDB' % label})
        if not ids:
            raise ValidationError({'config': '%s 还没有选择目标服务器' % label})
        if len(ids) > MAX_TARGETS_PER_NODE:
            raise ValidationError({'config': '%s 的目标过多（%d 台，上限 %d 台）'
                                   % (label, len(ids), MAX_TARGETS_PER_NODE)})
        # 去重后回写，避免同一台机器被发布两遍
        seen, out = set(), []
        for item in raw:
            sid = int(item.get('server_id'))
            if sid in seen:
                continue
            seen.add(sid)
            server = Server.objects.filter(pk=sid).first()
            if server is None:
                raise ValidationError({'config': '%s 的目标服务器（id=%s）在 CMDB 里不存在' % (label, sid)})
            out.append({'server_id': server.pk, 'label': server.hostname,
                        'ip': server.ip, 'ssh_port': server.ssh_port or 22})
        return out

    def _command(cfg, need_targets=True):
        cmd = str(cfg.get('command') or '').strip()
        if not cmd:
            raise ValidationError({'config': '%s 没有填写要执行的命令' % label})
        if len(cmd) > 16384:
            raise ValidationError({'config': '%s 的命令过长（上限 16384 字符）' % label})
        try:
            timeout = int(cfg.get('timeout') or 30)
        except (TypeError, ValueError):
            raise ValidationError({'config': '%s 的超时必须是整数秒' % label})
        if not 1 <= timeout <= MAX_NODE_TIMEOUT:
            raise ValidationError({'config': '%s 的超时必须介于 1–%d 秒' % (label, MAX_NODE_TIMEOUT)})
        out = {'command': cmd, 'timeout': timeout}
        if need_targets:
            out['targets'] = _targets(cfg)
        for key in ('credential', 'credential_id'):
            if cfg.get(key):
                try:
                    out['credential'] = int(cfg.get(key))
                except (TypeError, ValueError):
                    raise ValidationError({'config': '%s 的凭据取值非法' % label})
        return out

    if node_type in ('command', 'check'):
        return _command(config)
    if node_type == 'upload':
        cfg = _command({'command': 'x', 'timeout': config.get('timeout'),
                        'targets': config.get('targets'),
                        'credential': config.get('credential') or config.get('credential_id')},
                       need_targets=True)
        local = str(config.get('local_path') or '').strip()
        remote = str(config.get('remote_path') or '').strip()
        if not local:
            raise ValidationError({'config': '%s 没有填写制品文件路径' % label})
        if not remote:
            raise ValidationError({'config': '%s 没有填写目标机存放路径' % label})
        if not (remote.startswith('/') or remote.startswith('{{')):
            # ★ 允许以参数占位符开头（如 `{{dir}}/app.jar`）：保存时还没有本次执行的参数值，
            #   平台拼不出最终路径，拿"必须以 / 开头"去卡会给出一个莫名其妙、且无法满足的报错。
            #   真正的把关在 `engine._exec_upload` —— 那里是**渲染之后**判绝对路径，口径更严。
            raise ValidationError({'config': '%s 的目标机路径必须是绝对路径（如 /opt/app/app.jar），'
                                             '或以参数占位符开头（如 {{dir}}/app.jar）' % label})
        cfg.pop('command', None)
        cfg.pop('timeout', None)
        cfg['local_path'] = local
        cfg['remote_path'] = remote
        return cfg
    if node_type == 'build':
        sid = config.get('jenkins_server_id')
        if not sid:
            raise ValidationError({'config': '%s 没有选择 Jenkins 服务器' % label})
        job = str(config.get('job') or '').strip()
        if not job:
            raise ValidationError({'config': '%s 没有选择要构建的 Job' % label})
        params = config.get('parameters') or {}
        if not isinstance(params, dict):
            raise ValidationError({'config': '%s 的构建参数必须是 JSON 对象' % label})
        try:
            wait = int(config.get('wait_timeout') or MAX_BUILD_WAIT)
        except (TypeError, ValueError):
            raise ValidationError({'config': '%s 的等待时长必须是整数秒' % label})
        return {
            'jenkins_server_id': int(sid),
            'job': job,
            'parameters': {str(k): '' if v is None else str(v) for k, v in params.items()},
            'wait_timeout': max(30, min(wait, MAX_BUILD_WAIT)),
        }
    if node_type == 'notify':
        cid = config.get('channel_id')
        if not cid:
            raise ValidationError({'config': '%s 没有选择通知渠道' % label})
        on = str(config.get('on') or 'always')
        if on not in [c[0] for c in NOTIFY_ON_CHOICES]:
            raise ValidationError({'config': '%s 的通知条件非法（应为 always/success/failure）' % label})
        return {
            'channel_id': int(cid),
            'on': on,
            'title': str(config.get('title') or '')[:128],
            'content': str(config.get('content') or '')[:4000],
        }
    if node_type == 'param':
        return {}
    raise ValidationError({'node_type': '未知的节点类型：%s' % node_type})


# ===========================================================================
# 序列化器
# ===========================================================================
class PipelineNodeSerializer(CustomModelSerializer):
    node_type_label = serializers.SerializerMethodField()
    on_failure_label = serializers.SerializerMethodField()
    target_count = serializers.SerializerMethodField()

    def get_node_type_label(self, obj):
        return dict(NODE_TYPE_CHOICES).get(obj.node_type, obj.node_type)

    def get_on_failure_label(self, obj):
        return dict(ON_FAILURE_CHOICES).get(obj.on_failure, obj.on_failure)

    def get_target_count(self, obj):
        return len(obj.target_list())

    class Meta:
        model = PipelineNode
        fields = '__all__'
        read_only_fields = ['id', 'pipeline', 'creator']


class PipelineSerializer(CustomModelSerializer):
    status_label = serializers.SerializerMethodField()
    credential_name = serializers.CharField(source='credential.name', read_only=True, default=None)
    node_count = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()

    def get_status_label(self, obj):
        return dict(Pipeline._meta.get_field('status').choices).get(obj.status, obj.status)

    def get_node_count(self, obj):
        return obj.nodes.count()

    def get_creator_name(self, obj):
        try:
            return obj.creator.name or obj.creator.username
        except Exception:                                          # noqa: BLE001
            return None

    def validate(self, attrs):
        instance = self.instance

        def _pick(key):
            if key in attrs:
                return attrs.get(key)
            return getattr(instance, key, None) if instance is not None else None

        params = _pick('params')
        if params in (None, ''):
            params = []
        if not isinstance(params, list):
            raise serializers.ValidationError({'params': '运行时参数必须是 JSON 数组'})
        normalized, seen = [], set()
        for item in params:
            if not isinstance(item, dict):
                raise serializers.ValidationError({'params': '每个参数必须是 JSON 对象'})
            key = str(item.get('key') or '').strip()
            if not key:
                raise serializers.ValidationError({'params': '参数名不能为空'})
            if not key.replace('_', '').isalnum():
                raise serializers.ValidationError(
                    {'params': '参数名「%s」只允许字母、数字、下划线（它会被用进 {{%s}} 占位符）' % (key, key)})
            if key in seen:
                raise serializers.ValidationError({'params': '参数名「%s」重复' % key})
            seen.add(key)
            normalized.append({
                'key': key,
                'label': str(item.get('label') or key)[:64],
                'default': '' if item.get('default') is None else str(item.get('default'))[:512],
                'required': bool(item.get('required')),
            })
        attrs['params'] = normalized
        return super().validate(attrs)

    class Meta:
        model = Pipeline
        fields = '__all__'
        read_only_fields = ['id', 'creator']


class PipelineNodeRunSerializer(CustomModelSerializer):
    node_type_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    def get_node_type_label(self, obj):
        return dict(NODE_TYPE_CHOICES).get(obj.node_type, obj.node_type)

    def get_status_label(self, obj):
        return dict(PipelineNodeRun._meta.get_field('status').choices).get(obj.status, obj.status)

    class Meta:
        model = PipelineNodeRun
        fields = '__all__'
        read_only_fields = ['id']


class PipelineRunListSerializer(CustomModelSerializer):
    """列表用：**不带** node_runs。

    ★ 列表页把每条执行的节点明细也序列化出来，一页 20 条 × 每条最多 100 个节点
      就是 2000 个对象，纯属白扛。明细走详情接口（`retrieve`）那一次拿。
    """
    status_label = serializers.SerializerMethodField()
    trigger_type_label = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()

    def get_status_label(self, obj):
        return dict(PipelineRun._meta.get_field('status').choices).get(obj.status, obj.status)

    def get_trigger_type_label(self, obj):
        return dict(PipelineRun._meta.get_field('trigger_type').choices).get(obj.trigger_type, obj.trigger_type)

    def get_creator_name(self, obj):
        try:
            return obj.creator.name or obj.creator.username
        except Exception:                                          # noqa: BLE001
            return None

    class Meta:
        model = PipelineRun
        fields = '__all__'
        read_only_fields = ['id', 'creator']


class PipelineRunSerializer(CustomModelSerializer):
    status_label = serializers.SerializerMethodField()
    trigger_type_label = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    node_runs = PipelineNodeRunSerializer(many=True, read_only=True)

    def get_status_label(self, obj):
        return dict(PipelineRun._meta.get_field('status').choices).get(obj.status, obj.status)

    def get_trigger_type_label(self, obj):
        return dict(PipelineRun._meta.get_field('trigger_type').choices).get(obj.trigger_type, obj.trigger_type)

    def get_creator_name(self, obj):
        try:
            return obj.creator.name or obj.creator.username
        except Exception:                                          # noqa: BLE001
            return None

    class Meta:
        model = PipelineRun
        fields = '__all__'
        read_only_fields = ['id', 'creator']


# ===========================================================================
# 流水线
# ===========================================================================
class PipelineViewSet(CustomModelViewSet):
    queryset = Pipeline.objects.all().order_by('-create_datetime')
    serializer_class = PipelineSerializer
    search_fields = ['name']
    filter_fields = ['status']
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']
    # ★ 可见性**只由 `get_queryset` 决定**。必须关掉 DVAdmin 的部门数据权限
    #   `DataLevelPermissionMargeFilter`：它对「没有 dept_id 的用户」会 `none()`，
    #   把用户**自己建的**流水线也一并掏空（表现是"页面空白"，库里数据完好）。
    #   同款先例：`cmdb/views/server_grant.py`、`aiagent/views.py`、`log/views/collect.py`。
    extra_filter_class = []

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        return qs if is_asset_admin(user) else qs.filter(creator=user)

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @transaction.atomic
    def perform_destroy(self, instance):
        locked = Pipeline.objects.select_for_update().get(pk=instance.pk)
        if locked.runs.filter(status__in=['pending', 'running']).exists():
            raise ValidationError('该流水线还有未结束的执行记录，请先中止/等它结束再删除')
        locked.delete()

    def destroy(self, request, *args, **kwargs):
        """★ 覆写原因：DVAdmin 的 `destroy` **不走 `perform_destroy`**（直接 instance.delete()），
        只写 `perform_destroy` 守卫会变成摆设。同一个坑在 log/views/collect.py 里已经踩过一次。"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return DetailResponse(data=[], msg='删除成功')

    def multiple_delete(self, request, *args, **kwargs):
        keys = (request.data or {}).get('keys') or []
        if not keys:
            return ErrorResponse(msg='请提供 keys')
        busy = list(Pipeline.objects.filter(id__in=keys).filter(
            runs__status__in=['pending', 'running']).values_list('name', flat=True).distinct())
        if busy:
            raise ValidationError('以下流水线还有未结束的执行记录，请先处理：%s' % '、'.join(busy[:5]))
        Pipeline.objects.filter(id__in=keys).delete()
        return SuccessResponse(data=[], msg='删除成功')

    # ---- 下拉 ------------------------------------------------------------
    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='all')
    def all_list(self, request, *args, **kwargs):
        qs = Pipeline.objects.filter(status=1).order_by('name')
        data = list(qs.values('id', 'name', 'params'))
        return SuccessResponse(data=data)

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='options')
    def options(self, request, *args, **kwargs):
        """页面下拉：凭据 / Jenkins 服务器 / 节点类型 / 通知渠道 / 通知条件。

        ★ 服务器下拉**不在这里** —— 复用它已有的
          `GET /api/cmdb/server/dispatch_options/`（那份已做资产授权过滤，
          且不受按钮权限控制，少一份重复实现就少一个漏授权的口子）。
        """
        from dvadmin.alert.models import NotifyChannel
        from dvadmin.jenkins.models import JenkinsServer

        creds = visible_credential_queryset(request.user)
        credentials = list(creds.values('id', 'name', 'username', 'auth_type')[:200]) \
            if creds is not None else []
        return SuccessResponse(data={
            'credentials': credentials,
            'jenkins_servers': list(
                JenkinsServer.objects.all().order_by('sort', 'id').values('id', 'name', 'url')[:100]),
            'channels': list(
                NotifyChannel.objects.filter(enabled=True).order_by('type', 'name')
                .values('id', 'name', 'type')[:100]),
            'node_types': [{'value': v, 'label': l} for v, l in NODE_TYPE_CHOICES],
            'on_failure_options': [{'value': v, 'label': l} for v, l in ON_FAILURE_CHOICES],
            'notify_on_options': [{'value': v, 'label': l} for v, l in NOTIFY_ON_CHOICES],
            'limits': {'max_node_timeout': MAX_NODE_TIMEOUT,
                       'max_build_wait': MAX_BUILD_WAIT,
                       'max_targets_per_node': MAX_TARGETS_PER_NODE},
        })

    # ---- 编排 ------------------------------------------------------------
    @action(methods=['GET', 'POST'], detail=True, url_path='nodes')
    def nodes(self, request, pk=None):
        """GET 读取编排；POST 保存编排（整体替换）。"""
        pipeline = self.get_object()
        if request.method.lower() == 'get':
            rows = pipeline.nodes.order_by('seq', 'id')
            return SuccessResponse(data=PipelineNodeSerializer(rows, many=True).data)

        raw = request.data.get('nodes')
        if not isinstance(raw, list):
            raise ValidationError('nodes 必须是数组')
        if len(raw) > 100:
            raise ValidationError('单条流水线的节点不能超过 100 个')

        prepared = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ValidationError('第 %d 个节点的格式错误' % (index + 1))
            name = str(item.get('name') or '').strip()
            if not name:
                raise ValidationError('第 %d 个节点没有填名称' % (index + 1))
            node_type = str(item.get('node_type') or 'command')
            if node_type not in [c[0] for c in NODE_TYPE_CHOICES]:
                raise ValidationError('节点「%s」的类型非法' % name)
            on_failure = str(item.get('on_failure') or 'stop')
            if on_failure not in [c[0] for c in ON_FAILURE_CHOICES]:
                raise ValidationError('节点「%s」的失败处理非法' % name)
            config = validate_node_config(node_type, item.get('config') or {}, label='节点「%s」' % name)
            prepared.append({
                'id': item.get('id'),
                'name': name[:64],
                'node_type': node_type,
                'config': config,
                'on_failure': on_failure,
                'seq': index,
                'pos_x': int(item.get('pos_x') or 0),
                'pos_y': int(item.get('pos_y') or 0),
            })

        with transaction.atomic():
            existing = {n.pk: n for n in pipeline.nodes.all()}
            keep_ids = set()
            for row in prepared:
                nid = row.pop('id', None)
                node = existing.get(nid) if nid else None
                if node is not None:
                    for key, value in row.items():
                        setattr(node, key, value)
                    node.save()
                    keep_ids.add(node.pk)
                else:
                    created = PipelineNode.objects.create(pipeline=pipeline, **row)
                    keep_ids.add(created.pk)
            # 不在本次提交里的节点 = 用户在编排页删掉的
            pipeline.nodes.exclude(pk__in=keep_ids).delete()

        rows = pipeline.nodes.order_by('seq', 'id')
        return SuccessResponse(data=PipelineNodeSerializer(rows, many=True).data, msg='编排已保存')

    # ---- 发起执行 --------------------------------------------------------
    @action(methods=['POST'], detail=True, url_path='run')
    def run(self, request, pk=None):
        pipeline = self.get_object()
        raw_params = (request.data or {}).get('params') or {}
        run = engine.create_run(pipeline, raw_params, 'manual', request.user)
        return SuccessResponse(data=engine.snapshot(run), msg='已发起执行')


# ===========================================================================
# 节点预检（不真执行）
# ===========================================================================
class PipelineNodeToolViewSet(viewsets.ViewSet):
    """节点预检。

    ★★ 这里**刻意不真执行**（不起 Jenkins 构建、不连目标机、不发通知）。
      "试跑"听起来无害，但在发布场景里它是能重启生产服务的。
      设计页上误点一下就把生产重启了，是所有选项里最坏的形态。

      所以预检做的是**静态检查 + 变量替换回显**：
        · 占位符替换后到底会执行什么命令 / 传什么文件 / 提交什么构建参数
        · 目标服务器现在解析出来是哪几台、地址是什么
        · 制品文件在不在、大小多少
      真正要执行，走「发起执行」——那是有记录、有留痕、有中止入口的路径。

    ★ 权限沿用 ViewSet 默认的 `CustomPermission`（= `pipeline:Preview` 按钮），
      不用 `IsAuthenticated` 兜底 —— 否则那个已登记的按钮就成了摆设，
      这个接口会变成"任何人登录后都能读任意流水线的目标清单"。
    """
    permission_classes = [CustomPermission]

    @action(methods=['POST'], detail=False, url_path='preview')
    def preview(self, request, *args, **kwargs):
        pipeline_id = (request.data or {}).get('pipeline')
        node_type = str((request.data or {}).get('node_type') or 'command')
        config = (request.data or {}).get('config') or {}
        raw_params = (request.data or {}).get('params') or {}

        pipeline = Pipeline.objects.filter(pk=pipeline_id).first() if pipeline_id else None
        if pipeline is None:
            return ErrorResponse(msg='请先保存流水线，再预检节点')
        # 与列表可见性同口径：运营者看全部，其余人只能预检自己建的
        if not is_asset_admin(request.user) and pipeline.creator_id != request.user.pk:
            return ErrorResponse(msg='无权预检他人创建的流水线')

        errors, warnings, rendered = [], [], {}

        # 参数：先把定义归一，再做替换（与真正执行时同一份口径）
        try:
            params = engine.validate_params(pipeline, raw_params)
        except ValidationError as exc:
            errors.append(_detail_text(exc, 'params'))
            params = {}

        # 结构校验（复用保存时那一份，保证"预检通过 = 保存也能过"）
        try:
            cfg = validate_node_config(node_type, config, label='节点')
        except ValidationError as exc:
            errors.append(_detail_text(exc, 'config'))
            cfg = dict(config) if isinstance(config, dict) else {}

        if node_type in ('command', 'check'):
            rendered['command'] = engine.render_text(cfg.get('command') or '', params)
        elif node_type == 'upload':
            rendered['local_path'] = engine.render_text(cfg.get('local_path') or '', params)
            rendered['remote_path'] = engine.render_text(cfg.get('remote_path') or '', params)
            try:
                from dvadmin.release.ssh_sftp import resolve_local_path
                abs_path, size = resolve_local_path(rendered['local_path'])
                rendered['resolved_local_path'] = abs_path
                rendered['bytes'] = size
            except ValueError as exc:
                errors.append(str(exc))
        elif node_type == 'build':
            rendered['job'] = engine.render_text(cfg.get('job') or '', params)
            rendered['parameters'] = {k: engine.render_text(v, params)
                                      for k, v in (cfg.get('parameters') or {}).items()}
            if cfg.get('jenkins_server_id'):
                from dvadmin.jenkins.models import JenkinsServer
                server = JenkinsServer.objects.filter(pk=cfg['jenkins_server_id']).first()
                rendered['jenkins_server'] = server.name if server else None
                if server is None:
                    errors.append('选择的 Jenkins 服务器不存在')
        elif node_type == 'notify':
            rendered['title'] = engine.render_text(cfg.get('title') or '', params)
            rendered['content'] = engine.render_text(cfg.get('content') or '', params)
            rendered['on'] = cfg.get('on') or 'always'
        elif node_type == 'param':
            rendered['params'] = params

        # 目标解析（回读 CMDB，给出此刻真实会连上去的地址）
        targets = []
        if node_type in ('command', 'check', 'upload'):
            for server in engine.resolve_servers(cfg.get('targets')):
                targets.append({'server_id': server.pk, 'label': server.hostname,
                                'ip': server.ip, 'ssh_port': server.ssh_port or 22,
                                'status': server.status})
                if server.status != 'online':
                    warnings.append('目标「%s」当前状态是「%s」，执行时会被拒绝'
                                    % (server.hostname, server.get_status_display()))
            stored = (config or {}).get('targets') or []
            stored_ids = {int(t.get('server_id')) for t in stored
                          if isinstance(t, dict) and str(t.get('server_id', '')).isdigit()}
            got_ids = {t['server_id'] for t in targets}
            for missing in sorted(stored_ids - got_ids):
                warnings.append('目标 server_id=%s 在 CMDB 里已不存在，执行时会被跳过' % missing)

        # 凭据可用性
        credential = engine._credential_for(pipeline, cfg)               # noqa: SLF001
        if node_type in ('command', 'check', 'upload') and credential is None:
            errors.append('没有可用的凭据：请给流水线设置默认凭据，或在本节点指定凭据')

        # 未命中的占位符（执行时会原样带进命令，值得提醒）
        leftovers = sorted({tok for tok in
                            [w for w in _placeholder_tokens(rendered)]
                            if tok not in params})
        if leftovers:
            warnings.append('下列占位符没有对应参数，执行时会原样保留：%s'
                            % '、'.join('{{%s}}' % t for t in leftovers))

        return SuccessResponse(data={
            'ok': not errors,
            'errors': errors,
            'warnings': warnings,
            'rendered': rendered,
            'targets': targets,
            'params': params,
            'credential': credential.name if credential else None,
            'note': '预检不会真正执行（不触发构建、不连目标机、不发通知），'
                    '只回显占位符替换结果与目标解析情况。真正执行请用「发起执行」。',
        }, msg='预检完成' if not errors else '预检发现问题')


def _placeholder_tokens(rendered):
    """从渲染结果里挑出还没被替换掉的 ``{{xxx}}``。"""
    import re
    tokens = []
    for value in (rendered or {}).values():
        if isinstance(value, str):
            tokens.extend(re.findall(r'\{\{([A-Za-z0-9_]+)\}\}', value))
        elif isinstance(value, dict):
            for v in value.values():
                if isinstance(v, str):
                    tokens.extend(re.findall(r'\{\{([A-Za-z0-9_]+)\}\}', v))
    return tokens


# ===========================================================================
# 执行记录
# ===========================================================================
class PipelineRunViewSet(CustomModelViewSet):
    queryset = PipelineRun.objects.all().order_by('-create_datetime')
    serializer_class = PipelineRunSerializer
    list_serializer_class = PipelineRunListSerializer
    search_fields = ['pipeline_name']
    filter_fields = ['status', 'trigger_type', 'pipeline']
    http_method_names = ['get', 'post', 'head', 'options']
    extra_filter_class = []

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'retrieve':
            qs = qs.prefetch_related('node_runs')
        user = self.request.user
        return qs if is_asset_admin(user) else qs.filter(creator=user)

    def create(self, request, *args, **kwargs):
        # 执行记录只能由「发起执行」产生，不允许直接 POST 建
        return ErrorResponse(msg='执行记录只能通过流水线的「发起执行」产生')

    def retrieve(self, request, *args, **kwargs):
        """详情：与 `advance` 返回**同一种结构**（`engine.snapshot`），只是多带逐台结果。

        ★ 形状统一是刻意的：前端拿到 advance 的返回和详情的返回是同一套解析，
          不会出现"刷新一下页面形状就变了"这种极难排查的问题。
        """
        run = self.get_object()
        data = engine.snapshot(run, with_results=True)
        data.update({
            'pipeline': run.pipeline_id,
            'pipeline_name': run.pipeline_name or '',
            'params': run.params or {},
            'trigger_type': run.trigger_type,
            'trigger_type_label': dict(PipelineRun._meta.get_field('trigger_type').choices)
                                       .get(run.trigger_type, run.trigger_type),
            'creator_name': (lambda u: (u.name or u.username) if u else None)(run.creator),
            'create_datetime': run.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if run.create_datetime else None,
        })
        return DetailResponse(data=data)

    # ---- 推进一个节点 ----------------------------------------------------
    @action(methods=['POST'], detail=True, url_path='advance')
    def advance(self, request, pk=None):
        """推进一个节点。到终态后再调是无害的（直接返回当前全貌），
        前端可以无脑循环调用直到 `is_final` 为真。"""
        run = self.get_object()
        if run.status in RUN_FINAL_STATUS:
            return SuccessResponse(data=engine.snapshot(run), msg='该执行已结束')
        # ★ 防止两个页面（或双击）同时推进：同一时刻只允许一个节点处于 running
        if PipelineNodeRun.objects.filter(run=run, status='running').exists():
            raise ValidationError('该执行正在推进中（可能有另一个页面正在跑），请稍后刷新查看')
        data = engine.advance_run(run.pk, actor=request.user)
        return SuccessResponse(data=data, msg='节点执行完成')

    # ---- 中止 ------------------------------------------------------------
    @action(methods=['POST'], detail=True, url_path='abort')
    def abort(self, request, pk=None):
        run = self.get_object()
        with transaction.atomic():
            locked = PipelineRun.objects.select_for_update().get(pk=run.pk)
            if locked.status in RUN_FINAL_STATUS:
                return ErrorResponse(msg='该执行已结束，无法中止')
            locked.status = 'aborted'
            locked.finished_at = timezone.now()
            locked.current_node_id = None
            locked.save(update_fields=['status', 'finished_at', 'current_node_id'])
        return SuccessResponse(data=engine.snapshot(locked), msg='已中止（未执行的节点保持"待执行"）')

    # ---- 重跑失败节点 ----------------------------------------------------
    @action(methods=['POST'], detail=True, url_path='retry')
    def retry(self, request, pk=None):
        run = self.get_object()
        with transaction.atomic():
            locked = PipelineRun.objects.select_for_update().get(pk=run.pk)
            if locked.status == 'running':
                return ErrorResponse(msg='该执行正在进行中，不能重跑')
            failed = PipelineNodeRun.objects.filter(run=locked, status='failed')
            if not failed.exists():
                return ErrorResponse(msg='没有失败的节点可以重跑')
            failed.update(status='pending', message='', targets_result=[],
                          started_at=None, finished_at=None, duration=None)
            locked.status = 'running'
            locked.finished_at = None
            locked.current_node_id = None
            locked.last_error = ''
            locked.save(update_fields=['status', 'finished_at', 'current_node_id', 'last_error'])
        return SuccessResponse(data=engine.snapshot(locked), msg='已重置失败节点，可继续推进')
