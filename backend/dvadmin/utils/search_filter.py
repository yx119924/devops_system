# -*- coding: utf-8 -*-
"""文本模糊搜索（`icontains`）的通用后端 —— 把「前端搜索框」与「精确过滤」解耦。

背景（2026-10-14 定因，完整报告见 `deploy/全站搜索失效-排查报告_20261014.md`）
------------------------------------------------------------------
fast-crud 的搜索框值**以「列 key 为参数名」**平铺进 query
（`web/src/settings.ts` 的 `transformQuery` 里 `...form`），例如：

    GET /api/cmdb/server/?page=1&limit=20&hostname=192.168.0.164

但后端原有两条通路都接不住这个参数名：

* ``CustomDjangoFilterBackend`` 只认 ``filter_fields`` 里列出的字段名，
  其余参数在 ``filters.py::find_filter_lookups`` 匹配不到后被**静默丢弃**；
* DRF ``SearchFilter`` 只认 ``?search=``，而前端从不发这个参数
  ⇒ 各 viewset 写的 ``search_fields`` **从来没有生效过**。

⇒ 结果：20 个页面的文本搜索框「点了查询没反应 / 返回全量」。
更隐蔽的是，``icontains`` 的自动升级只在 ``filter_fields == "__all__"`` 时发生
（见 ``filters.py`` 里 ``filterset_fields == "__all__"`` 那个分支）—— 凡是写了窄
清单的 viewset，其文本字段**只能精确匹配**（搜「目标网关」查不到「目标网关不可达」）。

本模块的定位
------------
把各 viewset **早已声明**的 ``search_fields`` 当作「可模糊搜索字段」的唯一清单：
query 里出现同名的裸字段参数 ⇒ 按 ``icontains`` 过滤。
以后新建页面只要写 ``search_fields``，模糊搜索自动生效，不必再手写
``filter_queryset`` 补丁（历史上全仓只有 3 处打了这种补丁 —— 正是本次事故的形态：
同一件事散落多处，必然有漏）。

★ 字段类型白名单：**必须**，但不是为了「防 500」
------------------------------------------------
只有字符型字段能做 ``icontains``。实测（Django 4.2.14 + sqlite）：

    BooleanField__icontains='true'  ->  不报错，返回**空集**
    IntegerField__icontains='1'     ->  不报错，返回**全部**

也就是说，不加白名单的后果**不是报错，而是静默给出错误结果**：
``system/views/menu.py`` 的 ``search_fields`` 里带着 ``Menu.status``（布尔字段），
用户按状态一筛，会**一条都搜不出来**，而页面上没有任何提示。
这比 500 更难发现，所以这里用 ``isinstance((CharField, TextField))`` 严格放行：
子类（``URLField`` / ``EmailField`` / ``SlugField``）自动覆盖，
非字符字段一律跳过（它们继续由 ``filter_fields`` 做精确过滤）。
"""
from django.db import models as dj_models
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

#: 允许 `icontains` 的字段类型。用**类对象**而非类名判断：
#: `URLField` / `EmailField` / `SlugField` 都是 `CharField` 的子类，
#: 若按 `type(field).__name__ == 'CharField'` 比较，会把它们**静默漏掉**。
TEXT_FIELD_CLASSES = (dj_models.CharField, dj_models.TextField)

#: django-filter 的查找前缀（与 `filters.py::CustomDjangoFilterBackend.lookup_prefixes` 一致）
LOOKUP_PREFIXES = '^=@$~'


def _strip_prefix(field):
    """去掉 django-filter 的查找前缀（`^=@$~`），用于与 `search_fields` 名字对齐。"""
    if isinstance(field, str) and field and field[0] in LOOKUP_PREFIXES:
        return field[1:]
    return field


def like_fields(view, model):
    """挑出 ``view.search_fields`` 里**真的能做 icontains** 的裸字段名。

    跳过三类：

    * 含 ``__`` 的关联路径（``dept__name`` / ``creator__name`` / ``server__hostname``）
      —— 前端不会以这些名字发参，放进来只是白跑一次 ``query_params.get``；
    * 模型里不存在的名字（防御字段名漂移）；
    * 非字符型字段（布尔 / 整型 / 日期 / 外键 …）—— 理由见模块 docstring 的实测记录。
    """
    if model is None:
        return []
    picked = []
    for field in getattr(view, 'search_fields', None) or ():
        if not isinstance(field, str) or '__' in field:
            continue
        try:
            obj = model._meta.get_field(field)
        except Exception:
            continue
        if isinstance(obj, TEXT_FIELD_CLASSES):
            picked.append(field)
    return picked


def pick_filter_fields(view, model):
    """给 ``CustomDjangoFilterBackend`` 用的 ``filter_fields``：剔除**已交给模糊搜索**的字段。

    为什么必须剔（而不是两边都留）：同一字段若被 django-filter 做 ``exact``、
    又被他处做 ``icontains``，两个条件是 **AND** ⇒ 等价于 ``exact`` ⇒ 模糊依然无效。
    「历史告警」页搜「目标网关」查不到「目标网关不可达」就是这个原因
    （``alertname`` 同时躺在 ``filter_fields`` 与 ``search_fields`` 里）。

    ``"__all__"`` 或非 list/tuple **原样返回**：``__all__`` 下 django-filter 自己就把
    字符字段升成 ``icontains`` 了，不需要也不应该动它（``role`` / ``dictionary`` 等
    走默认的页面因此完全不受影响）。
    """
    raw = getattr(view, 'filter_fields', None)
    if not isinstance(raw, (list, tuple)):
        return raw
    dropped = set(like_fields(view, model))
    if not dropped:
        return raw
    return [f for f in raw if _strip_prefix(f) not in dropped]


class SearchLikeBackend(BaseFilterBackend):
    """把「以 ``search_fields`` 裸字段名命名的 query 参数」按 ``icontains`` 过滤。

    * 只做 AND 累积；空值 / 无参数时**原样返回** queryset，不改变既有行为；
    * 与 ``CustomDjangoFilterBackend`` 处理的参数集**不相交**（见 ``pick_filter_fields``），
      因此即使 ``CustomModelViewSet.filter_queryset`` 用 ``set()`` 求并集、
      backend 执行顺序不确定，本后端的结果也不受影响。
    """

    def filter_queryset(self, request, queryset, view):
        fields = like_fields(view, getattr(queryset, 'model', None))
        if not fields:
            return queryset
        cond = None
        for name in fields:
            value = request.query_params.get(name)
            if value in (None, ''):
                continue
            one = Q(**{name + '__icontains': value})
            cond = one if cond is None else (cond & one)
        return queryset.filter(cond) if cond is not None else queryset
