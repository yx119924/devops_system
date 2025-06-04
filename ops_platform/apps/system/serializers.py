from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Role

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50, required=True)
    password = serializers.CharField(max_length=100, required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.status:
                    raise serializers.ValidationError('该账号已被禁用')
                attrs['user'] = user
                return attrs
            raise serializers.ValidationError('账号或密码错误')
        raise serializers.ValidationError('请输入账号和密码')

class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'email', 'phone', 'avatar', 'status', 'last_login', 'roles']
        read_only_fields = ['id', 'last_login']

    def get_roles(self, obj):
        return [{
            'id': role.id,
            'role_name': role.role_name,
            'role_code': role.role_code
        } for role in obj.roles.all()]