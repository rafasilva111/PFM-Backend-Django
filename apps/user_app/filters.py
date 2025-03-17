###
#       General imports
##


##
#   Django
#

from django import forms
from django_filters import FilterSet, DateRangeFilter, BooleanFilter,ChoiceFilter,ModelChoiceFilter


###
#       App specific imports
##


##
#   Models
#
from apps.user_app.models import User




class UserFilter(FilterSet):    
    type = ChoiceFilter( 
        choices=User.UserType.choices,
        label='Type:',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    

    is_active = ChoiceFilter(
        field_name='is_active',
        label='Active:',
        choices=[
            (True, 'Yes'),  # Filter active users
            (False, 'No')   # Filter inactive users
        ],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    is_staff = ChoiceFilter(
        field_name='is_staff',
        label='Staff:',
        choices=[
            (True, 'Yes'),  # Filter active users
            (False, 'No')   # Filter inactive users
        ],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )


    class Meta:
        model = User
        fields = {}