from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import MessageViewSet, ChatAPIView, ChatHistoryAPIView

router = DefaultRouter()
router.register(r'messages', MessageViewSet)

urlpatterns = [
    path('', ChatAPIView.as_view(), name='chat'),
    path('history/', ChatHistoryAPIView.as_view(), name='chat-history'),
    path('', include(router.urls)),
]
