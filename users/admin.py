# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SocialAccount


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    
    list_display = (
        "id",
        "email",
        "nickname",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "created_at")
    search_fields = ("email", "nickname")
    ordering = ("-created_at",)
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("개인정보", {"fields": ("nickname", "profile_image")}),
        ("권한", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("날짜", {"fields": ("created_at", "updated_at")}),
    )
    
    readonly_fields = ("created_at", "updated_at")
    
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "nickname", "password1", "password2"),
        }),
    )


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):    
    list_display = (
        "id",
        "user",
        "provider",
        "provider_user_id_masked",
    )
    list_filter = ("provider",)
    search_fields = ("user__email", "user__nickname")
    
    def provider_user_id_masked(self, obj):
        """소셜 ID 마스킹"""
        pid = obj.provider_user_id
        if len(pid) > 8:
            return f"{pid[:4]}...{pid[-4:]}"
        return pid
    provider_user_id_masked.short_description = "소셜 ID"