# -*- coding: utf-8 -*-
"""
Alertmanager webhook receiver（接收 Alertmanager 发送的告警，分发到所有启用渠道）
"""
import logging

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny

from dvadmin.alert.services import dispatch_alerts, persist_alerts
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

logger = logging.getLogger(__name__)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def webhook_receiver(request):
    """Alertmanager webhook receiver：接收告警 → 持久化 + 按群组路由分发到通知渠道"""
    try:
        payload = request.data
        if not isinstance(payload, dict):
            return ErrorResponse(msg="payload 必须是 dict")
        # 1. 持久化告警事件（历史告警查询用）
        try:
            created, updated = persist_alerts(payload)
        except Exception as e:
            logger.exception("告警持久化失败")
            created, updated = 0, 0
        # 2. 分发通知
        route_note, results = dispatch_alerts(payload)
        ok_count = sum(1 for r in results if r.get("ok"))
        logger.info("告警分发 [%s] %d/%d 成功，持久化 新增%d 更新%d", route_note, ok_count, len(results), created, updated)
        return DetailResponse(
            data={"route": route_note, "results": results, "persisted": {"created": created, "updated": updated}},
            msg=f"{route_note}，成功 {ok_count}/{len(results)}，入库 新增{created} 更新{updated}",
        )
    except Exception as e:
        logger.exception("webhook 处理异常")
        return ErrorResponse(msg=f"webhook 处理异常：{e}")