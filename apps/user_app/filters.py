###
#       General imports
##


##
#   Django
#

from django import forms
from django_filters import FilterSet, DateRangeFilter, BooleanFilter,ChoiceFilter,ModelChoiceFilter
from django.contrib.auth.models import Group

###
#       App specific imports
##


##
#   Models
#

from apps.user_app.models import User, Invitation, Company
from apps.user_app.models import ProcessType
from django_filters import MultipleChoiceFilter




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
        
class InvitationFilter(FilterSet):
    
    inviter = ModelChoiceFilter(
        queryset=User.objects.filter(type__in=[User.UserType.COMPANY_ADMIN, User.UserType.APP_ADMIN]),
        label='Inviter:',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    company = ModelChoiceFilter(
        queryset=Company.objects.all(),
        label='Company:',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    group = ModelChoiceFilter(
        queryset=Group.objects.filter(name__in=[User.UserType.COMPANY_STAFF, User.UserType.COMPANY_ADMIN,User.UserType.APP_STAFF, User.UserType.APP_ADMIN]),
        label='Group:',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
    class Meta:
        model = Invitation
        fields = {}
        
class CompanyFilter(FilterSet):
    processes = ChoiceFilter(
        choices=ProcessType.choices,
        label='Processes:',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        method='filter_processes'
    )

    class Meta:
        model = Invitation  
        fields = {}

    def filter_processes(self, queryset, name, value):
        if value:
            # Regex pattern to match the value as a whole in a comma-separated list
            # Matches start (^), middle (,value,), end ($), beginning (value,) and ending (,value)
            regex_pattern = fr'(^|,){value}(,|$)'
            return queryset.filter(**{f"{name}__regex": regex_pattern})
        return queryset