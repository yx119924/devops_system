# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _

"""
@author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/1 001 22:38
@Remark: 菜单模块
"""
from rest_framework import serializers
from rest_framework.decorators import action

from dvadmin.system.models import Menu, RoleMenuPermission
from dvadmin.system.views.menu_button import MenuButtonSerializer
from dvadmin.utils.json_response import SuccessResponse, ErrorResponse
from dvadmin.utils.menu_sort import reorder_siblings
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class MenuSerializer(CustomModelSerializer):
    """
    菜单表的简单序列化器
    """
    menuPermission = serializers.SerializerMethodField(read_only=True)
    hasChild = serializers.SerializerMethodField()

    def get_menuPermission(self, instance):
        queryset = instance.menuPermission.order_by('-name').values('id', 'name', 'name_en', 'name_zh_tw', 'value')
        # MenuButtonSerializer(instance.menuPermission.all(), many=True)
        if queryset:
            return queryset
        else:
            return None

    def get_hasChild(self, instance):
        hasChild = Menu.objects.filter(parent=instance.id)
        if hasChild:
            return True
        return False

    class Meta:
        model = Menu
        fields = "__all__"
        read_only_fields = ["id"]


class MenuCreateSerializer(CustomModelSerializer):
    """
    菜单表的创建序列化器
    """
    name = serializers.CharField(required=False)

    def create(self, validated_data):
        menu_obj = Menu.objects.filter(parent_id=validated_data.get('parent', None)).order_by('-sort').first()
        last_sort = menu_obj.sort if menu_obj else 0
        validated_data['sort'] = last_sort + 1
        return super().create(validated_data)

    class Meta:
        model = Menu
        fields = "__all__"
        read_only_fields = ["id"]


class WebRouterSerializer(CustomModelSerializer):
    """
    前端菜单路由的简单序列化器
    """
    path = serializers.CharField(source="web_path")
    title = serializers.SerializerMethodField()

    def get_title(self, obj):
        lang = None
        req = getattr(self, 'request', None)
        if req:
            user = getattr(req, 'user', None)
            if user and getattr(user, 'is_authenticated', False):
                lang = getattr(user, 'language', None)
            # query_params.get() 返回列表（DRF），取第一个元素
            _qp_lang = req.query_params.get('language', None)
            if _qp_lang:
                lang = _qp_lang[0] if isinstance(_qp_lang, list) else _qp_lang
            if not lang:
                meta_lang = req.META.get('HTTP_ACCEPT_LANGUAGE', '')
                if meta_lang.startswith('en'):
                    lang = 'en'
                elif 'zh-tw' in meta_lang or 'zh-hant' in meta_lang:
                    lang = 'zh-tw'
        if lang == 'en':
            return obj.name_en or obj.name
        elif lang == 'zh-tw':
            return obj.name_zh_tw or obj.name
        return obj.name

    class Meta:
        model = Menu
        fields = (
            'id', 'parent', 'icon', 'sort', 'path', 'name', 'title', 'is_link','link_url', 'is_catalog', 'web_path', 'component',
            'component_name', 'cache', 'visible','is_iframe','is_affix', 'status', 'name_en', 'name_zh_tw')
        read_only_fields = ["id"]


class MenuViewSet(CustomModelViewSet):
    """
    菜单管理接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    create_serializer_class = MenuCreateSerializer
    update_serializer_class = MenuCreateSerializer
    search_fields = ['name', 'status']
    filter_fields = ['parent', 'name', 'status', 'is_link', 'visible', 'cache', 'is_catalog']

    def list(self, request):
        """懒加载"""
        request.query_params._mutable = True
        params = request.query_params
        parent = params.get('parent', None)
        page = params.get('page', None)
        limit = params.get('limit', None)
        if page:
            del params['page']
        if limit:
            del params['limit']
        if params:
            if parent:
                queryset = self.queryset.filter(parent=parent)
            else:
                queryset = self.queryset.filter()
        else:
            queryset = self.queryset.filter(parent__isnull=True)
        # ★ 必须带 id 做 tie-break：同父同 sort 的行（线上顶级曾有 3 个 sort=3）
        #   若无 id 次序，MySQL 对不同查询计划可能给出不同顺序 ⇒ 菜单管理树与
        #   侧边栏两个视图对不上。详见 dvadmin/utils/menu_sort.py 模块注释。
        queryset = self.filter_queryset(queryset).order_by('sort', 'id')
        serializer = MenuSerializer(queryset, many=True, request=request)
        data = serializer.data
        return SuccessResponse(data=data)

    @action(methods=['GET'], detail=False, permission_classes=[])
    def web_router(self, request):
        """用于前端获取当前角色的路由"""
        user = request.user
        if user.is_superuser:
            queryset = self.queryset.filter(status=1).order_by("sort", "id")
        elif user.is_authenticated:
            role_list = user.role.values_list('id', flat=True)
            menu_list = RoleMenuPermission.objects.filter(role__in=role_list).values_list('menu_id', flat=True)
            queryset = Menu.objects.filter(id__in=menu_list).order_by("sort", "id")
        else:
            queryset = self.queryset.none()
        serializer = WebRouterSerializer(queryset, many=True, request=request)
        data = serializer.data
        return SuccessResponse(data=data, total=len(data), msg=_("Query successful"))

    @action(methods=['GET'], detail=False, permission_classes=[])
    def get_all_menu(self, request):
        """用于菜单管理获取所有的菜单"""
        user = request.user
        queryset = self.queryset.all()
        if not user.is_authenticated:
            queryset = self.queryset.none()
        elif not user.is_superuser:
            role_list = user.role.values_list('id', flat=True)
            menu_list = RoleMenuPermission.objects.filter(role__in=role_list).values_list('menu_id')
            queryset = Menu.objects.filter(id__in=menu_list)
        queryset = queryset.order_by("sort", "id")
        serializer = WebRouterSerializer(queryset, many=True, request=request)
        data = serializer.data
        return SuccessResponse(data=data, total=len(data), msg=_("Query successful"))

    @action(methods=['POST'], detail=False, permission_classes=[])
    def move_up(self, request):
        """菜单上移"""
        return self._move_menu(request, 'up')

    @action(methods=['POST'], detail=False, permission_classes=[])
    def move_down(self, request):
        """菜单下移"""
        return self._move_menu(request, 'down')

    def _move_menu(self, request, direction):
        """同级内上移/下移一位。

        ★ 不再用 sort__lt / sort__gt 找"相邻"（2026-11-06 修复）：
          同父同 sort 时，前者会静默不生效（却回成功），后者会跨位跳转。
          正解见 dvadmin/utils/menu_sort.py：按 (sort, id) 排稳 → 相邻交换
          → 整组重编 1..N，顺带把该组的重复 sort 规范掉。
        """
        menu_id = request.data.get('menu_id')
        if not menu_id:
            return ErrorResponse(msg=str(_("请先选择要移动的菜单")))
        try:
            menu = Menu.objects.get(id=menu_id)
        except Menu.DoesNotExist:
            return ErrorResponse(msg=_("Menu does not exist"))

        siblings = list(Menu.objects.filter(parent=menu.parent))
        plan, moved = reorder_siblings(
            [{'id': item.id, 'sort': item.sort} for item in siblings],
            menu.id,
            direction,
        )
        if not moved:
            msg = "已经是第一个菜单，无法上移" if direction == 'up' else "已经是最后一个菜单，无法下移"
            return ErrorResponse(msg=str(_(msg)))

        by_id = {item.id: item for item in siblings}
        changed = []
        for mid, new_sort in plan:
            obj = by_id[mid]
            if obj.sort != new_sort:
                obj.sort = new_sort
                changed.append(obj)
        if changed:
            Menu.objects.bulk_update(changed, ['sort'])

        return SuccessResponse(
            data=[{'id': mid, 'sort': new_sort} for mid, new_sort in plan],
            msg=_("Move successful"),
        )
