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
  --dry-run    只打印，不写库
  --skip-menu  只注册按钮/授权，不动菜单
  --roles      指定哪些角色拿「全部按钮」（查询 + 导出），逗号分隔，key 或中文名都行
               例：--roles admin,ops,developer,tester
               不传则默认「管理员 + 运维」；只读角色固定只给查看与导出（GET）
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
    {
        "name": "巡检周报",
        "web_path": "/inspectionWeekly",
        "component": "inspection/weekly/index",
        "component_name": "inspectionWeekly",
        "icon": "ele-Calendar",
        "sort": 2,
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
    # 周报接口归周报菜单，挂在日报下会导致「日报页有周报按钮权限」的错位
    ("inspectionWeekly", "查询周报", "inspection:Weekly",
     "/api/inspection/weekly/", GET),
    ("inspectionWeekly", "导出周报Word", "inspection:ExportWeeklyWord",
     "/api/inspection/export/weekly/word/", GET),
    ("inspectionWeekly", "导出周报Excel", "inspection:ExportWeeklyExcel",
     "/api/inspection/export/weekly/excel/", GET),
]

ADMIN_ROLE_HINTS = ("超级管理员", "管理员", "运维")

# 只读角色也能用的按钮（导出属于只读操作，报告是要给人看的）
READONLY_EXTRA = {"inspection:ExportWord", "inspection:ExportExcel"}
READONLY_WEEKLY = {"inspection:ExportWeeklyWord", "inspection:ExportWeeklyExcel"}

# 只读角色可以拿到的全部按钮（都是 GET，不改数据）
# ★ 必须在 READONLY_EXTRA / READONLY_WEEKLY 都定义之后才能求值 ——
#   放前面会在模块导入阶段直接 NameError，脚本连 --dry-run 都跑不起来。
READONLY_ALLOW = (READONLY_EXTRA | READONLY_WEEKLY
                  | {"inspection:View", "inspection:Weekly"})


def _parse_roles(argv):
    """--roles admin,ops,developer,tester —— 支持角色 key，也支持中文角色名。"""
    for i, a in enumerate(argv):
        if a == "--roles" and i + 1 < len(argv):
            return [x.strip() for x in argv[i + 1].split(",") if x.strip()]
        if a.startswith("--roles="):
            return [x.strip() for x in a.split("=", 1)[1].split(",") if x.strip()]
    return []


TARGET_ROLES = _parse_roles(sys.argv)


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
        # ★★ MenuButton.value 在表上是**全局唯一**（dvadmin_system_menu_button.value），
        #    而 update_or_create(menu=..., value=...) 会把 menu 一起算进查询条件：
        #    按钮一旦换菜单（如 inspection:Weekly 从日报挪到周报），就查不到旧记录 ⇒
        #    走新建 ⇒ 撞唯一键报 1062 Duplicate entry。
        #    所以必须先按 value 查，命中就把它的 menu 改过来（搬菜单），而不是按 (menu,value) 查。
        obj = MenuButton.objects.filter(value=value).first()
        if obj is None:
            obj = MenuButton.objects.create(
                menu=menu, value=value, name=bname, api=api, method=method)
            created = True
        else:
            created = False
            moved = obj.menu_id != menu.id
            obj.menu = menu
            obj.name = bname
            obj.api = api
            obj.method = method
            obj.save()
            if moved:
                print("     ↳ 已从其它菜单迁移：%s → %s" % (value, menu.name))
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

    # ★ 先决定「谁能用」，再一致地授菜单与按钮。
    #   反过来的话会出现「菜单看得见、点进去每个请求都 4000」的半残状态 ——
    #   菜单授给全部角色、按钮只授给部分角色，就是这个后果。
    if TARGET_ROLES:
        grant_roles = []
        for token in TARGET_ROLES:
            r = (Role.objects.filter(key=token).first()
                 or Role.objects.filter(name=token).first())
            if r is None:
                print("[警告] 找不到角色：%s" % token)
                continue
            grant_roles.append(r)
            print("[ok] 匹配角色：%s（key=%s）" % (r.name, r.key))
        if not grant_roles:
            print("[FAIL] --roles 一个都没匹配上，可用 key：admin / ops / developer / tester / readonly")
            return
    else:
        grant_roles = list(admin_roles)
        if ops_role and ops_role.id not in seen:
            grant_roles.append(ops_role)
        if not grant_roles:
            print("[警告] 没识别到管理员/ops 角色 → 兜底把所有按钮授给全部角色（请自行复核）")
            grant_roles = all_roles

    # 菜单：授给 grant_roles + 只读角色（只读角色只能看，不能改，但要能打开页面）
    view_roles = list(grant_roles)
    if readonly_role and readonly_role not in view_roles:
        view_roles.append(readonly_role)

    m_cnt = 0
    for menu in menu_map.values():
        for r in view_roles:
            _, c = RoleMenuPermission.objects.get_or_create(role=r, menu=menu)
            m_cnt += 1 if c else 0
    print("[ok] 菜单授权：%s × %d 个菜单 → 新增 %d 条"
          % ("、".join(r.name for r in view_roles), len(menu_map), m_cnt))

    cnt_full = 0
    for r in grant_roles:
        for b in btn_by_code.values():
            _, c = RoleMenuButtonPermission.objects.update_or_create(
                role=r, menu_button=b, defaults={"data_range": 3})
            cnt_full += 1 if c else 0
    print("[ok] 全部按钮授权：%s → 新增 %d 条"
          % ("、".join(r.name for r in grant_roles), cnt_full))

    cnt_ro = 0
    if readonly_role and readonly_role not in grant_roles:
        for b in btn_by_code.values():
            if b.method != GET:
                continue
            if b.value not in READONLY_ALLOW:
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
