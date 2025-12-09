# accounts/views.py
import requests
import logging
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from drf_spectacular.utils import extend_schema, OpenApiExample

from users.models import User, SocialAccount
from users.serializers import (
    SocialLoginRequestSerializer,
    SocialLoginResponseSerializer,
    UserSerializer,
    UserUpdateSerializer,
    LogoutRequestSerializer,
    WithdrawalRequestSerializer,
    MessageResponseSerializer
)

logger = logging.getLogger(__name__)


class KakaoLoginAPIView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=["Auth - KakaoSocial"],
        summary="카카오 소셜 로그인",
        description=(
            "카카오 로그인을 처리합니다.\n\n"
            "1. 인가 코드 방식 = 'code' 전송.\n"
            "2. 엑세스 토큰 방식 = 'access_token' 전송 (모바일 SDK 사용 시)"
        ),
        request=SocialLoginRequestSerializer,
        responses={
            200: SocialLoginResponseSerializer,
            400: MessageResponseSerializer,
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
        code = request.data.get("code")
        access_token = request.data.get("access_token")
        
        if access_token:
            return self._login_with_access_token(access_token)
        
        if code:
            return self._login_with_code(code)
        
        return Response(
            {"messsage": "code 또는 access_token을 제공해야 합니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    def _login_with_code(self, code):
        """카카오 인가 코드로 로그인 처리"""
        token_res = requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.KAKAO_REST_API_KEY,
                "client_secret": settings.KAKAO_CLIENT_SECRET,
                "redirect_uri": settings.KAKAO_REDIRECT_URI,
                "code": code,
            },
        )
        
        logger.info(f"Kakao token response status: {token_res.status_code}")

        if token_res.status_code != 200:
            return Response(
                {"message": "Failed to obtain access token from Kakao"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_token = token_res.json().get("access_token")
        return self._login_with_access_token(access_token)
    
    
    def _login_with_access_token(self, access_token):
        """카카오 엑세스 토큰으로 로그인 처리"""
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
        nickname = properties.get("nickname") or email.split("@")[0] if email else "사용자"
        profile_image = properties.get("profile_image", "")

        # SocialAccount & User 연결
        try:
            social = SocialAccount.objects.get(
                provider=SocialAccount.Providers.KAKAO,
                provider_user_id=kakao_oid,
            )
            user = social.user
            created = False
        except SocialAccount.DoesNotExist:
            if not email:
                email = f"kakao_{kakao_oid}@tripnote.local"
                
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "nickname": nickname,
                    "profile_image": profile_image,
                },
            )
            SocialAccount.objects.create(
                user=user,
                provider=SocialAccount.Providers.KAKAO,
                provider_user_id=kakao_oid,
            )

        refresh = RefreshToken.for_user(user)

        response_data = {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": UserSerializer(user).data,
            "is_created": created,
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
    
class GoogleLoginAPIView(APIView):
    permission_classes = [AllowAny]
    
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
            400: MessageResponseSerializer,
        },
    )
    
    def post(self, request, *args, **kwargs):
        serializer = SocialLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        
        token_res = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "code": code
            },
        )
        
        logger.info(f"Google token response status: {token_res.status_code}")
        
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
        
        google_oid = profile_json.get("sub")
        email = profile_json.get("email")
        name = profile_json.get("name") or email.split("@")[0] if email else "사용자"
        picture = profile_json.get("picture", "")

        if not google_oid or not email:
            return Response(
                {"message": "Google user info does not contain required fields"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            social = SocialAccount.objects.get(
                provider=SocialAccount.Providers.GOOGLE,
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
                provider=SocialAccount.Providers.GOOGLE,
                provider_user_id=google_oid,
            )
        
        refresh = RefreshToken.for_user(user)
        
        response_data = {
            "access_token" : str(refresh.access_token),
            "refresh_token" : str(refresh),
            "user": UserSerializer(user).data,
            "is_created": created,
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    
class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Auth - Logout"],
        summary="로그아웃",
        description=("Refresh 토큰을 블랙리스트에 추가하여 로그아웃 처리합니다.\n"
                     "클라이언트에서eh 저장된 토큰을 삭제해야 합니다."),
        request=LogoutRequestSerializer,
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
        },
        examples=[
            OpenApiExample(
                "성공 예시",
                value={
                    "message": "로그아웃 되었습니다."
                },
                response_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = LogoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            refresh_token = serializer.validated_data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {"message": "로그아웃 되었습니다."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error("Error blacklisting token: %s", str(e))
            return Response(
                {"detail": "로그아웃 처리 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class WithdrawalAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Auth - Withdrawal"],
        summary="회원 탈퇴",
        description=(
            "사용자 회원 탈퇴 처리\n"
            "1. 연결된 소셜 계정의 연결을 해제 (카카오/구글 API 호출)\n"
            "2. 모든 토큰 무효화 처리\n"
            "3. 사용자 계정 삭제\n\n"
            "※주의 : 탈퇴 시 복구가 불가능합니다."),
        request=WithdrawalRequestSerializer,
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
        },
    )
    
    def delete(self, request):
        user = request.user
        serializer = WithdrawalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        refresh_token = serializer.validated_data.get("refresh")
        
        try:
            social_accounts = SocialAccount.objects.filter(user=user)
            
            for social in social_accounts:
                self._unlink_social_account(social)
                
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    pass
            
            outstanding_tokens = OutstandingToken.objects.filter(user=user)
            for o_token in outstanding_tokens:
                try:
                    BlacklistedToken.objects.get_or_create(token=o_token)
                except Exception as e:
                    pass
                
            user.delete()
            
            return Response(
                {"message": "회원 탈퇴가 완료되었습니다. 이용해 주셔서 감사합니다."},
                status=status.HTTP_200_OK,
            )
            
        except Exception as e:
            logger.error(f"Error during user {user.id} withdrawal: {str(e)}")
            return Response(
                {"message": "회원 탈퇴 처리 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    
    def _unlink_social_account(self, social: SocialAccount):
        try:
            if social.provider == SocialAccount.Providers.KAKAO:
                self._unlink_kakao(social)
            elif social.provider == SocialAccount.Providers.GOOGLE:
                self._unlink_google(social)
        except Exception as e:
            logger.error(f"Error unlinking social account {social.provider}: {str(e)}")
        finally:
            social.delete()
            
    def _unlink_kakao(self, social: SocialAccount):
        admin_key = getattr(settings, "KAKAO_ADMIN_KEY", None)
        
        if admin_key:
            requests.post(
                "https://kapi.kakao.com/v1/user/unlink",
                headers={
                    "Authorization": f"KakaoAK {admin_key}"
                },
                data={
                    "target_id_type": "user_id",
                    "target_id": social.provider_user_id,
                }
            )
            logger.info(f"Kakao account unlinked for user {social.provider_user_id}")
            
            
    def _unlink_google(self, social: SocialAccount):
        logger.info(f"Google account unlinking not implemented for user {social.provider_user_id}")
        

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["User - Profile"],
        summary="내 프로필 조회",
        description="인증된 사용자의 프로필 정보를 조회합니다.",
        responses={
            200: UserSerializer,
            400: MessageResponseSerializer,
        },
    )
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        tags=["User - Profile"],
        summary="내 프로필 수정",
        description="인증된 사용자의 프로필 정보를 수정합니다.",
        request=UserUpdateSerializer,
        responses={
            200: UserSerializer,
            400: MessageResponseSerializer,
        },
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                UserSerializer(request.user).data,
                status=status.HTTP_200_OK,
            )
        
        return Response(
            {"message": "프로필 수정에 실패했습니다.", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class SocialAccountsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Auth"],
        summary="연결된 소셜 계정 조회",
        description="현재 사용자에게 연결된 소셜 계정 목록을 조회합니다.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "social_accounts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "provider": {"type": "string"},
                                "connected_at": {"type": "string", "format": "date-time"}
                            }
                        }
                    }
                }
            }
        },
    )
    def get(self, request):
        social_accounts = SocialAccount.objects.filter(user=request.user)
        
        data = {
            "social_accounts": [
                {
                    "provider": sa.provider,
                    "provider_user_id": sa.provider_user_id[-4:].rjust(len(sa.provider_user_id), '*'),  # 마스킹
                }
                for sa in social_accounts
            ]
        }
        
        return Response(data, status=status.HTTP_200_OK)