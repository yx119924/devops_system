from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.bastion.access import grant_levels, restrict_servers
from dvadmin.cmdb.models import (
    BusinessLine,
    Environment,
    Idc,
    Server,
    SERVER_STATUS_CHOICES,
)
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class ServerSerializer(CustomModelSerializer):
    """列表/编辑-序列化器"""
    idc_name = serializers.CharField(source='idc.name', read_only=True, default=None)
    environment_name = serializers.CharField(source='environment.name', read_only=True, default=None)
    business_line_name = serializers.CharField(source='business_line.name', read_only=True, default=None)
    status_label = serializers.SerializerMethodField()
    grants_summary = serializers.SerializerMethodField()
    my_level = serializers.SerializerMethodField()

    def get_status_label(self, obj):
        return dict(SERVER_STATUS_CHOICES).get(obj.status, obj.status)

    def get_my_level(self, obj):
        """**当前用户**在这台服务器上的有效授权级别：``'read'`` / ``'write'`` / ``''``。

        前端据此决定「终端」按钮是否显示——只读授权的机器不该出现可点的入口，
        让用户点完再被后端 403 是糟糕的体验。级别由 ``get_queryset`` 一次性算好
        挂在 request 上，避免每行一次 DB 查询。
        """
        request = self.context.get('request')
        levels = getattr(request, '_xwops_grant_levels', None)
        if levels is None:
            # None = 该用户不受限（超管 / 资产运营者）
            return 'write'
        return levels.get(obj.pk, '')

    def get_grants_summary(self, obj):
        """资产授权概览，供列表「授权范围」列显示。

        形如 ``{'count': 2, 'roles': ['运维'], 'users': ['dev1'], 'has_write': True}``。
        依赖 ``get_queryset`` 里的 ``prefetch_related``，否则每行一次查询。
        """
        roles, users, has_write = [], [], False
        try:
            grants = list(obj.grants.all())
        except Exception:
            grants = []
        for g in grants:
            if g.role_id and g.role:
                roles.append(g.role.name)
            if g.user_id and g.user:
                users.append(g.user.name or g.user.username)
            if g.level == 'write':
                has_write = True
        return {
            'count': len(grants),
            'roles': roles,
            'users': users,
            'has_write': has_write,
        }

    class Meta:
        model = Server
        fields = '__all__'
        read_only_fields = ["id"]


class NameReadablePkField(serializers.PrimaryKeyRelatedField):
    """导入链路专用的外键字段：**校验收主键 id、序列化回显名称**。

    为什么必须这样（2026-10-13 修）：
      `utils/import_export.py` 的 `import_to_data()` 在把行数据交给序列化器**之前**，
      已经用 `choices.queryset.values(values_name, 'id')` 建好 `{名称: 主键}` 映射，
      并把单元格值替换成了**主键 id**（见该文件「获取参数映射」段、
      `array[key] = validation_data_dict.get(key, {}).get(cell_value, None)`）。
      ⇒ 校验必须走 PK 语义。原先用 `SlugRelatedField(slug_field='name')` 收名称，
        就会拿 `1` 去 `filter(name=1)`，报「机房:属性 name 为 1 的对象不存在。」。
      ⇒ 而「批量更新模板」是本序列化器的 `to_representation` 渲染给人看的，
        直接输出 `1` 用户看不懂，所以这里覆盖输出、回显名称。

    对照：`system/views/user.py` 的 `UserProfileImportSerializer` 完全不覆盖外键字段
    （用 ModelSerializer 默认生成的 PK 字段）—— 那才是与本导入链路匹配的写法。
    """

    def __init__(self, slug_field='name', **kwargs):
        self.slug_field = slug_field
        super().__init__(**kwargs)

    def use_pk_only_optimization(self):
        # ★ 必须关掉 DRF 的「只取 pk」优化：开启时 get_attribute() 返回的是
        #   PKOnlyObject(pk=1)（一个**只有 pk 属性**的假对象），
        #   下面的 to_representation 就取不到 .name ⇒ 模板回显会变成 None。
        return False

    def to_representation(self, value):
        if value is None:
            return None
        return getattr(value, self.slug_field, None)


class ImportServerSerializer(CustomModelSerializer):
    """Excel导入-序列化器：外键「收 id / 回显名称」，详见 NameReadablePkField"""
    idc = NameReadablePkField(slug_field='name', queryset=Idc.objects.all(), required=False, allow_null=True)
    environment = NameReadablePkField(slug_field='name', queryset=Environment.objects.all(), required=False, allow_null=True)
    business_line = NameReadablePkField(slug_field='name', queryset=BusinessLine.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Server
        fields = '__all__'
        read_only_fields = ["id"]


class ServerViewSet(CustomModelViewSet):
    """服务器管理

    可见范围由**资产授权**（``cmdb_server_grant``）决定，不再靠 DVAdmin 的
    ``data_range``（后者只能按"创建人部门"过滤，表达不了"这台机授权给 A 和 B"）：

    - 超级管理员 / 资产运营者（持有 ``server:Create|Update|Delete``，即运维、管理员）→ 全部
    - 其余用户 → 只看 ``ServerGrant`` 里 role/user 命中的服务器
    - 无命中 → 空列表（fail closed）

    ``all_list`` / ``dispatch_options`` 两个下拉接口不走 ``get_queryset()``
    （原因见各自 docstring），但都显式调用同一套 ``restrict_servers`` /
    ``writable_server_ids``，口径与列表页保持一致。
    """
    queryset = Server.objects.all()
    serializer_class = ServerSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 列表要展示「授权范围」列，预取避免 N+1
        qs = qs.prefetch_related('grants__role', 'grants__user')
        user = self.request.user
        # 当前用户的授权级别挂到 request 上，供 ServerSerializer.get_my_level 复用
        # （只算一次；None 表示不受限）
        self.request._xwops_grant_levels = grant_levels(user)
        return restrict_servers(qs, user)

    # Excel 导入
    import_serializer_class = ImportServerSerializer
    # ★ 2026-10-13：dict 形式（外键/枚举）的字段**必须**配 `display` ——
    #   `import_export_mixin.py` 的 update_template() 按
    #   `hidden_header.append(value.get('display'))` 决定数据行取哪个字段的名称，
    #   缺 display 会 append 一个 None ⇒ 该列的数据取不到 ⇒ 数据行比表头少 4 列
    #   （实测表头 17 列 / 数据 13 列），整张「批量更新模板」错位。
    import_field_dict = {
        'hostname': '主机名',
        'ip': '主管理IP',
        'extra_ips': '其他内网IP',
        'idc': {'title': '机房', 'display': 'idc', 'choices': {'queryset': Idc.objects.filter(status=1), 'values_name': 'name'}},
        'environment': {'title': '环境', 'display': 'environment', 'choices': {'queryset': Environment.objects.filter(status=1), 'values_name': 'name'}},
        'business_line': {'title': '业务线', 'display': 'business_line', 'choices': {'queryset': BusinessLine.objects.filter(status=1), 'values_name': 'name'}},
        'deploy_content': '部署内容',
        'os': '操作系统',
        'cpu': 'CPU核数',
        'memory': '内存GB',
        'disk': '磁盘',
        'ssh_port': 'SSH端口',
        'status': {
            'title': '状态',
            'display': 'status',
            'choices': {'data': {'online': '在线', 'offline': '离线', 'maintenance': '维护中', 'offline_shelf': '已下架'}},
        },
        'tags': '标签',
        'description': '描述',
    }

    search_fields = ['hostname', 'ip', 'extra_ips', 'deploy_content', 'tags']
    filter_fields = ['status', 'idc', 'environment', 'business_line']

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='all')
    def all_list(self, request, *args, **kwargs):
        """服务器下拉（供凭据 / 会话关联选择）。

        这里刻意**不**调用 ``self.filter_queryset()``。框架的
        ``DataLevelPermissionsFilter`` 是拿 ``request.path`` 去 ``MenuButton`` 表反查
        对应按钮权限的，而本 action 的路径 ``/api/cmdb/server/all/`` 从来没有登记过
        MenuButton → ``dataScope_list`` 为空 → 最终落到
        ``queryset.filter(dept_belong_id__in=[])`` → **对非超管恒返回空集**。

        这是框架的固有行为（不是权限设计意图），所以辅助型 action 一律不用它，
        服务器可见性统一由资产授权 ``restrict_servers`` 决定。
        """
        qs = restrict_servers(Server.objects.all(), request.user)
        data = qs.filter(status='online').order_by('hostname').values('hostname', 'id')
        return DetailResponse(data=list(data), msg="获取成功")

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='dispatch_options')
    def dispatch_options(self, request, *args, **kwargs):
        """命令下发目标下拉：只返回当前用户**可操作**（write 级别）的在线服务器。

        用 writable 而不是 visible：只有只读授权的服务器若出现在下拉里，
        用户选完、提交时才被 ``require_access`` 拒掉，体验是"能选但发不出去"。
        在下拉阶段就过滤掉，从源头避免无效操作。
        """
        from dvadmin.bastion.access import writable_server_ids

        ids = writable_server_ids(request.user)
        qs = Server.objects.all() if ids is None else Server.objects.filter(pk__in=ids)
        data = qs.filter(status='online').order_by('hostname').values('id', 'hostname', 'ip', 'ssh_port')
        return DetailResponse(data=list(data), msg="获取成功")

    @action(methods=['GET'], detail=True, permission_classes=[IsAuthenticated],
            url_path='ssh_credentials')
    def ssh_credentials(self, request, pk=None):
        """某台服务器上**当前用户可用**的凭据（Web SSH 弹窗选择用）。

        为什么不复用 ``/api/bastion/credential/`` 或 ``/api/bastion/credential/all/``：

        1. 那两个路径属**凭据管理**模块，开发 / 测试这类角色不该被授予
           "查看全公司凭据"的能力；而 ``CustomPermission`` 的 ``ValidationApi`` 是
           ``re.match`` **前缀**匹配（不要求结尾），所以哪怕新开一个
           ``/api/bastion/credential/xxx/`` 也照样会落到 ``credential:Search`` 那条
           按钮权限上，绕不开。
        2. 语义上，"这台机器该用哪个凭据"本来就属于**服务器**的数据，挂在服务器详情下
           更自然。

        返回只有 ``id/name/username/auth_type``：``Credential.password`` 与
        ``private_key`` 在序列化器里是 ``write_only``，明文永远不会出后端。
        真正的操作授权仍由 WS 建连时的 ``require_access(...)`` 把关（要求 write 级别），
        这里只控制"看不看得到可选列表"。
        """
        from django.db.models import Q

        from dvadmin.bastion.access import visible_server_ids
        from dvadmin.bastion.models import Credential

        server = Server.objects.filter(pk=pk).first()
        if server is None:
            return ErrorResponse(msg='服务器不存在')

        ids = visible_server_ids(request.user)
        if ids is not None and server.pk not in ids:
            return ErrorResponse(msg='无权访问该服务器')

        qs = Credential.objects.filter(Q(server_id=server.pk) | Q(server__isnull=True))
        data = qs.order_by('name').values('id', 'name', 'username', 'auth_type', 'server')
        return DetailResponse(data=list(data), msg="获取成功")
