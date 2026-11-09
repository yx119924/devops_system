# -*- coding: utf-8 -*-

"""
@author: 李强
@contact: QQ:1206709430
@Created on: 2021/6/8 003 0:30
@Remark: 操作日志管理
"""

from dvadmin.system.models import OperationLog
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class OperationLogSerializer(CustomModelSerializer):
    """
    日志-序列化器
    """

    class Meta:
        model = OperationLog
        fields = "__all__"
        read_only_fields = ["id"]


class OperationLogCreateUpdateSerializer(CustomModelSerializer):
    """
    操作日志  创建/更新时的列化器
    """

    class Meta:
        model = OperationLog
        fields = '__all__'


class OperationLogViewSet(CustomModelViewSet):
    """
    操作日志接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = OperationLog.objects.order_by('-create_datetime')
    serializer_class = OperationLogSerializer
    # ★ 2026-11-09 补：前端搜索框的列 key 是 `search`，发的是 `?search=关键字`，
    #   由 DRF 的 `SearchFilter` 处理 —— 它**必须有 `search_fields` 才动**，
    #   否则原样返回全量（「点查询没反应」的真正原因）。
    #   ★ 不收录 `request_body` / `json_result`：都是 TextField，内容可能很大，
    #     拼进 OR 查询会明显拖慢列表；也不收录 `status`（布尔，icontains 语义错误）。
    search_fields = ['request_modular', 'request_path', 'request_method',
                     'request_msg', 'request_ip', 'request_browser', 'response_code']
    # permission_classes = []
