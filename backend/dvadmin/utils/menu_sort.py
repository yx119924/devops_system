# -*- coding: utf-8 -*-
"""
菜单同级排序 —— 纯逻辑，不依赖 Django / ORM，便于离线验证与复用。

背景（2026-11-06 修复）：
    原 move_up / move_down 用 `sort__lt` / `sort__gt` 去找"相邻"兄弟，
    这要求同一父节点下 sort 严格唯一。而线上实际存在大量同值：

        parent_id = NULL : 监控告警(3) / 日志管理(3) / 发布管理(3)
        parent_id = 31   : 告警管理(3) / 监控大屏(3)

    后果有两类：
        ① 找不到邻居 —— 例如对"告警管理"下移，没有 sort>3 的兄弟，
           什么都不做，却仍返回 "Move down successful"（静默失败）；
        ② 找到的不是紧邻 —— 例如对"监控大屏"上移，命中的是 sort=2 的
           "指标查询"，于是跨过"告警管理"跳位交换。

    且 Menu.Meta.ordering 只有 ("sort",)，同值行的先后由数据库决定，
    导致「菜单管理树」与「侧边栏」两个视图顺序可以不一致。

本模块的做法：
    按 (sort, id) 排出稳定顺序 → 在内存里与紧邻项交换 → 整组重编为 1..N。
    这样一次点击既完成移动，又顺手把该组的重复 sort 规范掉，且天然幂等。
"""


def _sort_key(item):
    """sort 为 None 时视为最小（与 MySQL ORDER BY sort 的 NULL 排最前一致）。"""
    sort = item.get('sort')
    if sort is None:
        return (0, 0, item['id'])
    return (1, sort, item['id'])


def reorder_siblings(items, current_id, direction):
    """把 current_id 在同级中上移/下移一位，并把整组重编为 1..N。

    :param items: 可迭代对象，元素为含 'id' 与 'sort' 的 dict
    :param current_id: 要移动的菜单 id
    :param direction: 'up' | 'down'
    :return: (plan, moved)
        plan  —— [(id, new_sort), ...]，按新顺序排列（含全部兄弟）
        moved —— False 表示已到边界或 id 不在同级中，调用方**不应**报告成功

    幂等性：同一组连续 up 再 down 会回到原顺序。
    """
    if direction not in ('up', 'down'):
        raise ValueError(f"direction must be 'up' or 'down', got {direction!r}")

    ordered = sorted(items, key=_sort_key)
    ids = [item['id'] for item in ordered]

    if current_id not in ids:
        return [(item['id'], idx) for idx, item in enumerate(ordered, start=1)], False

    idx = ids.index(current_id)
    target = idx - 1 if direction == 'up' else idx + 1
    if target < 0 or target >= len(ordered):
        return [(item['id'], idx) for idx, item in enumerate(ordered, start=1)], False

    ordered[idx], ordered[target] = ordered[target], ordered[idx]
    return [(item['id'], idx) for idx, item in enumerate(ordered, start=1)], True
