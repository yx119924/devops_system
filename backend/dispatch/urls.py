# -*- coding: utf-8 -*-
from rest_framework import routers

from dvadmin.bastion.views.command_log import CommandLogViewSet
from dvadmin.bastion.views.credential import CredentialViewSet
from dvadmin.bastion.views.dispatch import CommandDispatchViewSet
from dvadmin.bastion.views.session import SessionRecordViewSet

router = routers.SimpleRouter()
router.register(r'credential', CredentialViewSet, basename='bastion_credential')
router.register(r'session', SessionRecordViewSet, basename='bastion_session')
router.register(r'command_log', CommandLogViewSet, basename='bastion_command_log')
router.register(r'dispatch', CommandDispatchViewSet, basename='bastion_command_dispatch')

urlpatterns = router.urls