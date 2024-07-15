from django_filters import FilterSet, DateRangeFilter, DateFilter,ChoiceFilter,CharFilter,ModelChoiceFilter
from apps.recipe_app.models import Recipe
from apps.recipe_app.models import User
from django import forms


class RecipeFilter(FilterSet):
    created_by = ModelChoiceFilter(
        queryset=User.objects.filter(user_type=User.UserType.COMPANY).all(),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Created By'
    )

    class Meta:
        model = Recipe
        fields = ['created_by']