# accounts/views.py
import requests
import logging
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample

from .models import User, SocialAccount
from .serializers import (
    SocialLoginRequestSerializer,
    SocialLoginResponseSerializer,
    UserSerializer,
)

#! 추후에 Flutter 진행 시 삭제해야 할 코드 (callback은 front에서 진행하는 것)
def callback_view(request):
    code = request.GET.get("code")
    error = request.GET.get("error")
    
    if error:
        return HttpResponse(f"kakao Login Error: {error}")
    
    return HttpResponse(f"kakao Authorization code: {code}")


class KakaoLoginAPIView(APIView):
    @extend_schema(
        tags=["Auth - KakaoSocial"],
        summary="카카오 소셜 로그인",
        description=(
            "카카오 인가 코드를 이용하여 우리 서비스용 JWT 토큰을 발급합니다.\n"
            "프론트에서 카카오 로그인 후 받은 `code`를 전송하세요."
        ),
        request=SocialLoginRequestSerializer,
        responses={
            200: SocialLoginResponseSerializer,
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
        },
        examples=[
            OpenApiExample(
                "성공 예시",
                value={
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                    "user": {
                        "id": 1,
                        "email": "test@example.com",
                        "username": "심슬냥",
                        "profile_image": "https://...",
                        "created_at": "2025-11-17T12:34:56Z",
                    },
                    "is_created": True,
                },
                response_only=True,
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__)
        # 1) 요청 검증
        serializer = SocialLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        
        # 2) 카카오 토큰/프로필 요청 
        kakao_rest_api_key = settings.KAKAO_REST_API_KEY
        kakao_client_secret = settings.KAKAO_CLIENT_SECRET
        kakao_redirect_uri = settings.KAKAO_REDIRECT_URI
        token_res = requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": kakao_rest_api_key,
                "client_secret": kakao_client_secret,
                "redirect_uri": kakao_redirect_uri,
                "code": code,
            },
        )
        
        logger.error("Kakao token response status: %s", token_res.status_code)
        logger.error("Kakao token response body: %s", token_res.text)

        if token_res.status_code != 200:
            return Response(
                {"detail": "Failed to obtain access token from Kakao"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_token = token_res.json().get("access_token")

        headers = {"Authorization": f"Bearer {access_token}"}
        profile_res = requests.get(
            "https://kapi.kakao.com/v2/user/me", headers=headers
        )

        if profile_res.status_code != 200:
            return Response(
                {"detail": "Failed to obtain user information from Kakao"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile_json = profile_res.json()
        kakao_oid = str(profile_json["id"])
        properties = profile_json.get("properties", {})
        kakao_account = profile_json.get("kakao_account", {})

        email = kakao_account.get("email")
        nickname = properties.get("nickname") or email
        profile_image = properties.get("profile_image", "")

        # 3) SocialAccount & User 연결
        try:
            social = SocialAccount.objects.get(
                provider=SocialAccount.Provider.KAKAO,
                provider_user_id=kakao_oid,
            )
            user = social.user
            created = False
        except SocialAccount.DoesNotExist:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": nickname,
                    "profile_image": profile_image,
                },
            )
            SocialAccount.objects.create(
                user=user,
                provider=SocialAccount.Provider.KAKAO,
                provider_user_id=kakao_oid,
            )

        # 4) JWT 발급
        refresh = RefreshToken.for_user(user)

        response_data = {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": UserSerializer(user).data,
            "is_created": created,
        }

        output_serializer = SocialLoginResponseSerializer(response_data)
        return Response(output_serializer.data, status=status.HTTP_200_OK)
    
    
class GoogleLoginAPIView(APIView):
    @extend_schema(
        tags=["Auth - GoogleSocial"],
        summary="구글 소셜 로그인",
        description=(
            "구글 인가 코드를 이용하여 우리 서비스용 JWT 토큰을 발급합니다.\n"
            "프론트에서 구글 로그인 후 받은 `code`를 전송하세요."
        ),
        request=SocialLoginRequestSerializer,
        responses={
            200: SocialLoginResponseSerializer,
            400: {"type": "object", "properties": {"detail": {"type": "string"}}},
        },
        examples=[
            OpenApiExample(
                "성공 예시",
                value={
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                    "user": {
                        "id": 1,
                        "email": "test@example.com",
                        "username": "심슬냥",
                        "profile_image": "https://...",
                        "created_at": "2025-11-17T12:34:56Z",
                    },
                    "is_created": True,
                },
                response_only=True,
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__)
        
        # 1) 요청 검증
        serializer = SocialLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        
        # 2) 구글 토큰/프로필 요청
        google_client_id = settings.GOOGLE_CLIENT_ID
        google_client_secret = settings.GOOGLE_CLIENT_SECRET
        google_redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        token_res = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "authorization_code",
                "client_id": google_client_id,
                "client_secret": google_client_secret,
                "redirect_uri": google_redirect_uri,
                "code": code
            },
        )
        
        logger.error("Google token response status: %s", token_res.status_code)
        logger.error("Google token response body: %s", token_res.text)
        
        if token_res.status_code != 200:
            return Response(
                {"detail": "Failed to obtain access token from Google"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        token_json = token_res.json()
        access_token = token_json.get("access_token")
        
        if not access_token:
            return Response(
                {"detail": "Google access token not found in response"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3) access_token으로 구글 userinfo 조회
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_res = requests.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers=headers,
        )
        
        if profile_res.status_code != 200:
            return Response(
                {"detail": "Google access token not found in response"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        profile_json = profile_res.json()
        
        # 구글의 고유 사용자 ID (sub)
        google_oid = profile_json.get("sub")
        email = profile_json.get("email")
        name = profile_json.get("name") or email
        picture = profile_json.get("picture", "")

        if not google_oid or not email:
            return Response(
                {"detail": "Google user info does not contain required fields"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # 4) SocialAccount & User 연결 (이메일 같으면 같은 계정으로 묶는 핵심 로직)
        try:
            social = SocialAccount.objects.get(
                provider=SocialAccount.Provider.GOOGLE,
                provider_user_id=google_oid,
            )
            user = social.user
            created = False
        except SocialAccount.DoesNotExist:
            user = User.objects.filter(email=email).first()
            
            if user is None:
                user = User.objects.create(
                    email=email,
                    username=name,
                    profile_image=picture,
                )
                created = True
            else:
                created = False
                
            SocialAccount.objects.create(
                user=user,
                provider=SocialAccount.Provider.GOOGLE,
                provider_user_id=google_oid,
            )
        
        refresh = RefreshToken.for_user(user)
        
        response_data = {
            "access_token" : str(refresh.access_token),
            "refresh_token" : str(refresh),
            "user": UserSerializer(user).data,
            "is_created": created,
        }
        
        output_serializer = SocialLoginResponseSerializer(response_data)
        return Response(output_serializer.data, status=status.HTTP_200_OK)