from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone


class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({
                'code': 400,
                'message': '用户名和密码不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({
                'code': 401,
                'message': '用户名或密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({
                'code': 403,
                'message': '用户已被禁用'
            }, status=status.HTTP_403_FORBIDDEN)

        # 更新最后登录时间
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # 生成Token
        refresh = RefreshToken.for_user(user)

        return Response({
            'code': 200,
            'message': '登录成功',
            'data': {
                'id': user.id,
                'username': user.username,
                'nickname': user.nickname,
                'email': user.email,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'last_login': user.last_login,
                'token': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }
        }, status=status.HTTP_200_OK)
