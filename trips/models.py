from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class Trip(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trips",
        verbose_name="사용자"
    )
    title = models.CharField(
        max_length=100,
        verbose_name="여행 제목"
    )
    description = models.TextField(
        blank=True,
        verbose_name="설명"
    )
    start_date = models.DateField(
        verbose_name="시작일"
    )
    end_date = models.DateField(
        verbose_name="종료일"
    )
    thumbnail = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="썸네일 이미지"
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name="공개 여부"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    
    class Status(models.TextChoices):
        PLANNING = "planning", "계획 중"
        ONGOING = "ongoing", "여행 중"
        COMPLETED = "completed", "완료"
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        verbose_name="상태"
    )


    class Meta:
        verbose_name = "여행"
        verbose_name_plural = "여행 목록"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.start_date} ~ {self.end_date})"
    
    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1
    
    @property
    def destination_names(self):
        return list(self.destinations.values_list("name", flat=True))
    
    @property
    def total_budget(self):
        return self.budgets.aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")
    
    @property
    def total_expense(self):
        return self.expenses.aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")
    
    @property
    def budget_remaining(self):
        return self.total_budget - self.total_expense
    
    @property
    def budget_usage_percent(self):
        if self.total_budget == 0:
            return 0
        return round((self.total_expense / self.total_budget) * 100, 1)
    
    @property
    def total_estimated_cost(self):
        return self.destinations.aggregate(
            total=models.Sum("estimated_cost")
        )["total"] or Decimal("0")


class Destination(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="destinations",
        verbose_name="여행"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="장소명"
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="주소"
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="위도"
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="경도"
    )
    day = models.PositiveIntegerField(
        default=1,
        verbose_name="일차"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="순서"
    )
    planned_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="예정 방문 시간"
    )
    estimated_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="예상 체류 시간(분)"
    )
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="예상 비용"
    )
    memo = models.TextField(
        blank=True,
        verbose_name="메모"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    
    class Category(models.TextChoices):
        ATTRACTION = "attraction", "관광지"
        RESTAURANT = "restaurant", "음식점"
        CAFE = "cafe", "카페"
        ACCOMMODATION = "accommodation", "숙소"
        SHOPPING = "shopping", "쇼핑"
        TRANSPORT = "transport", "교통"
        OTHER = "other", "기타"
    
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.ATTRACTION,
        verbose_name="카테고리"
    )

    class Meta:
        verbose_name = "여행지"
        verbose_name_plural = "여행지 목록"
        ordering = ["day", "order"]

    def __str__(self):
        return f"[{self.trip.title}] Day{self.day} - {self.name}"


class DayPlan(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="day_plans",
        verbose_name="여행"
    )
    day_number = models.PositiveIntegerField(
        verbose_name="일차"
    )
    date = models.DateField(
        verbose_name="날짜"
    )
    memo = models.TextField(
        blank=True,
        verbose_name="메모"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")


    class Meta:
        verbose_name = "일자별 계획"
        verbose_name_plural = "일자별 계획 목록"
        ordering = ["day_number"]
        unique_together = ("trip", "day_number")

    def __str__(self):
        return f"[{self.trip.title}] Day {self.day_number}"
    
    @property
    def destinations(self):
        """해당 일차의 여행지 목록"""
        return self.trip.destinations.filter(day=self.day_number)
    
    @property
    def estimated_cost(self):
        """해당 일차 예상 비용"""
        return self.destinations.aggregate(
            total=models.Sum("estimated_cost")
        )["total"] or Decimal("0")


class BudgetCategory(models.TextChoices):
    """예산/지출 카테고리"""
    TRANSPORT = "transport", "교통"
    ACCOMMODATION = "accommodation", "숙소"
    FOOD = "food", "식비"
    ATTRACTION = "attraction", "관광/입장료"
    SHOPPING = "shopping", "쇼핑"
    OTHER = "other", "기타"


class Budget(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="budgets",
        verbose_name="여행"
    )
    category = models.CharField(
        max_length=20,
        choices=BudgetCategory.choices,
        verbose_name="카테고리"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="예산 금액"
    )
    memo = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="메모"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "예산"
        verbose_name_plural = "예산 목록"
        unique_together = ("trip", "category")
        ordering = ["category"]

    def __str__(self):
        return f"[{self.trip.title}] {self.get_category_display()}: {self.amount:,}원"
    
    @property
    def spent_amount(self):
        """해당 카테고리 지출 금액"""
        return self.trip.expenses.filter(
            category=self.category
        ).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")
    
    @property
    def remaining_amount(self):
        """남은 금액"""
        return self.amount - self.spent_amount
    
    @property
    def usage_percent(self):
        """사용률 (%)"""
        if self.amount == 0:
            return 0
        return round((self.spent_amount / self.amount) * 100, 1)


class Expense(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="expenses",
        verbose_name="여행"
    )
    category = models.CharField(
        max_length=20,
        choices=BudgetCategory.choices,
        verbose_name="카테고리"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="금액"
    )
    description = models.CharField(
        max_length=200,
        verbose_name="내용"
    )
    expense_date = models.DateField(
        verbose_name="지출 날짜"
    )
    expense_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="지출 시간"
    )
    day_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="일차"
    )
    destination = models.ForeignKey(
        Destination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        verbose_name="연결된 여행지"
    )


    class PaymentMethod(models.TextChoices):
        CASH = "cash", "현금"
        CARD = "card", "카드"
        OTHER = "other", "기타"
    
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CARD,
        verbose_name="결제 수단"
    )
    receipt_image = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="영수증 이미지"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "지출"
        verbose_name_plural = "지출 목록"
        ordering = ["expense_date", "expense_time"]

    def __str__(self):
        return f"[{self.trip.title}] {self.description}: {self.amount:,}원"
    
    def save(self, *args, **kwargs):
        if self.day_number is None and self.expense_date:
            delta = (self.expense_date - self.trip.start_date).days
            if delta >= 0:
                self.day_number = delta + 1
        super().save(*args, **kwargs)


class TripLog(models.Model):
    """
    여행 기록 모델
    
    실제 방문한 장소 및 경험 기록
    """
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="여행"
    )
    destination = models.ForeignKey(
        Destination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
        verbose_name="연결된 계획"
    )
    place_name = models.CharField(
        max_length=100,
        verbose_name="장소명"
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="주소"
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="위도"
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="경도"
    )
    visit_date = models.DateField(
        verbose_name="방문 날짜"
    )
    visit_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="방문 시간"
    )
    day_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="일차"
    )
    actual_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="실제 체류 시간(분)"
    )
    rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="평점 (1-5)"
    )
    review = models.TextField(
        blank=True,
        verbose_name="후기"
    )


    class VisitStatus(models.TextChoices):
        PLANNED = "planned", "계획대로 방문"
        UNPLANNED = "unplanned", "계획에 없던 방문"
        SKIPPED = "skipped", "계획했지만 미방문"
    
    visit_status = models.CharField(
        max_length=20,
        choices=VisitStatus.choices,
        default=VisitStatus.PLANNED,
        verbose_name="방문 상태"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "여행 기록"
        verbose_name_plural = "여행 기록 목록"
        ordering = ["visit_date", "visit_time"]

    def __str__(self):
        return f"[{self.trip.title}] {self.place_name}"
    
    def save(self, *args, **kwargs):
        if self.day_number is None and self.visit_date:
            delta = (self.visit_date - self.trip.start_date).days
            if delta >= 0:
                self.day_number = delta + 1
        
        if self.destination and not self.place_name:
            self.place_name = self.destination.name
            self.address = self.destination.address
            self.latitude = self.destination.latitude
            self.longitude = self.destination.longitude
        
        super().save(*args, **kwargs)


class TripLogPhoto(models.Model):
    """
    여행 기록 사진 모델
    """
    log = models.ForeignKey(
        TripLog,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="여행 기록"
    )
    image_url = models.URLField(
        max_length=500,
        verbose_name="이미지 URL"
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="설명"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="순서"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        verbose_name = "여행 사진"
        verbose_name_plural = "여행 사진 목록"
        ordering = ["order"]

    def __str__(self):
        return f"[{self.log.place_name}] 사진 {self.order + 1}"