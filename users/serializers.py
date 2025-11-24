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


class SocialLoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = UserSerializer()
    is_created = serializers.BooleanField()