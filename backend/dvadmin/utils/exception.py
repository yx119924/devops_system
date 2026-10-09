# -*- coding: utf-8 -*-

"""
@author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/2 002 16:06
@Remark: 自定义异常处理
"""
import logging
import traceback

from django.db.models import ProtectedError
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException as DRFAPIException, AuthenticationFailed, NotAuthenticated
from rest_framework.status import HTTP_401_UNAUTHORIZED
from rest_framework.views import set_rollback, exception_handler

from dvadmin.utils.json_response import ErrorResponse

logger = logging.getLogger(__name__)


class CustomAuthenticationFailed(NotAuthenticated):
    # 设置 status_code 属性为 400
    status_code = 400

def CustomExceptionHandler(ex, context):
    """
    统一异常拦截处理
    目的:(1)取消所有的500异常响应,统一响应为标准错误返回
        (2)准确显示错误信息
    :param ex:
    :param context:
    :return:
    """
    msg = ''
    code = 4000
    # 调用默认的异常处理函数
    response = exception_handler(ex, context)
    if isinstance(ex, AuthenticationFailed):
        # 如果是身份验证错误
        if response and response.data.get('detail') == "Given token not valid for any token type":
            code = 401
            msg = ex.detail
        elif response and response.data.get('detail') == "Token is blacklisted":
            # token在黑名单
            return ErrorResponse(status=HTTP_401_UNAUTHORIZED)
        else:
            code = 401
            msg = ex.detail
    elif isinstance(ex,Http404):
        code = 400
        msg = _("Endpoint address is incorrect")
    elif isinstance(ex, DRFAPIException):
        set_rollback()
        # ★★ 2026-10-01 修：原实现假设「每个字段的错误值都是列表」——
        #
        #       for k, v in msg.items():
        #           for i in v:
        #               msg = "%s:%s" % (k, i)
        #
        #   但 DRF 的 `_get_error_details()` 对**字符串值**返回的是**单个 ErrorDetail**，
        #   不是列表（只有 `{'f': ['a','b']}` 这种才是列表）。于是 `for i in v`
        #   变成**逐字符遍历**，循环结束时 `i` 是消息的**最后一个字符**：
        #
        #       实际报错：「节点「③ 上传制品」 的目标机路径必须是绝对路径（如 /opt/app/app.jar）」
        #       页面上显示：config:）
        #
        #   —— 中文报错被吃成乱码，排查时完全看不出原因（本项目所有
        #   `ValidationError({'字段': '中文说明'})` 的写法都会中招）。
        #
        #   修法：列表用「；」连接（比原来的"取最后一个"更完整），
        #   标量按原样拼；多个字段也一起拼上。
        detail = ex.detail
        if isinstance(detail, dict):
            parts = []
            for k, v in detail.items():
                if isinstance(v, (list, tuple)):
                    parts.append('%s:%s' % (k, '；'.join(str(x) for x in v)))
                else:
                    parts.append('%s:%s' % (k, v))
            msg = '；'.join(parts) if parts else str(detail)
        else:
            msg = detail
    elif isinstance(ex, ProtectedError):
        set_rollback()
        msg = _("Delete failed: this record has related data bindings")
    # elif isinstance(ex, DatabaseError):
    #     set_rollback()
    #     msg = "接口服务器异常,请联系管理员"
    elif isinstance(ex, Exception):
        logger.exception(traceback.format_exc())
        msg = str(ex)
    return ErrorResponse(msg=msg, code=code)
