from rest_framework import routers

from dvadmin.aiagent.views import (
    AiChatSessionViewSet, AiGuardViewSet, AiProviderViewSet, AiToolCallViewSet)

router = routers.SimpleRouter()
router.register(r'provider', AiProviderViewSet, basename='ai_provider')
router.register(r'guard', AiGuardViewSet, basename='ai_guard')
router.register(r'chat', AiChatSessionViewSet, basename='ai_chat')
router.register(r'toolcall', AiToolCallViewSet, basename='ai_toolcall')

urlpatterns = router.urls
