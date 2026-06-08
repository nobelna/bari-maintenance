"""
Management command: seed_data
Populates the database with units, expense categories, owners, and
April 2026 data extracted directly from the Excel spreadsheet.
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import (
    Distribution, ExpenseCategory, MonthlyExpense, Owner,
    OwnerDeduction, RentalIncome, Unit,
)

APRIL_2026 = datetime.date(2026, 4, 1)

UNITS = [
    # (name, floor, position)
    ('Roof (7th floor Partial)', '7th_roof', 'partial'),
    ('6th Floor Front',          '6th',      'front'),
    ('6th Floor Back',           '6th',      'back'),
    ('5th Floor Front',          '5th',      'front'),
    ('5th Floor Back',           '5th',      'back'),
    ('4th Floor Front',          '4th',      'front'),
    ('4th Floor Back (Partial)', '4th',      'partial'),
    ('3rd Floor Front',          '3rd',      'front'),
    ('3rd Floor Back',           '3rd',      'back'),
    ('2nd Floor Front',          '2nd',      'front'),
    ('2nd Floor Back',           '2nd',      'back'),
    ('1st Floor Side 1',         '1st',      'side1'),
    ('1st Floor Side 2',         '1st',      'side2'),
    ('Garage',                   'garage',   'garage'),
]

# April 2026 rent amounts (same order as UNITS)
APRIL_RENTS = [
    9000, 17000, 18000, 17300, 19000,
    17000, 8000, 7000, 0, 17000,
    19000, 13000, 12000, 3200,
]

EXPENSE_CATEGORIES = [
    # (name, order, is_recurring)
    ('CareTaker Salary',                     1, True),
    ('Ajimpur Expense',                      2, True),
    ('Masjid',                               3, True),
    ('Mohanagar Project Housing Society',    4, True),
    ('Additional Cost',                      5, False),
    ('Electricity Bill (Motor/Stair/Roof)',  6, True),
    ('City Corporation Tax',                 7, True),
    ('Maintenance',                          8, True),
]

# April 2026 expense amounts (same order)
APRIL_EXPENSES = [
    (13000, ''),
    (2000,  ''),
    (1000,  ''),
    (500,   ''),
    (3300,  'Water pipe cleaning 1000, Net bill 1000, Mizan 300, Cleaning material 1000'),
    (5000,  ''),
    (3300,  ''),
    (5000,  ''),
]

OWNERS = [
    # (name, is_resident, order)
    ('Nahidul Islam',           False, 1),
    ('Mohammad Moshiur Rahman', False, 2),
    ('Md Nishadul Islam',       True,  3),
    ('Naimul Islam Nobel',      False, 4),
]

# April 2026 deductions per owner  {owner_name: [(description, amount), ...]}
APRIL_DEDUCTIONS = {
    'Md Nishadul Islam': [
        ('House Rent',  17000),
        ('Electricity',  1150),
        ('Bua (Maid)',   1000),
        ('Dish Bill',    1700),
    ],
    'Mohammad Moshiur Rahman': [
        ('Other',  550),   # net was 35,300 in the Excel (gross 35,850 - 550)
    ],
}


class Command(BaseCommand):
    help = 'Seed the database with units, categories, owners, and April 2026 data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Delete all existing data before seeding.',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting existing data…')
            Distribution.objects.all().delete()
            OwnerDeduction.objects.all().delete()
            MonthlyExpense.objects.all().delete()
            RentalIncome.objects.all().delete()
            Owner.objects.all().delete()
            ExpenseCategory.objects.all().delete()
            Unit.objects.all().delete()

        # ── Units ────────────────────────────────────────────────────────────
        self.stdout.write('Creating units…')
        unit_objs = []
        for name, floor, position in UNITS:
            obj, created = Unit.objects.get_or_create(
                name=name,
                defaults={'floor': floor, 'position': position, 'is_active': True},
            )
            unit_objs.append(obj)
            if created:
                self.stdout.write(f'  + Unit: {name}')

        # ── Expense categories ────────────────────────────────────────────────
        self.stdout.write('Creating expense categories…')
        cat_objs = []
        for name, order, recurring in EXPENSE_CATEGORIES:
            obj, created = ExpenseCategory.objects.get_or_create(
                name=name,
                defaults={'order': order, 'is_recurring': recurring},
            )
            cat_objs.append(obj)
            if created:
                self.stdout.write(f'  + Category: {name}')

        # ── Owners ───────────────────────────────────────────────────────────
        self.stdout.write('Creating owners…')
        owner_objs = []
        for name, is_resident, order in OWNERS:
            obj, created = Owner.objects.get_or_create(
                name=name,
                defaults={'is_resident': is_resident, 'order': order},
            )
            owner_objs.append(obj)
            if created:
                self.stdout.write(f'  + Owner: {name}')

        # ── April 2026 rental income ─────────────────────────────────────────
        self.stdout.write(f'Seeding rental income for {APRIL_2026.strftime("%B %Y")}…')
        for unit, amount in zip(unit_objs, APRIL_RENTS):
            ri, _ = RentalIncome.objects.update_or_create(
                unit=unit, month=APRIL_2026,
                defaults={'amount': Decimal(amount), 'is_paid': True},
            )
            self.stdout.write(f'  ৳{amount:,} → {unit.name}')

        # ── April 2026 expenses ───────────────────────────────────────────────
        self.stdout.write(f'Seeding expenses for {APRIL_2026.strftime("%B %Y")}…')
        for cat, (amount, notes) in zip(cat_objs, APRIL_EXPENSES):
            MonthlyExpense.objects.update_or_create(
                category=cat, month=APRIL_2026,
                defaults={'amount': Decimal(amount), 'notes': notes},
            )
            self.stdout.write(f'  ৳{amount:,} → {cat.name}')

        # ── April 2026 deductions per owner ──────────────────────────────────
        for owner in owner_objs:
            owner_deds = APRIL_DEDUCTIONS.get(owner.name, [])
            if owner_deds:
                self.stdout.write(f'Seeding deductions for {owner.name}…')
                for desc, amount in owner_deds:
                    OwnerDeduction.objects.update_or_create(
                        owner=owner, month=APRIL_2026, description=desc,
                        defaults={'amount': Decimal(amount)},
                    )
                    self.stdout.write(f'  – {desc}: ৳{amount:,}')

        # ── Superuser ────────────────────────────────────────────────────────
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin', password='admin1234', email='admin@bari.local',
            )
            self.stdout.write(
                self.style.WARNING('Superuser created — username: admin / password: admin1234')
            )

        self.stdout.write(self.style.SUCCESS('\nSeed complete! Run: python manage.py runserver'))
