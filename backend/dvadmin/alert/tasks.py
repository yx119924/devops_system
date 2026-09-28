import logging

from celery import shared_task
from dvadmin.alert.services import persist_alerts, dispatch_alerts

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, soft_time_limit=240, time_limit=270)
def process_webhook(self, payload):
    try:
        persist_alerts(payload)
        _, results = dispatch_alerts(payload)
        if any(not result.get('ok') for result in results):
            raise RuntimeError('notification delivery failed')
    except Exception:
        logger.warning('告警任务失败，将重试；task_id=%s', self.request.id)
        raise self.retry(exc=RuntimeError('alert processing failed'), countdown=30)
