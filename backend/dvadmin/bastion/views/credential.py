from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from dvadmin.bastion.access import visible_credential_queryset
from dvadmin.bastion.models import Credential
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class CredentialSerializer(CustomModelSerializer):
    """凭据-序列化器：密码/私钥仅写入（不返回明文），读取时返回脱敏状态"""
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True,
                                     help_text="密码明文（仅写入）")
    private_key = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True,
                                        help_text="私钥明文（仅写入）")
    has_password = serializers.SerializerMethodField()
    has_private_key = serializers.SerializerMethodField()
    server_name = serializers.CharField(source='server.hostname', read_only=True, default=None)
    auth_type_label = serializers.SerializerMethodField()

    def get_has_password(self, obj):
        return bool(obj.password)

    def get_has_private_key(self, obj):
        return bool(obj.private_key)

    def get_auth_type_label(self, obj):
        return dict(Credential._meta.get_field('auth_type').choices).get(obj.auth_type, obj.auth_type)

    class Meta:
        model = Credential
        fields = '__all__'
        read_only_fields = ["id"]

    def create(self, validated_data):
        plain_pwd = validated_data.pop('password', None)
        plain_key = validated_data.pop('private_key', None)
        obj = super().create(validated_data)
        if plain_pwd:
            obj.set_password(plain_pwd)
        if plain_key:
            obj.set_private_key(plain_key)
        obj.save()
        return obj

    def update(self, instance, validated_data):
        plain_pwd = validated_data.pop('password', None)
        plain_key = validated_data.pop('private_key', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        # 仅当传入了新密码/私钥才更新（留空表示不修改）
        if plain_pwd:
            instance.set_password(plain_pwd)
        if plain_key:
            instance.set_private_key(plain_key)
        instance.save()
        return instance


class CredentialViewSet(CustomModelViewSet):
    """凭据管理

    可见范围：
    - 超级管理员 / 资产运营者（运维、管理员）：全部凭据
    - 其余用户：**绑定到其被授权服务器**的凭据 + 未绑定服务器的**通用凭据**。

    为什么通用凭据也要放出来：命令下发与 Web SSH 都要求先选凭据，而
    ``require_access`` 只禁止"凭据绑定的服务器 != 目标服务器"的串用，
    并未禁止通用凭据。若把通用凭据藏起来，被授权用户会"看得到服务器却选不到凭据"，
    功能直接不可用。而凭据列表接口只返回元信息（名称/用户名/是否已配置密码），
    不返回任何密钥明文（``password`` / ``private_key`` 都是 ``write_only``）。

    ★ 该口径已抽到 ``bastion/access.py::visible_credential_queryset`` ——
      「AI 问答」的凭据下拉也要同一份名单，两处各写一遍迟早会出现越权口子。
    """
    queryset = Credential.objects.all()
    serializer_class = CredentialSerializer
    search_fields = ['name', 'username']
    filter_fields = ['auth_type', 'server']

    def _visible_queryset(self):
        """可见凭据集合。列表页与下拉接口共用，避免两处口径跑偏。"""
        return visible_credential_queryset(self.request.user)

    def get_queryset(self):
        return self._visible_queryset()

    @action(methods=['GET'], detail=False, permission_classes=[IsAuthenticated], url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回当前用户**可用**的凭据（命令下发 / Web SSH 选择用）。

        可选 ``?server_id=X``：只看"绑定到 X"的凭据 + 未绑定服务器的通用凭据。
        Web SSH 弹窗要的就是这个口径——让用户在几十条凭据里挑一条无关的没有意义。

        刻意**不**调用 ``self.filter_queryset()``：``/api/bastion/credential/all/``
        从未登记 MenuButton，框架的 ``DataLevelPermissionsFilter`` 反查不到按钮权限
        就会落到 ``dept_belong_id__in=[]``，对非超管恒返回空集（下拉变空）。
        可见性统一由 ``_visible_queryset`` 决定。
        """
        qs = self._visible_queryset()
        raw_sid = request.query_params.get('server_id')
        if raw_sid not in (None, '', '0'):
            try:
                sid = int(raw_sid)
            except (TypeError, ValueError):
                return ErrorResponse(msg='server_id 必须是整数')
            # 通用凭据（未绑定服务器）也放行，否则"有机器却选不到凭据"
            qs = qs.filter(Q(server_id=sid) | Q(server__isnull=True))
        data = qs.order_by('name').values('id', 'name', 'username', 'auth_type', 'server')
        return DetailResponse(data=list(data), msg="获取成功")
