import calendar
import datetime
import io
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OwnerDeductionForm, UnitForm
from .models import (
    Distribution, ExpenseCategory, MonthlyExpense, Owner,
    OwnerDeduction, RentalIncome, Unit,
)

# ─── helpers ────────────────────────────────────────────────────────────────

def _month_from_request(request) -> datetime.date:
    """Return the first day of the month from GET params; default = this month."""
    today = datetime.date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if not (1 <= month <= 12 and 2000 <= year <= 2100):
            raise ValueError
        return datetime.date(year, month, 1)
    except (ValueError, TypeError):
        return datetime.date(today.year, today.month, 1)


def _adjacent_month(d: datetime.date, delta: int) -> datetime.date:
    """Shift d by delta months (±)."""
    month = d.month + delta
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return datetime.date(year, month, 1)


def _month_summary(month_date: datetime.date) -> dict:
    total_income = (
        RentalIncome.objects.filter(month=month_date)
        .aggregate(v=Sum('amount'))['v'] or Decimal('0')
    )
    total_expense = (
        MonthlyExpense.objects.filter(month=month_date)
        .aggregate(v=Sum('amount'))['v'] or Decimal('0')
    )
    net = total_income - total_expense
    num_owners = Owner.objects.count() or 4
    per_person = (net / num_owners).quantize(Decimal('0.01'))
    return {
        'total_income': total_income,
        'total_expense': total_expense,
        'net': net,
        'per_person': per_person,
        'num_owners': num_owners,
    }


def _nav_context(month_date: datetime.date) -> dict:
    return {
        'month_date': month_date,
        'prev_month': _adjacent_month(month_date, -1),
        'next_month': _adjacent_month(month_date, 1),
    }


# ─── dashboard ──────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    month_date = _month_from_request(request)
    summary = _month_summary(month_date)

    # Last 6 months for quick navigation
    recent_months = [_adjacent_month(month_date, -i) for i in range(5, -1, -1)]

    # Rental income snapshot
    income_qs = RentalIncome.objects.filter(month=month_date).select_related('unit')

    # Expense snapshot
    expense_qs = MonthlyExpense.objects.filter(month=month_date).select_related('category')

    # Distribution snapshot
    dist_qs = Distribution.objects.filter(month=month_date).select_related('owner')

    ctx = {
        **_nav_context(month_date),
        **summary,
        'recent_months': recent_months,
        'incomes': income_qs,
        'expenses': expense_qs,
        'distributions': dist_qs,
    }
    return render(request, 'core/dashboard.html', ctx)


# ─── rental income ───────────────────────────────────────────────────────────

@login_required
def rental_income(request):
    month_date = _month_from_request(request)
    units = Unit.objects.filter(is_active=True)

    income_map = {
        ri.unit_id: ri
        for ri in RentalIncome.objects.filter(month=month_date)
    }

    rows = [{'unit': u, 'income': income_map.get(u.id)} for u in units]
    total = sum(ri.amount for ri in income_map.values())

    ctx = {
        **_nav_context(month_date),
        'rows': rows,
        'total': total,
    }
    return render(request, 'core/rental_income.html', ctx)


@login_required
def rental_income_save(request):
    if request.method != 'POST':
        return redirect('rental_income')

    try:
        month_date = datetime.date.fromisoformat(request.POST.get('month', ''))
    except ValueError:
        messages.error(request, 'Invalid month value.')
        return redirect('rental_income')

    for unit in Unit.objects.filter(is_active=True):
        raw = request.POST.get(f'amount_{unit.id}', '').strip()
        if raw == '':
            continue
        try:
            amount = Decimal(raw)
        except InvalidOperation:
            messages.warning(request, f'Invalid amount for {unit.name} — skipped.')
            continue
        notes = request.POST.get(f'notes_{unit.id}', '').strip()
        is_paid = request.POST.get(f'paid_{unit.id}') == 'on'
        RentalIncome.objects.update_or_create(
            unit=unit, month=month_date,
            defaults={'amount': amount, 'notes': notes, 'is_paid': is_paid},
        )

    messages.success(request, f'Rental income for {month_date.strftime("%B %Y")} saved.')
    return redirect(f'/rental-income/?year={month_date.year}&month={month_date.month}')


# ─── expenses ────────────────────────────────────────────────────────────────

@login_required
def expenses(request):
    month_date = _month_from_request(request)
    categories = ExpenseCategory.objects.all()

    expense_map = {
        e.category_id: e
        for e in MonthlyExpense.objects.filter(month=month_date).select_related('category')
    }

    rows = [{'category': c, 'expense': expense_map.get(c.id)} for c in categories]
    total = sum(e.amount for e in expense_map.values())

    ctx = {
        **_nav_context(month_date),
        'rows': rows,
        'total': total,
    }
    return render(request, 'core/expenses.html', ctx)


@login_required
def expenses_save(request):
    if request.method != 'POST':
        return redirect('expenses')

    try:
        month_date = datetime.date.fromisoformat(request.POST.get('month', ''))
    except ValueError:
        messages.error(request, 'Invalid month value.')
        return redirect('expenses')

    for cat in ExpenseCategory.objects.all():
        raw = request.POST.get(f'amount_{cat.id}', '').strip()
        notes = request.POST.get(f'notes_{cat.id}', '').strip()
        if raw == '':
            # Remove existing record if user cleared it
            MonthlyExpense.objects.filter(category=cat, month=month_date).delete()
            continue
        try:
            amount = Decimal(raw)
        except InvalidOperation:
            messages.warning(request, f'Invalid amount for {cat.name} — skipped.')
            continue
        MonthlyExpense.objects.update_or_create(
            category=cat, month=month_date,
            defaults={'amount': amount, 'notes': notes},
        )

    messages.success(request, f'Expenses for {month_date.strftime("%B %Y")} saved.')
    return redirect(f'/expenses/?year={month_date.year}&month={month_date.month}')


# ─── distribution ────────────────────────────────────────────────────────────

@login_required
def distribution(request):
    month_date = _month_from_request(request)
    summary = _month_summary(month_date)

    owners = Owner.objects.all()

    # Deductions per owner
    deduction_qs = OwnerDeduction.objects.filter(month=month_date).select_related('owner')
    deduction_map: dict[int, list] = {}
    for d in deduction_qs:
        deduction_map.setdefault(d.owner_id, []).append(d)

    # Saved distribution records
    dist_map = {
        d.owner_id: d
        for d in Distribution.objects.filter(month=month_date)
    }

    rows = []
    for owner in owners:
        owner_deductions = deduction_map.get(owner.id, [])
        total_ded = sum(d.amount for d in owner_deductions)
        net = summary['per_person'] - total_ded
        rows.append({
            'owner': owner,
            'gross': summary['per_person'],
            'deduction_list': owner_deductions,
            'total_deductions': total_ded,
            'net': net,
            'saved': dist_map.get(owner.id),
        })

    ctx = {
        **_nav_context(month_date),
        **summary,
        'rows': rows,
    }
    return render(request, 'core/distribution.html', ctx)


@login_required
def distribution_save(request):
    if request.method != 'POST':
        return redirect('distribution')

    try:
        month_date = datetime.date.fromisoformat(request.POST.get('month', ''))
    except ValueError:
        messages.error(request, 'Invalid month value.')
        return redirect('distribution')

    summary = _month_summary(month_date)

    for owner in Owner.objects.all():
        deductions_total = (
            OwnerDeduction.objects.filter(owner=owner, month=month_date)
            .aggregate(v=Sum('amount'))['v'] or Decimal('0')
        )
        net = summary['per_person'] - deductions_total
        notes = request.POST.get(f'notes_{owner.id}', '').strip()
        Distribution.objects.update_or_create(
            owner=owner, month=month_date,
            defaults={
                'gross_amount': summary['per_person'],
                'total_deductions': deductions_total,
                'net_amount': net,
                'notes': notes,
            },
        )

    messages.success(request, f'Distribution for {month_date.strftime("%B %Y")} saved.')
    return redirect(f'/distribution/?year={month_date.year}&month={month_date.month}')


# ─── deductions ──────────────────────────────────────────────────────────────

@login_required
def deduction_add(request):
    month_date = _month_from_request(request)

    if request.method == 'POST':
        form = OwnerDeductionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Deduction added.')
            d = form.instance
            return redirect(
                f'/distribution/?year={d.month.year}&month={d.month.month}'
            )
    else:
        form = OwnerDeductionForm(initial={'month': month_date})

    return render(request, 'core/deduction_form.html', {
        **_nav_context(month_date),
        'form': form,
        'title': 'Add Deduction',
    })


@login_required
def deduction_delete(request, pk):
    ded = get_object_or_404(OwnerDeduction, pk=pk)
    month = ded.month
    if request.method == 'POST':
        ded.delete()
        messages.success(request, 'Deduction removed.')
    return redirect(f'/distribution/?year={month.year}&month={month.month}')


# ─── units ───────────────────────────────────────────────────────────────────

@login_required
def units(request):
    units_qs = Unit.objects.all()
    return render(request, 'core/units.html', {'units': units_qs})


@login_required
def unit_create(request):
    if request.method == 'POST':
        form = UnitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit created.')
            return redirect('units')
    else:
        form = UnitForm()
    return render(request, 'core/unit_form.html', {'form': form, 'title': 'Add Unit'})


@login_required
def unit_edit(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    if request.method == 'POST':
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit updated.')
            return redirect('units')
    else:
        form = UnitForm(instance=unit)
    return render(request, 'core/unit_form.html', {
        'form': form, 'title': 'Edit Unit', 'unit': unit,
    })


# ─── report helpers ──────────────────────────────────────────────────────────

FLOOR_ORDER = ['7th_roof', '6th', '5th', '4th', '3rd', '2nd', '1st', 'garage']
SINGLE_FLOORS = {'7th_roof', 'garage'}

# Positions treated as "left" (first column) vs "right" (second column)
LEFT_POSITIONS = {'front', 'side1', 'roof', 'full', 'partial', 'garage'}


def _build_income_rows(month_date):
    """
    Returns a list of dicts representing the paired-unit layout used in the Excel.
    Each row has: left_unit, left_amount, right_unit, right_amount, subtotal
    """
    income_map = {
        ri.unit_id: ri.amount
        for ri in RentalIncome.objects.filter(month=month_date).select_related('unit')
    }

    # Group active units by floor
    floor_groups: dict[str, list] = {}
    for unit in Unit.objects.filter(is_active=True).order_by('floor', 'position', 'name'):
        floor_groups.setdefault(unit.floor, []).append(unit)

    rows = []
    for floor in FLOOR_ORDER:
        group = floor_groups.get(floor, [])
        if not group:
            continue

        if floor in SINGLE_FLOORS:
            # Single-column row
            u = group[0]
            amt = income_map.get(u.id, Decimal('0'))
            rows.append({
                'left_name': u.name, 'left_amount': amt,
                'right_name': '', 'right_amount': None,
                'subtotal': amt,
                'is_single': True,
            })
            for u in group[1:]:
                amt = income_map.get(u.id, Decimal('0'))
                rows.append({
                    'left_name': u.name, 'left_amount': amt,
                    'right_name': '', 'right_amount': None,
                    'subtotal': amt,
                    'is_single': True,
                })
        else:
            # Pair units: try front/left vs back/right
            left = [u for u in group if u.position in LEFT_POSITIONS]
            right = [u for u in group if u.position not in LEFT_POSITIONS]

            # If both sides missing, treat all as left singles
            if not right:
                for u in left:
                    amt = income_map.get(u.id, Decimal('0'))
                    rows.append({
                        'left_name': u.name, 'left_amount': amt,
                        'right_name': '', 'right_amount': None,
                        'subtotal': amt,
                        'is_single': True,
                    })
            else:
                # Zip pairs; if uneven, extras appear as singles
                for l_unit, r_unit in zip(left, right):
                    la = income_map.get(l_unit.id, Decimal('0'))
                    ra = income_map.get(r_unit.id, Decimal('0'))
                    rows.append({
                        'left_name': l_unit.name, 'left_amount': la,
                        'right_name': r_unit.name, 'right_amount': ra,
                        'subtotal': la + ra,
                        'is_single': False,
                    })
                for u in left[len(right):] + right[len(left):]:
                    amt = income_map.get(u.id, Decimal('0'))
                    rows.append({
                        'left_name': u.name, 'left_amount': amt,
                        'right_name': '', 'right_amount': None,
                        'subtotal': amt,
                        'is_single': True,
                    })
    return rows


def _build_report_context(month_date):
    summary = _month_summary(month_date)

    income_rows = _build_income_rows(month_date)
    total_income = sum(r['subtotal'] for r in income_rows)

    expense_qs = MonthlyExpense.objects.filter(month=month_date).select_related('category')
    total_expense = sum(e.amount for e in expense_qs)

    owners = Owner.objects.all()
    deduction_qs = OwnerDeduction.objects.filter(month=month_date).select_related('owner')
    deduction_map: dict[int, list] = {}
    for d in deduction_qs:
        deduction_map.setdefault(d.owner_id, []).append(d)

    per_person = ((total_income - total_expense) / (owners.count() or 4)).quantize(Decimal('0.01'))

    dist_rows = []
    for owner in owners:
        owner_deds = deduction_map.get(owner.id, [])
        total_ded = sum(d.amount for d in owner_deds)
        net = per_person - total_ded
        dist_rows.append({
            'owner': owner,
            'gross': per_person,
            'deductions': owner_deds,
            'total_deductions': total_ded,
            'net': net,
        })

    return {
        **_nav_context(month_date),
        'income_rows': income_rows,
        'total_income': total_income,
        'expenses': expense_qs,
        'total_expense': total_expense,
        'net': total_income - total_expense,
        'dist_rows': dist_rows,
        'per_person': per_person,
        'num_owners': owners.count(),
    }


# ─── report views ─────────────────────────────────────────────────────────────

@login_required
def report(request):
    month_date = _month_from_request(request)
    ctx = _build_report_context(month_date)
    return render(request, 'core/report.html', ctx)


@login_required
def report_xlsx(request):
    """Generate and download a formatted Excel report matching the original spreadsheet."""
    import openpyxl
    from openpyxl.styles import (
        Alignment, Border, Font, PatternFill, Side,
    )
    from openpyxl.utils import get_column_letter

    month_date = _month_from_request(request)
    ctx = _build_report_context(month_date)
    month_label = month_date.strftime('%B %Y')

    wb = openpyxl.Workbook()

    # ── colour palette ──────────────────────────────────────────────────────
    GREEN  = PatternFill('solid', fgColor='1E7E34')
    RED    = PatternFill('solid', fgColor='C82333')
    BLUE   = PatternFill('solid', fgColor='1055A0')
    LGREY  = PatternFill('solid', fgColor='F2F2F2')
    LGREEN = PatternFill('solid', fgColor='D4EDDA')
    LRED   = PatternFill('solid', fgColor='F8D7DA')
    LBLUE  = PatternFill('solid', fgColor='D0E4F7')

    WHITE_BOLD = Font(bold=True, color='FFFFFF')
    BOLD       = Font(bold=True)
    NORMAL     = Font()

    thin = Side(style='thin', color='BBBBBB')
    BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

    CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
    RIGHT  = Alignment(horizontal='right', vertical='center')
    LEFT_A = Alignment(horizontal='left', vertical='center', wrap_text=True)

    def hdr(ws, cell, value, fill, font=WHITE_BOLD, align=CENTER):
        ws[cell] = value
        ws[cell].fill = fill
        ws[cell].font = font
        ws[cell].alignment = align
        ws[cell].border = BORDER

    def cell(ws, c, value, bold=False, fill=None, align=LEFT_A, num_fmt=None):
        ws[c] = value
        ws[c].font = BOLD if bold else NORMAL
        ws[c].alignment = align
        ws[c].border = BORDER
        if fill:
            ws[c].fill = fill
        if num_fmt:
            ws[c].number_format = num_fmt

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 1 – Rental Income
    # ════════════════════════════════════════════════════════════════════════
    ws1 = wb.active
    ws1.title = 'Rental Income'
    ws1.column_dimensions['A'].width = 26
    ws1.column_dimensions['B'].width = 14
    ws1.column_dimensions['C'].width = 26
    ws1.column_dimensions['D'].width = 14
    ws1.column_dimensions['E'].width = 14

    # Title
    ws1.merge_cells('A1:E1')
    ws1['A1'] = f'Monthly Rental Income of {month_label}'
    ws1['A1'].font = Font(bold=True, size=14)
    ws1['A1'].alignment = CENTER
    ws1['A1'].fill = GREEN
    ws1['A1'].font = Font(bold=True, size=14, color='FFFFFF')
    ws1.row_dimensions[1].height = 28

    # Headers row 3
    for col, label in [('A', 'Description'), ('B', 'Amount (Tk)'),
                        ('C', 'Description'), ('D', 'Amount (Tk)'), ('E', 'Subtotal')]:
        hdr(ws1, f'{col}3', label, GREEN)
    ws1.row_dimensions[3].height = 20

    row = 4
    for r in ctx['income_rows']:
        cell(ws1, f'A{row}', r['left_name'])
        cell(ws1, f'B{row}', float(r['left_amount']) if r['left_amount'] else '-', align=RIGHT, num_fmt='#,##0')
        if r['is_single']:
            cell(ws1, f'C{row}', '-')
            cell(ws1, f'D{row}', '-', align=RIGHT)
        else:
            cell(ws1, f'C{row}', r['right_name'])
            cell(ws1, f'D{row}', float(r['right_amount']) if r['right_amount'] else 0, align=RIGHT, num_fmt='#,##0')
        cell(ws1, f'E{row}', float(r['subtotal']), align=RIGHT, num_fmt='#,##0')
        ws1.row_dimensions[row].height = 18
        row += 1

    # Total row
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws1[f'{col}{row}'].fill = LGREEN
        ws1[f'{col}{row}'].border = BORDER
    ws1[f'A{row}'] = 'Total (Taka)'
    ws1[f'A{row}'].font = BOLD
    ws1[f'E{row}'] = float(ctx['total_income'])
    ws1[f'E{row}'].font = BOLD
    ws1[f'E{row}'].alignment = RIGHT
    ws1[f'E{row}'].number_format = '#,##0'
    ws1.row_dimensions[row].height = 20

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 2 – Expense
    # ════════════════════════════════════════════════════════════════════════
    ws2 = wb.create_sheet('Expense')
    ws2.column_dimensions['A'].width = 38
    ws2.column_dimensions['B'].width = 14
    ws2.column_dimensions['C'].width = 14
    ws2.column_dimensions['D'].width = 50

    ws2.merge_cells('A1:D1')
    ws2['A1'] = f'Monthly Expense – {month_label}'
    ws2['A1'].font = Font(bold=True, size=14, color='FFFFFF')
    ws2['A1'].fill = RED
    ws2['A1'].alignment = CENTER
    ws2.row_dimensions[1].height = 28

    for col, label in [('A', 'Monthly Expense'), ('B', 'Taka'),
                        ('C', 'Additional'), ('D', 'Comment')]:
        hdr(ws2, f'{col}2', label, RED)

    erow = 3
    for exp in ctx['expenses']:
        cell(ws2, f'A{erow}', exp.category.name)
        cell(ws2, f'B{erow}', float(exp.amount), align=RIGHT, num_fmt='#,##0')
        cell(ws2, f'C{erow}', '')
        cell(ws2, f'D{erow}', exp.notes or '')
        ws2.row_dimensions[erow].height = 18
        erow += 1

    # Total
    for col in ['A', 'B', 'C', 'D']:
        ws2[f'{col}{erow}'].fill = LRED
        ws2[f'{col}{erow}'].border = BORDER
    ws2[f'A{erow}'] = 'Total (Taka)'
    ws2[f'A{erow}'].font = BOLD
    ws2[f'B{erow}'] = float(ctx['total_expense'])
    ws2[f'B{erow}'].font = BOLD
    ws2[f'B{erow}'].alignment = RIGHT
    ws2[f'B{erow}'].number_format = '#,##0'
    ws2.row_dimensions[erow].height = 20

    # ════════════════════════════════════════════════════════════════════════
    # Sheet 3 – Distribution
    # ════════════════════════════════════════════════════════════════════════
    ws3 = wb.create_sheet('Distribution')
    ws3.column_dimensions['A'].width = 28
    ws3.column_dimensions['B'].width = 16
    ws3.column_dimensions['C'].width = 10
    ws3.column_dimensions['D'].width = 42
    ws3.column_dimensions['E'].width = 16

    ws3.merge_cells('A1:E1')
    ws3['A1'] = f'Monthly Distribution of {month_label}'
    ws3['A1'].font = Font(bold=True, size=14, color='FFFFFF')
    ws3['A1'].fill = BLUE
    ws3['A1'].alignment = CENTER
    ws3.row_dimensions[1].height = 28

    # Summary row
    ws3['A3'] = 'Total Rent after Expense'
    ws3['A3'].font = BOLD
    ws3['B3'] = float(ctx['net'])
    ws3['B3'].number_format = '#,##0'
    ws3['B3'].alignment = RIGHT
    ws3['C3'] = '(Taka)'
    ws3['D3'] = 'Expense per person'
    ws3['D3'].font = BOLD
    ws3['E3'] = 'Amount'
    ws3['E3'].font = BOLD
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws3[f'{col}3'].fill = LBLUE
        ws3[f'{col}3'].border = BORDER

    drow = 4
    for r in ctx['dist_rows']:
        ded_text = ', '.join(
            f"{d.description}-{int(d.amount):,}" for d in r['deductions']
        )
        if r['total_deductions']:
            ded_text += f" = Total {int(r['total_deductions']):,}"

        cell(ws3, f'A{drow}', r['owner'].name)
        cell(ws3, f'B{drow}', float(r['gross']), align=RIGHT, num_fmt='#,##0')
        cell(ws3, f'C{drow}', '(Taka)')
        cell(ws3, f'D{drow}', ded_text or '')
        cell(ws3, f'E{drow}', float(r['net']), align=RIGHT, num_fmt='#,##0')
        ws3[f'E{drow}'].font = BOLD
        ws3.row_dimensions[drow].height = 18
        drow += 1

    # Save to buffer
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"Bari_Maintenance_{month_date.strftime('%B_%Y')}.xlsx"
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
