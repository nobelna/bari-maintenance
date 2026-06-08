from django.contrib import admin
from .models import (
    Distribution, ExpenseCategory, MonthlyExpense, Owner,
    OwnerDeduction, RentalIncome, Unit,
)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'floor', 'position', 'is_active']
    list_filter = ['floor', 'is_active']
    search_fields = ['name']
    list_editable = ['is_active']


@admin.register(RentalIncome)
class RentalIncomeAdmin(admin.ModelAdmin):
    list_display = ['unit', 'month', 'amount', 'is_paid']
    list_filter = ['month', 'is_paid', 'unit__floor']
    search_fields = ['unit__name']
    date_hierarchy = 'month'


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_recurring']
    list_editable = ['order', 'is_recurring']


@admin.register(MonthlyExpense)
class MonthlyExpenseAdmin(admin.ModelAdmin):
    list_display = ['category', 'month', 'amount', 'notes']
    list_filter = ['month', 'category']
    date_hierarchy = 'month'


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_resident', 'phone', 'order']
    list_editable = ['order']


@admin.register(OwnerDeduction)
class OwnerDeductionAdmin(admin.ModelAdmin):
    list_display = ['owner', 'month', 'description', 'amount']
    list_filter = ['month', 'owner']


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = ['owner', 'month', 'gross_amount', 'total_deductions', 'net_amount']
    list_filter = ['month', 'owner']
    date_hierarchy = 'month'
