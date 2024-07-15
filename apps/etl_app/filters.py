from django_filters import FilterSet, DateRangeFilter, DateFilter,ChoiceFilter,ModelChoiceFilter
from apps.etl_app.models import Task, Job,TaskType
from apps.user_app.models import User
from django import forms



class TaskFilter(FilterSet):
    user = ModelChoiceFilter(
        queryset=User.objects.filter(user_type=User.UserType.COMPANY).all(),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Company:'
    )
    started_at = DateRangeFilter(field_name='started_at', label='Started At',widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    finished_at = DateRangeFilter(field_name='finished_at', label='Finished At',widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    type = ChoiceFilter( choices=TaskType.choices,label='Type', widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    status = ChoiceFilter( choices=Task.Status.choices,label='Status', widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    
    class Meta:
        model = Task
        fields = {}


class JobFilter(FilterSet):
    user = ModelChoiceFilter(
        queryset=User.objects.filter(user_type=User.UserType.COMPANY).all(),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='Company:'
    )
    type = ChoiceFilter( choices=TaskType.choices,label='Type', widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))

    class Meta:
        model = Job
        fields = {}