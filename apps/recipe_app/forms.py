
from django import forms
from .models import RecipeReport

class RecipeReportForm(forms.ModelForm):
    class Meta:
        model = RecipeReport
        fields = ['title', 'message', 'type','recipe','user']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter the title'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter the description of the problem you are facing'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'recipe': forms.Select(attrs={'class': 'form-select'}),
            'user': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': 'Title',
            'message': 'Message',
            'type': 'Error Type',
        }
