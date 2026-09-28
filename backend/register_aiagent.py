#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 运维助手 —— 后端落地脚本（幂等，可重复执行）

一次做四件事：
  1. 文件补丁：application/settings.py 注册 dvadmin.aiagent、application/urls.py 挂 api/aiagent/
  2. 建菜单：父目录「AI 运维助手」+ 子菜单「模型配置」（可选「智能问答」）
  3. 建按钮权限：MenuButton（查询/新增/编辑/删除 + 测试连接 / 设为默认 / 护栏三项）
  4. 授权

★ 授权口径（这是 BYOK 决定的，改之前先想清楚）
  「模型配置」现在是**个人私有**的（每人填自己的 API Key），所以：
    · 菜单「模型配置」+ `ai_provider:*` → **所有角色**（不然普通运维没法配自己的 Key，功能等于没上线）
    · 只有 `ai_guard:*`（护栏：白/黑名单、开关、脱敏、限额）→ **仅管理员角色**
      —— 护栏能改白名单，等于能决定 AI 能跑什么命令，不该下放
  「智能问答」→ **所有角色**（会话与数据按 owner 隔离，跨人不可见）
  ★ 前端会按 `ai_guard:Update` 这个权限码隐藏「安全护栏」页签，
    所以**没有**只授 `ai_guard:Current` 而不授 Update 的中间档（那样页签露出来却存不了）。

为什么第 4 步必须有：
  前端 is_superuser **不作数** —— 按钮显隐是拿「当前角色的按钮数据」逐条比对的
  （见 register_business_buttons.py 第 7.5 节的注释）。只建 MenuButton 不授权，
  超管进去也是「页面在、按钮全没了」。
  ★ 更硬的一层：后端的 `CustomPermission` 也是拿 RoleMenuButtonPermission 逐条
    `re.match(api模板 + ':' + method索引)` 的 —— **没授权 = 接口返回业务码 4000**，
    不是"按钮灰着但接口还能调"。

用法（在 django 容器里跑，容器里能同时看到 /backend 和 django 环境）：
  docker cp register_aiagent.py dvadmin3-django:/backend/
  docker exec dvadmin3-django python /backend/register_aiagent.py --dry-run   # 先看
  docker exec dvadmin3-django python /backend/register_aiagent.py             # 再写

参数：
  --dry-run     只打印，不写文件也不写库
  --no-rebind   不把没有任何角色的超管账号兜底绑到管理员角色
  --with-chat   额外注册「智能问答」子菜单与它的接口权限
                ★ 只有 ai/chat/index.vue 已经构建进 web 镜像之后才能加，
                  否则菜单点进去会因找不到组件而空白/报错
  --skip-patch  跳过 settings.py / urls.py 补丁（只想重跑菜单时用）
  --skip-migrate 不提示 makemigrations/migrate（本步没有新模型时可以）

跑完必须做：
  docker restart dvadmin3-django dvadmin3-celery
  （settings.py 的 INSTALLED_APPS 变了，不重启不生效；celery 同理）
  然后 makemigrations aiagent && migrate（「智能问答」引入了 3 张新表）
"""
import os
import sys

DRY_RUN = "--dry-run" in sys.argv
NO_REBIND = "--no-rebind" in sys.argv
WITH_CHAT = "--with-chat" in sys.argv
SKIP_PATCH = "--skip-patch" in sys.argv

# ============================================================
# 常量：菜单与按钮定义
# ============================================================
PARENT_MENU = {
    "name": "AI 运维助手",
    "web_path": "/ai",
    "icon": "ele-MagicStick",
    "sort": 6,          # 现有：监控告警 4 / 发布管理 5
    "is_catalog": True,
}

CHILD_MENUS = [
    {
        "name": "模型配置",
        "web_path": "/ai-model",
        "component": "ai/model/index",
        "component_name": "aiModel",
        "icon": "ele-Setting",
        "sort": 2,
        "is_catalog": False,
    },
]
if WITH_CHAT:
    CHILD_MENUS.insert(0, {
        "name": "智能问答",
        "web_path": "/ai-chat",
        "component": "ai/chat/index",
        "component_name": "aiChat",
        "icon": "ele-ChatDotRound",
        "sort": 1,
        "is_catalog": False,
    })

# HTTP method 常量（与 CustomPermission 的 methodList 索引一致）
GET, POST, PUT, DELETE = 0, 1, 2, 3

# 授权对象
ALL_ROLES = "all"       # 所有角色
ADMIN_ONLY = "admin"    # 仅管理员角色

# 按钮定义：(所属菜单, 按钮名, 权限码, API 路径, method, 授权对象)
BUTTONS = [
    # —— 个人模型配置：每个用户都要能配自己的 Key（BYOK），所以放开给所有角色 ——
    ("模型配置", "查询", "ai_provider:Search", "/api/aiagent/provider/", GET, ALL_ROLES),
    ("模型配置", "新增", "ai_provider:Create", "/api/aiagent/provider/", POST, ALL_ROLES),
    ("模型配置", "编辑", "ai_provider:Update", "/api/aiagent/provider/{id}/", PUT, ALL_ROLES),
    ("模型配置", "删除", "ai_provider:Delete", "/api/aiagent/provider/{id}/", DELETE, ALL_ROLES),
    ("模型配置", "测试连接", "ai_provider:Test", "/api/aiagent/provider/{id}/test/", POST, ALL_ROLES),
    ("模型配置", "设为默认", "ai_provider:SetDefault", "/api/aiagent/provider/{id}/set_default/", POST, ALL_ROLES),
    # —— 安全护栏：全局生效、能改白名单 = 能决定 AI 跑什么命令，只给管理员 ——
    ("模型配置", "读取护栏", "ai_guard:Current", "/api/aiagent/guard/current/", GET, ADMIN_ONLY),
    ("模型配置", "保存护栏", "ai_guard:Update", "/api/aiagent/guard/update_current/", PUT, ADMIN_ONLY),
    ("模型配置", "命令试跑", "ai_guard:Check", "/api/aiagent/guard/check_command/", POST, ADMIN_ONLY),
]

# 「智能问答」的接口权限。★ 都会逐个登记：
#   `CustomPermission` 是按 (api模板, method索引) 逐条匹配 RoleMenuButtonPermission 的，
#   漏登记任何一条 → 那条接口对非超管恒返回业务码 4000。
#   `{id}` 会被替换成 `([a-zA-Z0-9-]+)`，与框架行为一致（照抄上游的写法即可）。
CHAT_BUTTONS = [
    ("智能问答", "会话列表", "ai_chat:Search", "/api/aiagent/chat/", GET, ALL_ROLES),
    ("智能问答", "下拉选项", "ai_chat:Options", "/api/aiagent/chat/options/", GET, ALL_ROLES),
    ("智能问答", "提问", "ai_chat:Send", "/api/aiagent/chat/send/", POST, ALL_ROLES),
    ("智能问答", "会话详情", "ai_chat:Retrieve", "/api/aiagent/chat/{id}/", GET, ALL_ROLES),
    ("智能问答", "删除会话", "ai_chat:Delete", "/api/aiagent/chat/{id}/", DELETE, ALL_ROLES),
    ("智能问答", "会话台账", "ai_chat:ToolCalls", "/api/aiagent/chat/{id}/tool_calls/", GET, ALL_ROLES),
    # 全量台账（超管看全量、其余只看自己 —— 可见范围在 ViewSet 里按 is_superuser 分叉）
    ("智能问答", "全量台账", "ai_toolcall:Search", "/api/aiagent/toolcall/", GET, ALL_ROLES),
]

# 兼容旧调用：以前只有一个 BUTTONS 列表
ALL_BUTTONS = BUTTONS + (CHAT_BUTTONS if WITH_CHAT else [])

# 授权对象：菜单 + 按钮都给这些角色
ADMIN_ROLE_HINTS = ("超级管理员", "管理员")


# ============================================================
# 第 1 步：文件补丁（settings.py / urls.py）
# ============================================================
def find_backend_root():
    for p in (os.environ.get("XWOPS_BACKEND"), "/backend", "/opt/devops-platform/backend"):
        if p and os.path.isfile(os.path.join(p, "application", "settings.py")):
            return p
    return None


def patch_files(root):
    settings_path = os.path.join(root, "application", "settings.py")
    urls_path = os.path.join(root, "application", "urls.py")
    changed = []

    with open(settings_path, "r", encoding="utf-8") as f:
        content = f.read()
    if '"dvadmin.aiagent"' in content or "'dvadmin.aiagent'" in content:
        print("[skip] settings.py 已含 dvadmin.aiagent")
    else:
        anchor = '    "dvadmin.jenkins",\n'
        if anchor not in content:
            anchor = '    "dvadmin.alert",\n'
        if anchor not in content:
            raise SystemExit("[FAIL] settings.py 找不到 dvadmin.jenkins / dvadmin.alert 锚点，请手工确认")
        new = anchor + '    "dvadmin.aiagent",\n'
        if DRY_RUN:
            print("[dry-run] settings.py 将在 %s 后插入 dvadmin.aiagent" % anchor.strip())
        else:
            with open(settings_path, "w", encoding="utf-8") as f:
                f.write(content.replace(anchor, new, 1))
            changed.append("settings.py")
            print("[ok] settings.py 已注册 dvadmin.aiagent")

    with open(urls_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "dvadmin.aiagent.urls" in content:
        print("[skip] urls.py 已含 api/aiagent")
    else:
        anchor = '    path("api/jenkins/", include("dvadmin.jenkins.urls")),\n'
        if anchor not in content:
            anchor = '    path("api/alert/", include("dvadmin.alert.urls")),\n'
        if anchor not in content:
            raise SystemExit("[FAIL] urls.py 找不到 api/jenkins / api/alert 锚点，请手工确认")
        new = anchor + '    path("api/aiagent/", include("dvadmin.aiagent.urls")),\n'
        if DRY_RUN:
            print("[dry-run] urls.py 将插入 api/aiagent/ 路由")
        else:
            with open(urls_path, "w", encoding="utf-8") as f:
                f.write(content.replace(anchor, new, 1))
            changed.append("urls.py")
            print("[ok] urls.py 已挂载 api/aiagent/")

    return changed


# ============================================================
# 第 2~4 步：菜单 / 按钮 / 授权（需要 django 环境）
# ============================================================
def setup_django():
    root = find_backend_root()
    if root and root not in sys.path:
        sys.path.insert(0, root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")
    try:
        import django
        django.setup()
        return True
    except Exception as exc:                                   # noqa: BLE001
        print("[跳过菜单步骤] django 环境不可用：%s" % exc)
        print("            请在 django 容器内执行：docker exec dvadmin3-django python register_aiagent.py")
        return False


def run_menu_steps():
    from django.apps import apps

    Menu = apps.get_model("system", "Menu")
    MenuButton = apps.get_model("system", "MenuButton")
    Role = apps.get_model("system", "Role")
    RoleMenuPermission = apps.get_model("system", "RoleMenuPermission")
    RoleMenuButtonPermission = apps.get_model("system", "RoleMenuButtonPermission")
    Users = apps.get_model("system", "Users")

    # ---- 2.1 父菜单 ----
    defaults = {
        "web_path": PARENT_MENU["web_path"],
        "icon": PARENT_MENU["icon"],
        "sort": PARENT_MENU["sort"],
        "status": True,
        "cache": False,
        "visible": True,
        "is_catalog": True,
        "is_link": False,
        "is_iframe": False,
    }
    if DRY_RUN:
        parent = Menu.objects.filter(name=PARENT_MENU["name"]).first()
        print("[dry-run] 父菜单「%s」%s" % (PARENT_MENU["name"], "已存在" if parent else "待创建"))
    else:
        parent, created = Menu.objects.get_or_create(name=PARENT_MENU["name"], defaults=defaults)
        if not created:
            for k, v in defaults.items():
                setattr(parent, k, v)
            parent.save()
        print("[ok] 父菜单「%s」id=%s %s" % (parent.name, parent.id, "新建" if created else "已存在(已校正字段)"))

    if DRY_RUN:
        for cm in CHILD_MENUS:
            exists = Menu.objects.filter(name=cm["name"]).exists()
            print("[dry-run] 子菜单「%s」web_path=%s component=%s %s"
                  % (cm["name"], cm["web_path"], cm["component"], "已存在" if exists else "待创建"))
        menus = {name: Menu.objects.filter(name=name).first() for name in
                 [PARENT_MENU["name"]] + [c["name"] for c in CHILD_MENUS]}
    else:
        menus = {parent.name: parent}
        for cm in CHILD_MENUS:
            d = {k: v for k, v in cm.items() if k != "name"}
            d.update({"parent": parent, "status": True, "cache": False, "visible": True,
                      "is_link": False, "is_iframe": False})
            obj, created = Menu.objects.get_or_create(name=cm["name"], defaults=d)
            if not created:
                for k, v in d.items():
                    setattr(obj, k, v)
                obj.save()
            menus[cm["name"]] = obj
            print("[ok] 子菜单「%s」id=%s %s" % (obj.name, obj.id, "新建" if created else "已存在(已校正字段)"))

    # ---- 3. 按钮 ----
    # btn_objs 里带授权对象，第 4 步按 ALL_ROLES / ADMIN_ONLY 分开授
    btn_objs = []          # [(button_obj, 授权对象)]
    will_create = {PARENT_MENU["name"]} | {c["name"] for c in CHILD_MENUS}
    for menu_name, bname, value, api, method, grant in ALL_BUTTONS:
        menu = menus.get(menu_name)
        if menu is None:
            if DRY_RUN and menu_name in will_create:
                # dry-run 下菜单还没落库，这是正常的，别说成「漏了 --with-chat」
                print("[dry-run] 按钮 %s / %s / %s / method=%s / grant=%s（菜单「%s」本次会一并创建）"
                      % (menu_name, bname, value, method, grant, menu_name))
                continue
            print("[skip] 按钮 %s：菜单「%s」不存在（若期望它有，请带 --with-chat 重跑）" % (value, menu_name))
            continue
        if DRY_RUN:
            print("[dry-run] 按钮 %s / %s / %s / method=%s / grant=%s"
                  % (menu_name, bname, value, method, grant))
            continue
        obj, created = MenuButton.objects.update_or_create(
            menu=menu, value=value, defaults={"name": bname, "api": api, "method": method}
        )
        btn_objs.append((obj, grant))
        print("[ok] 按钮 %s（%s，授权=%s）" % (value, "新建" if created else "更新", grant))

    # ---- 4. 授权 ----
    if DRY_RUN:
        print("[dry-run] 授权步骤跳过（--dry-run 不写库）")
        return

    admin_roles = list(Role.objects.filter(admin=True)) if hasattr(Role, "admin") else []
    for r in Role.objects.all():
        if any(h in (r.name or "") for h in ADMIN_ROLE_HINTS) and r not in admin_roles:
            admin_roles.append(r)
    # 兜底：超管账号实际绑定的角色也纳入（不管叫什么名字）
    super_users = list(Users.objects.filter(is_superuser=True))
    for u in super_users:
        for r in u.role.all():
            if r not in admin_roles:
                admin_roles.append(r)
        if u.current_role and u.current_role not in admin_roles:
            admin_roles.append(u.current_role)

    all_roles = list(Role.objects.all())
    if not all_roles:
        print("[警告] 库里一个角色都没有，菜单/按钮未授权 → 需要到「角色管理」里手工勾")
        return

    # ★ 菜单：全部给所有角色。
    #   「模型配置」不再是超管专属（BYOK 要求每人能配自己的 Key），
    #   「安全护栏」页签由前端按 ai_guard:Update 权限码隐藏，不靠菜单控制。
    grant_menus = [m for m in menus.values() if m is not None]
    m_cnt = 0
    for r in all_roles:
        for m in grant_menus:
            _, c = RoleMenuPermission.objects.get_or_create(role=r, menu=m)
            m_cnt += 1 if c else 0

    all_cnt = admin_cnt = 0
    for r in all_roles:
        for b, grant in btn_objs:
            if grant != ALL_ROLES:
                continue
            _, c = RoleMenuButtonPermission.objects.update_or_create(
                role=r, menu_button=b, defaults={"data_range": 3}
            )
            all_cnt += 1 if c else 0
    for r in admin_roles:
        for b, grant in btn_objs:
            if grant != ADMIN_ONLY:
                continue
            _, c = RoleMenuButtonPermission.objects.update_or_create(
                role=r, menu_button=b, defaults={"data_range": 3}
            )
            admin_cnt += 1 if c else 0

    print("[ok] 菜单授权：%d 个角色 × %d 个菜单 → 新增 %d 条"
          % (len(all_roles), len(grant_menus), m_cnt))
    print("[ok] 按钮授权：所有角色(%s) → 新增 %d 条；管理员角色(%s) → 新增 %d 条"
          % (", ".join(r.name for r in all_roles), all_cnt,
             ", ".join(r.name for r in admin_roles) or "无", admin_cnt))
    if not admin_roles:
        print("[警告] 没识别到管理员角色 → ai_guard:*（护栏）没授出去，"
              "「安全护栏」页签会因缺 ai_guard:Update 而被前端隐藏")

    if NO_REBIND:
        print("[--no-rebind] 跳过 current_role 兜底绑定")
    else:
        for u in super_users:
            if not u.current_role_id and admin_roles:
                u.current_role = admin_roles[0]
                u.save(update_fields=["current_role"])
                print("[ok] 用户 %s 未设置当前角色，已绑定 %s" % (u.username, admin_roles[0].name))


# ============================================================
def main():
    print("=" * 62)
    print("AI 运维助手 落地脚本  %s" % ("[DRY-RUN 只预览]" if DRY_RUN else ""))
    if WITH_CHAT:
        print("★ 本次包含「智能问答」菜单 —— 请确认 ai/chat/index.vue 已构建进 web 镜像")
        print("  否则菜单点进去会因找不到组件而空白（后端接口没问题，只是页面不在）")
    print("=" * 62)

    print("\n--- 第 1 步：文件补丁 ---")
    root = find_backend_root()
    if SKIP_PATCH:
        print("[--skip-patch] 跳过")
    elif not root:
        print("[警告] 没找到 backend 根目录（/backend 或 /opt/devops-platform/backend），跳过文件补丁")
    else:
        print("backend 根目录 = %s" % root)
        patch_files(root)

    print("\n--- 第 2~4 步：菜单 / 按钮 / 授权 ---")
    if setup_django():
        run_menu_steps()

    print("\n" + "=" * 62)
    if DRY_RUN:
        print("dry-run 结束，没有写任何东西")
    else:
        print("完成。接下来必须做：")
        print("  1) docker exec dvadmin3-django python manage.py makemigrations aiagent")
        print("     （「智能问答」引入 ai_chat_session / ai_tool_call / ai_usage 三张新表）")
        print("  2) docker exec dvadmin3-django python manage.py migrate aiagent")
        print("  3) docker restart dvadmin3-django dvadmin3-celery")
        print("     （settings.py 变了不重启不生效）")
        print("  4) 重建 web 镜像（.vue 是编译进镜像的，改了页面必须重建）")
        print("  5) 重新登录（权限在重新登录后才生效）")
        print("  6) 验证：GET /api/aiagent/chat/options/ 应返回 credentials/providers/guard")
    print("=" * 62)


if __name__ == "__main__":
    main()
