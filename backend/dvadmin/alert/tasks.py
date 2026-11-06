import logging

from celery import shared_task
from dvadmin.alert.services import persist_alerts, dispatch_alerts

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, soft_time_limit=240, time_limit=270)
def process_webhook(self, payload):
    """落库与通知分两步，各自兜底 —— 一步失败不掩盖另一步的结果。

    ★ 2026-11-06 改造原因：
      原实现把 persist 和 dispatch 套在同一个 try 里，通知渠道抖一下整个任务就重试，
      日志里只有一句「告警任务失败」，**看不出是「没落库」还是「落库了但没发出去」**。
      两者失败的处置完全不同：
        · 落库失败 ⇒ 必须重试，否则这条告警永久丢失（AM 的 webhook 不重试）；
        · 通知失败 ⇒ 重试只会重复投递，渠道本身挂了重试也救不回来，记日志更重要。
    """
    total = len(payload.get('alerts') or [])
    persist_failed = False

    try:
        created, updated, failed = persist_alerts(payload)
        if created or updated:
            logger.info('告警落库完成：新增 %d、更新 %d；task_id=%s',
                        created, updated, self.request.id)
        if failed:
            logger.error('告警落库失败 %d 条，已跳过；task_id=%s detail=%s',
                         len(failed), self.request.id, failed)
            # 整批全失败 ⇒ 大概率是数据库/连接类系统故障，值得重试；
            # 只有个别条失败 ⇒ 数据本身的问题，重试仍会失败，不重试。
            if total and len(failed) >= total:
                persist_failed = True
    except Exception:
        persist_failed = True
        logger.exception('告警落库整体失败；task_id=%s', self.request.id)

    notify_failed = []
    try:
        _, results = dispatch_alerts(payload)
        notify_failed = [r for r in results if not r.get('ok')]
    except Exception:
        logger.exception('告警通知过程异常；task_id=%s', self.request.id)

    if notify_failed:
        logger.error('告警已落库，但 %d 个通知渠道未送达；task_id=%s detail=%s',
                     len(notify_failed), self.request.id, notify_failed)

    # 只有落库失败才重试：通知失败重试救不回来，只会重复投递。
    if persist_failed:
        raise self.retry(exc=RuntimeError('alert persist failed'), countdown=30)
