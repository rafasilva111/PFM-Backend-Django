from django_filters import FilterSet, DateRangeFilter, DateFilter,ChoiceFilter,CharFilter,ModelChoiceFilter
from apps.recipe_app.models import Recipe, RecipeAuditLog, RecipeAuditLogStatusHistory, RecipeReport
from apps.user_app.models import User
from django import forms


class RecipeFilter(FilterSet):
    created_by = ModelChoiceFilter(
        queryset=User.objects.filter(type=User.UserType.COMPANY).all(),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Created By'
    )
    
    verified = ChoiceFilter(
        choices=[
            ('True', 'Yes'),
            ('False', 'No')
        ],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Verified'
    )

    class Meta:
        model = Recipe
        fields = ['created_by', 'verified']

class RecipeAuditLogFilter(FilterSet):
    
    type = ChoiceFilter(
        choices=RecipeAuditLog.Type.choices,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Type'
    )
    
    accepted = ChoiceFilter(
        choices=[
            ('True', 'Yes'),
            ('False', 'No')
        ],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Accepted'
    )

    class Meta:
        model = RecipeAuditLog
        fields = ["type"]
        
class RecipeAuditLogStatusHistoryFilter(FilterSet):
    status = ChoiceFilter(
        choices=RecipeAuditLogStatusHistory.Status.choices,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Status'
    )
    
    changed_by = ModelChoiceFilter(
        queryset=User.objects.filter(groups__name__in=['Staff', 'SuperUser']).distinct(),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Changed By'
    )
    
    class Meta:
        model = RecipeAuditLogStatusHistory
        fields = ["status", "changed_by"]
        
class RecipeReportFilter(FilterSet):
    reviewed = ChoiceFilter(
        choices=[
            ('True', 'Yes'),
            ('False', 'No')
        ],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Reviewed'
    )
    
    status = ChoiceFilter(
        choices=RecipeReport.Type.choices,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Status'
    )
    
    class Meta:
        model = RecipeReport
        fields = ['reviewed', 'status']