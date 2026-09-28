# -*- coding: utf-8 -*-
"""CMDB 资产授权（``cmdb_server_grant``）的唯一判定入口。

为什么要有这一层
----------------
"服务器"是整个平台的**资源主键**——命令下发、Web SSH、凭据、会话录像、命令审计、
首页统计，全都以它为操作对象。如果每个入口各写一遍授权判断，迟早会漏一个，
而漏掉的那个就是绕过口。所以所有入口统一走这三个函数：

=====================================  ==========================================================
调用方                                  用途
=====================================  ==========================================================
``cmdb/views/server.py``               列表/详情 ``get_queryset``、命令下发下拉 ``dispatch_options``
``cmdb/views/server_grant.py``         授权配置本身（仅资产运营者可写）
``bastion/views/dispatch.py``          命令下发：创建时**逐目标**校验 write 级别
``bastion/views/terminal.py``          Web SSH：签发一次性 ticket 前校验 write 级别
``bastion/consumers.py``               WebSocket 建连 / 会话中定时复检
``application/dashboard.py``           首页服务器统计按"可见集合"计算
=====================================  ==========================================================

授权判定（`ServerGrant` 表的语义见 ``cmdb/models.py::ServerGrant``）
-------------------------------------------------------------------
1. 超级管理员 → 全部服务器，write
2. **资产运营者**：持有 ``server:Create`` / ``server:Update`` / ``server:Delete``
   任一按钮权限的角色（= 运维 / 管理员）→ 全部服务器，write
3. 其余用户 → 只认 ``ServerGrant``：``role`` 命中（用户所属任一角色）或 ``user`` 命中；
   同一台服务器命中多条时取**最高**级别
4. 无命中 → 看不到、做不了（**fail closed**）

fail closed 是刻意的：新增用户忘了配授权，结果是"他什么都看不到"而不是
"他什么都能干"。前者会被投诉后立刻修好，后者不会有人发现。

文件授权兼容
------------
旧版本用 ``BASTION_ACCESS_FILE`` 指向的 JSON 文件按**用户名**授权：

.. code-block:: json

    {"dev1": {"actions": ["ssh", "dispatch"], "server_ids": [1, 2], "credential_ids": "*"}}

该文件若存在，仍会**叠加**在 DB 授权之上（取并集），保证从文件迁移到 DB 期间
不会把已有用户锁死。确认迁移完成后设 ``BASTION_ACCESS_FILE_DISABLED=1``
即可彻底关掉文件回退，让 DB 成为唯一事实来源。
"""

import json
import os
from pathlib import Path

from rest_framework.exceptions import PermissionDenied

# 动作 → 所需最低授权级别
ACTION_MIN_LEVEL = {
    'ssh': 'write',
    'dispatch': 'write',
}

GRANT_READ = 'read'
GRANT_WRITE = 'write'

_FILE_ACTION_LEVEL = {'ssh': GRANT_WRITE, 'dispatch': GRANT_WRITE}


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------
def _level_rank(level):
    return {'read': 1, 'write': 2}.get(level, 0)


def _level_for(levels, server_id):
    return levels.get(server_id, '')


# ---------------------------------------------------------------------------
# 身份判定
# ---------------------------------------------------------------------------
def is_asset_admin(user):
    """资产运营者：超管，或持有 ``server:Create`` / ``server:Update`` / ``server:Delete``
    中任一的角色。这类角色可以管理全部服务器资产（但不因此获得别模块的权限）。"""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    try:
        from dvadmin.utils.perm_helper import has_button
    except Exception:
        return False
    return has_button(user, 'server:Create', 'server:Update', 'server:Delete')


# ---------------------------------------------------------------------------
# DB 授权
# ---------------------------------------------------------------------------
def user_grant_levels(user):
    """普通用户在 ``ServerGrant`` 里的授权：``{server_id: 'read'|'write'}``。

    同一台服务器命中多条（例如"给运维组 write" + "给某人 read"）时取最高级别。
    不做缓存：一次请求内可能被调用多次，但结果依赖 DB，缓存反而会掩盖刚改的授权。
    """
    from django.db.models import Q

    from dvadmin.cmdb.models import ServerGrant

    if not user or not getattr(user, 'is_authenticated', False):
        return {}

    role_ids = []
    if hasattr(user, 'role'):
        role_ids = list(user.role.values_list('id', flat=True))

    cond = Q(user=user)
    if role_ids:
        cond |= Q(role__in=role_ids)

    levels = {}
    for sid, lvl in ServerGrant.objects.filter(cond).values_list('server_id', 'level'):
        if sid is None:
            continue
        if _level_rank(lvl) > _level_rank(levels.get(sid, '')):
            levels[sid] = lvl
    return levels


# ---------------------------------------------------------------------------
# 文件授权（兼容层，逐步废弃）
# ---------------------------------------------------------------------------
def _file_grant(user):
    """读旧的 JSON 授权文件，返回 ``{server_id: level}``；文件不存在/损坏 → 空。"""
    if os.environ.get('BASTION_ACCESS_FILE_DISABLED') == '1':
        return {}
    path = os.environ.get('BASTION_ACCESS_FILE', '/backend/conf/bastion_access.json')
    try:
        grants = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    if not isinstance(grants, dict):
        return {}
    grant = grants.get(user.username)
    if not isinstance(grant, dict):
        return {}

    actions = grant.get('actions') or []
    # 该用户在文件里被允许的动作 → 能拿到哪一级别
    level = ''
    for act in actions:
        lvl = _FILE_ACTION_LEVEL.get(act, '')
        if _level_rank(lvl) > _level_rank(level):
            level = lvl
    if not level:
        return {}

    server_ids = grant.get('server_ids', [])
    if server_ids == '*':
        from dvadmin.cmdb.models import Server
        return {sid: level for sid in Server.objects.values_list('id', flat=True)}
    if not isinstance(server_ids, list):
        return {}
    out = {}
    for sid in server_ids:
        try:
            out[int(sid)] = level
        except (TypeError, ValueError):
            continue
    return out


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------
def grant_levels(user):
    """用户在每台服务器上的有效级别 ``{server_id: 'read'|'write'}``；
    ``None`` 表示"不受限"（超管 / 资产运营者）。"""
    if not user or not getattr(user, 'is_authenticated', False):
        return {}
    if is_asset_admin(user):
        return None

    levels = user_grant_levels(user)
    # 文件授权叠加（取最高）
    for sid, lvl in _file_grant(user).items():
        if _level_rank(lvl) > _level_rank(levels.get(sid, '')):
            levels[sid] = lvl
    return levels


def visible_server_ids(user):
    """可**查看**的服务器 id 列表；``None`` 表示全部（超管 / 资产运营者）。"""
    levels = grant_levels(user)
    if levels is None:
        return None
    return sorted(levels.keys())


def writable_server_ids(user):
    """可**操作**（下发命令 / Web SSH）的服务器 id 列表；``None`` 表示全部。"""
    levels = grant_levels(user)
    if levels is None:
        return None
    return sorted(sid for sid, lvl in levels.items() if lvl == GRANT_WRITE)


def restrict_servers(queryset, user):
    """把服务器 queryset 裁剪到当前用户可见范围。超管/运营者原样返回。"""
    ids = visible_server_ids(user)
    return queryset if ids is None else queryset.filter(pk__in=ids)


def visible_credential_queryset(user, queryset=None):
    """用户**可用**的凭据集合（命令下发 / Web SSH / AI 问答的凭据下拉共用）。

    ★ 本函数是从 ``bastion/views/credential.py::CredentialViewSet._visible_queryset``
      原样抽出来的 —— AI 问答也要一份"我能选哪些凭据"，如果各写一遍，
      迟早会出现"某个入口能选到越权凭据"的口子。

    口径：
      · 超管 / 资产运营者 → 全部凭据
      · 其余用户 → 绑定到其**可见服务器**的凭据 + 未绑定服务器的**通用凭据**

    为什么通用凭据也要放出来：``require_access`` 只禁止"凭据绑定的服务器 != 目标服务器"
    的串用，并未禁止通用凭据。若把它藏起来，被授权用户会"看得到服务器却选不到凭据"，
    功能直接不可用。而凭据接口只返回元信息（名称/用户名/是否已配置），不含任何密钥明文。
    """
    from django.db.models import Q

    from dvadmin.bastion.models import Credential

    qs = Credential.objects.all() if queryset is None else queryset
    if is_asset_admin(user):
        return qs
    ids = visible_server_ids(user)
    if ids is None:
        return qs
    if not ids:
        return qs.filter(server__isnull=True)
    return qs.filter(Q(server_id__in=ids) | Q(server__isnull=True)).distinct()


def restrict_servers_by_field(queryset, user, field='server_id'):
    """按 ``server_id`` 之类的字段裁剪**非服务器**表（会话 / 命令审计 / 凭据 / 下发）。

    非运营者只能看到与自己被授权服务器相关的记录。抽成函数是为了让
    session / command_log / credential / dispatch 四个 ViewSet 口径一致。
    """
    ids = visible_server_ids(user)
    if ids is None:
        return queryset
    return queryset.filter(**{field + '__in': ids})


def visible_server_ips(user):
    """可查看范围对应的服务器 IP 集合；``None`` 表示全部。

    ``CommandLog`` 表没有 ``server`` 外键（只有目标 ``ip`` 字段），所以命令审计的
    裁剪只能按 IP 做。返回 ``set`` 方便直接与其它来源求交。
    """
    from dvadmin.cmdb.models import Server

    ids = visible_server_ids(user)
    if ids is None:
        return None
    if not ids:
        return set()
    ips = set()
    for ip, extra in Server.objects.filter(pk__in=ids).values_list('ip', 'extra_ips'):
        if ip:
            ips.add(ip.strip())
        # extra_ips 是逗号分隔的多网卡地址，审计记录的 ip 可能是其中任意一个
        for one in (extra or '').split(','):
            one = one.strip()
            if one:
                ips.add(one)
    return ips


def restrict_command_log(queryset, user):
    """按可见服务器的 IP 裁剪命令审计 queryset。

    命中范围用 ``ip`` 而不是 join ``session__server`` / ``dispatch__items__server``，
    因为一条日志只会出现一次，join 会引入去重（``.distinct()``）开销；
    且历史日志的 ``server`` 可能已被删除（``SET_NULL``），按 IP 比对更稳。
    """
    ips = visible_server_ips(user)
    if ips is None:
        return queryset
    return queryset.filter(ip__in=ips)


def require_access(user, server, credential, action):
    """校验"对该服务器执行某动作"。不通过直接抛 ``PermissionDenied``。

    :param action: ``'ssh'`` 或 ``'dispatch'``——两者都要求 ``write`` 级别。
    """
    if not user or not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_active', True):
        raise PermissionDenied('用户未登录或已停用')

    need = ACTION_MIN_LEVEL.get(action)
    if not need:
        raise PermissionDenied('未知的操作类型：%s' % action)

    if server is None:
        raise PermissionDenied('目标服务器不存在')
    if credential is None:
        raise PermissionDenied('必须选择凭据')

    levels = grant_levels(user)
    if levels is not None:
        level = levels.get(server.pk, '')
        if _level_rank(level) < _level_rank(need):
            if level == GRANT_READ:
                raise PermissionDenied('对服务器「%s」只有只读授权，不能下发命令 / 建立 SSH 会话'
                                       % (server.hostname or server.ip))
            raise PermissionDenied('无权操作服务器「%s」：未授予资产授权，请联系运维申请'
                                   % (server.hostname or server.ip))

    # 跨表一致性：凭据绑定到别的服务器时不允许串用
    if credential.server_id and credential.server_id != server.pk:
        raise PermissionDenied('凭据绑定的服务器与目标服务器不一致')

    if server.status != 'online':
        raise PermissionDenied('服务器不在线或已停用，无法执行操作')
