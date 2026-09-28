# -*- coding: utf-8 -*-
"""服务器资产授权（``cmdb_server_grant``）的配置接口。

只有**资产运营者**（超级管理员，或持有 ``server:Create`` / ``server:Update`` /
``server:Delete`` 任一按钮权限的角色，即运维 / 管理员）可以读写。

两道关卡，刻意重复：
1. ``CustomPermission`` 按 ``serverGrant:*`` 按钮权限判定（框架层）
2. ``AssetAdminPermission`` 在代码里再判一次（业务层）

为什么要有第 2 道：``CustomPermission`` 是按 URL+method 匹配 MenuButton 的，
**只要有人往 MenuButton 表里加一条指向本 ViewSet 的记录、又勾给了别的角色**，
第 1 道就被打开了。资产授权是整个权限体系的地基，不该只靠一张配置表守着。
"""
from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission

from dvadmin.bastion.access import is_asset_admin
from dvadmin.cmdb.models import GRANT_LEVEL_CHOICES, Server, ServerGrant
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet

LEVEL_KEYS = tuple(k for k, _ in GRANT_LEVEL_CHOICES)


class AssetAdminPermission(BasePermission):
    """谁能管理资产授权。

    两条路：
    1. **资产运营者**（超管 / 运维 / 管理员）——在「服务器管理」页给单台服务器配
    2. **能配角色权限的人**（``role:SetMenu``）——在「角色管理」页给某个角色配

    第 2 条是必需的：角色管理页里的「服务器资产授权」面板要按角色视角读写，
    而那个操作者天然是管理员，未必持有 ``server:Update``。
    """

    message = '仅运维或管理员可管理资产授权'

    def has_permission(self, request, view):
        user = request.user
        if is_asset_admin(user):
            return True
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'is_superuser', False):
            return True
        try:
            from dvadmin.utils.perm_helper import has_button
        except Exception:
            return False
        return has_button(user, 'role:SetMenu')


class ServerGrantSerializer(CustomModelSerializer):
    server_name = serializers.CharField(source='server.hostname', read_only=True, default=None)
    server_ip = serializers.CharField(source='server.ip', read_only=True, default=None)
    role_name = serializers.CharField(source='role.name', read_only=True, default=None)
    user_name = serializers.SerializerMethodField()
    level_label = serializers.SerializerMethodField()
    grantee = serializers.SerializerMethodField()

    def get_user_name(self, obj):
        if not obj.user_id or not obj.user:
            return None
        return obj.user.name or obj.user.username

    def get_level_label(self, obj):
        return dict(GRANT_LEVEL_CHOICES).get(obj.level, obj.level)

    def get_grantee(self, obj):
        """统一的「授权对象」展示：角色优先，其次用户。"""
        if obj.role_id and obj.role:
            return {'type': 'role', 'id': obj.role_id, 'name': obj.role.name}
        if obj.user_id and obj.user:
            return {'type': 'user', 'id': obj.user_id, 'name': obj.user.name or obj.user.username}
        return None

    def validate(self, attrs):
        role = attrs.get('role') or getattr(self.instance, 'role', None)
        user = attrs.get('user') or getattr(self.instance, 'user', None)
        if not role and not user:
            raise ValidationError('「授权角色」和「授权用户」至少要填一个')
        level = attrs.get('level') or getattr(self.instance, 'level', 'read')
        if level not in LEVEL_KEYS:
            raise ValidationError('授权级别只能是 read 或 write')
        return super().validate(attrs)

    class Meta:
        model = ServerGrant
        fields = '__all__'
        read_only_fields = ['id']


class ServerGrantViewSet(CustomModelViewSet):
    """服务器资产授权

    - ``list`` / ``retrieve``：某台服务器授权给了谁
    - ``create`` / ``update`` / ``destroy``：逐条维护
    - ``set_grants``：**整体覆盖**某台服务器的授权（推荐入口，原子操作）
    """
    queryset = ServerGrant.objects.select_related('server', 'role', 'user').all()
    serializer_class = ServerGrantSerializer
    search_fields = ['server__hostname', 'server__ip', 'role__name', 'user__username', 'user__name']
    filter_fields = ['server', 'role', 'user', 'level']
    permission_classes = [AssetAdminPermission]
    extra_filter_class = []

    @staticmethod
    def _to_int(value, label, idx):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError('第 %d 项 %s 必须是整数' % (idx, label))

    @action(methods=['GET'], detail=False, url_path='options')
    def options(self, request, *args, **kwargs):
        """授权弹窗的下拉数据：可授权的角色 + 用户。

        单独开一个接口而不是让前端去调 ``/api/system/role/`` 和
        ``/api/system/user/``：那两个接口属于「系统管理」模块，普通运维角色
        往往没有它们的按钮权限（P0 修正时刻意**排除**了 ``role:`` / ``user:`` 前缀），
        直接复用会变成"有授权能力却打不开授权弹窗"。这里只吐 id + 名称，
        权限由 ``AssetAdminPermission`` 统一把守。
        """
        from dvadmin.system.models import Role, Users

        roles = list(Role.objects.filter(status=1).order_by('id').values('id', 'name', 'key'))
        users = list(
            Users.objects.filter(is_active=True).order_by('id')
            .values('id', 'username', 'name')
        )
        return DetailResponse(data={'roles': roles, 'users': users}, msg='获取成功')

    @action(methods=['POST'], detail=True, url_path='set_grants')
    @transaction.atomic
    def set_grants(self, request, pk=None):
        """整体覆盖某台服务器的授权。

        请求体::

            {"grants": [
                {"role": 4, "level": "write"},
                {"role": 6, "level": "read"},
                {"user": 6, "level": "write"}
            ]}

        传空数组 ``{"grants": []}`` 表示**收回全部授权**（此后该服务器只对运维/管理员可见）。

        为什么提供整体覆盖而不是逐条增删：前端授权弹窗是"勾选完一次保存"的交互，
        逐条 diff 需要前端自己算差异，任何一次失败都会留下半套授权。
        这里在事务里一次性重建，要么全生效要么全不生效。
        """
        try:
            server = Server.objects.get(pk=pk)
        except Server.DoesNotExist:
            raise ValidationError('服务器不存在')

        raw = request.data.get('grants')
        if raw is None:
            raise ValidationError('缺少 grants 字段（传空数组表示收回全部授权）')
        if not isinstance(raw, list):
            raise ValidationError('grants 必须是数组')

        from dvadmin.system.models import Role, Users

        rows = []
        seen = set()
        for i, item in enumerate(raw):
            idx = i + 1
            if not isinstance(item, dict):
                raise ValidationError('第 %d 项格式错误：应为对象' % idx)
            role_id, user_id = item.get('role'), item.get('user')
            if not role_id and not user_id:
                raise ValidationError('第 %d 项缺少 role 或 user' % idx)
            if role_id and user_id:
                raise ValidationError('第 %d 项 role 与 user 只能填一个' % idx)

            level = item.get('level') or 'read'
            if level not in LEVEL_KEYS:
                raise ValidationError('第 %d 项 level 只能是 %s' % (idx, ' / '.join(LEVEL_KEYS)))

            if role_id:
                role_id = self._to_int(role_id, 'role', idx)
                if not Role.objects.filter(pk=role_id).exists():
                    raise ValidationError('第 %d 项角色不存在：%s' % (idx, role_id))
                user_id = None
                key = ('role', role_id)
            else:
                user_id = self._to_int(user_id, 'user', idx)
                if not Users.objects.filter(pk=user_id).exists():
                    raise ValidationError('第 %d 项用户不存在：%s' % (idx, user_id))
                role_id = None
                key = ('user', user_id)

            if key in seen:
                continue  # 静默去重：前端重复勾选不应直接报错
            seen.add(key)
            rows.append({
                'server_id': server.pk,
                'role_id': role_id,
                'user_id': user_id,
                'level': level,
            })

        ServerGrant.objects.filter(server=server).delete()
        if rows:
            ServerGrant.objects.bulk_create([ServerGrant(**r) for r in rows])

        saved = ServerGrant.objects.select_related('role', 'user').filter(server=server)
        return DetailResponse(
            data={'server_id': server.pk, 'count': len(rows),
                  'grants': ServerGrantSerializer(saved, many=True).data},
            msg='授权已保存（共 %d 条）' % len(rows),
        )

    # ------------------------------------------------------------
    # 角色视角（供「角色管理」页的资产授权面板使用）
    # ------------------------------------------------------------
    @staticmethod
    def _role_of(request):
        from dvadmin.system.models import Role

        raw = request.query_params.get('role_id')
        if raw is None:
            raw = (request.data or {}).get('role_id')
        try:
            return Role.objects.filter(pk=int(raw)).first()
        except (TypeError, ValueError):
            return None

    @action(methods=['GET'], detail=False, url_path='role_options')
    def role_options(self, request, *args, **kwargs):
        """某角色对**全部服务器**的授权级别（无授权 = ``level`` 为空串）。

        角色管理页要渲染的是"这个角色能碰哪些机器、什么级别"，
        所以返回全量服务器而不是只返回已授权的——否则前端没地方新增授权。
        """
        role = self._role_of(request)
        if role is None:
            return ErrorResponse(msg='缺少合法的 role_id')

        levels = {
            g.server_id: g.level
            for g in ServerGrant.objects.filter(role_id=role.pk).only('server_id', 'level')
        }
        servers = []
        for s in Server.objects.all().order_by('id'):
            servers.append({
                'server': s.pk,
                'hostname': s.hostname,
                'ip': s.ip,
                'ssh_port': s.ssh_port,
                'status': s.status,
                'level': levels.get(s.pk, ''),
            })
        return DetailResponse(
            data={'role_id': role.pk, 'role_name': role.name,
                  'servers': servers, 'levels': list(LEVEL_KEYS)},
            msg='获取成功',
        )

    @action(methods=['POST'], detail=False, url_path='set_role_grants')
    @transaction.atomic
    def set_role_grants(self, request, *args, **kwargs):
        """整体覆盖某角色的服务器资产授权。

        请求体::

            {"role_id": 6, "grants": [
                {"server": 1, "level": "write"},
                {"server": 2, "level": "read"}
            ]}

        传 ``level`` 为空串 / 不传 → 收回该服务器的授权。
        **只处理 ``grants`` 里出现的服务器**，未出现的保持原样——角色管理页是
        "改哪台保存哪台"的交互，不能把别的服务器授权一起清掉。
        """
        role = self._role_of(request)
        if role is None:
            return ErrorResponse(msg='缺少合法的 role_id')

        raw = request.data.get('grants')
        if raw is None:
            raise ValidationError('缺少 grants 字段（传空数组表示不做修改）')
        if not isinstance(raw, list):
            raise ValidationError('grants 必须是数组')

        # 先按服务器聚合出最终要写入/删除的集合
        keep, drop, submitted = [], set(), set()
        for i, item in enumerate(raw):
            idx = i + 1
            if not isinstance(item, dict):
                raise ValidationError('第 %d 项格式错误：应为对象' % idx)
            try:
                server_id = int(item.get('server'))
            except (TypeError, ValueError):
                raise ValidationError('第 %d 项缺少合法的 server' % idx)
            if not Server.objects.filter(pk=server_id).exists():
                raise ValidationError('第 %d 项服务器不存在：%s' % (idx, server_id))
            submitted.add(server_id)

            level = item.get('level') or ''
            if not level:
                drop.add(server_id)
                continue
            if level not in LEVEL_KEYS:
                raise ValidationError('第 %d 项 level 只能是 %s' % (idx, ' / '.join(LEVEL_KEYS)))
            keep.append({'server_id': server_id, 'role_id': role.pk,
                         'user_id': None, 'level': level})

        if submitted:
            ServerGrant.objects.filter(role_id=role.pk, server_id__in=submitted).delete()
        if keep:
            ServerGrant.objects.bulk_create([ServerGrant(**r) for r in keep])

        saved = ServerGrant.objects.filter(role_id=role.pk).only('server_id', 'level')
        return DetailResponse(
            data={'role_id': role.pk, 'count': len(keep),
                  'grants': [{'server': g.server_id, 'level': g.level} for g in saved]},
            msg='授权已保存（%d 台服务器）' % len(keep),
        )
