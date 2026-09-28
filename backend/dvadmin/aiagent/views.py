# -*- coding: utf-8 -*-
"""
AI 运维助手 —— 接口层

「模型配置」（个人私有，BYOK）
  /api/aiagent/provider/             供应商 CRUD
  /api/aiagent/provider/all/         下拉（我自己启用中的）
  /api/aiagent/provider/{id}/test/   连接测试
  /api/aiagent/provider/{id}/set_default/
  /api/aiagent/guard/current/        读护栏配置（全局单例）
  /api/aiagent/guard/update_current/ 改护栏配置
  /api/aiagent/guard/check_command/  用当前白名单试一条命令（让用户在页面上验证护栏）

「智能问答」（会话个人私有）
  /api/aiagent/chat/                 我的会话列表 / 删除
  /api/aiagent/chat/options/         新建会话的下拉 + 护栏/配额现状
  /api/aiagent/chat/send/            提问（同步返回最终回答）
  /api/aiagent/chat/{id}/            会话详情（含完整 messages，用于回放）
  /api/aiagent/chat/{id}/tool_calls/ 本会话的命令执行台账
  /api/aiagent/toolcall/             全量台账（超管看全部，其余看自己；只读）

★ 这些路径都要在 MenuButton 里逐条登记并授权，否则非超管调用一律业务码 4000
  （`CustomPermission` 是按 (api模板, method索引) 逐条匹配 RoleMenuButtonPermission 的）。
  登记脚本：deploy/tools/register_aiagent.py --with-chat
"""
from django.http import Http404
from rest_framework import serializers
from rest_framework.decorators import action

from dvadmin.aiagent.agent import AgentError, run_turn, usage_snapshot
from dvadmin.aiagent.guard import check_command, load_guard_rules, parse_rules
from dvadmin.aiagent.models import (
    SECRET_PREFIX, AiChatSession, AiGuardConfig, AiProviderConfig, AiToolCall)
from dvadmin.aiagent.providers.base import ProviderError
from dvadmin.aiagent.providers.openai_compat import get_provider
from dvadmin.bastion.access import visible_credential_queryset
from dvadmin.bastion.crypto import encrypt
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet

# ============================================================
# 模型名守卫
# ============================================================
# ★ 这些名字 DeepSeek 官方已于 2026-07-24 弃用，填了必然 400。
#   早期没有守卫，用户填 `deepseek-chat`（甚至大小写写成 `DeepSeek-chat`）→ 报 400 →
#   而前端又把业务错误显示成「网络不通或超时」，白白排查一轮网络。
#   ⇒ 在这里直接拦住，给出可操作的替换建议（早失败、说得清）。
#   ★ 只对 DeepSeek **官方域名**生效：中转站 / 自建网关可能仍然支持旧名字，不能一刀切。
DEEPSEEK_DEPRECATED_MODELS = {
    "deepseek-chat": "deepseek-flash",
    "deepseek-reasoner": "deepseek-v4-pro",
}
DEEPSEEK_OFFICIAL_HOST = "api.deepseek.com"
DEEPSEEK_CURRENT_MODELS = "deepseek-flash（快而省，推荐） / deepseek-v4-pro（重推理）"


# ============================================================
# 供应商配置
# ============================================================

class AiProviderSerializer(CustomModelSerializer):
    """供应商配置（**个人私有**）。

    ★ API Key 只写不读：写入时加密，读取时只返回 `has_api_key` 布尔值。
      编辑时留空 = 保留原值（和「通知渠道」的处理方式一致）。

    ★ `owner` 必须 read_only：否则客户端可以传 owner 把配置挂到别人名下，
      或者把别人的配置"改"成自己的。归属只能由后端按登录用户写。
    """
    api_key = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                    write_only=True,
                                    help_text="API Key 明文，仅写入；留空表示保留原值")

    class Meta:
        model = AiProviderConfig
        fields = '__all__'
        read_only_fields = ["id", "owner"]

    def _owner_from_request(self):
        """新建时的归属用户 = 当前登录用户（后端唯一来源，绝不取客户端传值）。"""
        request = (self.context or {}).get('request')
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            return user
        return None

    def validate(self, attrs):
        instance = self.instance
        raw_key = (attrs.get('api_key') or '').strip()

        if raw_key:
            attrs['api_key'] = SECRET_PREFIX + encrypt(raw_key)
        else:
            # 留空：新建必须填，编辑则保留原值
            if instance is None or not instance.api_key:
                raise serializers.ValidationError({'api_key': '请填写 API Key'})
            attrs.pop('api_key', None)

        # ★ 同一归属下配置名不重复。
        #   DB 上也有 UniqueConstraint(owner, name) 兜底，但 MySQL 里 NULL 不参与唯一约束，
        #   而且 DB 报错是英文 IntegrityError / 500，这里给出可读的中文提示。
        owner = instance.owner if instance is not None else self._owner_from_request()
        name = (attrs.get('name') or (instance.name if instance else '') or '').strip()
        if name:
            dup = AiProviderConfig.objects.filter(name=name)
            dup = dup.filter(owner=owner) if owner is not None else dup.filter(owner__isnull=True)
            if instance is not None:
                dup = dup.exclude(id=instance.id)
            if dup.exists():
                raise serializers.ValidationError({
                    'name': '你已经有叫「%s」的配置了，换个名字' % name})

        base = (attrs.get('base_url')
                or (instance.base_url if instance else '')
                or '').strip().rstrip('/')
        if not base:
            raise serializers.ValidationError({'base_url': '请填写接口地址'})
        if not base.startswith(('http://', 'https://')):
            raise serializers.ValidationError({'base_url': '接口地址必须以 http:// 或 https:// 开头'})
        attrs['base_url'] = base

        model_name = (attrs.get('model')
                      or (instance.model if instance else '')
                      or '').strip()
        if not model_name:
            raise serializers.ValidationError({'model': '请填写模型名称'})
        attrs['model'] = model_name

        # ★ 弃用模型名守卫（只对 DeepSeek 官方域名生效，见文件头注释）
        if DEEPSEEK_OFFICIAL_HOST in base.lower():
            replacement = DEEPSEEK_DEPRECATED_MODELS.get(model_name.lower())
            if replacement:
                raise serializers.ValidationError({
                    'model': 'DeepSeek 已于 2026-07-24 弃用模型名 `%s`，'
                             '直接调用会返回 400（模型名区分大小写）。'
                             '请改用 `%s`。当前可选：%s'
                             % (model_name, replacement, DEEPSEEK_CURRENT_MODELS)
                })

        timeout = attrs.get('timeout', instance.timeout if instance else 60)
        if timeout is not None and (timeout < 5 or timeout > 600):
            raise serializers.ValidationError({'timeout': '超时时间应在 5~600 秒之间'})

        max_tokens = attrs.get('max_tokens', instance.max_tokens if instance else 2048)
        if max_tokens is not None and (max_tokens < 64 or max_tokens > 32768):
            raise serializers.ValidationError({'max_tokens': '最大输出 token 应在 64~32768 之间'})

        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret.pop('api_key', None)
        ret['has_api_key'] = bool(instance.api_key)
        return ret


class AiProviderViewSet(CustomModelViewSet):
    """我的模型配置（个人私有）。

    ★★ 隔离靠本类的 get_queryset 显式实现，**不能**依赖 DVAdmin 的部门数据权限：

      `DataLevelPermissionMargeFilter` 的语义是「按 dept_belong_id 过滤」——
        · 没有分配部门的用户 → `queryset.none()` → **永远看到空列表**
        · 同部门的两个人 → 若角色 data_range 是 1/2/4，会**互相看到对方的配置**
      两条都不是我们想要的。个人配置不是"部门数据"，所以直接关掉，
      改用 `owner=当前用户`。先例：`dvadmin/cmdb/views/server_grant.py` 同样 `extra_filter_class = []`。

    ★ 关掉它不影响接口权限：`permission_classes = [CustomPermission]` 仍在，
      未授权调用依然返回业务码 4000。失去的只是时间范围查询参数，本接口用不到。
    """

    queryset = AiProviderConfig.objects.all()
    serializer_class = AiProviderSerializer
    search_fields = ['name', 'model', 'base_url', 'description']
    filter_fields = ['enabled', 'provider_type', 'is_default']
    # 「先例」见类 docstring。空列表 = 不挂 CoreModelFilterBankend / DataLevelPermissionMargeFilter
    extra_filter_class = []

    def get_queryset(self):
        """只返回当前登录用户自己的配置。

        ★ 这是**全类唯一的隔离点**：DRF 的 get_object() 走的就是这个 queryset，
          所以「改 pk 越权读/改/删别人的配置」在对象级也被挡住（返回 404，不泄露存在性）。
        """
        user = getattr(self.request, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            return AiProviderConfig.objects.none()
        return AiProviderConfig.objects.filter(owner=user)

    @staticmethod
    def _ensure_single_default(obj):
        """默认配置按**归属**唯一（每个人的"我的默认"互不影响）。"""
        if obj.is_default:
            AiProviderConfig.objects.filter(owner_id=obj.owner_id) \
                .exclude(id=obj.id).update(is_default=False)

    def perform_create(self, serializer):
        # 归属只认登录用户，客户端传什么都不作数（serializer 里 owner 是 read_only）
        user = self.request.user
        # 第一条配置自动成为"我的默认"，省掉一次手动点选
        first = not AiProviderConfig.objects.filter(owner=user).exists()
        obj = serializer.save(owner=user,
                              is_default=bool(serializer.validated_data.get('is_default')) or first)
        self._ensure_single_default(obj)

    def perform_update(self, serializer):
        self._ensure_single_default(serializer.save())

    @action(methods=['GET'], detail=False, url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：**我自己的**、启用中的配置"""
        data = self.get_queryset().filter(enabled=True).values(
            'id', 'name', 'model', 'is_default')
        return DetailResponse(data=list(data), msg="获取成功")

    @action(methods=['POST'], detail=True, url_path='test')
    def test_provider(self, request, pk=None):
        """连接测试：发一条最小请求，返回延迟与模型回显"""
        obj = self.get_object()
        try:
            provider = get_provider(obj)
        except Exception as exc:
            return ErrorResponse(msg=str(exc))

        result = provider.test()
        if result.get('ok'):
            return DetailResponse(
                data=result,
                msg="连接成功：%s（延迟 %.2fs，消耗 %s token）"
                    % (result.get('reply') or 'OK', result.get('latency') or 0,
                       result.get('tokens') or 0))
        return ErrorResponse(msg=result.get('error') or '连接失败')

    @action(methods=['POST'], detail=True, url_path='set_default')
    def set_default(self, request, pk=None):
        """把我的某条配置设为默认（不影响别人的默认）"""
        obj = self.get_object()
        AiProviderConfig.objects.filter(owner=request.user).update(is_default=False)
        AiProviderConfig.objects.filter(id=obj.id).update(is_default=True)
        return DetailResponse(msg="已设为我的默认配置")


# ============================================================
# 安全护栏配置
# ============================================================

class AiGuardSerializer(CustomModelSerializer):
    class Meta:
        model = AiGuardConfig
        fields = '__all__'
        read_only_fields = ["id"]


class AiGuardViewSet(CustomModelViewSet):
    """护栏配置（全局单例，前端通过 current / update_current 读写）"""
    queryset = AiGuardConfig.objects.all()
    serializer_class = AiGuardSerializer

    @action(methods=['GET'], detail=False, url_path='current')
    def current(self, request, *args, **kwargs):
        obj = AiGuardConfig.load()
        data = self.get_serializer(obj).data
        # 顺带回传解析后的规则条数，方便前端显示
        data['allowed_count'] = len(parse_rules(obj.allowed_commands))
        data['denied_count'] = len(parse_rules(obj.denied_commands))
        data['denied_path_count'] = len(parse_rules(obj.denied_paths))
        return DetailResponse(data=data, msg="获取成功")

    @action(methods=['PUT', 'POST'], detail=False, url_path='update_current')
    def update_current(self, request, *args, **kwargs):
        obj = AiGuardConfig.load()
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return DetailResponse(data=serializer.data, msg="护栏配置已保存，立即生效")

    @action(methods=['POST'], detail=False, url_path='check_command')
    def check_command_api(self, request, *args, **kwargs):
        """用当前生效的白/黑名单试跑一条命令，让用户在页面上直接验证护栏效果。"""
        command = (request.data.get('command') or '').strip()
        if not command:
            return ErrorResponse(msg="请输入要测试的命令")
        rules = load_guard_rules()
        allowed, reason, segments = check_command(
            command, rules['allowed'], rules['denied'], rules['denied_paths'])
        executable = allowed and bool(rules['readonly_mode']) and bool(rules['enabled_tools'])
        return DetailResponse(
            data={'allowed': allowed,
                  'executable': executable,
                  'reason': reason if not allowed else (
                      "该命令会被执行" if executable else
                      "命令本身合规，但「只读模式」或「允许调用只读工具」已关闭 → 实际不会执行"),
                  'segments': segments,
                  'readonly_mode': rules['readonly_mode'],
                  'enabled_tools': rules['enabled_tools']},
            msg="该命令会被执行" if executable else (
                "该命令本身会被放行，但当前开关下不会执行" if allowed else "该命令会被拒绝"))


# ============================================================
# 智能问答：会话
# ============================================================

class AiChatSessionSerializer(CustomModelSerializer):
    """会话详情（含完整消息上下文，供页面回放）。"""
    credential_name = serializers.CharField(source='credential.name', read_only=True, default=None)
    provider_name = serializers.CharField(source='provider.name', read_only=True, default=None)

    class Meta:
        model = AiChatSession
        fields = '__all__'
        read_only_fields = ['id', 'owner', 'messages', 'rounds', 'tool_count',
                            'total_tokens', 'status', 'last_error', 'title', 'readonly']


class AiChatSessionListSerializer(CustomModelSerializer):
    """会话列表 —— **刻意不返回 `messages`**：一个长会话的上下文可能上百 KB，
    列表页拉 20 条就是几 MB，页面会明显卡。看历史走详情接口。"""
    credential_name = serializers.CharField(source='credential.name', read_only=True, default=None)
    provider_name = serializers.CharField(source='provider.name', read_only=True, default=None)

    class Meta:
        model = AiChatSession
        fields = ['id', 'title', 'credential_name', 'provider_name', 'rounds',
                  'tool_count', 'total_tokens', 'status', 'create_datetime',
                  'update_datetime']


class AiChatSessionViewSet(CustomModelViewSet):
    """智能问答会话（**个人私有**）。

    ★ 与「模型配置」同一套隔离原则：`extra_filter_class = []` 关掉 DVAdmin 的部门数据权限，
      改用 `owner=当前用户`（理由见 AiProviderViewSet 的类 docstring）。
      会话里含提问原文、命令输出、主机名 —— 比模型配置更不该跨人可见。

    ★ 只提供 get/post/delete：会话不做编辑（没有"改一下历史对话"这种语义）。
    """
    queryset = AiChatSession.objects.all()
    serializer_class = AiChatSessionSerializer
    list_serializer_class = AiChatSessionListSerializer
    search_fields = ['title']
    filter_fields = ['status']
    extra_filter_class = []
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            return AiChatSession.objects.none()
        return AiChatSession.objects.filter(owner=user).order_by('-update_datetime')

    def get_object(self):
        """pk 必须是数字，否则 404。

        ★ 为什么需要这个：路由是 `/api/aiagent/chat/{pk}/`，而同一个 prefix 下还有
          `/api/aiagent/chat/send/`、`/api/aiagent/chat/options/`。DRF 会把
          `send` 当成 pk 交给 detail 路由，`filter(pk="send")` 在 Django 里直接抛
          ValueError → **500**（一条日志很脏、也没意义）。
          在这里提前判掉，返回 404（不泄露存在性、不发 500）。
        """
        pk = self.kwargs.get(self.lookup_field or 'pk')
        if not str(pk).isdigit():
            raise Http404
        return super().get_object()

    # ------------------------------------------------------------
    # 下拉与状态
    # ------------------------------------------------------------
    @action(methods=['GET'], detail=False, url_path='options')
    def options(self, request, *args, **kwargs):
        """新建会话需要的下拉数据 + 护栏/配额现状。

        ★ 刻意**不**调用 `self.filter_queryset()`：`/api/aiagent/chat/options/`
          这类下拉路径很容易漏登记 MenuButton，框架的 `DataLevelPermissionsFilter`
          反查不到按钮权限就会落到 `dept_belong_id__in=[]`，对非超管恒返回空集。
          可见性完全由 `visible_credential_queryset` 与 `owner` 决定。
        """
        from dvadmin.bastion.access import is_asset_admin, writable_server_ids

        user = request.user
        creds = visible_credential_queryset(user).order_by('name').values(
            'id', 'name', 'username', 'auth_type', 'server')
        providers = AiProviderConfig.objects.filter(owner=user, enabled=True).values(
            'id', 'name', 'model', 'is_default')
        rules = load_guard_rules()
        server_count = 'all' if is_asset_admin(user) else len(writable_server_ids(user) or [])
        return DetailResponse(data={
            'credentials': list(creds),
            'providers': list(providers),
            'server_count': server_count,
            'usage': usage_snapshot(user),
            'guard': {
                'readonly_mode': rules['readonly_mode'],
                'enabled_tools': rules['enabled_tools'],
                'desensitize': rules['desensitize'],
                'max_rounds': rules['max_rounds'],
                'chat_timeout': rules['chat_timeout'],
                'command_timeout': rules['command_timeout'],
                'max_servers': rules['max_servers'],
                'allowed_sample': rules['allowed'][:15],
            },
        }, msg="获取成功")

    # ------------------------------------------------------------
    # 提问
    # ------------------------------------------------------------
    @action(methods=['POST'], detail=False, url_path='send')
    def send(self, request, *args, **kwargs):
        """问一句。

        body:
            message       必填，问题
            session_id    可选；给了就续问，不给就新建会话
            credential_id 可选（新建会话时必填）—— 本会话所有 SSH 都用它
            provider_id   可选（新建会话时）—— 不填就用「我的默认」那条

        ★ 同步返回最终回答（与「命令下发」的 execute 同一惯例），
          不是流式、不是轮询。单次时长上限由护栏的 `chat_timeout` 控制。
        """
        user = request.user
        message = (request.data.get('message') or '').strip()
        if not message:
            return ErrorResponse(msg="请输入要排查的问题")
        if len(message) > 4000:
            return ErrorResponse(msg="问题太长了（上限 4000 字），请精简后重试")

        session = None
        raw_sid = request.data.get('session_id')
        if raw_sid not in (None, '', 0, '0'):
            session = self.get_queryset().filter(pk=raw_sid).first()
            if session is None:
                return ErrorResponse(msg="会话不存在或不属于你，请刷新页面后重试")

        created = session is None
        if created:
            session, err = self._build_session(request, user, message)
            if err:
                return ErrorResponse(msg=err)

        try:
            data = run_turn(session, message, user)
        except AgentError as exc:
            # 前置校验类失败（配额、配置被删/停用…）：刚建的会话不留下，免得列表里全是空壳
            if created:
                session.delete()
            return ErrorResponse(msg=str(exc))
        except ProviderError as exc:
            # 大模型调用失败：会话与提问都保留（用户可以原样重发）
            return ErrorResponse(msg=str(exc))

        return DetailResponse(data=data,
                              msg="已完成排查（%s 轮工具调用，耗时 %.1fs）"
                                  % (data.get('tools'), data.get('elapsed') or 0))

    def _build_session(self, request, user, message):
        """新建会话：校验凭据/模型配置的归属，返回 (session, err_msg)。"""
        cred_id = request.data.get('credential_id')
        if cred_id in (None, '', 0, '0'):
            return None, "请先选择一条 SSH 凭据 —— AI 只会用你选定的这条凭据连服务器"
        credential = visible_credential_queryset(user).filter(pk=cred_id).first()
        if credential is None:
            return None, "凭据不存在，或你没有使用它的权限（请到「凭据管理」确认授权）"

        prov_id = request.data.get('provider_id')
        if prov_id in (None, '', 0, '0'):
            # 不填 → 用「我的默认」；如果连一条都没有，给出可操作的指引
            provider = AiProviderConfig.objects.filter(
                owner=user, enabled=True).order_by('-is_default', 'id').first()
        else:
            provider = AiProviderConfig.objects.filter(owner=user, pk=prov_id).first()
        if provider is None:
            return None, ("你还没有可用的模型配置。请先到「AI 运维助手 → 模型配置」"
                          "新建一条并填入自己的 API Key（配置只对你自己可见）。")
        if not provider.enabled:
            return None, "模型配置「%s」已停用，请启用它或换一条" % provider.name

        session = AiChatSession.objects.create(
            owner=user, creator=user, credential=credential, provider=provider,
            messages=[], title=message[:40], readonly=True, status='active')
        return session, None

    # ------------------------------------------------------------
    # 会话内的工具台账
    # ------------------------------------------------------------
    @action(methods=['GET'], detail=True, url_path='tool_calls')
    def tool_calls(self, request, pk=None):
        """本会话的命令执行台账（含被护栏拒绝、无授权的尝试）。"""
        session = self.get_object()
        qs = session.tool_logs.order_by('id')
        return DetailResponse(data=AiToolCallSerializer(qs, many=True).data, msg="获取成功")


class AiToolCallSerializer(CustomModelSerializer):
    class Meta:
        model = AiToolCall
        fields = '__all__'
        read_only_fields = ['id']


class AiToolCallViewSet(CustomModelViewSet):
    """工具调用台账（只读）。

    可见范围：
      · 超级管理员 → 全部（审计要看全量，"AI 想读 /etc/shadow 被拦了几次"是运维要的信号）
      · 其余用户 → 只看自己

    只读：`http_method_names` 里没有 post/put/delete —— 审计数据不允许被业务侧改写。
    """
    queryset = AiToolCall.objects.all()
    serializer_class = AiToolCallSerializer
    search_fields = ['tool_name', 'command', 'purpose', 'server_label', 'ip', 'reject_reason']
    filter_fields = ['session', 'status', 'tool_name']
    extra_filter_class = []
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            return AiToolCall.objects.none()
        if getattr(user, 'is_superuser', False):
            return AiToolCall.objects.all()
        return AiToolCall.objects.filter(owner=user)
