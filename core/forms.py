from django import forms
from .models import Unit, OwnerDeduction, Owner


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ['name', 'floor', 'position', 'is_active', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class OwnerDeductionForm(forms.ModelForm):
    class Meta:
        model = OwnerDeduction
        fields = ['owner', 'month', 'description', 'amount']
        widgets = {
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'month': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
