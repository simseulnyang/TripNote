# trips/admin.py
from django.contrib import admin
from .models import Trip, Destination, DayPlan, Budget, Expense, TripLog, TripLogPhoto


class DestinationInline(admin.TabularInline):
    model = Destination
    extra = 0
    fields = ("day", "order", "name", "category", "estimated_cost", "memo")


class DayPlanInline(admin.TabularInline):
    model = DayPlan
    extra = 0
    fields = ("day_number", "date", "memo")
    readonly_fields = ("day_number", "date")


class BudgetInline(admin.TabularInline):
    model = Budget
    extra = 0
    fields = ("category", "amount", "memo")


class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 0
    fields = ("expense_date", "category", "description", "amount", "payment_method")


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "user", "start_date", "end_date",
        "duration_days", "status", "total_budget_display", "total_expense_display",
        "budget_usage_display", "created_at",
    )
    list_filter = ("status", "is_public", "created_at")
    search_fields = ("title", "user__email")
    date_hierarchy = "start_date"
    ordering = ("-created_at",)
    
    fieldsets = (
        (None, {"fields": ("user", "title", "description")}),
        ("일정", {"fields": ("start_date", "end_date", "status")}),
        ("설정", {"fields": ("thumbnail", "is_public")}),
    )
    
    readonly_fields = ("created_at", "updated_at")
    inlines = [BudgetInline, DestinationInline, DayPlanInline, ExpenseInline]
    
    def duration_days(self, obj):
        return obj.duration_days
    duration_days.short_description = "기간"
    
    def total_budget_display(self, obj):
        return f"{obj.total_budget:,.0f}원"
    total_budget_display.short_description = "총 예산"
    
    def total_expense_display(self, obj):
        return f"{obj.total_expense:,.0f}원"
    total_expense_display.short_description = "총 지출"
    
    def budget_usage_display(self, obj):
        return f"{obj.budget_usage_percent}%"
    budget_usage_display.short_description = "사용률"


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "day", "order", "name", "category", "estimated_cost")
    list_filter = ("category", "day")
    search_fields = ("name", "trip__title")
    ordering = ("trip", "day", "order")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "category", "amount_display", "spent_display", "remaining_display", "usage_display")
    list_filter = ("category",)
    search_fields = ("trip__title",)
    
    def amount_display(self, obj):
        return f"{obj.amount:,.0f}원"
    amount_display.short_description = "예산"
    
    def spent_display(self, obj):
        return f"{obj.spent_amount:,.0f}원"
    spent_display.short_description = "지출"
    
    def remaining_display(self, obj):
        return f"{obj.remaining_amount:,.0f}원"
    remaining_display.short_description = "잔액"
    
    def usage_display(self, obj):
        return f"{obj.usage_percent}%"
    usage_display.short_description = "사용률"


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "expense_date", "day_number", "category", "description", "amount_display", "payment_method")
    list_filter = ("category", "payment_method", "expense_date")
    search_fields = ("description", "trip__title")
    date_hierarchy = "expense_date"
    ordering = ("-expense_date",)
    
    def amount_display(self, obj):
        return f"{obj.amount:,.0f}원"
    amount_display.short_description = "금액"


class TripLogPhotoInline(admin.TabularInline):
    model = TripLogPhoto
    extra = 0
    fields = ("order", "image_url", "caption")


@admin.register(TripLog)
class TripLogAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "visit_date", "day_number", "place_name", "visit_status", "rating")
    list_filter = ("visit_status", "rating", "visit_date")
    search_fields = ("place_name", "trip__title")
    date_hierarchy = "visit_date"
    ordering = ("-visit_date",)
    inlines = [TripLogPhotoInline]


@admin.register(DayPlan)
class DayPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "day_number", "date")
    search_fields = ("trip__title",)
    ordering = ("trip", "day_number")