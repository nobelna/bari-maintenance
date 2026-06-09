from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Rental Income
    path('rental-income/', views.rental_income, name='rental_income'),
    path('rental-income/save/', views.rental_income_save, name='rental_income_save'),

    # Expenses
    path('expenses/', views.expenses, name='expenses'),
    path('expenses/save/', views.expenses_save, name='expenses_save'),

    # Distribution
    path('distribution/', views.distribution, name='distribution'),
    path('distribution/save/', views.distribution_save, name='distribution_save'),

    # Deductions
    path('deductions/add/', views.deduction_add, name='deduction_add'),
    path('deductions/<int:pk>/delete/', views.deduction_delete, name='deduction_delete'),

    # Expense Categories
    path('expenses/categories/', views.expense_categories, name='expense_categories'),
    path('expenses/categories/add/', views.expense_category_create, name='expense_category_create'),
    path('expenses/categories/<int:pk>/edit/', views.expense_category_edit, name='expense_category_edit'),
    path('expenses/categories/<int:pk>/delete/', views.expense_category_delete, name='expense_category_delete'),

    # Units
    path('units/', views.units, name='units'),
    path('units/add/', views.unit_create, name='unit_create'),
    path('units/<int:pk>/edit/', views.unit_edit, name='unit_edit'),

    # Reports
    path('report/', views.report, name='report'),
    path('report/xlsx/', views.report_xlsx, name='report_xlsx'),
]
