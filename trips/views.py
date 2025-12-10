from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Avg

from trips.models import Trip, Destination, DayPlan, Budget, Expense, TripLog, BudgetCategory
from trips.serializers import (
    TripListSerializer,
    TripDetailSerializer,
    TripCreateSerializer,
    TripUpdateSerializer,
    DestinationSerializer,
    DestinationCreateSerializer,
    DayPlanSerializer,
    BudgetSerializer,
    BudgetCreateSerializer,
    ExpenseSerializer,
    ExpenseCreateSerializer,
    TripLogSerializer,
    TripLogCreateSerializer,
)
from trips.permissions import IsOwnerOrReadOnly


@extend_schema_view(
    list=extend_schema(
        tags=["Trips"],
        summary="여행 목록 조회",
        description="로그인한 사용자의 여행 목록을 조회합니다.",
    ),
    create=extend_schema(
        tags=["Trips"],
        summary="여행 생성",
        description="새로운 여행을 생성합니다. 여행지와 예산도 함께 생성할 수 있습니다.",
    ),
    retrieve=extend_schema(
        tags=["Trips"],
        summary="여행 상세 조회",
    ),
    update=extend_schema(tags=["Trips"], summary="여행 전체 수정"),
    partial_update=extend_schema(tags=["Trips"], summary="여행 부분 수정"),
    destroy=extend_schema(tags=["Trips"], summary="여행 삭제"),
)
class TripViewSet(viewsets.ModelViewSet):
    """여행 일정 CRUD API"""
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        trip = serializer.instance
        response_serializer = TripDetailSerializer(trip)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def get_queryset(self):
        return Trip.objects.filter(user=self.request.user).prefetch_related(
            "destinations", "day_plans", "budgets", "expenses", "logs"
        )
    
    def get_serializer_class(self):
        if self.action == "list":
            return TripListSerializer
        elif self.action == "create":
            return TripCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return TripUpdateSerializer
        return TripDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    
    @extend_schema(tags=["Trips"], summary="여행지 목록", responses={200: DestinationSerializer(many=True)})
    @action(detail=True, methods=["get"])
    def destinations(self, request, pk=None):
        trip = self.get_object()
        return Response(DestinationSerializer(trip.destinations.all(), many=True).data)
    
    
    @extend_schema(tags=["Trips"], summary="여행지 추가", request=DestinationCreateSerializer, responses={201: DestinationSerializer})
    @destinations.mapping.post
    def add_destination(self, request, pk=None):
        trip = self.get_object()
        serializer = DestinationCreateSerializer(data=request.data)
        if serializer.is_valid():
            day = serializer.validated_data.get("day", 1)
            if day > trip.duration_days:
                return Response({"message": f"일차는 {trip.duration_days}일 이내여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)
            destination = serializer.save(trip=trip)
            return Response(DestinationSerializer(destination).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    @extend_schema(tags=["Trips"], summary="일자별 계획 조회", responses={200: DayPlanSerializer(many=True)})
    @action(detail=True, methods=["get"])
    def days(self, request, pk=None):
        trip = self.get_object()
        return Response(DayPlanSerializer(trip.day_plans.all(), many=True).data)
    
    @extend_schema(tags=["Trips"], summary="특정 일차 수정")
    @action(detail=True, methods=["patch"], url_path="days/(?P<day_number>[0-9]+)")
    def update_day(self, request, pk=None, day_number=None):
        trip = self.get_object()
        day_plan = get_object_or_404(DayPlan, trip=trip, day_number=day_number)
        serializer = DayPlanSerializer(day_plan, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    @extend_schema(tags=["Budget"], summary="예산 목록", responses={200: BudgetSerializer(many=True)})
    @action(detail=True, methods=["get"])
    def budgets(self, request, pk=None):
        trip = self.get_object()
        return Response(BudgetSerializer(trip.budgets.all(), many=True).data)
    
    @extend_schema(tags=["Budget"], summary="예산 설정", request=BudgetCreateSerializer, responses={200: BudgetSerializer})
    @budgets.mapping.post
    def set_budget(self, request, pk=None):
        trip = self.get_object()
        serializer = BudgetCreateSerializer(data=request.data)
        if serializer.is_valid():
            budget, created = Budget.objects.update_or_create(
                trip=trip,
                category=serializer.validated_data["category"],
                defaults={
                    "amount": serializer.validated_data["amount"],
                    "memo": serializer.validated_data.get("memo", ""),
                }
            )
            return Response(BudgetSerializer(budget).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(tags=["Budget"], summary="예산 요약")
    @action(detail=True, methods=["get"], url_path="budgets/summary")
    def budget_summary(self, request, pk=None):
        trip = self.get_object()
        return Response({
            "total_budget": trip.total_budget,
            "total_expense": trip.total_expense,
            "total_estimated_cost": trip.total_estimated_cost,
            "remaining": trip.budget_remaining,
            "usage_percent": trip.budget_usage_percent,
            "by_category": BudgetSerializer(trip.budgets.all(), many=True).data,
        })
    
    
    @extend_schema(tags=["Expense"], summary="지출 목록", responses={200: ExpenseSerializer(many=True)})
    @action(detail=True, methods=["get"])
    def expenses(self, request, pk=None):
        trip = self.get_object()
        return Response(ExpenseSerializer(trip.expenses.all(), many=True).data)
    
    @extend_schema(tags=["Expense"], summary="지출 추가", request=ExpenseCreateSerializer, responses={201: ExpenseSerializer})
    @expenses.mapping.post
    def add_expense(self, request, pk=None):
        trip = self.get_object()
        serializer = ExpenseCreateSerializer(data=request.data, context={"trip": trip})
        if serializer.is_valid():
            expense = serializer.save(trip=trip)
            return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(tags=["Expense"], summary="지출 요약")
    @action(detail=True, methods=["get"], url_path="expenses/summary")
    def expense_summary(self, request, pk=None):
        trip = self.get_object()
        expenses = trip.expenses.all()
        
        by_category = {}
        by_day = {}
        by_payment = {}
        
        for exp in expenses:
            cat = exp.get_category_display()
            by_category[cat] = by_category.get(cat, 0) + float(exp.amount)
            
            day = f"Day {exp.day_number}" if exp.day_number else "미분류"
            by_day[day] = by_day.get(day, 0) + float(exp.amount)
            
            method = exp.get_payment_method_display()
            by_payment[method] = by_payment.get(method, 0) + float(exp.amount)
        
        return Response({
            "total": trip.total_expense,
            "by_category": by_category,
            "by_day": by_day,
            "by_payment_method": by_payment,
        })
    
    
    @extend_schema(tags=["TripLog"], summary="여행 기록 목록", responses={200: TripLogSerializer(many=True)})
    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        trip = self.get_object()
        return Response(TripLogSerializer(trip.logs.all(), many=True).data)
    
    @extend_schema(tags=["TripLog"], summary="여행 기록 추가", request=TripLogCreateSerializer, responses={201: TripLogSerializer})
    @logs.mapping.post
    def add_log(self, request, pk=None):
        trip = self.get_object()
        serializer = TripLogCreateSerializer(data=request.data)
        if serializer.is_valid():
            log = serializer.save(trip=trip)
            return Response(TripLogSerializer(log).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    @extend_schema(
        tags=["Comparison"],
        summary="계획 vs 실제 비교",
        description="예산 대비 지출, 계획한 일정 대비 실제 방문 비교"
    )
    @action(detail=True, methods=["get"])
    def comparison(self, request, pk=None):
        trip = self.get_object()
        
        # 예산 비교
        budget_comparison = []
        for category, label in BudgetCategory.choices:
            budget = trip.budgets.filter(category=category).first()
            budget_amount = budget.amount if budget else 0
            expense_total = trip.expenses.filter(category=category).aggregate(total=Sum("amount"))["total"] or 0
            
            budget_comparison.append({
                "category": category,
                "category_display": label,
                "budget": float(budget_amount),
                "actual": float(expense_total),
                "difference": float(budget_amount - expense_total),
                "usage_percent": round(float(expense_total) / float(budget_amount) * 100, 1) if budget_amount > 0 else 0,
            })
        
        # 일정 비교
        schedule_comparison = []
        for day_plan in trip.day_plans.all():
            planned = set(trip.destinations.filter(day=day_plan.day_number).values_list("name", flat=True))
            actual_visited = set(trip.logs.filter(day_number=day_plan.day_number, visit_status__in=["planned", "unplanned"]).values_list("place_name", flat=True))
            
            schedule_comparison.append({
                "day_number": day_plan.day_number,
                "date": day_plan.date,
                "planned_count": len(planned),
                "actual_count": len(actual_visited),
                "planned_places": list(planned),
                "actual_places": list(actual_visited),
                "visited_as_planned": list(planned & actual_visited),
                "skipped": list(planned - actual_visited),
                "unplanned_visits": list(actual_visited - planned),
            })
        
        # 전체 요약
        total_planned = trip.destinations.count()
        planned_visited = trip.logs.filter(visit_status="planned").count()
        unplanned_visited = trip.logs.filter(visit_status="unplanned").count()
        avg_rating = trip.logs.filter(rating__isnull=False).aggregate(avg=Avg("rating"))["avg"]
        
        summary = {
            "total_budget": float(trip.total_budget),
            "total_expense": float(trip.total_expense),
            "budget_remaining": float(trip.budget_remaining),
            "budget_usage_percent": trip.budget_usage_percent,
            "total_estimated_cost": float(trip.total_estimated_cost),
            "estimated_vs_actual_diff": float(trip.total_estimated_cost - trip.total_expense),
            "total_planned_places": total_planned,
            "total_visited_places": planned_visited + unplanned_visited,
            "planned_and_visited": planned_visited,
            "unplanned_visits": unplanned_visited,
            "plan_completion_rate": round(planned_visited / total_planned * 100, 1) if total_planned > 0 else 0,
            "average_rating": round(avg_rating, 1) if avg_rating else None,
        }
        
        return Response({
            "budget_comparison": budget_comparison,
            "schedule_comparison": schedule_comparison,
            "summary": summary,
        })


# 개별 리소스 ViewSet 

@extend_schema_view(
    retrieve=extend_schema(tags=["Destinations"], summary="여행지 상세"),
    update=extend_schema(tags=["Destinations"], summary="여행지 전체 수정"),
    partial_update=extend_schema(tags=["Destinations"], summary="여행지 부분 수정"),
    destroy=extend_schema(tags=["Destinations"], summary="여행지 삭제"),
)
class DestinationViewSet(viewsets.ModelViewSet):
    """여행지 개별 관리 API"""
    permission_classes = [IsAuthenticated]
    serializer_class = DestinationSerializer
    http_method_names = ["get", "put", "patch", "delete"]
    
    def get_queryset(self):
        return Destination.objects.filter(trip__user=self.request.user)


@extend_schema_view(
    retrieve=extend_schema(tags=["Expense"], summary="지출 상세"),
    update=extend_schema(tags=["Expense"], summary="지출 수정"),
    partial_update=extend_schema(tags=["Expense"], summary="지출 부분 수정"),
    destroy=extend_schema(tags=["Expense"], summary="지출 삭제"),
)
class ExpenseViewSet(viewsets.ModelViewSet):
    """지출 개별 관리 API"""
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer
    http_method_names = ["get", "put", "patch", "delete"]
    
    def get_queryset(self):
        return Expense.objects.filter(trip__user=self.request.user)


@extend_schema_view(
    retrieve=extend_schema(tags=["TripLog"], summary="여행 기록 상세"),
    update=extend_schema(tags=["TripLog"], summary="여행 기록 수정"),
    partial_update=extend_schema(tags=["TripLog"], summary="여행 기록 부분 수정"),
    destroy=extend_schema(tags=["TripLog"], summary="여행 기록 삭제"),
)
class TripLogViewSet(viewsets.ModelViewSet):
    """여행 기록 개별 관리 API"""
    permission_classes = [IsAuthenticated]
    serializer_class = TripLogSerializer
    http_method_names = ["get", "put", "patch", "delete"]
    
    def get_queryset(self):
        return TripLog.objects.filter(trip__user=self.request.user)
