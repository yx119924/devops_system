#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""巡检中心 —— 菜单与按钮权限注册（幂等，可重复执行）

做三件事：
  1. 确保「巡检中心」目录存在（is_catalog=True 的父目录）
  2. 在该目录下建子菜单「巡检日报」(/inspectionDaily)
  3. 把三个接口登记成 MenuButton 并授权

★ 为什么每个接口都要登记（本项目最贵的教训之一，见 register_release.py:11-20）
  漏登记任何一个 → 那条接口对**非超管**恒返回业务码 4000（HTTP 200 + code 4000），
  前端表现为「页面在、数据空」，日志里看不出是权限问题。
  只建 MenuButton 不授 RoleMenuButtonPermission → 连超管也是「按钮全没了」
  （前端按钮显隐拿的是当前角色的按钮数据，is_superuser 不作数）。

用法（在 django 容器里跑）
--------------------------
  docker cp register_inspection.py dvadmin3-django:/backend/
  docker exec dvadmin3-django python /backend/register_inspection.py --dry-run   # 先看
  docker exec dvadmin3-django python /backend/register_inspection.py             # 再写

参数：
  --dry-run   只打印，不写库
  --skip-menu 只注册按钮/授权，不动菜单
"""
import os
import sys

DRY_RUN = "--dry-run" in sys.argv
SKIP_MENU = "--skip-menu" in sys.argv

PARENT_MENU = {
    "name": "巡检中心",
    "web_path": "/inspection",
    "icon": "ele-DocumentChecked",
    "sort": 6,
}

CHILD_MENUS = [
    {
        "name": "巡检日报",
        "web_path": "/inspectionDaily",
        "component": "inspection/daily/index",
        "component_name": "inspectionDaily",
        "icon": "ele-Tickets",
        "sort": 1,
    },
]

# HTTP method 常量（与 CustomPermission 的 methodList 索引一致）
GET, POST, PUT, DELETE = 0, 1, 2, 3

# ★ api 统一写成 /api/xxx 形态：permission.py:122-127 会同时用「原样」和
#   「/api + 剥前缀后的 path」两种形态去 re.match，所以改造前后都能命中。
#   写成 /devops/xxx 反而匹配不上 —— request.path 里没有 /devops。
BUTTONS = [
    ("inspectionDaily", "查询日报", "inspection:View",
     "/api/inspection/daily/", GET),
    ("inspectionDaily", "导出Word报告", "inspection:ExportWord",
     "/api/inspection/export/word/", GET),
    ("inspectionDaily", "导出Excel附表", "inspection:ExportExcel",
     "/api/inspection/export/excel/", GET),
    ("inspectionDaily", "查询周报", "inspection:Weekly",
     "/api/inspection/weekly/", GET),
]

ADMIN_ROLE_HINTS = ("超级管理员", "管理员", "运维")

# 只读角色也能用的按钮（导出属于只读操作，报告是要给人看的）
READONLY_EXTRA = {"inspection:ExportWord", "inspection:ExportExcel"}


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
        print("       请在 django 容器内执行：docker exec dvadmin3-django python register_inspection.py")
        return False


def upsert_menu(Menu, parent, spec):
    defaults = {
        "web_path": spec["web_path"],
        "component": spec["component"],
        "component_name": spec["component_name"],
        "icon": spec["icon"],
        "sort": spec["sort"],
        "status": True,
        "cache": False,
        "visible": True,
        "is_catalog": False,
        "is_link": False,
        "is_iframe": False,
    }
    menu, created = Menu.objects.get_or_create(name=spec["name"], parent=parent, defaults=defaults)
    if not created:
        for k, v in defaults.items():
            setattr(menu, k, v)
        menu.save()
    return menu, created


def main():
    print("=" * 72)
    print("巡检中心 · 菜单与按钮注册  %s" % ("[DRY-RUN 只预览]" if DRY_RUN else ""))
    print("=" * 72)

    if not setup_django():
        return

    from django.apps import apps

    Menu = apps.get_model("system", "Menu")
    MenuButton = apps.get_model("system", "MenuButton")
    Role = apps.get_model("system", "Role")
    RoleMenuPermission = apps.get_model("system", "RoleMenuPermission")
    RoleMenuButtonPermission = apps.get_model("system", "RoleMenuButtonPermission")
    Users = apps.get_model("system", "Users")

    # ---- 1. 父目录
    parent = Menu.objects.filter(name=PARENT_MENU["name"], is_catalog=True).first()
    if parent is None:
        parent = Menu.objects.filter(name=PARENT_MENU["name"]).first()
    if parent is None:
        if DRY_RUN:
            print("[dry-run] 父目录「%s」不存在，待创建" % PARENT_MENU["name"])
        else:
            parent, _ = Menu.objects.get_or_create(
                name=PARENT_MENU["name"], is_catalog=True,
                defaults={"web_path": PARENT_MENU["web_path"], "icon": PARENT_MENU["icon"],
                          "sort": PARENT_MENU["sort"], "status": True, "cache": False,
                          "visible": True})
            print("[ok] 父目录「%s」id=%s（新建）" % (parent.name, parent.id))
    if parent is not None:
        print("[ok] 父目录「%s」id=%s" % (parent.name, parent.id))
    else:
        if DRY_RUN:
            parent = None

    # ---- 2. 子菜单
    menu_map = {}
    for spec in CHILD_MENUS:
        if SKIP_MENU:
            menu = Menu.objects.filter(name=spec["name"]).first()
            print("[--skip-menu] 使用已有菜单「%s」id=%s" % (spec["name"], menu.id if menu else "未找到"))
        elif DRY_RUN:
            exists = Menu.objects.filter(name=spec["name"], parent=parent).first()
            print("[dry-run] 子菜单「%s」web_path=%s component=%s %s"
                  % (spec["name"], spec["web_path"], spec["component"],
                     "已存在 id=%s" % exists.id if exists else "待创建"))
            menu = exists
        else:
            if parent is None:
                print("[FAIL] 父目录不存在，无法建子菜单")
                return
            menu, created = upsert_menu(Menu, parent, spec)
            print("[ok] 子菜单「%s」id=%s %s"
                  % (menu.name, menu.id, "新建" if created else "已存在(已校正字段)"))
        if menu is not None:
            menu_map[spec["component_name"]] = menu

    if not DRY_RUN:
        print("     ★ 前提：web/src/views/inspection/** 必须已经构建进 web 镜像，")
        print("       否则菜单点进去会因找不到组件而空白（接口没问题，只是页面不在）")

    # ---- 3. 按钮
    btn_by_code = {}
    for comp, bname, value, api, method in BUTTONS:
        menu = menu_map.get(comp)
        if DRY_RUN:
            print("[dry-run] 按钮 %-16s %-22s %s method=%s" % (bname, value, api, method))
            continue
        if menu is None:
            print("[skip] 按钮 %s：菜单 %s 不存在" % (value, comp))
            continue
        obj, created = MenuButton.objects.update_or_create(
            menu=menu, value=value, defaults={"name": bname, "api": api, "method": method})
        btn_by_code[value] = obj
        print("[ok] 按钮 %s（%s）" % (value, "新建" if created else "更新"))

    if DRY_RUN:
        print()
        print("[dry-run] 授权步骤跳过（--dry-run 不写库）")
        print("=" * 72)
        return

    # ---- 4. 授权
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

    ops_role = Role.objects.filter(key="ops").first()
    readonly_role = Role.objects.filter(key="readonly").first()
    all_roles = list(Role.objects.all())
    if not all_roles:
        print("[警告] 库里一个角色都没有，菜单/按钮没授出去 → 需到「角色管理」手工勾选")
        return

    # 菜单：给所有角色（巡检报告是只读视图，不涉及数据变更）
    m_cnt = 0
    for menu in menu_map.values():
        for r in all_roles:
            _, c = RoleMenuPermission.objects.get_or_create(role=r, menu=menu)
            m_cnt += 1 if c else 0
    print("[ok] 菜单授权：%d 个角色 × %d 个菜单 → 新增 %d 条"
          % (len(all_roles), len(menu_map), m_cnt))

    grant_roles = list(admin_roles)
    if ops_role and ops_role.id not in seen:
        grant_roles.append(ops_role)
    if not grant_roles:
        print("[警告] 没识别到管理员/ops 角色 → 兜底把所有按钮授给全部角色（请自行复核）")
        grant_roles = all_roles

    cnt_full = 0
    for r in grant_roles:
        for b in btn_by_code.values():
            _, c = RoleMenuButtonPermission.objects.update_or_create(
                role=r, menu_button=b, defaults={"data_range": 3})
            cnt_full += 1 if c else 0
    print("[ok] 完整按钮授权：%s → 新增 %d 条"
          % (", ".join(r.name for r in grant_roles), cnt_full))

    cnt_ro = 0
    if readonly_role:
        for b in btn_by_code.values():
            if b.method != GET:
                continue
            if b.value not in READONLY_EXTRA and b.value != "inspection:View":
                continue
            _, c = RoleMenuButtonPermission.objects.update_or_create(
                role=readonly_role, menu_button=b, defaults={"data_range": 3})
            cnt_ro += 1 if c else 0
        print("[ok] 只读角色（%s）：查询 + 导出 → 新增 %d 条" % (readonly_role.name, cnt_ro))
    else:
        print("[提示] 没有 key=readonly 的角色，跳过只读授权")

    # ---- 5. 回显
    print()
    print("--- 按钮清单 ---")
    for comp, menu in menu_map.items():
        for b in MenuButton.objects.filter(menu=menu):
            roles = RoleMenuButtonPermission.objects.filter(menu_button=b).count()
            print("  %-18s id=%-5s %-16s %-30s method=%s 已授权角色=%d"
                  % (comp, b.id, b.name, b.value, b.method, roles))

    print()
    print("=" * 72)
    print("完成。接下来必须做：")
    print("  1) 重建 backend 镜像（requirements.txt 新增了 python-docx）：")
    print("     docker compose build dvadmin3-django dvadmin3-celery")
    print("     docker compose up -d dvadmin3-django dvadmin3-celery")
    print("     ★ 只重启不重建 → import docx 会 ModuleNotFoundError，导出接口 500")
    print("  2) 重建 web 镜像（新增了 views/inspection 页面）：")
    print("     docker compose build dvadmin3-web && docker compose up -d dvadmin3-web")
    print("  3) 重新登录（菜单/按钮权限在重新登录后才生效）")
    print("  4) 验证：GET /devops/inspection/daily/?date=昨天 应返回 code=2000 且 total ≥ 0")
    print("=" * 72)


if __name__ == "__main__":
    main()
