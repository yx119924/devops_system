# -*- coding: utf-8 -*-
"""流水线执行引擎 —— **推进一个节点**。

核心只有一个入口：``advance_run(run_id)``。

★ 为什么是「一个节点一步」（09-23 拍板的 C 方案）
--------------------------------------------------
执行引擎将来有两条路：

  · **前端驱动**：``POST /api/release/run/{id}/advance/`` 一次推进一步（本期实现）
  · **Celery**  ：``pipeline_execute.delay(run_id)`` 里 ``while`` 调 ``advance_run()``

把「执行一个节点」抽干净之后，两种引擎**共用同一份代码**：
前端、接口契约、数据模型全都不用改，只是多一个入口。这样本期**不需要重建 celery 镜像**
（已知坑：`dvadmin3-celery` 镜像里没有 paramiko），也就不必挑窗口中断在跑的异步告警任务。

★ 为什么执行体在事务外（这是个容易写反的地方）
----------------------------------------------
SSH / 等 Jenkins 出结果动辄几十秒。若把整个节点执行包在 ``select_for_update`` 事务里，
一个慢节点就会把数据库连接和行锁一直占住，别人连查这条 run 都要排队。
所以固定三步：**短事务改状态 → 事务外执行 → 短事务回写结果**。

★ 目标地址一律回读 CMDB
------------------------
编排时存在 ``config['targets']`` 里的 ``ip/ssh_port`` 只是**快照**（用于页面回显）。
真正连接前一律按 ``server_id`` 回查 ``cmdb.Server`` 拿最新地址 ——
否则服务器换网段之后，流水线会继续往一个已经没人的 IP 上发布。

★ 授权在哪里校验
----------------
**创建执行时**逐目标校验（``require_access``，与命令下发同一套资产授权），
执行时只回读地址、不再判权。理由：执行可能发生在很久之后（未来挂 Celery 时更是如此），
那时的"当前用户"没有意义；授权必须在**人按下按钮的那一刻**成立。
"""
import copy
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from dvadmin.bastion.access import is_asset_admin, require_access
from dvadmin.bastion.models import CommandLog, Credential, is_dangerous_command
from dvadmin.bastion.ssh_client import ssh_exec
from dvadmin.cmdb.models import Server
from dvadmin.jenkins.models import JenkinsServer
from dvadmin.jenkins.views.jenkins import jenkins_auth
from dvadmin.release.models import (
    MAX_BUILD_WAIT, MAX_NODE_TIMEOUT, MAX_TARGETS_PER_NODE, PipelineNodeRun,
    PipelineRun, RUN_FINAL_STATUS,
)
from dvadmin.release.ssh_sftp import resolve_local_path, sftp_put

# 单节点（命令/检查/上传）的**总时长**上限：所有目标共用这一个预算。
#
# ★ 为什么要有它：并发执行时，最坏耗时 = timeout × ⌈目标数 / 并发数⌉，
#   50 台 × 300 秒能算到 30 分钟以上 —— 而前端那个请求是有超时的，
#   用户会看到一个"卡死"的页面，实际上后端还在跑。给节点一个明确的总预算，
#   超预算的目标直接标失败并写清原因，比无声地拖更诚实。
NODE_WALL_BUDGET = 300

# 命令/检查/上传节点的目标并发数
NODE_MAX_WORKERS = 8

# Jenkins 轮询间隔（秒）
BUILD_POLL_INTERVAL = 5


# ===========================================================================
# 小工具
# ===========================================================================
def render_text(text, params):
    """把 ``{{key}}`` 换成参数值。

    ★ 只做**一层字面替换**，绝不求值 —— 用户可控的文本一旦参与表达式求值，
      就是一条远程代码执行通道。占位符没命中时原样保留（宁可让用户看到
      ``{{xxx}}`` 还在，也不要静默换成空字符串把命令改得面目全非）。
    """
    if not text:
        return ''
    out = str(text)
    for key, value in (params or {}).items():
        out = out.replace('{{%s}}' % key, '' if value is None else str(value))
    return out


def _clamp_int(value, default, low, high):
    try:
        num = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(num, high))


def _credential_for(pipeline, cfg):
    """节点级凭据优先，否则用流水线默认凭据。"""
    cid = (cfg or {}).get('credential') or (cfg or {}).get('credential_id')
    if cid:
        cred = Credential.objects.filter(pk=cid).first()
        if cred is not None:
            return cred
    return pipeline.credential if pipeline is not None else None


def _credential_payload(credential):
    if credential is None:
        return {'username': 'root', 'auth_type': 'password', 'password': None, 'private_key': None}
    return {
        'username': credential.username or 'root',
        'auth_type': credential.auth_type or 'password',
        'password': credential.get_password() if credential.auth_type == 'password' else None,
        'private_key': credential.get_private_key() if credential.auth_type == 'private_key' else None,
    }


def resolve_servers(cfg_targets):
    """把节点配置里的目标解析成 CMDB 里的 ``Server`` 实例（**地址以 CMDB 为准**）。

    取不到的（资产被删）会被跳过 —— 调用方需要自己判断"是不是一台都没剩下"。
    """
    servers, seen = [], set()
    for item in (cfg_targets or []):
        if not isinstance(item, dict):
            continue
        try:
            sid = int(item.get('server_id'))
        except (TypeError, ValueError):
            continue
        if sid in seen:
            continue
        server = Server.objects.filter(pk=sid).first()
        if server is None:
            continue
        seen.add(sid)
        servers.append(server)
    return servers


def validate_targets_for_run(user, pipeline, credential, cfg_targets, label='节点'):
    """创建执行时的**授权关卡**：逐目标校验。

    前端下拉被绕过（手工构造 targets）也拦得住 —— 校验落在后端，不在页面。
    """
    servers = resolve_servers(cfg_targets)
    if not servers:
        raise ValidationError('%s没有可用的目标服务器（未选择，或资产已被删除）' % label)
    if len(servers) > MAX_TARGETS_PER_NODE:
        raise ValidationError('%s的目标过多（%d 台，上限 %d 台）'
                              % (label, len(servers), MAX_TARGETS_PER_NODE))
    for server in servers:
        require_access(user, server, credential, 'dispatch')
    return servers


def _path_matches(full_path, prefix):
    """Jenkins 目录授权的前缀匹配（**按路径段**，不是裸 startswith）。

    与 `jenkins/views/jenkins.py::_path_matches` 同口径：授权 `生产环境/` 不连带
    `生产环境-2.0版本/`、`生产环境-华为云/`。
    """
    pc = str(prefix or '').rstrip('/')
    return full_path == pc or full_path.startswith(pc + '/')


def jenkins_allowed_paths(user, source):
    """用户在某个 Jenkins 服务器上被授权的目录；``None`` = 不受限。

    ★★ 为什么「构建」节点必须过这一关
    ----------------------------------
    平台既有的「构建发布」页是走接口层 `CustomPermission` + `_check_job_allowed`
    来限制"哪些目录的 Job 我能点构建"的（按 dev/test/pre/prod 分环境授权）。

    而流水线的执行体是**在 Django 进程里直接调 Jenkins API**，绕开了那一层。
    如果不管，一个只有 `pipeline:Run` 的人就能在流水线里配任意 Job，
    **把分环境授权整个旁路掉** —— 这是"新功能打开了旧控制"的典型形态。
    所以：构建节点在**发起执行时**按同一套 `JenkinsRolePermission` 判一次。
    """
    from dvadmin.jenkins.models import JenkinsRolePermission
    from dvadmin.utils.perm_helper import user_role_ids

    if is_asset_admin(user):
        return None
    role_ids = user_role_ids(user)
    if not role_ids:
        return []
    perms = list(JenkinsRolePermission.objects.filter(server=source, role_id__in=role_ids))
    if not perms:
        return []                                  # 无记录 = 默认拒绝（与既有口径一致）
    out = set()
    for perm in perms:
        if not perm.allowed_paths:                 # 空列表 = 全部可见
            return None
        out.update(perm.allowed_paths)
    return sorted(out)


def validate_build_access(user, cfg, label='节点'):
    """校验"这次执行里的构建节点，我有没有权限点它"。"""
    sid = (cfg or {}).get('jenkins_server_id')
    job = str((cfg or {}).get('job') or '').strip()
    if not sid or not job:
        raise ValidationError('%s没有选择 Jenkins 服务器或 Job' % label)
    source = JenkinsServer.objects.filter(pk=sid).first()
    if source is None:
        raise ValidationError('%s选择的 Jenkins 服务器不存在' % label)
    allowed = jenkins_allowed_paths(user, source)
    if allowed is None:
        return
    if not allowed:
        raise PermissionDenied('无权在 Jenkins「%s」上构建任何 Job：未授予目录授权，请联系运维申请'
                               % (source.name or source.url))
    if not any(_path_matches(job, prefix) for prefix in allowed):
        raise PermissionDenied('无权构建 Jenkins Job「%s」：不在你被授权的目录内' % job)


# ===========================================================================
# 建执行记录
# ===========================================================================
def validate_params(pipeline, raw):
    """按流水线定义归一本次参数。缺必填 → 抛错。"""
    defs = pipeline.param_defs()
    raw = raw if isinstance(raw, dict) else {}
    out = {}
    for d in defs:
        key = d['key']
        value = raw.get(key)
        if value is None or value == '':
            value = d['default']
        value = '' if value is None else str(value)
        if d['required'] and not value:
            raise ValidationError({'params': '参数「%s」必填' % d['label']})
        out[key] = value[:512]
    # ★ 未在定义里出现的参数一律丢弃：模板能引用的键集合必须**等于**页面上看得到的键集合，
    #   否则会出现"某个值能影响发布结果，但界面上找不到它从哪来"的隐形输入。
    return out


def create_run(pipeline, raw_params, trigger_type, operator):
    """创建一次执行，并把节点**快照**成 node_run。

    ★ 快照而不是外键直连：编排页改一个字，历史记录不该跟着变。
    """
    if not getattr(pipeline, 'pk', None):
        raise ValidationError('流水线不存在')
    if pipeline.status != 1:
        raise ValidationError('流水线已停用，请先启用再执行')

    nodes = list(pipeline.nodes.order_by('seq', 'id'))
    if not nodes:
        raise ValidationError('该流水线还没有配置任何节点')

    params = validate_params(pipeline, raw_params)

    # ---- 授权关卡：逐节点逐目标校验（在人按下按钮的这一刻成立）----
    for node in nodes:
        cfg = node.config or {}
        if node.node_type in ('param', 'notify'):
            continue
        if node.node_type == 'build':
            # 构建节点没有目标机，但**必须过 Jenkins 目录授权**（否则流水线
            # 会把「按 dev/test/pre/prod 分环境授权」这条既有控制整个旁路掉）
            validate_build_access(operator, cfg, label='节点「%s」' % node.name)
            continue
        credential = _credential_for(pipeline, cfg)
        if credential is None:
            raise ValidationError('节点「%s」没有可用的凭据：请给流水线设置默认凭据，'
                                  '或在该节点上指定凭据' % node.name)
        validate_targets_for_run(operator, pipeline, credential, cfg.get('targets'),
                                 label='节点「%s」' % node.name)

    with transaction.atomic():
        run = PipelineRun.objects.create(
            pipeline=pipeline,
            pipeline_name=pipeline.name,
            status='pending',
            params=params,
            trigger_type=trigger_type,
            total_nodes=len(nodes),
            creator=operator,
        )
        PipelineNodeRun.objects.bulk_create([
            PipelineNodeRun(
                run=run,
                node=node,
                node_name=node.name,
                node_type=node.node_type,
                seq=node.seq,
                on_failure=node.on_failure,
                config=copy.deepcopy(node.config or {}),
                status='pending',
                creator=operator,
            )
            for node in nodes
        ])
    return run


# ===========================================================================
# 推进
# ===========================================================================
def _counters(run):
    rows = list(PipelineNodeRun.objects.filter(run=run).values_list('status', flat=True))
    total = len(rows)
    failed = sum(1 for s in rows if s == 'failed')
    pending = sum(1 for s in rows if s == 'pending')
    return {'total': total, 'failed': failed, 'pending': pending, 'done': total - pending}


def snapshot(run, with_results=False):
    """给前端的一次执行全貌。

    ``advance`` 与 ``retrieve`` 都用这一个函数 —— **形状只有一个**，
    前端不需要为"两个接口返回两种结构"各写一套解析（这是"两个真相"的温床）。

    ``with_results=True`` 时把每个节点的逐台结果（stdout/exit_code）一并带上。
    ★ 默认不带：``advance`` 会被前端循环调用，10 个节点 × 5 台 × 每条 20KB
      的 stdout 全带上，一次响应就上兆；而推进时前端并不需要历史节点的输出。
      完整输出走详情接口那一次。
    """
    run.refresh_from_db()
    rows = PipelineNodeRun.objects.filter(run=run).order_by('seq', 'id')
    nodes = []
    for r in rows:
        item = {
            'id': r.pk,
            'node_id': r.node_id,
            'seq': r.seq,
            'name': r.node_name,
            'node_type': r.node_type,
            'status': r.status,
            'status_label': dict(r._meta.get_field('status').choices).get(r.status, r.status),
            'message': r.message or '',
            'duration': r.duration,
            'on_failure': r.on_failure,
            'finished_at': r.finished_at.strftime('%Y-%m-%d %H:%M:%S') if r.finished_at else None,
            'result_count': len(r.targets_result or []),
        }
        if with_results:
            item['targets_result'] = r.targets_result or []
        nodes.append(item)
    return {
        'id': run.pk,
        'status': run.status,
        'status_label': dict(run._meta.get_field('status').choices).get(run.status, run.status),
        'is_final': run.is_final,
        'total_nodes': run.total_nodes,
        'done_nodes': run.done_nodes,
        'failed_nodes': run.failed_nodes,
        'current_node_id': run.current_node_id,
        'last_error': run.last_error or '',
        'started_at': run.started_at.strftime('%Y-%m-%d %H:%M:%S') if run.started_at else None,
        'finished_at': run.finished_at.strftime('%Y-%m-%d %H:%M:%S') if run.finished_at else None,
        'nodes': nodes,
    }


def advance_run(run_id, actor=None):
    """推进 ``run`` 的**下一个**待执行节点，返回执行后的全貌。

    到终态后再调是无害的（直接返回当前全貌）—— 前端可以无脑循环调用。
    """
    with transaction.atomic():
        run = PipelineRun.objects.select_for_update().get(pk=run_id)
        if run.status in RUN_FINAL_STATUS:
            return snapshot(run)

        nrun = (PipelineNodeRun.objects.select_for_update()
                .filter(run=run, status='pending').order_by('seq', 'id').first())
        if nrun is None:
            _finalize(run)
            return snapshot(run)

        if run.started_at is None:
            run.started_at = timezone.now()
        run.status = 'running'
        run.current_node_id = nrun.node_id
        run.save(update_fields=['status', 'current_node_id', 'started_at'])

        nrun.status = 'running'
        nrun.started_at = timezone.now()
        nrun.save(update_fields=['status', 'started_at'])
        nrun_id = nrun.pk

    # ---------------- 事务外：真正干活 ----------------
    started = time.monotonic()
    try:
        ok, message, results = execute_node(run, nrun)
    except Exception as exc:                                       # noqa: BLE001
        ok, message, results = False, '执行异常：%s' % exc, []
    duration = round(time.monotonic() - started, 3)

    # ---------------- 事务内：回写 ----------------
    with transaction.atomic():
        run = PipelineRun.objects.select_for_update().get(pk=run_id)
        nrun = PipelineNodeRun.objects.select_for_update().get(pk=nrun_id)

        nrun.status = 'success' if ok else 'failed'
        nrun.message = (message or '')[:512]
        nrun.targets_result = results
        nrun.finished_at = timezone.now()
        nrun.duration = duration
        nrun.save(update_fields=['status', 'message', 'targets_result', 'finished_at', 'duration'])

        _audit(run, nrun, results, actor)

        counters = _counters(run)
        finished = False
        if not ok and nrun.on_failure == 'stop':
            run.status = 'failed'
            run.last_error = '节点「%s」失败：%s' % (nrun.node_name, (message or '')[:400])
            finished = True
        elif counters['pending'] == 0:
            if counters['failed']:
                # ★ 有失败节点但被配置成「失败继续」⇒ 用 partial 表达，
                #   不要报 success（发布链路上"看起来成功"比"报错"危险得多）
                run.status = 'partial'
                run.last_error = '有 %d 个节点失败（节点配置为「失败继续」）' % counters['failed']
            else:
                run.status = 'success'
            finished = True
        else:
            run.status = 'running'

        run.total_nodes = counters['total']
        run.done_nodes = counters['done']
        run.failed_nodes = counters['failed']
        if finished:
            run.finished_at = timezone.now()
            run.current_node_id = None
        run.save(update_fields=['status', 'total_nodes', 'done_nodes', 'failed_nodes',
                                'finished_at', 'current_node_id', 'last_error'])

    return snapshot(run)


def _finalize(run):
    """没有待执行节点了 ⇒ 收口成终态。"""
    counters = _counters(run)
    if counters['failed']:
        run.status = 'partial'
        run.last_error = run.last_error or ('有 %d 个节点失败' % counters['failed'])
    else:
        run.status = 'success'
    run.total_nodes, run.done_nodes, run.failed_nodes = counters['total'], counters['done'], counters['failed']
    run.finished_at = timezone.now()
    run.current_node_id = None
    run.save(update_fields=['status', 'total_nodes', 'done_nodes', 'failed_nodes',
                            'finished_at', 'current_node_id', 'last_error'])


def _audit(run, nrun, results, actor):
    """把节点执行写进命令审计（``CommandLog``）。

    ★ 为什么接进既有审计流而不是另造一张表：运维查"这台机器上谁干了什么"时，
      只会看「命令审计」一个页面。发布命令散落在流水线自己的表里，等于没有留痕。
    """
    if nrun.node_type not in ('command', 'check'):
        return
    command = render_text((nrun.config or {}).get('command') or '', run.params or {})
    if not command:
        return
    creator_id = actor.pk if actor is not None else run.creator_id
    dangerous = is_dangerous_command(command)
    rows = []
    for item in (results or []):
        rows.append(CommandLog(
            session=None, dispatch=None, source='release', command=command,
            is_dangerous=dangerous, ip=item.get('ip') or '', creator_id=creator_id,
        ))
    if rows:
        CommandLog.objects.bulk_create(rows)


# ===========================================================================
# 节点执行
# ===========================================================================
def execute_node(run, nrun):
    """执行一个节点，返回 ``(ok, message, results)``。"""
    node_type = nrun.node_type
    cfg = nrun.config or {}
    params = run.params or {}
    pipeline = run.pipeline

    if node_type == 'param':
        filled = [k for k in (params or {})]
        return True, '参数已就绪（%s）' % ('、'.join(filled) if filled else '无'), []
    if node_type in ('command', 'check'):
        return _exec_command(pipeline, nrun, cfg, params)
    if node_type == 'upload':
        return _exec_upload(pipeline, nrun, cfg, params)
    if node_type == 'build':
        return _exec_build(cfg, params)
    if node_type == 'notify':
        return _exec_notify(run, nrun, cfg, params)
    return False, '未知的节点类型：%s' % node_type, []


def _collect(servers, worker_fn, wall_budget):
    """并发执行 + 总时长预算保护。``worker_fn(server)`` 返回 result dict。

    ★ 预算耗尽后**不再发起新连接**，剩下的目标直接标失败并写清原因 ——
      悄悄不发、或者假装成功，都是发布场景里最坏的形态。
    """
    results = []
    deadline = time.monotonic() + wall_budget
    workers = max(1, min(NODE_MAX_WORKERS, len(servers)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for server in servers:
            if time.monotonic() >= deadline:
                results.append({
                    'server_id': server.pk, 'label': server.hostname, 'ip': server.ip,
                    'ok': False, 'stdout': '', 'stderr': '', 'exit_code': None,
                    'duration': None,
                    'error': '节点总时长已达上限（%d 秒），本台未执行' % wall_budget,
                })
                continue
            futures[pool.submit(worker_fn, server, max(1, int(deadline - time.monotonic())))] = server
        for fut in as_completed(futures):
            server = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:                               # noqa: BLE001
                results.append({
                    'server_id': server.pk, 'label': server.hostname, 'ip': server.ip,
                    'ok': False, 'stdout': '', 'stderr': '', 'exit_code': None,
                    'duration': None, 'error': '执行异常：%s' % exc,
                })
    return results


def _summarize(results, noun='台'):
    total = len(results)
    ok_count = sum(1 for r in results if r.get('ok'))
    if not total:
        return False, '没有可执行的目标', results
    first_err = next((r.get('error') or r.get('stderr') or '' for r in results if not r.get('ok')), '')
    message = '%d/%d %s成功' % (ok_count, total, noun)
    if ok_count < total and first_err:
        message += '｜首个错误：' + str(first_err).strip().replace('\n', ' ')[:200]
    return ok_count == total, message, results


def _exec_command(pipeline, nrun, cfg, params):
    command = render_text(cfg.get('command') or '', params).strip()
    if not command:
        return False, '节点未配置要执行的命令', []
    if len(command) > 16384:
        return False, '命令过长（上限 16384 字符）', []

    credential = _credential_for(pipeline, cfg)
    if credential is None:
        return False, '没有可用的凭据（流水线默认凭据为空，且节点未指定）', []
    servers = resolve_servers(cfg.get('targets'))
    if not servers:
        return False, '没有可用的目标服务器（未选择，或资产已被删除）', []
    if len(servers) > MAX_TARGETS_PER_NODE:
        return False, '目标过多（%d 台，上限 %d 台）' % (len(servers), MAX_TARGETS_PER_NODE)

    timeout = _clamp_int(cfg.get('timeout'), 30, 1, MAX_NODE_TIMEOUT)
    payload = _credential_payload(credential)

    def _one(server, budget):
        # ★ 目标地址以 CMDB 为准（编排时存的 ip 只是快照）
        res = ssh_exec(
            host=server.ip, port=server.ssh_port or 22,
            username=payload['username'], auth_type=payload['auth_type'],
            password=payload['password'], private_key=payload['private_key'],
            command=command, timeout=min(timeout, budget),
        )
        ok = bool(res.get('ok')) and res.get('exit_code') == 0
        return {
            'server_id': server.pk, 'label': server.hostname, 'ip': server.ip,
            'ok': ok,
            'stdout': (res.get('stdout') or '')[:20000],
            'stderr': (res.get('stderr') or '')[:8000],
            'exit_code': res.get('exit_code'),
            'duration': res.get('duration'),
            'error': (res.get('error') or '')[:500] or ('' if ok else 'exit_code=%s' % res.get('exit_code')),
        }

    results = _collect(servers, _one, NODE_WALL_BUDGET)
    return _summarize(results)


def _exec_upload(pipeline, nrun, cfg, params):
    local_raw = render_text(cfg.get('local_path') or '', params).strip()
    remote = render_text(cfg.get('remote_path') or '', params).strip()
    try:
        abs_path, size = resolve_local_path(local_raw)
    except ValueError as exc:
        return False, str(exc), []
    if not remote.startswith('/'):
        return False, '目标机路径必须是绝对路径（如 /opt/app/app.jar）', []

    credential = _credential_for(pipeline, cfg)
    if credential is None:
        return False, '没有可用的凭据（流水线默认凭据为空，且节点未指定）', []
    servers = resolve_servers(cfg.get('targets'))
    if not servers:
        return False, '没有可用的目标服务器（未选择，或资产已被删除）', []
    if len(servers) > MAX_TARGETS_PER_NODE:
        return False, '目标过多（%d 台，上限 %d 台）' % (len(servers), MAX_TARGETS_PER_NODE)

    payload = _credential_payload(credential)

    def _one(server, budget):
        res = sftp_put(
            host=server.ip, port=server.ssh_port or 22,
            username=payload['username'], auth_type=payload['auth_type'],
            password=payload['password'], private_key=payload['private_key'],
            local_path=abs_path, remote_path=remote, timeout=max(10, min(60, budget)),
        )
        return {
            'server_id': server.pk, 'label': server.hostname, 'ip': server.ip,
            'ok': bool(res.get('ok')),
            'stdout': '%d 字节 → %s' % (res.get('bytes') or 0, remote),
            'stderr': '', 'exit_code': 0 if res.get('ok') else None,
            'duration': res.get('duration'),
            'error': (res.get('error') or '')[:500],
        }

    results = _collect(servers, _one, NODE_WALL_BUDGET)
    ok, message, out = _summarize(results)
    if ok:
        message = '%d/%d 台上传成功（%d 字节 → %s）' % (len(out), len(out), size, remote)
    return ok, message, out


# ---------------------------------------------------------------------------
# Jenkins：触发构建并等结果
# ---------------------------------------------------------------------------
def _jenkins_crumb(session, base, auth):
    try:
        resp = session.get(base + '/crumbIssuer/api/json', auth=auth, timeout=10, allow_redirects=False)
        if resp.status_code != 200:
            return None
        body = resp.json()
        field, value = body.get('crumbRequestField'), body.get('crumb')
        if field and value:
            return field, value
    except Exception:                                              # noqa: BLE001
        return None
    return None


def _jenkins_path(job):
    """``dev/中心/backend`` → ``/job/dev/job/中心/job/backend``。

    与 `jenkins/views/jenkins.py::_jenkins_path` 同口径（嵌套 folder 每层都要 /job/）。
    """
    parts = str(job).split('/')
    if any(p in ('', '.', '..') or '\\' in p for p in parts):
        raise ValueError('Job 路径包含非法路径段')
    return '/job/' + '/job/'.join(parts)


def _jenkins_last_build(session, base, jpath, auth):
    try:
        resp = session.get(base + jpath + '/lastBuild/api/json',
                           auth=auth, params={'tree': 'number,building,result'},
                           timeout=15, allow_redirects=False)
        if resp.status_code != 200:
            return None
        body = resp.json()
        return body if isinstance(body, dict) else None
    except Exception:                                              # noqa: BLE001
        return None


def _jenkins_trigger(session, base, jpath, auth, parameters):
    """触发构建。**有参数走 buildWithParameters、无参数先走 build，400 再降级**。

    与 `jenkins/views/jenkins.py::build` 同一套逻辑：参数化 Job（含参数只写在
    Jenkinsfile 里的 Pipeline Job）走 `/build` 会返回 400 "Nothing is submitted"。
    """
    headers = {}
    crumb = _jenkins_crumb(session, base, auth)
    if crumb:
        headers[crumb[0]] = crumb[1]

    def _post(endpoint):
        url = base + jpath + '/' + endpoint
        data = dict(parameters or {}) if endpoint == 'buildWithParameters' else {}
        return session.post(url, auth=auth, headers=headers, data=data, timeout=30, allow_redirects=False)

    endpoint = 'buildWithParameters' if parameters else 'build'
    resp = _post(endpoint)
    if resp.status_code in (200, 201, 302):
        return True, ''
    if resp.status_code == 400 and endpoint == 'build':
        resp = _post('buildWithParameters')
        if resp.status_code in (200, 201, 302):
            return True, ''
    if resp.status_code == 403:
        # crumb 过期：重取一次再试
        crumb = _jenkins_crumb(session, base, auth)
        headers = {crumb[0]: crumb[1]} if crumb else {}
        resp = _post(endpoint)
        if resp.status_code in (200, 201, 302):
            return True, ''
    return False, 'HTTP %s' % resp.status_code


def _exec_build(cfg, params):
    sid = cfg.get('jenkins_server_id')
    job = render_text(cfg.get('job') or '', params).strip()
    if not sid:
        return False, '节点未选择 Jenkins 服务器', []
    if not job:
        return False, '节点未选择要构建的 Job', []
    source = JenkinsServer.objects.filter(pk=sid).first()
    if source is None:
        return False, 'Jenkins 服务器不存在（id=%s）' % sid, []

    raw_params = cfg.get('parameters') or {}
    if not isinstance(raw_params, dict):
        return False, '构建参数格式错误（应为 JSON 对象）', []
    build_params = {str(k): render_text(v, params) for k, v in raw_params.items()}

    wait = _clamp_int(cfg.get('wait_timeout'), MAX_BUILD_WAIT, 30, MAX_BUILD_WAIT)
    base = (source.url or '').strip().rstrip('/')
    if not base:
        return False, 'Jenkins 地址为空', []
    try:
        jpath = _jenkins_path(job)
    except ValueError as exc:
        return False, str(exc), []

    auth = jenkins_auth(source)
    session = requests.Session()
    started = time.monotonic()

    before = _jenkins_last_build(session, base, jpath, auth)
    before_number = (before or {}).get('number')
    if before and before.get('building'):
        return False, '该 Job 正在构建中（#%s），请等它结束后再执行流水线' % before_number, []

    ok, err = _jenkins_trigger(session, base, jpath, auth, build_params)
    if not ok:
        return False, '触发构建失败：%s（Job=%s）' % (err, job), []

    deadline = time.monotonic() + wait
    result, number = None, None
    while time.monotonic() < deadline:
        time.sleep(BUILD_POLL_INTERVAL)
        info = _jenkins_last_build(session, base, jpath, auth)
        if not info:
            continue
        num = info.get('number')
        if before_number is not None and num == before_number:
            continue
        number = num
        if info.get('building'):
            continue
        result = info.get('result')
        break

    duration = round(time.monotonic() - started, 3)
    if number is None or result is None:
        return False, ('等待构建结果超时（%d 秒）：构建可能仍在 Jenkins 上运行，'
                       '请到 Jenkins 查看 #%s' % (wait, number or '?')), [{
            'label': job, 'ip': base, 'ok': False, 'stdout': '', 'stderr': '',
            'exit_code': None, 'duration': duration, 'error': '等待超时',
        }]

    entry = {
        'label': job, 'ip': base, 'ok': result == 'SUCCESS',
        'stdout': 'Jenkins #%s 结果：%s' % (number, result),
        'stderr': '', 'exit_code': 0 if result == 'SUCCESS' else 1,
        'duration': duration,
        'error': '' if result == 'SUCCESS' else 'Jenkins 构建结果 %s' % result,
    }
    return result == 'SUCCESS', 'Jenkins #%s 构建%s' % (number, result), [entry]


# ---------------------------------------------------------------------------
# 通知
# ---------------------------------------------------------------------------
def _send_to_channel(channel, content):
    """按渠道类型发送。与 `alert/services.py::dispatch_alerts` 同一套发送器。"""
    from dvadmin.alert.secrets import decrypt_config
    from dvadmin.alert.services import send_dingtalk, send_email, send_feishu, send_wechat

    try:
        cfg = decrypt_config(channel.config)
    except Exception:                                              # noqa: BLE001
        return False, '渠道密钥读取失败'
    if not isinstance(cfg, dict):
        return False, '渠道配置类型错误（应为 JSON 对象）'
    webhook = cfg.get('webhook', '')
    try:
        if channel.type == 'feishu':
            if not webhook:
                return False, '缺少 webhook'
            ok, _resp = send_feishu(webhook, content)
        elif channel.type == 'dingtalk':
            if not webhook:
                return False, '缺少 webhook'
            ok, _resp = send_dingtalk(webhook, content, cfg.get('secret'))
        elif channel.type == 'wechat':
            if not webhook:
                return False, '缺少 webhook'
            ok, _resp = send_wechat(webhook, content)
        elif channel.type == 'email':
            ok, _resp = send_email(cfg, content)
        else:
            return False, '未知渠道类型 %s' % channel.type
    except Exception as exc:                                       # noqa: BLE001
        return False, '发送失败：%s' % exc
    return bool(ok), '发送成功' if ok else '发送失败'


def _exec_notify(run, nrun, cfg, params):
    from dvadmin.alert.models import NotifyChannel

    channel_id = cfg.get('channel_id')
    channel = NotifyChannel.objects.filter(pk=channel_id, enabled=True).first() if channel_id else None
    if channel is None:
        return False, '通知渠道不存在或已停用', []

    # 本次结果：只要**已经**有失败节点就算 failure
    had_failure = PipelineNodeRun.objects.filter(run=run, status='failed').exclude(pk=nrun.pk).exists()
    actual = 'failure' if had_failure else 'success'
    want = cfg.get('on') or 'always'
    if want != 'always' and want != actual:
        return True, '本次结果（%s）与通知条件（%s）不符，按配置跳过' % (actual, want), []

    status_text = dict(PipelineNodeRun._meta.get_field('status').choices).get(actual, actual)
    title = render_text(cfg.get('title') or '', params).strip() or '流水线通知'
    content = render_text(cfg.get('content') or '', params).strip()
    if not content:
        content = ('流水线：%s\n本次参数：%s\n当前节点：%s\n执行结果：%s'
                   % (run.pipeline_name or '-',
                      '、'.join('%s=%s' % (k, v) for k, v in (run.params or {}).items()) or '无',
                      nrun.node_name or '-', status_text))
    text = '%s\n%s' % (title, content)
    ok, message = _send_to_channel(channel, text)
    entry = {
        'label': channel.name, 'ip': channel.type, 'ok': ok,
        'stdout': message, 'stderr': '', 'exit_code': 0 if ok else 1,
        'duration': None, 'error': '' if ok else message,
    }
    return ok, '%s：%s' % (channel.name, message), [entry]


__all__ = [
    'advance_run', 'create_run', 'execute_node', 'render_text', 'resolve_servers',
    'snapshot', 'validate_params', 'validate_targets_for_run', 'PermissionDenied',
]
