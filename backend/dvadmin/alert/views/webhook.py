# -*- coding: utf-8 -*-
"""
Alertmanager webhook receiver（接收 Alertmanager 发送的告警，分发到所有启用渠道）
"""
import hashlib
import hmac
import json
import os
import time
from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny

from dvadmin.alert.tasks import process_webhook



@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def webhook_receiver(request):
    """Authenticate before parsing; bounded payloads are delivered through Celery."""
    secret = getattr(settings, 'ALERT_WEBHOOK_SECRET', '') or os.environ.get('ALERT_WEBHOOK_SECRET', '')
    if len(secret) < 32:
        return Response({'detail': '告警接收密钥未配置'}, status=503)
    supplied = request.headers.get('Authorization', '')
    if not hmac.compare_digest(supplied.encode(), ('Bearer ' + secret).encode()):
        return Response({'detail': '认证失败'}, status=401)
    if len(request.body) > 262144:
        return Response({'detail': '告警请求超过 256 KiB'}, status=413)
    payload = request.data
    if not isinstance(payload, dict) or not isinstance(payload.get('alerts'), list):
        return Response({'detail': '缺少 alerts 数组'}, status=400)
    alerts = payload['alerts']
    if not 1 <= len(alerts) <= 100:
        return Response({'detail': '单批仅支持 1 到 100 条告警'}, status=400)
    for alert in alerts:
        if (not isinstance(alert, dict) or alert.get('status') not in ('firing', 'resolved')
                or not isinstance(alert.get('labels'), dict)
                or not isinstance(alert.get('annotations', {}), dict)):
            return Response({'detail': '告警结构不合法'}, status=400)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    key = 'xwops:webhook:' + digest
    try:
        if cache.get(key):
            return Response({'detail': '重复请求已接收'}, status=202)
        bucket = 'xwops:webhook-rate:' + str(int(time.time()) // 60)
        cache.add(bucket, 0, 90)
        if cache.incr(bucket) > 60:
            return Response({'detail': '请求过于频繁'}, status=429)
        if not cache.add(key, 'queued', 60):
            return Response({'detail': '重复请求已接收'}, status=202)
        try:
            process_webhook.delay(payload)
        except Exception:
            cache.delete(key)
            raise
    except Exception:
        return Response({'detail': '告警队列暂不可用，请重试'}, status=503)
    return Response({'detail': '已进入告警队列'}, status=202)
