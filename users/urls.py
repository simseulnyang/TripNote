from django.urls import path
from users.views import KakaoLoginAPIView, GoogleLoginAPIView, callback_view

urlpatterns = [
    path('kakao/login/', KakaoLoginAPIView.as_view(), name='kakao-login'),
    path('kakao/callback/', callback_view, name='kakao-callback'),
    path('google/login/', GoogleLoginAPIView.as_view(), name='google-login'),
    path('google/callback/', callback_view, name='google-callback'),
]