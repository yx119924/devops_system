from rest_framework import serializers
from rest_framework.decorators import action

from dvadmin.alert.models import CHANNEL_TYPE_CHOICES, NotifyChannel
from dvadmin.alert.services import send_dingtalk, send_email, send_feishu, send_wechat
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet

# 前端表单展平字段（写入时组装回 config，输出时从 config 拆出），
# 让用户在 UI 上按渠道类型填写结构化字段，而不是手写 JSON。
FLATTEN_FIELDS = [
    "webhook", "secret",
    "smtp_host", "smtp_port", "smtp_username", "smtp_password", "smtp_to",
]

WEBHOOK_TYPES = {"feishu", "dingtalk", "wechat"}


class NotifyChannelSerializer(CustomModelSerializer):
    type_label = serializers.SerializerMethodField()

    webhook = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                    help_text="Webhook 地址（飞书/钉钉/企业微信机器人）")
    secret = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                   help_text="钉钉机器人加签密钥（可选，仅钉钉）")
    smtp_host = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                      help_text="SMTP 服务器地址")
    smtp_port = serializers.IntegerField(required=False, allow_null=True,
                                         help_text="SMTP 端口（SSL 通常 465）")
    smtp_username = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                          help_text="SMTP 发件账号")
    smtp_password = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                          help_text="SMTP 密码/授权码")
    smtp_to = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                    help_text="收件人邮箱，多个用逗号分隔")

    def get_type_label(self, obj):
        return dict(CHANNEL_TYPE_CHOICES).get(obj.type, obj.type)

    class Meta:
        model = NotifyChannel
        fields = '__all__'
        read_only_fields = ["id"]

    def to_representation(self, instance):
        """把 config 展平，方便前端编辑表单回填"""
        ret = super().to_representation(instance)
        cfg = instance.config or {}
        ret['webhook'] = cfg.get('webhook', '')
        ret['secret'] = cfg.get('secret', '')
        ret['smtp_host'] = cfg.get('smtp_host', '')
        ret['smtp_port'] = cfg.get('smtp_port', 465)
        ret['smtp_username'] = cfg.get('username', '')
        ret['smtp_password'] = cfg.get('password', '')
        ret['smtp_to'] = ', '.join(cfg.get('to_addrs') or [])
        return ret

    @staticmethod
    def _build_config(channel_type, data):
        """把展平字段组装成 config dict。返回 (config, error_msg)。"""
        if channel_type == 'email':
            host = (data.get('smtp_host') or '').strip()
            port = data.get('smtp_port') or 465
            username = (data.get('smtp_username') or '').strip()
            password = data.get('smtp_password') or ''
            to_raw = (data.get('smtp_to') or '').strip()
            to_addrs = [x.strip() for x in to_raw.replace('，', ',').split(',') if x.strip()]
            missing = []
            if not host:
                missing.append('SMTP 服务器')
            if not username:
                missing.append('发件账号')
            if not password:
                missing.append('密码/授权码')
            if not to_addrs:
                missing.append('收件人')
            if missing:
                return None, f"邮箱渠道缺少必填项：{'、'.join(missing)}"
            return {'smtp_host': host, 'smtp_port': int(port), 'username': username,
                    'password': password, 'to_addrs': to_addrs}, None

        webhook = (data.get('webhook') or '').strip()
        if not webhook:
            return None, f"{dict(CHANNEL_TYPE_CHOICES).get(channel_type, channel_type)}渠道缺少 Webhook 地址"
        cfg = {'webhook': webhook}
        if channel_type == 'dingtalk' and (data.get('secret') or '').strip():
            cfg['secret'] = (data.get('secret') or '').strip()
        return cfg, None

    @staticmethod
    def _strip_flatten(validated_data):
        for k in FLATTEN_FIELDS:
            validated_data.pop(k, None)

    def validate(self, attrs):
        """组装 config 并校验必填项。放 validate() 里让 DRF 自动把字段错误包成
        {'config': ['...']} 结构，DVAdmin3 异常处理器才能完整输出中文报错。"""
        channel_type = attrs.get('type') or (self.instance.type if self.instance else 'feishu')
        cfg, err = self._build_config(channel_type, attrs)
        if err:
            raise serializers.ValidationError({'config': err})
        attrs['config'] = cfg
        self._strip_flatten(attrs)
        return attrs


class NotifyChannelViewSet(CustomModelViewSet):
    """通知渠道"""
    queryset = NotifyChannel.objects.all()
    serializer_class = NotifyChannelSerializer
    search_fields = ['name', 'type', 'description']
    filter_fields = ['enabled', 'type']

    @action(methods=['GET'], detail=False, url_path='all')
    def all_list(self, request, *args, **kwargs):
        """下拉选项：返回全部启用渠道"""
        queryset = self.filter_queryset(self.get_queryset())
        data = queryset.filter(enabled=True).order_by('type').values('id', 'name', 'type')
        return DetailResponse(data=data, msg="获取成功")

    @action(methods=['POST'], detail=True, url_path='test')
    def test_channel(self, request, pk=None):
        """发送一条测试消息到该渠道，验证连通性"""
        ch = self.get_object()
        content = "【DevOps 告警】测试消息\n这是一条来自 DevOps 平台的渠道连通性测试。"
        cfg = ch.config or {}
        try:
            if ch.type == 'feishu':
                webhook = (cfg or {}).get('webhook', '')
                if not webhook:
                    return ErrorResponse(msg='飞书 webhook 为空')
                ok, resp = send_feishu(webhook, content)
            elif ch.type == 'dingtalk':
                webhook = (cfg or {}).get('webhook', '')
                if not webhook:
                    return ErrorResponse(msg='钉钉 webhook 为空')
                ok, resp = send_dingtalk(webhook, content, (cfg or {}).get('secret'))
            elif ch.type == 'wechat':
                webhook = (cfg or {}).get('webhook', '')
                if not webhook:
                    return ErrorResponse(msg='企业微信 webhook 为空')
                ok, resp = send_wechat(webhook, content)
            elif ch.type == 'email':
                ok, resp = send_email(cfg or {}, content)
            else:
                return ErrorResponse(msg=f"未知渠道类型 {ch.type}")

            if ok:
                return DetailResponse(data=resp, msg="发送成功")
            return ErrorResponse(msg=f"渠道返回错误：{resp}")
        except Exception as e:
            return ErrorResponse(msg=f"发送异常：{e}")
