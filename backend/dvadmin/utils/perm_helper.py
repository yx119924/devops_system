# -*- coding: utf-8 -*-
"""
统一权限助手 —— 把 DVAdmin 三层权限（菜单/接口/数据）的判定逻辑收敛到一处。

为什么需要它
------------
框架里这套判定散在三处、口径还不完全一致：

============================  ==========================================================
``system/views/menu.py``      ``web_router``：``RoleMenuPermission`` → 前端路由（菜单层）
``utils/permission.py``       ``CustomPermission``：URL+method 匹配按钮（接口层）
``system/views/menu_button.py``  ``menu_button_all_permission``：前端 ``hasAuth(code)`` 数据源
============================  ==========================================================

业务代码（首页统计、资产过滤、Jenkins Job 过滤）要复用同一套口径时，只能自己重写一遍，
很容易和框架跑偏。本模块就是那个「一处」。

口径对齐
--------
- ``user_menu_paths`` 与 ``web_router`` 保持一致：超管拿全量（``status=1``），
  普通用户按 ``RoleMenuPermission`` 取菜单，这样"首页能看到的入口" = "真的点得进去"。
- ``user_button_codes`` 与 ``menu_button_all_permission`` 保持一致：
  超管拿全部 ``MenuButton.value``，普通用户拿本角色已勾选的码，
  这样"首页隐藏的卡片" = "``hasAuth`` 隐藏的按钮"。
"""

from __future__ import print_function

__all__ = [
    "user_menu_paths",
    "has_any_path",
    "user_button_codes",
    "has_button",
    "user_role_ids",
]


def user_role_ids(user):
    """当前用户的全部角色 id 列表。无角色 / 未登录 → 空列表。

    注意：**不要用 ``user.current_role``**。它是登录时写入的 FK，历史用户可能为 NULL
    （本项目线上 ``ops1`` / ``dev1`` 的 ``current_role_id`` 都是 NULL），
    一旦依赖它就会出现"莫名其妙全被拒绝"。框架的 ``CustomPermission`` 用的是
    ``user.role`` 多对多，这里与之对齐。
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    if not hasattr(user, "role"):
        return []
    return list(user.role.values_list("id", flat=True))


def user_menu_paths(user):
    """当前用户可见的菜单 ``web_path`` 集合。

    :returns: ``set`` 表示该用户可见的路径集合；``None`` 表示"不受限"（超级管理员）。
    """
    from dvadmin.system.models import Menu

    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        return None

    role_ids = user_role_ids(user)
    if not role_ids:
        return set()

    from dvadmin.system.models import RoleMenuPermission

    menu_ids = RoleMenuPermission.objects.filter(
        role__in=role_ids
    ).values_list("menu_id", flat=True)

    return set(
        Menu.objects.filter(id__in=menu_ids, status=1)
        .values_list("web_path", flat=True)
    ) - {None, ""}


def has_any_path(paths, *candidates):
    """``paths`` 为 ``None``（不受限）时恒为 True；否则命中任一候选即 True。"""
    if paths is None:
        return True
    if not paths or not candidates:
        return False
    return any(c in paths for c in candidates)


def user_button_codes(user):
    """当前用户拥有的按钮权限码集合（与前端 ``BtnPermissionStore.data`` 同源）。"""
    from dvadmin.system.models import MenuButton

    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        return set(MenuButton.objects.values_list("value", flat=True))

    role_ids = user_role_ids(user)
    if not role_ids:
        return set()

    from dvadmin.system.models import RoleMenuButtonPermission

    return set(
        RoleMenuButtonPermission.objects.filter(role__in=role_ids)
        .values_list("menu_button__value", flat=True)
    ) - {None, ""}


def has_button(user, *codes):
    """当前用户是否拥有其中任一按钮权限码。"""
    if not codes:
        return False
    owned = user_button_codes(user)
    return any(c in owned for c in codes)
