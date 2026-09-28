# views.py
import asyncio
import time

import jwt
from django.http import StreamingHttpResponse

from application import settings
from dvadmin.system.models import MessageCenterTargetUser
from django.core.cache import cache


async def event_stream(user_id):
    """
    异步 SSE 事件流生成器
    使用 async/await 避免阻塞事件循环
    """
    last_sent_time = 0

    while True:
        # 从缓存中获取最后数据库变更时间（使用 sync_to_async 包装）
        from asgiref.sync import sync_to_async
        
        # 获取缓存值
        last_db_change_time = await sync_to_async(cache.get)('last_db_change_time', 0)
        
        # 只有当数据库发生变化时才检查总数
        if last_db_change_time and last_db_change_time > last_sent_time:
            count = await sync_to_async(
                lambda: MessageCenterTargetUser.objects.filter(users=user_id, is_read=False).count()
            )()
            yield f"data: {count}\n\n"
            last_sent_time = time.time()

        # 使用 asyncio.sleep 而不是 time.sleep，避免阻塞事件循环
        await asyncio.sleep(1)


async def sse_view(request):
    """
    异步 SSE 视图
    """
    token = request.GET.get('token')
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    user_id = decoded.get('user_id')
    
    response = StreamingHttpResponse(event_stream(user_id), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response
