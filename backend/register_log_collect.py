#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日志采集配置 —— 菜单与按钮权限注册（幂等，可重复执行）

做三件事：
  1. 在「日志管理」目录下建子菜单「采集配置」
     （web_path=/logCollect, component=log/collect/index, component_name=logCollect）
  2. 把 ``LogCollectTaskViewSet`` 上**每一个** @action 登记成 MenuButton
  3. 授权给角色

★ 为什么每个 @action 都要登记（这是本项目最贵的教训之一）
--------------------------------------------------------
DVAdmin 的 ``CustomPermission`` 是拿请求的 (api 路径, HTTP method 下标) 去
``RoleMenuButtonPermission`` 里**逐条** ``re.match(api模板)`` 的。所以：

  · 漏登记任何一个 action → 那条接口对**非超管**恒返回业务码 **4000**
    （注意：是 HTTP 200 + code 4000，不是 401/403，看日志很容易误判成"没登录"）
  · 只建 MenuButton、不授 ``RoleMenuButtonPermission`` → 连续超管也是
    「页面在、按钮全没了」（前端按钮显隐是拿"当前角色的按钮数据"逐条比对的，
    ``is_superuser`` **不作数**）

所以建了菜单/按钮之后**一定要授权**，且授权要用"用户实际绑定的角色"而不是
"名字里带管理员"。

用法（在 django 容器里跑）
--------------------------
  docker cp register_log_collect.py dvadmin3-django:/backend/
  docker exec dvadmin3-django python /backend/register_log_collect.py --dry-run   # 先看
  docker exec dvadmin3-django python /backend/register_log_collect.py             # 再写

参数：
  --dry-run   只打印，不写库
  --skip-menu 只注册按钮/授权，不动菜单（菜单已手工建好时用）
"""
import os
import sys

DRY_RUN = "--dry-run" in sys.argv
SKIP_MENU = "--skip-menu" in sys.argv

# ============================================================
# 菜单定义
# ============================================================
PARENT_MENU_NAME = "日志管理"          # 已存在的目录（register_menu_grafana_es.sh 建的）

CHILD_MENU = {
    "name": "采集配置",
    "web_path": "/logCollect",
    "component": "log/collect/index",
    "component_name": "logCollect",
    "icon": "ele-Files",
    "sort": 4,                          # 现有：ES 数据源 1 / 日志检索 2
    "is_catalog": False,
}

# HTTP method 常量（与 CustomPermission 的 methodList 索引一致）
GET, POST, PUT, DELETE = 0, 1, 2, 3

# 按钮定义：(按钮名, 权限码, API 路径, method)
# ★ 与 backend/log/views/collect.py 的 @action 一一对应，改那边记得回来同步
BUTTONS = [
    # —— 标准 CRUD（CustomModelViewSet 提供）——
    ("查询", "logCollect:Search", "/api/log/collect/", GET),
    ("新增", "logCollect:Create", "/api/log/collect/", POST),
    ("查看", "logCollect:View", "/api/log/collect/{id}/", GET),
    ("编辑", "logCollect:Update", "/api/log/collect/{id}/", PUT),
    ("删除", "logCollect:Delete", "/api/log/collect/{id}/", DELETE),
    # —— 下拉类（接口是 IsAuthenticated，这里登记是为了前端按钮显隐一致）——
    ("任务下拉", "logCollect:All", "/api/log/collect/all/", GET),
    ("页面下拉", "logCollect:Options", "/api/log/collect/options/", GET),
    ("主配置", "logCollect:MainPatch", "/api/log/collect/{id}/main_patch/", GET),
    ("台账", "logCollect:Records", "/api/log/collect/{id}/records/", GET),
    # —— 会动目标机的三个动作：只给管理员 / 普通运维 ——
    ("环境检测", "logCollect:Detect", "/api/log/collect/{id}/detect/", POST),
    ("规则试跑", "logCollect:Preview", "/api/log/collect/{id}/preview/", POST),
    ("下发配置", "logCollect:Apply", "/api/log/collect/{id}/apply/", POST),
    ("停止采集", "logCollect:Stop", "/api/log/collect/{id}/stop/", POST),
]

# ★ 会改目标机的动作（下发/停止）—— 只给管理员与 ops，不给 readonly
TX_BUTTONS = {"logCollect:Apply", "logCollect:Stop"}

ADMIN_ROLE_HINTS = ("超级管理员", "管理员", "运维")


# ============================================================
def setup_django():
    for p in (os.environ.get("XWOPS_BACKEND"), "/backend", "/opt/devops-platform/backend"):
        if p and os.path.isfile(os.path.join(p, "application", "settings.py")):
            if p not in sys.path:
                sys.path.insert(0, p)
            break
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")
    try:
        import django
        django.setup()
        return True
    except Exception as exc:                                       # noqa: BLE001
        print("[跳过] django 环境不可用：%s" % exc)
        print("       请在 django 容器内执行：docker exec dvadmin3-django python register_log_collect.py")
        return False


def main():
    print("=" * 66)
    print("日志采集配置 · 菜单与按钮注册  %s" % ("[DRY-RUN 只预览]" if DRY_RUN else ""))
    print("=" * 66)

    if not setup_django():
        return

    from django.apps import apps

    Menu = apps.get_model("system", "Menu")
    MenuButton = apps.get_model("system", "MenuButton")
    Role = apps.get_model("system", "Role")
    RoleMenuPermission = apps.get_model("system", "RoleMenuPermission")
    RoleMenuButtonPermission = apps.get_model("system", "RoleMenuButtonPermission")
    Users = apps.get_model("system", "Users")

    # ---- 1. 父菜单（日志管理目录）----
    parent = Menu.objects.filter(name=PARENT_MENU_NAME).first()
    if parent is None:
        print("[FAIL] 未找到父菜单「%s」。" % PARENT_MENU_NAME)
        print("       先跑 register_menu_grafana_es.sh 建「日志管理」目录，再跑本脚本。")
        return
    print("[ok] 父菜单「%s」id=%s" % (parent.name, parent.id))

    # ---- 2. 子菜单 ----
    menu = None
    if SKIP_MENU:
        menu = Menu.objects.filter(name=CHILD_MENU["name"], parent=parent).first()
        print("[--skip-menu] 直接使用已有菜单：%s" % (menu.id if menu else "未找到"))
    elif DRY_RUN:
        exists = Menu.objects.filter(name=CHILD_MENU["name"], parent=parent).first()
        print("[dry-run] 子菜单「%s」web_path=%s component=%s %s"
              % (CHILD_MENU["name"], CHILD_MENU["web_path"], CHILD_MENU["component"],
                 "已存在 id=%s" % exists.id if exists else "待创建"))
        menu = exists
    else:
        defaults = {
            "web_path": CHILD_MENU["web_path"],
            "component": CHILD_MENU["component"],
            "component_name": CHILD_MENU["component_name"],
            "icon": CHILD_MENU["icon"],
            "sort": CHILD_MENU["sort"],
            "status": True,
            "cache": False,
            "visible": True,
            "is_catalog": False,
            "is_link": False,
            "is_iframe": False,
        }
        menu, created = Menu.objects.get_or_create(
            name=CHILD_MENU["name"], parent=parent, defaults=defaults)
        if not created:
            for k, v in defaults.items():
                setattr(menu, k, v)
            menu.save()
        print("[ok] 子菜单「%s」id=%s %s"
              % (menu.name, menu.id, "新建" if created else "已存在(已校正字段)"))
        print("     ★ 前提：web/src/views/log/collect/index.vue 必须已经构建进 web 镜像，")
        print("       否则菜单点进去会因找不到组件而空白（接口没问题，只是页面不在）")

    # ---- 3. 按钮 ----
    btn_objs = []
    for bname, value, api, method in BUTTONS:
        if DRY_RUN:
            print("[dry-run] 按钮 %-14s %-22s %s method=%s" % (bname, value, api, method))
            continue
        if menu is None:
            print("[skip] 按钮 %s：菜单不存在" % value)
            continue
        obj, created = MenuButton.objects.update_or_create(
            menu=menu, value=value,
            defaults={"name": bname, "api": api, "method": method})
        btn_objs.append(obj)
        print("[ok] 按钮 %s（%s）" % (value, "新建" if created else "更新"))

    if DRY_RUN:
        print()
        print("[dry-run] 授权步骤跳过（--dry-run 不写库）")
        print("=" * 66)
        return

    # ---- 4. 授权 ----
    # 找出「管理员档」：admin=True / 名字含管理员运维 / 超管实际绑定的角色
    admin_roles, seen = [], set()
    if hasattr(Role, "admin"):
        for r in Role.objects.filter(admin=True):
            if r.id not in seen:
                seen.add(r.id)
                admin_roles.append(r)
    for r in Role.objects.all():
        if any(h in (r.name or "") for h in ADMIN_ROLE_HINTS) and r.id not in seen:
            seen.add(r.id)
            admin_roles.append(r)
    for u in Users.objects.filter(is_superuser=True):
        for r in u.role.all():
            if r.id not in seen:
                seen.add(r.id)
                admin_roles.append(r)
        if u.current_role_id and u.current_role_id not in seen:
            seen.add(u.current_role_id)
            admin_roles.append(u.current_role)

    ops_role = Role.objects.filter(key="ops").first()
    readonly_role = Role.objects.filter(key="readonly").first()
    all_roles = list(Role.objects.all())

    if not all_roles:
        print("[警告] 库里一个角色都没有，菜单/按钮没授出去 → 需要到「角色管理」里手工勾选")
        return

    # 菜单：给所有角色（采集配置是运维日常功能，靠按钮权限细分动作）
    m_cnt = 0
    for r in all_roles:
        _, c = RoleMenuPermission.objects.get_or_create(role=r, menu=menu)
        m_cnt += 1 if c else 0
    print("[ok] 菜单授权：%d 个角色 → 新增 %d 条" % (len(all_roles), m_cnt))

    # 按钮：
    #   · 管理员档 + ops      → 全部按钮
    #   · readonly            → 只有 GET 类，且**不含会改目标机的动作**
    #   · 若既没有管理员档也没有 ops → 兜底给全部角色全部按钮（否则功能等于没上线）
    grant_roles = list(admin_roles)
    if ops_role and ops_role.id not in seen:
        grant_roles.append(ops_role)
    if not grant_roles:
        print("[警告] 没识别到管理员/ops 角色 → 兜底把所有按钮授给全部角色（请自行复核）")
        grant_roles = all_roles

    cnt_full = 0
    for r in grant_roles:
        for b in btn_objs:
            _, c = RoleMenuButtonPermission.objects.update_or_create(
                role=r, menu_button=b, defaults={"data_range": 3})
            cnt_full += 1 if c else 0
    print("[ok] 完整按钮授权：%s → 新增 %d 条"
          % (", ".join(r.name for r in grant_roles), cnt_full))

    cnt_ro = 0
    if readonly_role:
        for b in btn_objs:
            if b.method != GET or b.value in TX_BUTTONS:
                continue
            _, c = RoleMenuButtonPermission.objects.update_or_create(
                role=readonly_role, menu_button=b, defaults={"data_range": 3})
            cnt_ro += 1 if c else 0
        print("[ok] 只读角色（%s）：仅 GET 类按钮 → 新增 %d 条" % (readonly_role.name, cnt_ro))
    else:
        print("[提示] 没有 key=readonly 的角色，跳过只读授权")

    # ---- 5. 回显 ----
    print()
    print("--- 按钮清单 ---")
    for b in MenuButton.objects.filter(menu=menu):
        roles = RoleMenuButtonPermission.objects.filter(menu_button=b).count()
        print("  id=%-5s %-14s %-22s method=%s 已授权角色=%d"
              % (b.id, b.name, b.value, b.method, roles))

    print()
    print("=" * 66)
    print("完成。接下来必须做：")
    print("  1) docker exec dvadmin3-django python manage.py makemigrations log")
    print("  2) docker exec dvadmin3-django python manage.py migrate log")
    print("     （新增 log_collect_task / log_collect_record 两张表）")
    print("  3) docker restart dvadmin3-django dvadmin3-celery")
    print("     （log/urls.py 与 views 变更需要重启才加载）")
    print("  4) 重建 web 镜像（.vue 是编译进镜像的，新增页面必须重建）")
    print("  5) 重新登录（菜单/按钮权限在重新登录后才生效）")
    print("  6) 验证：GET /api/log/collect/options/ 应返回 sources / credentials / levels")
    print("=" * 66)


if __name__ == "__main__":
    main()
