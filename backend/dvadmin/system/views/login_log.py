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
    # ⚠️ 不要取消下面这行的注释：`extra_filter_class = []` 会连文本搜索一起关掉。
    #    确实需要关「部门数据权限」时，写 `disable_dept_scope = True`（2026-11-09）。
    # extra_filter_class = []
