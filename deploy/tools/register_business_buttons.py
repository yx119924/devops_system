# -*- coding: utf-8 -*-
"""
XwOps 业务页面按钮权限注册 + 标准角色模板（幂等，可重复执行）

背景：
  DVAdmin3 后端 CustomPermission 按「API路径 + HTTP方法」去 RoleMenuButtonPermission
  表匹配权限。业务 CRUD 页（继承 CustomModelViewSet）此前未注册 MenuButton，
  导致任何非 superuser 访问列表/增删改接口都被拒（前端红框提示）。

本脚本一次性完成：
  1. 给所有业务 CRUD 页注册 MenuButton（查询/新增/编辑/删除 + 额外 action）
  2. 建两个标准角色：普通运维(ops) / 只读查看(readonly)
  3. 给角色授权菜单 + 按钮权限
  4. 将指定用户换绑到标准角色（默认 zhuyk -> ops）

用法（在 django 容器内执行）：
  docker exec dvadmin3-django python register_business_buttons.py [用户名]
  不带参数默认处理 zhuyk；传入 --dry-run 只预览不写库。
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")
django.setup()

from django.apps import apps

Menu = apps.get_model("system", "Menu")
MenuButton = apps.get_model("system", "MenuButton")
Role = apps.get_model("system", "Role")
RoleMenuPermission = apps.get_model("system", "RoleMenuPermission")
RoleMenuButtonPermission = apps.get_model("system", "RoleMenuButtonPermission")
Users = apps.get_model("system", "Users")

# HTTP method 常量（与 CustomPermission 的 methodList 索引一致）
GET, POST, PUT, DELETE = 0, 1, 2, 3

DRY_RUN = "--dry-run" in sys.argv
TARGET_USER = "zhuyk"
for arg in sys.argv[1:]:
    if not arg.startswith("--"):
        TARGET_USER = arg


def get_menu(name):
    return Menu.objects.get(name=name)


# ============================================================
# 1. 按钮定义
# ============================================================
# 标准 CRUD 页：(菜单名, value前缀, api前缀)
CRUD_PAGES = [
    ("机房管理", "idc", "/api/cmdb/idc/"),
    ("环境管理", "environment", "/api/cmdb/environment/"),
    ("业务线管理", "businessLine", "/api/cmdb/business_line/"),
    ("服务器管理", "server", "/api/cmdb/server/"),
    ("凭据管理", "credential", "/api/bastion/credential/"),
    ("数据源管理", "prometheus", "/api/monitor/prometheus/"),
    ("告警规则", "rule", "/api/alert/rule/"),
    ("通知渠道", "channel", "/api/alert/channel/"),
    ("告警群组", "group", "/api/alert/group/"),
    ("告警模板", "template", "/api/alert/template/"),
    ("命令下发", "dispatch", "/api/bastion/dispatch/"),
]

# 只读页：(菜单名, value前缀, api前缀) —— 只需查询按钮
READONLY_PAGES = [
    ("会话记录", "session", "/api/bastion/session/"),
    ("命令审计", "commandLog", "/api/bastion/command_log/"),
    ("历史告警", "event", "/api/alert/event/"),
]

# 额外 action 按钮：(菜单名, 按钮名, value, api, method)
EXTRA_ACTIONS = [
    ("数据源管理", "测试连接", "prometheus:Test", "/api/monitor/prometheus/{id}/test/", GET),
    ("指标查询", "数据源下拉", "query:SourceList", "/api/monitor/prometheus/all/", GET),
    ("指标查询", "即时查询", "query:Query", "/api/monitor/prometheus/{id}/query/", POST),
    ("指标查询", "告警列表", "query:Alerts", "/api/monitor/prometheus/{id}/alerts/", GET),
    ("告警规则", "重载规则", "rule:Reload", "/api/alert/rule/reload/", POST),
    ("告警规则", "规则预览", "rule:Preview", "/api/alert/rule/preview/", POST),
    ("告警规则", "规则下拉", "rule:All", "/api/alert/rule/all/", GET),
    ("通知渠道", "渠道下拉", "channel:All", "/api/alert/channel/all/", GET),
    ("通知渠道", "测试发送", "channel:Test", "/api/alert/channel/{id}/test/", POST),
    ("告警群组", "群组下拉", "group:All", "/api/alert/group/all/", GET),
    ("告警模板", "模板下拉", "template:All", "/api/alert/template/all/", GET),
    ("告警模板", "模板预览", "template:Preview", "/api/alert/template/preview/", POST),
    # 命令下发已有按钮（P3 阶段注册，纳入统一授权）
    ("命令下发", "查看", "dispatch:View", "/api/bastion/dispatch/{id}/", GET),
    ("命令下发", "执行", "dispatch:Execute", "/api/bastion/dispatch/{id}/execute/", POST),
    ("命令下发", "重试失败", "dispatch:Retry", "/api/bastion/dispatch/{id}/execute/", POST),
    ("命令下发", "查看结果", "dispatch:Items", "/api/bastion/dispatch/{id}/items/", GET),
]

# ============================================================
# 2. 生成完整按钮清单
# ============================================================
buttons = []  # (menu_name, name, value, api, method)

for menu_name, prefix, api in CRUD_PAGES:
    buttons.append((menu_name, "查询", f"{prefix}:Search", api, GET))
    buttons.append((menu_name, "新增", f"{prefix}:Create", api, POST))
    buttons.append((menu_name, "编辑", f"{prefix}:Update", api + "{id}/", PUT))
    buttons.append((menu_name, "删除", f"{prefix}:Delete", api + "{id}/", DELETE))

for menu_name, prefix, api in READONLY_PAGES:
    buttons.append((menu_name, "查询", f"{prefix}:Search", api, GET))

buttons.extend(EXTRA_ACTIONS)

# ============================================================
# 3. 注册按钮（幂等）
# ============================================================
btn_objs = []
created_btns = 0
updated_btns = 0

for menu_name, name, value, api, method in buttons:
    menu = get_menu(menu_name)
    if DRY_RUN:
        print(f"[dry-run] 按钮 {menu_name} / {name} / {value} / {api} / method={method}")
        continue
    obj, created = MenuButton.objects.update_or_create(
        menu=menu,
        value=value,
        defaults={"name": name, "api": api, "method": method},
    )
    btn_objs.append(obj)
    if created:
        created_btns += 1
    else:
        updated_btns += 1

# ============================================================
# 4. 标准角色
# ============================================================
if not DRY_RUN:
    ops, _ = Role.objects.get_or_create(
        key="ops", defaults={"name": "普通运维", "sort": 3, "status": True}
    )
    readonly, _ = Role.objects.get_or_create(
        key="readonly", defaults={"name": "只读查看", "sort": 4, "status": True}
    )
    print(f"\n角色：普通运维(ops) id={ops.id}，只读查看(readonly) id={readonly.id}")

# ============================================================
# 5. 菜单权限（ops / readonly 用同一套业务菜单）
# ============================================================
BUSINESS_MENUS = [
    "日志管理", "登录日志", "操作日志",
    "定时任务", "任务管理", "任务日志",
    "资产管理", "机房管理", "环境管理", "业务线管理", "服务器管理",
    "堡垒机", "凭据管理", "会话记录", "命令审计", "命令下发",
    "监控告警", "数据源管理", "指标查询", "告警管理",
    "告警规则", "通知渠道", "告警群组", "活跃告警", "历史告警", "告警模板",
]

menu_perm_count = 0
if not DRY_RUN:
    for menu_name in BUSINESS_MENUS:
        menu = get_menu(menu_name)
        _, c1 = RoleMenuPermission.objects.get_or_create(role=ops, menu=menu)
        _, c2 = RoleMenuPermission.objects.get_or_create(role=readonly, menu=menu)
        menu_perm_count += (1 if c1 else 0) + (1 if c2 else 0)

# ============================================================
# 6. 按钮权限
#    ops      -> 全部按钮
#    readonly -> 仅查询类按钮（method == GET）
# ============================================================
btn_perm_count = 0
if not DRY_RUN:
    for b in btn_objs:
        _, c = RoleMenuButtonPermission.objects.update_or_create(
            role=ops, menu_button=b, defaults={"data_range": 3}
        )
        btn_perm_count += 1 if c else 0
        if b.method == GET:
            _, c = RoleMenuButtonPermission.objects.update_or_create(
                role=readonly, menu_button=b, defaults={"data_range": 3}
            )
            btn_perm_count += 1 if c else 0

# ============================================================
# 7. 目标用户换绑
# ============================================================
if DRY_RUN:
    print("\n[dry-run] 结束，未写库")
    sys.exit(0)

try:
    user = Users.objects.get(username=TARGET_USER)
    user.role.clear()
    user.role.add(ops)
    user.current_role = ops
    user.save(update_fields=["current_role"])
    print(f"\n用户 {TARGET_USER} 已换绑到「普通运维」(ops)，current_role 已设置")
except Users.DoesNotExist:
    print(f"\n[警告] 用户 {TARGET_USER} 不存在，跳过换绑")

# ============================================================
# 8. 汇总
# ============================================================
print("\n========== 完成汇总 ==========")
print(f"按钮：新增 {created_btns}，更新 {updated_btns}，共 {len(buttons)} 条定义")
print(f"菜单授权：新增 {menu_perm_count} 条")
print(f"按钮授权：新增 {btn_perm_count} 条")
print("注意：权限在用户【重新登录】后生效")
