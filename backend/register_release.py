#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布流水线 —— 菜单与按钮权限注册（幂等，可重复执行）

做四件事：
  1. 确保「发布管理」目录存在（Jenkins 那批已经建过；没有就补建，避免依赖执行顺序）
  2. 在该目录下建两个子菜单：「流水线编排」（/releasePipeline）、「执行记录」（/releaseRun）
  3. 把 `release/views/pipeline.py` 上**每一个** @action 登记成 MenuButton
  4. 授权给角色

★ 为什么每个 @action 都要登记（本项目最贵的教训之一）
------------------------------------------------------
DVAdmin 的 `CustomPermission` 是拿请求的 (api 路径, HTTP method 下标) 去
`RoleMenuButtonPermission` 里**逐条** `re.match(api模板)` 的。所以：

  · 漏登记任何一个 action → 那条接口对**非超管**恒返回业务码 **4000**
    （注意：是 HTTP 200 + code 4000，不是 401/403，看日志很容易误判成"没登录"）
  · 只建 MenuButton、不授 `RoleMenuButtonPermission` → 连超管也是
    「页面在、按钮全没了」（前端按钮显隐是拿"当前角色的按钮数据"逐条比对的，
    `is_superuser` **不作数**）

用法（在 django 容器里跑）
--------------------------
  docker cp register_release.py dvadmin3-django:/backend/
  docker exec dvadmin3-django python /backend/register_release.py --dry-run   # 先看
  docker exec dvadmin3-django python /backend/register_release.py             # 再写

参数：
  --dry-run   只打印，不写库
  --skip-menu 只注册按钮/授权，不动菜单
"""
import os
import sys

DRY_RUN = "--dry-run" in sys.argv
SKIP_MENU = "--skip-menu" in sys.argv

PARENT_MENU = {
    "name": "发布管理",
    "web_path": "/publish",
    "icon": "ele-Promotion",
    "sort": 5,
}

CHILD_MENUS = [
    {
        "name": "流水线编排",
        "web_path": "/releasePipeline",
        "component": "release/pipeline/index",
        "component_name": "releasePipeline",
        "icon": "ele-Share",
        "sort": 3,
    },
    {
        "name": "执行记录",
        "web_path": "/releaseRun",
        "component": "release/run/index",
        "component_name": "releaseRun",
        "icon": "ele-List",
        "sort": 4,
    },
]

# HTTP method 常量（与 CustomPermission 的 methodList 索引一致）
GET, POST, PUT, DELETE = 0, 1, 2, 3

# 按钮定义：(所属菜单 component_name, 按钮名, 权限码, API 路径, method)
# ★ 与 `release/views/pipeline.py` 的 @action 一一对应，改那边记得回来同步
BUTTONS = [
    # ---- 流水线编排 ----
    ("releasePipeline", "查询", "pipeline:Search", "/api/release/pipeline/", GET),
    ("releasePipeline", "新增", "pipeline:Create", "/api/release/pipeline/", POST),
    ("releasePipeline", "查看", "pipeline:View", "/api/release/pipeline/{id}/", GET),
    ("releasePipeline", "编辑", "pipeline:Update", "/api/release/pipeline/{id}/", PUT),
    ("releasePipeline", "删除", "pipeline:Delete", "/api/release/pipeline/{id}/", DELETE),
    ("releasePipeline", "流水线下拉", "pipeline:All", "/api/release/pipeline/all/", GET),
    ("releasePipeline", "页面下拉", "pipeline:Options", "/api/release/pipeline/options/", GET),
    ("releasePipeline", "读取编排", "pipeline:Nodes", "/api/release/pipeline/{id}/nodes/", GET),
    ("releasePipeline", "保存编排", "pipeline:NodeSave", "/api/release/pipeline/{id}/nodes/", POST),
    ("releasePipeline", "节点预检", "pipeline:Preview", "/api/release/node/preview/", POST),
    ("releasePipeline", "发起执行", "pipeline:Run", "/api/release/pipeline/{id}/run/", POST),
    # ---- 执行记录 ----
    ("releaseRun", "查询", "pipelineRun:Search", "/api/release/run/", GET),
    ("releaseRun", "查看", "pipelineRun:View", "/api/release/run/{id}/", GET),
    ("releaseRun", "推进节点", "pipelineRun:Advance", "/api/release/run/{id}/advance/", POST),
    ("releaseRun", "中止执行", "pipelineRun:Abort", "/api/release/run/{id}/abort/", POST),
    ("releaseRun", "重跑失败", "pipelineRun:Retry", "/api/release/run/{id}/retry/", POST),
]

# ★ 会**真的动生产**的动作（发起执行 / 推进节点 / 重跑）——
#   只给管理员与 ops，不给 readonly。给错一个，就是"只读用户能重启生产服务"。
TX_BUTTONS = {"pipeline:Run", "pipelineRun:Advance", "pipelineRun:Retry"}

ADMIN_ROLE_HINTS = ("超级管理员", "管理员", "运维")


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
        print("       请在 django 容器内执行：docker exec dvadmin3-django python register_release.py")
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
    print("=" * 70)
    print("发布流水线 · 菜单与按钮注册  %s" % ("[DRY-RUN 只预览]" if DRY_RUN else ""))
    print("=" * 70)

    if not setup_django():
        return

    from django.apps import apps

    Menu = apps.get_model("system", "Menu")
    MenuButton = apps.get_model("system", "MenuButton")
    Role = apps.get_model("system", "Role")
    RoleMenuPermission = apps.get_model("system", "RoleMenuPermission")
    RoleMenuButtonPermission = apps.get_model("system", "RoleMenuButtonPermission")
    Users = apps.get_model("system", "Users")

    # ---- 1. 父目录 ----
    parent = Menu.objects.filter(name=PARENT_MENU["name"], is_catalog=True).first()
    if parent is None:
        parent = Menu.objects.filter(name=PARENT_MENU["name"]).first()
    if parent is None:
        if DRY_RUN:
            print("[dry-run] 父目录「%s」不存在，待创建" % PARENT_MENU["name"])
            parent = None
        else:
            parent, _ = Menu.objects.get_or_create(
                name=PARENT_MENU["name"], is_catalog=True,
                defaults={"web_path": PARENT_MENU["web_path"], "icon": PARENT_MENU["icon"],
                          "sort": PARENT_MENU["sort"], "status": True, "cache": False, "visible": True})
            print("[ok] 父目录「%s」id=%s（新建）" % (parent.name, parent.id))
    if parent is not None:
        print("[ok] 父目录「%s」id=%s" % (parent.name, parent.id))

    # ---- 2. 子菜单 ----
    menu_map = {}
    for spec in CHILD_MENUS:
        if SKIP_MENU:
            menu = Menu.objects.filter(name=spec["name"], parent=parent).first()
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
            print("[ok] 子菜单「%s」id=%s %s" % (menu.name, menu.id, "新建" if created else "已存在(已校正字段)"))
        if menu is not None:
            menu_map[spec["component_name"]] = menu

    if not DRY_RUN:
        print("     ★ 前提：web/src/views/release/** 必须已经构建进 web 镜像，")
        print("       否则菜单点进去会因找不到组件而空白（接口没问题，只是页面不在）")

    # ---- 3. 按钮 ----
    btn_by_code = {}
    for comp, bname, value, api, method in BUTTONS:
        menu = menu_map.get(comp)
        if DRY_RUN:
            print("[dry-run] 按钮 %-16s %-24s %s method=%s" % (bname, value, api, method))
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
        print("=" * 70)
        return

    # ---- 4. 授权 ----
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
        print("[警告] 库里一个角色都没有，菜单/按钮没授出去 → 需要到「角色管理」里手工勾选")
        return

    # 菜单：给所有角色（按钮权限再细分动作）
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
    print("[ok] 完整按钮授权：%s → 新增 %d 条" % (", ".join(r.name for r in grant_roles), cnt_full))

    cnt_ro = 0
    if readonly_role:
        for b in btn_by_code.values():
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
    for comp, menu in menu_map.items():
        for b in MenuButton.objects.filter(menu=menu):
            roles = RoleMenuButtonPermission.objects.filter(menu_button=b).count()
            print("  %-16s id=%-5s %-16s %-26s method=%s 已授权角色=%d"
                  % (comp, b.id, b.name, b.value, b.method, roles))

    print()
    print("=" * 70)
    print("完成。接下来必须做：")
    print("  1) docker exec dvadmin3-django python manage.py migrate bastion")
    print("     （给命令审计的 source 加 'release' 档；只改枚举，不动数据）")
    print("  2) docker exec dvadmin3-django python manage.py migrate release")
    print("     （新增 release_pipeline / release_pipeline_node /")
    print("       release_pipeline_run / release_pipeline_node_run 四张表）")
    print("  3) docker restart dvadmin3-django dvadmin3-celery")
    print("     （INSTALLED_APPS / urls.py / views 变更需要重启才加载）")
    print("  4) 重建 web 镜像（.vue 是编译进镜像的，新增页面必须重建）")
    print("  5) 重新登录（菜单/按钮权限在重新登录后才生效）")
    print("  6) 验证：GET /api/release/pipeline/options/ 应返回 credentials / jenkins_servers / node_types")
    print("=" * 70)


if __name__ == "__main__":
    main()
