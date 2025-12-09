from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TripViewSet, DestinationViewSet, ExpenseViewSet, TripLogViewSet

app_name = "trips"

router = DefaultRouter()
router.register(r"", TripViewSet, basename="trip")

destination_router = DefaultRouter()
destination_router.register(r"", DestinationViewSet, basename="destination")

expense_router = DefaultRouter()
expense_router.register(r"", ExpenseViewSet, basename="expense")

log_router = DefaultRouter()
log_router.register(r"", TripLogViewSet, basename="triplog")

urlpatterns = [
    path("", include(router.urls)),
    path("destinations/", include(destination_router.urls)),
    path("expenses/", include(expense_router.urls)),
    path("logs/", include(log_router.urls)),
]