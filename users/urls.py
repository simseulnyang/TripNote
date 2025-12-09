from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from users.views import KakaoLoginAPIView, GoogleLoginAPIView, LogoutAPIView, WithdrawalAPIView, UserProfileAPIView, SocialAccountsAPIView

urlpatterns = [
    path('kakao/login/', KakaoLoginAPIView.as_view(), name='kakao-login'),
    path('google/login/', GoogleLoginAPIView.as_view(), name='google-login'),
    
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    
    path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('social-accounts/', SocialAccountsAPIView.as_view(), name='social-accounts'),
    
    path('withdrawal/', WithdrawalAPIView.as_view(), name='withdrawal'),
]