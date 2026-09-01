from rest_framework import serializers

from dvadmin.bastion.models import Credential
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
    """凭据管理"""
    queryset = Credential.objects.all()
    serializer_class = CredentialSerializer
    search_fields = ['name', 'username']
    filter_fields = ['auth_type', 'server']
