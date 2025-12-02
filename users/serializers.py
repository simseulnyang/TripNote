from rest_framework import serializers
from users.models import User


class SocialLoginRequestSerializer(serializers.Serializer):
    code = serializers.CharField(help_text="OAuth 인가 코드 (authorization code)")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "nickname",
            "profile_image",
            "created_at",
        )
        read_only_fields = fields
        
        
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "nickname",
            "profile_image",
        )
        
    def validate_nickname(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("닉네임은 최소 2자 이상이어야 합니다.")
        if len(value) > 22:
            raise serializers.ValidationError("닉네임은 최대 22자 이하여야 합니다.")
        
        user = self.instance
        if User.objects.exclude(id=user.id).filter(nickname=value).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        
        return value


class SocialLoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = UserSerializer()
    is_created = serializers.BooleanField(
        help_text="소셜 로그인 시 신규 회원 생성 여부(True: 신규 회원 생성, False: 기존 회원 로그인)"
    )
    
    
class LogoutRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()
    
    
class WithdrawalRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=False,
        help_text="Refresh Token(선택, 제공 시 해당 토큰도 무효화 처리됩니다.)"
    )
    confirm = serializers.BooleanField(
        default=False,
        help_text="회원 탈퇴 확인 여부(True: 탈퇴 진행, False: 탈퇴 미진행)"
    )
    
    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("회원 탈퇴를 진행하려면 confirm 필드를 True로 설정해야 합니다.")
        return value
    
    
class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    errors = serializers.DictField(required=False)