# -*- coding: utf-8 -*-
"""
命令下发并发执行器：ThreadPoolExecutor + paramiko
- execute_dispatch(dispatch_id, max_workers=None, retry_failed=False)
  * max_workers：并发数，默认取 dispatch.max_workers
  * retry_failed=True：只重跑 failed/timeout 的 item，其余保留原结果
- 每次执行都会写 CommandLog 命令审计（审计留痕）
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .models import CommandDispatch, CommandDispatchItem, CommandLog, is_dangerous_command
from .ssh_client import ssh_exec


def _run_one(item, command, credential_payload, timeout):
    """单条执行。credential_payload = {username, auth_type, password, private_key}"""
    try:
        res = ssh_exec(
            host=item.ip,
            port=item.ssh_port or 22,
            username=credential_payload.get('username') or 'root',
            auth_type=credential_payload.get('auth_type') or 'password',
            password=credential_payload.get('password'),
            private_key=credential_payload.get('private_key'),
            command=command,
            timeout=timeout,
        )
        if res.get('error'):
            item.status = 'failed'
            item.error = res['error'][:500]
            item.duration = res.get('duration')
        elif res.get('exit_code') == 0:
            item.status = 'success'
            item.stdout = res.get('stdout') or ''
            item.stderr = res.get('stderr') or ''
            item.exit_code = res.get('exit_code')
            item.duration = res.get('duration')
        else:
            item.status = 'failed'
            item.stdout = res.get('stdout') or ''
            item.stderr = res.get('stderr') or ''
            item.exit_code = res.get('exit_code')
            item.duration = res.get('duration')
            item.error = f'exit_code={res.get("exit_code")}'
    except Exception as e:
        msg = str(e) or e.__class__.__name__
        item.status = 'failed' if 'Timeout' not in msg and 'timed out' not in msg else 'timeout'
        item.error = msg[:500]
        item.duration = None
    return item


def _aggregate(dispatch):
    """重新聚合 total/success/failed + 状态"""
    items = list(CommandDispatchItem.objects.filter(dispatch=dispatch))
    total = len(items)
    succ = sum(1 for it in items if it.status == 'success')
    dispatch.total = total
    dispatch.success_count = succ
    dispatch.failed_count = total - succ
    if total and total == succ:
        dispatch.status = 'success'
    elif succ == 0:
        dispatch.status = 'failed'
    else:
        dispatch.status = 'partial'


def execute_dispatch(dispatch_id, max_workers=None, retry_failed=False):
    """
    执行一个下发任务：
    1. 拉取 dispatch + 待执行 items（retry 时只取 failed/timeout）
    2. 解密凭据
    3. ThreadPoolExecutor 并发执行（并发数取 dispatch.max_workers）
    4. 回写每条 item，写 CommandLog 审计，聚合 status
    """
    dispatch = CommandDispatch.objects.get(id=dispatch_id)

    # 待执行 items：retry 只跑失败项
    if retry_failed:
        items = list(CommandDispatchItem.objects.filter(
            dispatch=dispatch, status__in=['failed', 'timeout']
        ))
    else:
        items = list(CommandDispatchItem.objects.filter(dispatch=dispatch))

    if not items:
        dispatch.status = 'failed' if not retry_failed else dispatch.status
        dispatch.last_error = '没有可执行的目标' if not items else ''
        dispatch.finished_at = datetime.now()
        dispatch.save(update_fields=['status', 'last_error', 'finished_at'])
        return dispatch

    dispatch.status = 'running'
    dispatch.started_at = datetime.now()
    dispatch.last_error = ''
    dispatch.save(update_fields=['status', 'started_at', 'last_error'])

    # 解密凭据
    credential_payload = {
        'username': 'root',
        'auth_type': 'password',
        'password': None,
        'private_key': None,
    }
    if dispatch.credential_id:
        cred = dispatch.credential
        credential_payload = {
            'username': cred.username or 'root',
            'auth_type': cred.auth_type,
            'password': cred.get_password() if cred.auth_type == 'password' else None,
            'private_key': cred.get_private_key() if cred.auth_type == 'private_key' else None,
        }

    timeout = dispatch.timeout or 30
    workers = max_workers or dispatch.max_workers or 10
    workers = max(1, min(int(workers), 50))

    # 高危命令判断（任务级，所有目标相同）
    dangerous = is_dangerous_command(dispatch.command)

    futures = {}
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(items)))) as pool:
        for it in items:
            futures[pool.submit(_run_one, it, dispatch.command, credential_payload, timeout)] = it

        agg_err = ''
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as e:
                agg_err = (agg_err + '; ' if agg_err else '') + str(e)

    CommandDispatchItem.objects.bulk_update(items, ['status', 'stdout', 'stderr', 'exit_code', 'duration', 'error'])

    # 命令审计留痕：为本次执行的每台目标写 CommandLog
    creator_id = dispatch.creator_id
    logs = [
        CommandLog(
            dispatch=dispatch,
            session=None,
            source='dispatch',
            command=dispatch.command,
            is_dangerous=dangerous,
            ip=it.ip,
            creator_id=creator_id,
        )
        for it in items
    ]
    CommandLog.objects.bulk_create(logs)

    # 聚合
    _aggregate(dispatch)
    dispatch.finished_at = datetime.now()
    if agg_err:
        dispatch.last_error = agg_err[:2000]
    dispatch.save(update_fields=['total', 'success_count', 'failed_count', 'status', 'finished_at', 'last_error'])
    return dispatch
