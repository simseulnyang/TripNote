from decimal import Decimal
from django.db import models
from rest_framework import serializers
from trips.models import (
    Trip, Destination, DayPlan,
    Budget, Expense, BudgetCategory,
    TripLog, TripLogPhoto
)


class DestinationSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    
    class Meta:
        model = Destination
        fields = (
            "id",
            "name",
            "address",
            "latitude",
            "longitude",
            "day",
            "order",
            "planned_time",
            "estimated_duration",
            "estimated_cost",
            "category",
            "category_display",
            "memo",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class DestinationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Destination
        fields = (
            "name",
            "address",
            "latitude",
            "longitude",
            "day",
            "order",
            "planned_time",
            "estimated_duration",
            "estimated_cost",
            "category",
            "memo",
        )
    
    def validate_day(self, value):
        if value < 1:
            raise serializers.ValidationError("일차는 1 이상이어야 합니다.")
        return value


class BudgetSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    spent_amount = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    usage_percent = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Budget
        fields = (
            "id",
            "category",
            "category_display",
            "amount",
            "memo",
            "spent_amount",
            "remaining_amount",
            "usage_percent",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class BudgetCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = (
            "category",
            "amount",
            "memo",
        )
    
    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("예산은 0 이상이어야 합니다.")
        return value


class ExpenseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    destination_name = serializers.CharField(source="destination.name", read_only=True, allow_null=True)
    
    class Meta:
        model = Expense
        fields = (
            "id",
            "category",
            "category_display",
            "amount",
            "description",
            "expense_date",
            "expense_time",
            "day_number",
            "destination",
            "destination_name",
            "payment_method",
            "payment_method_display",
            "receipt_image",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "day_number", "created_at", "updated_at")


class ExpenseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = (
            "category",
            "amount",
            "description",
            "expense_date",
            "expense_time",
            "destination",
            "payment_method",
            "receipt_image",
        )
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("금액은 0보다 커야 합니다.")
        return value
    
    def validate(self, attrs):
        # 지출 날짜가 여행 기간 내인지 확인
        trip = self.context.get("trip")
        if trip and "expense_date" in attrs:
            expense_date = attrs["expense_date"]
            if expense_date < trip.start_date or expense_date > trip.end_date:
                raise serializers.ValidationError({
                    "expense_date": "지출 날짜는 여행 기간 내여야 합니다."
                })
        return attrs


class TripLogPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripLogPhoto
        fields = (
            "id",
            "image_url",
            "caption",
            "order",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class TripLogSerializer(serializers.ModelSerializer):
    photos = TripLogPhotoSerializer(many=True, read_only=True)
    visit_status_display = serializers.CharField(source="get_visit_status_display", read_only=True)
    destination_name = serializers.CharField(source="destination.name", read_only=True, allow_null=True)
    
    class Meta:
        model = TripLog
        fields = (
            "id",
            "destination",
            "destination_name",
            "place_name",
            "address",
            "latitude",
            "longitude",
            "visit_date",
            "visit_time",
            "day_number",
            "actual_duration",
            "rating",
            "review",
            "visit_status",
            "visit_status_display",
            "photos",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "day_number", "created_at", "updated_at")


class TripLogCreateSerializer(serializers.ModelSerializer):
    photos = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = TripLog
        fields = (
            "destination",
            "place_name",
            "address",
            "latitude",
            "longitude",
            "visit_date",
            "visit_time",
            "actual_duration",
            "rating",
            "review",
            "visit_status",
            "photos",
        )
    
    def validate_rating(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("평점은 1~5 사이여야 합니다.")
        return value
    
    def create(self, validated_data):
        photos_data = validated_data.pop("photos", [])
        trip_log = TripLog.objects.create(**validated_data)
        
        # 사진 생성
        for idx, photo_url in enumerate(photos_data):
            TripLogPhoto.objects.create(
                log=trip_log,
                image_url=photo_url,
                order=idx
            )
        
        return trip_log


class DayPlanSerializer(serializers.ModelSerializer):
    destinations = serializers.SerializerMethodField()
    estimated_cost = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    expenses = serializers.SerializerMethodField()
    logs = serializers.SerializerMethodField()
    
    class Meta:
        model = DayPlan
        fields = (
            "id",
            "day_number",
            "date",
            "memo",
            "estimated_cost",
            "destinations",
            "expenses",
            "logs",
        )
        read_only_fields = ("id",)
    
    def get_destinations(self, obj):
        destinations = obj.trip.destinations.filter(day=obj.day_number)
        return DestinationSerializer(destinations, many=True).data
    
    def get_expenses(self, obj):
        expenses = obj.trip.expenses.filter(day_number=obj.day_number)
        return ExpenseSerializer(expenses, many=True).data
    
    def get_logs(self, obj):
        logs = obj.trip.logs.filter(day_number=obj.day_number)
        return TripLogSerializer(logs, many=True).data


class BudgetSummarySerializer(serializers.Serializer):
    total_budget = serializers.DecimalField(max_digits=12, decimal_places=0)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=0)
    total_estimated_cost = serializers.DecimalField(max_digits=12, decimal_places=0)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=0)
    usage_percent = serializers.FloatField()
    by_category = BudgetSerializer(many=True)


class ExpenseSummarySerializer(serializers.Serializer):
    total = serializers.DecimalField(max_digits=12, decimal_places=0)
    by_category = serializers.DictField()
    by_day = serializers.DictField()
    by_payment_method = serializers.DictField()


class TripListSerializer(serializers.ModelSerializer):
    duration_days = serializers.IntegerField(read_only=True)
    destination_names = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    destination_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_budget = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    budget_usage_percent = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Trip
        fields = (
            "id",
            "title",
            "description",
            "start_date",
            "end_date",
            "duration_days",
            "thumbnail",
            "destination_names",
            "destination_count",
            "status",
            "status_display",
            "is_public",
            "total_budget",
            "total_expense",
            "budget_usage_percent",
            "created_at",
        )
        read_only_fields = fields
    
    def get_destination_count(self, obj):
        return obj.destinations.count()


class TripDetailSerializer(serializers.ModelSerializer):
    duration_days = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    destinations = DestinationSerializer(many=True, read_only=True)
    day_plans = DayPlanSerializer(many=True, read_only=True)
    budgets = BudgetSerializer(many=True, read_only=True)
    
    # 예산 요약
    total_budget = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    total_estimated_cost = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    budget_remaining = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    budget_usage_percent = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Trip
        fields = (
            "id",
            "title",
            "description",
            "start_date",
            "end_date",
            "duration_days",
            "thumbnail",
            "status",
            "status_display",
            "is_public",
            "destinations",
            "day_plans",
            "budgets",
            "total_budget",
            "total_expense",
            "total_estimated_cost",
            "budget_remaining",
            "budget_usage_percent",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class TripCreateSerializer(serializers.ModelSerializer):
    destinations = DestinationCreateSerializer(many=True, required=False)
    budgets = BudgetCreateSerializer(many=True, required=False)
    thumbnail = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = Trip
        fields = (
            "title",
            "description",
            "start_date",
            "end_date",
            "thumbnail",
            "is_public",
            "destinations",
            "budgets",
        )
    
    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        
        if start_date and end_date:
            if end_date < start_date:
                raise serializers.ValidationError({
                    "end_date": "종료일은 시작일 이후여야 합니다."
                })
            
            duration = (end_date - start_date).days + 1
            if duration > 30:
                raise serializers.ValidationError({
                    "end_date": "여행 기간은 최대 30일까지 설정할 수 있습니다."
                })
        
        return attrs
    
    def validate_title(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("제목은 2자 이상이어야 합니다.")
        return value
    
    def create(self, validated_data):
        destinations_data = validated_data.pop("destinations", [])
        budgets_data = validated_data.pop("budgets", [])
        
        trip = Trip.objects.create(**validated_data)
        
        # Destination 생성
        for dest_data in destinations_data:
            Destination.objects.create(trip=trip, **dest_data)
        
        # Budget 생성
        for budget_data in budgets_data:
            Budget.objects.create(trip=trip, **budget_data)
        
        # DayPlan 자동 생성
        self._create_day_plans(trip)
        
        return trip
    
    def _create_day_plans(self, trip):
        from datetime import timedelta
        
        current_date = trip.start_date
        day_number = 1
        
        while current_date <= trip.end_date:
            DayPlan.objects.create(
                trip=trip,
                day_number=day_number,
                date=current_date,
            )
            current_date += timedelta(days=1)
            day_number += 1


class TripUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = (
            "title",
            "description",
            "start_date",
            "end_date",
            "thumbnail",
            "status",
            "is_public",
        )
    
    def validate(self, attrs):
        instance = self.instance
        start_date = attrs.get("start_date", instance.start_date if instance else None)
        end_date = attrs.get("end_date", instance.end_date if instance else None)
        
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "종료일은 시작일 이후여야 합니다."
            })
        
        return attrs
    
    def update(self, instance, validated_data):
        old_start = instance.start_date
        old_end = instance.end_date
        
        instance = super().update(instance, validated_data)
        
        new_start = instance.start_date
        new_end = instance.end_date
        
        if old_start != new_start or old_end != new_end:
            self._update_day_plans(instance)
        
        return instance
    
    def _update_day_plans(self, trip):
        from datetime import timedelta
        
        trip.day_plans.all().delete()
        
        current_date = trip.start_date
        day_number = 1
        
        while current_date <= trip.end_date:
            DayPlan.objects.create(
                trip=trip,
                day_number=day_number,
                date=current_date,
            )
            current_date += timedelta(days=1)
            day_number += 1


class TripComparisonSerializer(serializers.Serializer):
    
    # 예산 비교
    budget_comparison = serializers.SerializerMethodField()
    
    # 일정 비교
    schedule_comparison = serializers.SerializerMethodField()
    
    # 요약 통계
    summary = serializers.SerializerMethodField()
    
    def get_budget_comparison(self, trip):
        """카테고리별 예산 vs 실제 지출 비교"""
        result = []
        for category, label in BudgetCategory.choices:
            budget = trip.budgets.filter(category=category).first()
            budget_amount = budget.amount if budget else Decimal("0")
            
            expense_total = trip.expenses.filter(
                category=category
            ).aggregate(
                total=models.Sum("amount")
            )["total"] or Decimal("0")
            
            result.append({
                "category": category,
                "category_display": label,
                "budget": budget_amount,
                "actual": expense_total,
                "difference": budget_amount - expense_total,
                "usage_percent": round((expense_total / budget_amount * 100), 1) if budget_amount > 0 else 0,
            })
        
        return result
    
    def get_schedule_comparison(self, trip):
        result = []
        for day_plan in trip.day_plans.all():
            planned = trip.destinations.filter(day=day_plan.day_number)
            actual = trip.logs.filter(day_number=day_plan.day_number)
            
            planned_names = set(planned.values_list("name", flat=True))
            actual_names = set(actual.values_list("place_name", flat=True))
            
            result.append({
                "day_number": day_plan.day_number,
                "date": day_plan.date,
                "planned_count": planned.count(),
                "actual_count": actual.count(),
                "planned_places": list(planned_names),
                "actual_places": list(actual_names),
                "visited_as_planned": list(planned_names & actual_names),
                "skipped": list(planned_names - actual_names),
                "unplanned_visits": list(actual_names - planned_names),
            })
        
        return result
    
    def get_summary(self, trip):
        total_planned = trip.destinations.count()
        total_visited = trip.logs.filter(
            visit_status__in=["planned", "unplanned"]
        ).count()
        
        planned_visited = trip.logs.filter(visit_status="planned").count()
        unplanned_visited = trip.logs.filter(visit_status="unplanned").count()
        skipped = trip.logs.filter(visit_status="skipped").count()
        
        avg_rating = trip.logs.filter(
            rating__isnull=False
        ).aggregate(
            avg=models.Avg("rating")
        )["avg"]
        
        return {
            "total_budget": trip.total_budget,
            "total_expense": trip.total_expense,
            "budget_remaining": trip.budget_remaining,
            "budget_usage_percent": trip.budget_usage_percent,
            "total_planned_places": total_planned,
            "total_visited_places": total_visited,
            "planned_and_visited": planned_visited,
            "unplanned_visits": unplanned_visited,
            "skipped_places": skipped,
            "plan_completion_rate": round((planned_visited / total_planned * 100), 1) if total_planned > 0 else 0,
            "average_rating": round(avg_rating, 1) if avg_rating else None,
        }