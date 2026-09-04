# -*- coding: utf-8 -*-
"""
创建/复用 readonly 测试用户并生成 zhuyk + readonly 的 JWT
（运行在 dvadmin3-django 容器内）
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")
django.setup()

from django.apps import apps
from rest_framework_simplejwt.tokens import RefreshToken

Users = apps.get_model("system", "Users")
Role = apps.get_model("system", "Role")

# 1. readonly 角色
ro = Role.objects.get(key="readonly")

# 2. 测试用户：复用现有 "test" 用户（已存在，无角色），绑到 readonly
user, created = Users.objects.get_or_create(
    username="test",
    defaults={"is_active": True, "name": "只读测试账号"},
)
user.set_password("Test@readonly2026")
user.is_active = True
user.save()

user.role.clear()
user.role.add(ro)
user.current_role = ro
user.save(update_fields=["current_role"])
print(f"用户 test 已绑到 readonly (id={user.id}), created={created}")

# 3. 生成 JWT
def gen(u):
    return str(RefreshToken.for_user(u).access_token)

zhuyk = Users.objects.get(username="zhuyk")
tokens = {
    "zhuyk_ops": gen(zhuyk),
    "test_readonly": gen(user),
}
for k, v in tokens.items():
    print(f"{k}={v}")

print("\nDONE")