from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    객체의 소유자만 수정/삭제 가능
    
    - 읽기 권한: 모든 인증된 사용자
    - 쓰기 권한: 객체 소유자만
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'is_public') and obj.is_public:
                return True
            if hasattr(obj, 'user'):
                return obj.user == request.user
            return True
        
        # 쓰기 권한은 소유자만
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsOwner(permissions.BasePermission):
    """
    객체의 소유자만 모든 작업 가능
    """
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'trip'):
            return obj.trip.user == request.user
        return False