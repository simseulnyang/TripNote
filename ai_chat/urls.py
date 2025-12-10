from django.urls import path
from .views import ChatSessionListView, ChatSessionDetailView, ChatMessageView

urlpatterns = [
    path('sessions/', ChatSessionListView.as_view(), name='chat-session-list'),
    path('sessions/<int:session_id>/', ChatSessionDetailView.as_view(), name='chat-session-detail'),
    path('send/', ChatMessageView.as_view(), name='chat-send'),
]