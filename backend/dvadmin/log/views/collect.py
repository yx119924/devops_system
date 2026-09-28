# -*- coding: utf-8 -*-
"""日志采集配置 ViewSet。

端点（★ 每一个 ``@action`` 都要在 ``register_log_collect.py`` 里逐条登记
MenuButton —— 后端 ``CustomPermission`` 是按 (api 模板, method 下标) 逐条
匹配 ``RoleMenuButtonPermission`` 的，漏一条那条接口对非超管就恒返回 4000）：

===============================================  ==========================================
``GET/POST/PUT/DELETE /api/log/collect/``        采集任务 CRUD
``GET    /api/log/collect/all/``                 下拉（启用中的任务）
``GET    /api/log/collect/options/``             页面下拉（ES 数据源 / 凭据 / 级别）
``POST   /api/log/collect/{id}/detect/``         环境检测（只读，逐目标）
``POST   /api/log/collect/{id}/apply/``          下发配置片段
``POST   /api/log/collect/{id}/stop/``           停止采集（删片段）
``POST   /api/log/collect/{id}/preview/``        规则试跑（抓样本跑过滤，只读）
``GET    /api/log/collect/{id}/records/``        操作台账
``GET    /api/log/collect/{id}/main_patch/``     目标机主配置待补内容
===============================================  ==========================================

权限三层（与命令下发同构）
--------------------------
1. 接口层：``CustomPermission`` 按按钮权限控制
2. 目标层：**逐目标** ``require_access(user, server, credential, 'dispatch')``
   —— 这是真正的关卡，前端下拉被绕过（手工构造 targets）也拦得住
3. 可见层：``get_queryset`` —— 资产运营者看全部，其余人只看自己建的

★ 目标 IP 一律从 CMDB 重新读取，**不信任请求里带的 ip**
（照抄 ``bastion/views/dispatch.py`` 的做法，防止"凭据被发到前端指定的 IP"）。
"""
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from dvadmin.bastion.access import is_asset_admin, require_access, visible_credential_queryset
from dvadmin.cmdb.models import Server
from dvadmin.log import collector
from dvadmin.log.models import (
    COLLECT_LEVEL_CHOICES, LogCollectRecord, LogCollectTask, DEFAULT_REMOTE_DIR,
)
from dvadmin.utils.json_response import DetailResponse, ErrorResponse, SuccessResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


def next_run_status(action, ok_count, total):
    """按动作推导「目标机上的落地状态」。

    ★★ 为什么不能只看 ``ok_count``（2026-09-24 真机自测的 S11-5）：

      初版写的是 ``'applied' if ok_count == total else 'failed'`` ——
      **完全没有看 action**，于是「停止」成功后也被写成 ``applied``：

        ① 列表里状态是错的：用户明明停掉了，看到"已下发"。
        ② 更糟的是**自锁**：``_assert_deletable`` 只放行非 ``applied`` 的记录，
           所以"停完还是删不掉"，而用户没有任何办法把状态改回来。
           —— 一个 bug 把另一处守卫变成了牢笼。

      ⇒ 两个动作对"成功"的定义方向相反，必须分开判：

      · ``stop`` ：**只有全部目标都清干净**才敢标 ``stopped``。
        部分失败时**保守留 ``applied``** —— 只要还有一台残留片段在采数据，
        就不该让"已下发不许直接删"的守卫放行（那会留下看不见的孤儿采集）。
      · ``apply``：只要有**任意一台**落地成功，目标机上就有片段在采数据 ⇒
        ``applied``。哪怕只有 1/3 成功也**不能**标 ``failed``，同理会让守卫失效。
        只有 0 台成功才是 ``failed``。

      "部分成功"这件事本身不丢 —— 它由 ``last_message`` 里的
      「N/M 台成功」和台账里的逐目标明细承载。
    """
    if action == 'stop':
        return 'stopped' if total > 0 and ok_count >= total else 'applied'
    return 'applied' if ok_count > 0 else 'failed'


# ===========================================================================
# 序列化器
# ===========================================================================
class LogCollectTaskSerializer(CustomModelSerializer):
    """采集任务序列化器。写入前把「生成侧会炸的配置」全部挡在入口。"""

    status_label = serializers.SerializerMethodField()
    run_status_label = serializers.SerializerMethodField()
    source_name = serializers.CharField(source='source.name', read_only=True, default=None)
    credential_name = serializers.CharField(source='credential.name', read_only=True, default=None)
    target_count = serializers.SerializerMethodField()
    es_index_pattern = serializers.SerializerMethodField()
    remote_path = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    # ★ 只读回填字段：前端「编辑」表单要显示已选中的服务器，
    #   但 targets 是 [{server_id,label,ip,ssh_port}]，直接塞进多选框对不上。
    #   这里给一个纯 id 数组，表单直接可用；提交时被 DRF 忽略（SerializerMethodField 恒只读）。
    cmdb_targets = serializers.SerializerMethodField()
    # ★ 同理：附加字段在表单里是 textarea 编辑的 JSON 文本，
    #   编辑时要能把它原样回填出来（不是 dict，textarea 塞不进去）
    extra_fields_text = serializers.SerializerMethodField()

    def get_cmdb_targets(self, obj):
        return [t.get('server_id') for t in (obj.targets or []) if t.get('server_id')]

    def get_extra_fields_text(self, obj):
        extra = obj.extra_fields or {}
        if not extra:
            return ''
        try:
            import json
            return json.dumps(extra, ensure_ascii=False, indent=2)
        except Exception:                                          # noqa: BLE001
            return ''

    def get_status_label(self, obj):
        return dict(LogCollectTask._meta.get_field('status').choices).get(obj.status, obj.status)

    def get_run_status_label(self, obj):
        return dict(LogCollectTask._meta.get_field('run_status').choices).get(obj.run_status, obj.run_status)

    def get_target_count(self, obj):
        return len(obj.targets or [])

    def get_es_index_pattern(self, obj):
        return obj.es_index_pattern

    def get_remote_path(self, obj):
        return obj.remote_path if obj.pk else ""

    def get_creator_name(self, obj):
        try:
            return obj.creator.name or obj.creator.username
        except Exception:                                          # noqa: BLE001
            return None

    def validate(self, attrs):
        """★ 所有校验都在这里做 —— 让「保存时就报错」，而不是等下发时才炸。"""
        user = self.context['request'].user
        instance = self.instance

        # 未传时取实例上的旧值（PUT 是全量更新，但前端可能只改一部分字段的场景
        # 由前端保证；这里为稳妥做一次合并，让校验看到"最终值"）
        def _pick(key):
            if key in attrs:
                return attrs.get(key)
            return getattr(instance, key, None) if instance is not None else None

        index_prefix = (_pick('index_prefix') or '').strip()
        ok, msg = collector.validate_index_prefix(index_prefix)
        if not ok:
            raise serializers.ValidationError({'index_prefix': msg})
        attrs['index_prefix'] = index_prefix

        path_pattern = (_pick('path_pattern') or '').strip()
        ok, msg = collector.validate_path_pattern(path_pattern)
        if not ok:
            raise serializers.ValidationError({'path_pattern': msg})
        attrs['path_pattern'] = path_pattern

        remote_dir = (_pick('remote_dir') or DEFAULT_REMOTE_DIR).strip().rstrip('/')
        ok, msg = collector.validate_remote_dir(remote_dir)
        if not ok:
            raise serializers.ValidationError({'remote_dir': msg})
        attrs['remote_dir'] = remote_dir

        # ★ RE2 兼容性：Python 能编译但 filebeat 会挂的正则，在保存时就拦住
        for field, label in (('include_regex', '包含规则'),
                             ('exclude_regex', '排除规则'),
                             ('multiline_start', '多行起始正则'),
                             ('time_regex', '时间提取正则')):
            val = (_pick(field) or '').strip()
            if not val:
                attrs[field] = ''
                continue
            ok, msg = collector.check_re2_compatible(val)
            if not ok:
                raise serializers.ValidationError({field: msg})
            attrs[field] = val

        t_regex = attrs.get('time_regex', _pick('time_regex') or '')
        t_layout = (_pick('time_layout') or '').strip()
        if t_regex and not t_layout:
            raise serializers.ValidationError({'time_layout': '填了时间提取正则就必须填时间格式'})
        if t_layout and not t_regex:
            raise serializers.ValidationError({'time_regex': '填了时间格式就必须填时间提取正则'})
        if t_regex and 'log_time' not in t_regex:
            raise serializers.ValidationError(
                {'time_regex': '正则里必须含命名组 (?P<log_time>...)，否则提取不到时间'})
        if t_layout:
            attrs['time_layout'] = t_layout

        extra = _pick('extra_fields')
        if extra in (None, ''):
            extra = {}
        # 保留名校验（覆盖 xwops_task_id / index_prefix 等会静默破坏采集）
        ok, msg = collector.check_extra_fields(extra)
        if not ok:
            raise serializers.ValidationError({'extra_fields': msg})
        attrs['extra_fields'] = extra

        # ---- 目标：必须来自 CMDB，且逐台过资产授权 ----
        targets = _pick('targets')
        if targets is None:
            targets = []
        if not isinstance(targets, list) or not 1 <= len(targets) <= 100:
            raise serializers.ValidationError({'targets': '必须选择 1 到 100 台 CMDB 服务器'})

        credential = _pick('credential')
        if not credential:
            raise serializers.ValidationError({'credential': '必须选择连接目标机的凭据'})

        normalized, seen = [], set()
        for target in targets:
            if not isinstance(target, dict):
                raise serializers.ValidationError({'targets': '目标格式错误'})
            try:
                server = Server.objects.get(pk=int(target.get('server_id', 0)))
            except (Server.DoesNotExist, TypeError, ValueError):
                raise serializers.ValidationError({'targets': '目标必须来自 CMDB；请先登记服务器'})
            require_access(user, server, credential, 'dispatch')
            if server.pk in seen:
                continue
            seen.add(server.pk)
            # ★ ip/ssh_port 从 CMDB 重新读，不用请求里带的值
            normalized.append({
                'server_id': server.pk,
                'label': server.hostname,
                'ip': server.ip,
                'ssh_port': server.ssh_port or 22,
            })
        attrs['targets'] = normalized

        return super().validate(attrs)

    class Meta:
        model = LogCollectTask
        fields = '__all__'
        read_only_fields = ['id', 'run_status', 'last_action_at', 'last_message', 'creator']


class LogCollectRecordSerializer(CustomModelSerializer):
    action_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()

    def get_action_label(self, obj):
        return dict(LogCollectRecord._meta.get_field('action').choices).get(obj.action, obj.action)

    def get_status_label(self, obj):
        return dict(LogCollectRecord._meta.get_field('status').choices).get(obj.status, obj.status)

    def get_creator_name(self, obj):
        try:
            return obj.creator.name or obj.creator.username
        except Exception:                                          # noqa: BLE001
            return None

    class Meta:
        model = LogCollectRecord
        fields = '__all__'
        read_only_fields = ['id']


# ===========================================================================
# ViewSet
# ===========================================================================
class LogCollectTaskViewSet(CustomModelViewSet):
    """日志采集任务。

    权限三层见模块 docstring。特别注意：**每个 @action 都要登记按钮权限**。
    """
    queryset = LogCollectTask.objects.all().order_by('-create_datetime')
    serializer_class = LogCollectTaskSerializer
    search_fields = ['name', 'path_pattern', 'index_prefix', 'description']
    filter_fields = ['status', 'run_status', 'collect_mode']
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']
    # ★ 可见性**只由 `get_queryset` 决定**（资产运营者看全部、其余人只看自己建的）。
    #   必须关掉 DVAdmin 的部门数据权限 `DataLevelPermissionMargeFilter`：
    #   它对「没有 dept_id 的用户」会 `none()`，把用户**自己建的**任务也一并掏空
    #   —— 表现是"页面空白"，而库里数据完好，极难排查。
    #   同款先例：`cmdb/views/server_grant.py`、`aiagent/views.py`。
    extra_filter_class = []

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # 资产运营者（运维/管理员）看全部，便于排障；其余人只看自己建的
        return qs if is_asset_admin(user) else qs.filter(creator=user)

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    # ---- 「已下发不许直接删」的守卫 --------------------------------------
    def _assert_deletable(self, instance):
        """★ 已下发的任务必须先「停止」才能删除。

        为什么不让它悄悄删掉：数据库里删一条记录很简单，但**目标机上的
        ``xwops-task-<id>.yml`` 还在**，filebeat 会继续采集 —— 用户在平台上
        看不到这个任务了，日志却还在往 ES 里灌，属于"看不见的副作用"。
        宁可让他多点一次「停止」，也不制造这种状态。

        ★★ 2026-09-24 真机自测发现：这个守卫**当初是摆设**。
           DVAdmin 的 `CustomModelViewSet.destroy` 长这样：

               def destroy(self, request, *args, **kwargs):
                   instance = self.get_object()
                   instance.delete()                     # ← 直接删
                   return DetailResponse(data=[], msg=_("Delete successful"))

           **它根本不走 DRF 的 `perform_destroy`**。所以只写 `perform_destroy` 时，
           「已下发」的任务照样被删掉，目标机上留下孤儿片段 —— 真机实测里
           S10 就是这样：DELETE 返回 "Delete successful"，随后 stop 变成
           "Endpoint address is incorrect"（对象已不存在）。
           ⇒ 必须**覆写 `destroy`**，并且连 `multiple_delete`（批量删）一起补。
        """
        if instance.run_status == 'applied':
            raise ValidationError(
                '该任务已下发到目标机，请先点「停止」删除目标机上的配置片段，再删除任务；'
                '否则目标机会残留采集片段继续往 ES 写数据')

    @transaction.atomic
    def perform_destroy(self, instance):
        locked = LogCollectTask.objects.select_for_update().get(pk=instance.pk)
        self._assert_deletable(locked)
        locked.delete()

    def destroy(self, request, *args, **kwargs):
        """★ 覆写原因见 `_assert_deletable`（DVAdmin 的 destroy 绕过 perform_destroy）。"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return DetailResponse(data=[], msg='删除成功')

    def multiple_delete(self, request, *args, **kwargs):
        """批量删除同样绕过 `perform_destroy`，这里补上同样的守卫。

        ★ 批量删更要拦：一次点掉 10 个已下发的任务 = 目标机上留下 10 份孤儿片段，
          而且**平台侧再也查不到是哪几台**（记录都没了），只能靠登机器翻 inputs.d。
        """
        keys = (request.data or {}).get('keys') or []
        if not keys:
            return ErrorResponse(msg='请提供 keys')
        tasks = list(LogCollectTask.objects.filter(id__in=keys))
        applied = [t.name for t in tasks if t.run_status == 'applied']
        if applied:
            raise ValidationError(
                '以下任务已下发到目标机，请先「停止」再删除：%s%s'
                % ('、'.join(applied[:5]), ' 等 %d 个' % len(applied) if len(applied) > 5 else ''))
        LogCollectTask.objects.filter(id__in=keys).delete()
        return SuccessResponse(data=[], msg='删除成功')

    # ---- 内部工具 --------------------------------------------------------
    def _targets_for(self, task, request):
        """取出本次要操作的目标。传 ``server_id`` 则只取那一台。

        ★ 目标 IP 在这里**再回读一次 CMDB**：任务创建后服务器 IP 可能被改过，
        按库里最新的地址连，避免"改了资产却还在往旧 IP 下发"。
        """
        raw = task.targets or []
        want = request.data.get('server_id') if isinstance(request.data, dict) else None
        out = []
        for t in raw:
            try:
                sid = int(t.get('server_id'))
            except (TypeError, ValueError):
                continue
            if want and int(want) != sid:
                continue
            try:
                server = Server.objects.get(pk=sid)
            except Server.DoesNotExist:
                continue
            require_access(request.user, server, task.credential, 'dispatch')
            out.append(server)
        return out

    def _record(self, task, action, results, operator):
        """把逐目标的结果写进台账。成功失败都写（失败更值得留痕）。"""
        rows = []
        for r in results:
            rows.append(LogCollectRecord(
                task=task,
                action=action,
                status='success' if r.get('ok') else 'failed',
                target_label=r.get('server') or '',
                ip=r.get('ip') or '',
                message=(r.get('message') or '')[:512],
                detail=(r.get('detail') or '')[:20000],
                duration=r.get('duration'),
                creator=operator,
            ))
        if rows:
            LogCollectRecord.objects.bulk_create(rows)

    def _run_on_targets(self, request, task, action, fn):
        """对每台目标执行 ``fn(task, server, credential)``，聚合结果 + 写台账。"""
        if not task.credential_id:
            return ErrorResponse(msg='该任务没有配置凭据，无法连接目标机')
        try:
            targets = self._targets_for(task, request)
        except Exception as exc:                                   # noqa: BLE001
            return ErrorResponse(msg='目标校验失败：%s' % exc)
        if not targets:
            return ErrorResponse(msg='没有可操作的目标（目标为空，或你没有这些机器的操作授权）')

        results = []
        for server in targets:
            try:
                res = fn(task, server, task.credential)
            except Exception as exc:                               # noqa: BLE001
                res = {'ok': False, 'server': server.hostname, 'ip': server.ip,
                       'message': '执行异常：%s' % exc}
            # ★「只采新增」说明（含 input 类型降级原因）并入 warnings，
            #   下发结果面板直接用同一块渲染区显示，用户下发完就知道发生了什么。
            notes = res.get('tail_notes') or []
            if notes:
                res['warnings'] = list(res.get('warnings') or []) + list(notes)
            results.append(res)

        self._record(task, action, results, request.user)

        ok_count = sum(1 for r in results if r.get('ok'))
        summary = '%d/%d 台成功' % (ok_count, len(results))
        # ★ 状态必须按 action 分派 —— 只看 ok_count 会让「停止」写成「已下发」，
        #   进而把"已下发不许直接删"的守卫变成自锁。详见 next_run_status()。
        LogCollectTask.objects.filter(pk=task.pk).update(
            run_status=next_run_status(action, ok_count, len(results)),
            last_action_at=timezone.now(),
            last_message=summary + '｜' + '；'.join(
                (r.get('message') or '')[:80] for r in results[:3]),
        )
        task.refresh_from_db()
        return SuccessResponse(data={'results': results, 'summary': summary},
                               msg=summary)

    # ---- 下拉 ------------------------------------------------------------
    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉：启用中的采集任务。"""
        qs = LogCollectTask.objects.filter(status=1).order_by('name')
        data = list(qs.values('id', 'name', 'index_prefix', 'path_pattern'))
        return SuccessResponse(data=data)

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='options')
    def options(self, request, *args, **kwargs):
        """页面下拉：ES 数据源 / 可用凭据 / 级别选项 / 默认片段目录。

        服务器下拉**不在这里** —— 复用它已有的
        ``GET /api/cmdb/server/dispatch_options/``（那份已做资产授权过滤，且
        不受按钮权限控制，少一份重复实现就少一个漏授权的口子）。
        """
        from dvadmin.log.models import ElasticsearchSource
        sources = list(ElasticsearchSource.objects.filter(status=1).order_by('sort')
                       .values('id', 'name', 'url', 'index_pattern'))
        creds = visible_credential_queryset(request.user)
        credentials = list(creds.values('id', 'name', 'username', 'auth_type')[:200]) \
            if creds is not None else []
        return SuccessResponse(data={
            'sources': sources,
            'credentials': credentials,
            'levels': [{'value': v, 'label': l} for v, l in COLLECT_LEVEL_CHOICES],
            'default_remote_dir': DEFAULT_REMOTE_DIR,
        })

    @action(methods=['GET'], detail=True, permission_classes=[IsAuthenticated], url_path='main_patch')
    def main_patch(self, request, pk=None):
        """目标机主配置需要补的内容（只返回文本，平台不自动写）。"""
        task = self.get_object()
        return SuccessResponse(data={
            'remote_dir': task.remote_dir,
            'content': collector.build_main_patch(task.remote_dir),
            'remote_file': task.remote_path,
        })

    # ---- 环境检测 --------------------------------------------------------
    @action(methods=['POST'], detail=True, url_path='detect')
    def detect(self, request, pk=None):
        """只读检测目标机 filebeat 环境（是否安装 / 版本 / output / 是否加载片段目录）。"""
        task = self.get_object()

        def _fn(t, server, credential):
            res = collector.detect_environment(server, credential)
            if res.get('ok'):
                # ★「只采新增」的落地方式（含可能的 input 类型降级）必须回显 ——
                #   静默降级会让用户下次看配置文件一头雾水，谎称"filestream 也行"更糟。
                notes = collector.render_tail_note(task, res.get('beat_type') or 'filestream')
                res['tail_notes'] = notes
                warns = list(res.get('warnings') or []) + list(notes)
                res['warnings'] = warns
                res['message'] = ('正常' if not warns
                                  else '；'.join(warns)[:400])
                res['detail'] = res.get('raw') or ''
            res['server'] = server.hostname
            res['ip'] = server.ip
            return res

        # 目标层校验放在 collector 之前（无凭据也能检测，但目标是必需的）
        if not (task.targets or []):
            return ErrorResponse(msg='该任务还没有选择目标服务器')
        try:
            targets = self._targets_for(task, request)
        except Exception as exc:                                   # noqa: BLE001
            return ErrorResponse(msg='目标校验失败：%s' % exc)
        if not targets:
            return ErrorResponse(msg='没有可检测的目标（目标为空，或你没有这些机器的操作授权）')

        results = []
        for server in targets:
            try:
                results.append(_fn(task, server, task.credential))
            except Exception as exc:                               # noqa: BLE001
                results.append({'ok': False, 'server': server.hostname, 'ip': server.ip,
                                'message': '检测异常：%s' % exc})
        self._record(task, 'detect', results, request.user)
        ok_count = sum(1 for r in results if r.get('ok'))
        return SuccessResponse(data={'results': results},
                               msg='%d/%d 台检测完成' % (ok_count, len(results)))

    # ---- 下发 / 停止 -----------------------------------------------------
    @action(methods=['POST'], detail=True, url_path='apply')
    def apply(self, request, pk=None):
        """下发配置片段到目标机（并重启/热加载 filebeat）。"""
        task = self.get_object()
        if task.status != 1:
            return ErrorResponse(msg='任务已停用，请先启用再下发')
        return self._run_on_targets(request, task, 'apply', collector.apply_config)

    @action(methods=['POST'], detail=True, url_path='stop')
    def stop(self, request, pk=None):
        """从目标机删除配置片段（= 该任务停止采集）。**不会动目标机其它配置。**"""
        task = self.get_object()
        return self._run_on_targets(request, task, 'stop', collector.stop_config)

    # ---- 规则试跑 --------------------------------------------------------
    @action(methods=['POST'], detail=True, url_path='preview')
    def preview(self, request, pk=None):
        """规则试跑：抓目标机样本行，用平台侧复现的规则跑一遍，回显保留/丢弃对照。

        ★ 只读操作，适合"配完规则先看效果再下发"。
        """
        task = self.get_object()
        if not task.credential_id:
            return ErrorResponse(msg='该任务没有配置凭据，无法读取目标机日志')
        try:
            targets = self._targets_for(task, request)
        except Exception as exc:                                   # noqa: BLE001
            return ErrorResponse(msg='目标校验失败：%s' % exc)
        if not targets:
            return ErrorResponse(msg='没有可试跑的目标')
        lines = request.data.get('lines', 200)
        server = targets[0]
        res = collector.sample_and_filter(task, server, task.credential, lines=lines)
        if res.get('ok'):
            self._record(task, 'preview',
                         [{'ok': True, 'server': server.hostname, 'ip': server.ip,
                           'message': res.get('message')}], request.user)
            return SuccessResponse(data=res, msg=res.get('message') or '试跑完成')
        return ErrorResponse(msg=res.get('message') or '试跑失败')

    # ---- 台账 ------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='records')
    def records(self, request, pk=None):
        """操作台账（检测/下发/停止/试跑）。"""
        task = self.get_object()
        page = int(request.query_params.get('page', 1) or 1)
        limit = min(int(request.query_params.get('limit', 20) or 20), 200)
        qs = task.records.order_by('-create_datetime')
        total = qs.count()
        start = max(0, (page - 1) * limit)
        rows = qs[start:start + limit]
        return SuccessResponse(data={
            'total': total,
            'list': LogCollectRecordSerializer(rows, many=True).data,
        })
