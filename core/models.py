from django.db import models


class Unit(models.Model):
    FLOOR_CHOICES = [
        ('7th_roof', '7th Floor / Roof'),
        ('6th', '6th Floor'),
        ('5th', '5th Floor'),
        ('4th', '4th Floor'),
        ('3rd', '3rd Floor'),
        ('2nd', '2nd Floor'),
        ('1st', '1st Floor'),
        ('garage', 'Garage'),
    ]
    POSITION_CHOICES = [
        ('front', 'Front'),
        ('back', 'Back'),
        ('side1', 'Side 1'),
        ('side2', 'Side 2'),
        ('partial', 'Partial'),
        ('full', 'Full'),
        ('garage', 'Garage'),
        ('roof', 'Roof Only'),
    ]

    name = models.CharField(max_length=120)
    floor = models.CharField(max_length=20, choices=FLOOR_CHOICES)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['floor', 'position', 'name']

    def __str__(self):
        return self.name


class RentalIncome(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='incomes')
    month = models.DateField(help_text='First day of the month')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['unit', 'month']
        ordering = ['-month', 'unit__floor', 'unit__position']

    def __str__(self):
        return f"{self.unit.name} – {self.month.strftime('%B %Y')}: ৳{self.amount:,.0f}"


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=120)
    is_recurring = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name


class MonthlyExpense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='expenses')
    month = models.DateField(help_text='First day of the month')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['category', 'month']
        ordering = ['-month', 'category__order']

    def __str__(self):
        return f"{self.category.name} – {self.month.strftime('%B %Y')}: ৳{self.amount:,.0f}"


class Owner(models.Model):
    name = models.CharField(max_length=120)
    is_resident = models.BooleanField(
        default=False,
        help_text='Lives in the building (may have monthly deductions)',
    )
    phone = models.CharField(max_length=20, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class OwnerDeduction(models.Model):
    """Monthly deductions for a resident owner (house rent, electricity, bua, dish bill…)."""

    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='deductions')
    month = models.DateField()
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['-month', 'owner', 'description']

    def __str__(self):
        return f"{self.owner.name} – {self.description}: ৳{self.amount:,.0f}"


class Distribution(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='distributions')
    month = models.DateField()
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['owner', 'month']
        ordering = ['-month', 'owner__order']

    def __str__(self):
        return f"{self.owner.name} – {self.month.strftime('%B %Y')}: ৳{self.net_amount:,.0f}"
