# -*- coding: utf-8 -*-

"""
@author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/3 003 0:30
@Remark: 按钮权限管理
"""
from dvadmin.system.models import LoginLog
from dvadmin.utils.field_permission import FieldPermissionMixin
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class LoginLogSerializer(CustomModelSerializer):
    """
    登录日志权限-序列化器
    """

    class Meta:
        model = LoginLog
        fields = "__all__"
        read_only_fields = ["id"]


class LoginLogViewSet(CustomModelViewSet, FieldPermissionMixin):
    """
    登录日志接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = LoginLog.objects.all()
    serializer_class = LoginLogSerializer
    # ★ 2026-11-09 补：本页搜索框的列 key 就叫 `search`（前端 crud.tsx:66），
    #   前端发的是 `?search=关键字`，由 DRF 的 `SearchFilter` 处理。
    #   而 `SearchFilter` **必须有 `search_fields` 才动** —— 没有就原样返回全量，
    #   表现是「输入关键字点查询没反应」。这与采集配置页不是同一条路径
    #   （那个发 `?name=`，走 `SearchLikeBackend`）。
    #   ★ 只放字符字段：布尔 / 整型放进 icontains 不报错但语义是错的
    #     （见 `dvadmin/utils/search_filter.py` 顶部的实测记录）。
    search_fields = ['username', 'ip', 'browser', 'os', 'province', 'city']
    # ⚠️ 不要取消下面这行的注释：`extra_filter_class = []` 会连文本搜索一起关掉。
    #    确实需要关「部门数据权限」时，写 `disable_dept_scope = True`（2026-11-09）。
    # extra_filter_class = []
