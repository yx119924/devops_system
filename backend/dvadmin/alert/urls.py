from django.urls import path
from rest_framework import routers

from dvadmin.alert.views.channel import NotifyChannelViewSet
from dvadmin.alert.views.event import AlertEventViewSet
from dvadmin.alert.views.group import AlertGroupViewSet
from dvadmin.alert.views.manage import (
    active_alerts,
    route_summary,
    silence_delete,
    silence_list_create,
)
from dvadmin.alert.views.rule import AlertRuleViewSet
from dvadmin.alert.views.template import AlertTemplateViewSet
from dvadmin.alert.views.webhook import webhook_receiver

router = routers.SimpleRouter()
router.register(r'rule', AlertRuleViewSet, basename='alert_rule')
router.register(r'channel', NotifyChannelViewSet, basename='alert_channel')
router.register(r'group', AlertGroupViewSet, basename='alert_group')
router.register(r'event', AlertEventViewSet, basename='alert_event')
router.register(r'template', AlertTemplateViewSet, basename='alert_template')

urlpatterns = router.urls + [
    path('webhook/receiver/', webhook_receiver),
    path('manage/alerts/', active_alerts),
    path('manage/silences/', silence_list_create),
    path('manage/silences/<str:silence_id>/', silence_delete),
    path('manage/route/', route_summary),
]
