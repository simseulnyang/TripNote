from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from users.managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=100, unique=True)
    profile_image = models.URLField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
    
    def has_perm(self, perm, obj = ...):
        return super().has_perm(perm, obj)
    
    def has_module_perms(self, app_label):
        return super().has_module_perms(app_label)
    
    
class SocialAccount(models.Model):
    class Providers(models.TextChoices):
        KAKAO = 'kakao', 'Kakao'
        GOOGLE = 'google', 'Google'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=Providers.choices)
    provider_user_id = models.CharField(max_length=255, help_text="카카오_oid, 구글_sub 등 소셜 서비스 고유 ID")

    class Meta:
        unique_together = ('provider', 'provider_user_id')

    def __str__(self):
        return f"{self.provider} - {self.provider_user_id}"