# -*- coding: utf-8 -*-
"""
Jenkins 发布管理：角色 + Job 可见权限配置（幂等，可重复执行）

1. 新增「开发(developer)」「测试(tester)」两个角色
2. 给 developer/tester 授权 Jenkins 菜单（发布管理 + 2 页面）
3. 给 developer/tester 授权 Jenkins 按钮（查询+操作，不含服务器增删改）
4. 配置 JenkinsRolePermission（每个角色能看到的 job 路径前缀）

用法（django 容器内）：
  docker exec dvadmin3-django python /backend/register_jenkins_permission.py

如需调整各角色可见路径，改下方 PERM_CONFIG 后重跑即可（幂等覆盖）。
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")
django.setup()

from django.apps import apps

Menu = apps.get_model("system", "Menu")
MenuButton = apps.get_model("system", "MenuButton")
Role = apps.get_model("system", "Role")
RoleMenuPermission = apps.get_model("system", "RoleMenuPermission")
RoleMenuButtonPermission = apps.get_model("system", "RoleMenuButtonPermission")

from dvadmin.jenkins.models import JenkinsServer, JenkinsRolePermission

# ============================================================
# 1. 角色
# ============================================================
dev, _ = Role.objects.get_or_create(key="developer", defaults={"name": "开发", "sort": 5, "status": True})
tester, _ = Role.objects.get_or_create(key="tester", defaults={"name": "测试", "sort": 6, "status": True})
print(f"角色：开发(developer) id={dev.id}，测试(tester) id={tester.id}")

# ============================================================
# 2. 菜单授权（developer / tester）
# ============================================================
JENKINS_MENUS = ["发布管理", "Jenkins 服务器", "构建发布"]
for menu_name in JENKINS_MENUS:
    try:
        menu = Menu.objects.get(name=menu_name)
    except Menu.DoesNotExist:
        print(f"[警告] 菜单「{menu_name}」不存在，跳过")
        continue
    RoleMenuPermission.objects.get_or_create(role=dev, menu=menu)
    RoleMenuPermission.objects.get_or_create(role=tester, menu=menu)
print("菜单授权完成")

# ============================================================
# 3. 按钮授权（developer/tester：查询 + 操作，不含服务器增删改）
# ============================================================
JENKINS_BUTTONS = [
    "jenkinsServer:Search", "jenkinsServer:Test",
    "jenkinsJob:ServerList", "jenkinsJob:Jobs", "jenkinsJob:Build",
    "jenkinsJob:Status", "jenkinsJob:Console",
]
for value in JENKINS_BUTTONS:
    try:
        btn = MenuButton.objects.get(value=value)
    except MenuButton.DoesNotExist:
        print(f"[警告] 按钮「{value}」不存在，跳过（先跑 register_business_buttons.py）")
        continue
    RoleMenuButtonPermission.objects.get_or_create(role=dev, menu_button=btn, defaults={"data_range": 3})
    RoleMenuButtonPermission.objects.get_or_create(role=tester, menu_button=btn, defaults={"data_range": 3})
print("按钮授权完成")

# ============================================================
# 4. Job 可见权限（JenkinsRolePermission）
#    allowed_paths 空列表 = 全部；否则只匹配这些路径前缀
# ============================================================
PERM_CONFIG = {
    "ops": [],                          # 普通运维：全部
    "readonly": [],                     # 只读查看：全部（但按钮仅 GET，不能构建）
    "developer": ["dev/", "pre/", "test/"],   # 开发：非生产环境
    "tester": ["test/"],                      # 测试：仅 test
}

servers = JenkinsServer.objects.all()
if not servers.exists():
    print("[警告] 还没有 Jenkins 服务器，跳过 Job 权限配置（先在页面添加服务器）")
else:
    for server in servers:
        for role_key, paths in PERM_CONFIG.items():
            try:
                role = Role.objects.get(key=role_key)
            except Role.DoesNotExist:
                print(f"[警告] 角色 key={role_key} 不存在，跳过")
                continue
            obj, created = JenkinsRolePermission.objects.update_or_create(
                server=server, role=role,
                defaults={"allowed_paths": paths},
            )
        print(f"服务器「{server.name}」Job 权限已配置")

print("\n========== Jenkins 权限配置完成 ==========")
print("权限在用户【重新登录】后生效")
