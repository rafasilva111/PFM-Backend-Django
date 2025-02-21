
###
#       General imports
##


##
#   Django
#

from django import forms
from django_filters import FilterSet, DateRangeFilter, DateFilter,ChoiceFilter,ModelChoiceFilter


###
#       App specific imports
##


##
#   Models
#

from apps.task_app.models import Task, Job
from apps.user_app.models import User




class TaskFilter(FilterSet):
    started_at = DateRangeFilter(field_name='started_at', label='Started At',widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    finished_at = DateRangeFilter(field_name='finished_at', label='Finished At',widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    type = ChoiceFilter( choices=Task.TaskType.choices,label='Type', widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    status = ChoiceFilter( choices=Task.Status.choices,label='Status', widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    
    class Meta:
        model = Task
        fields = {}


class JobFilter(FilterSet):
    type = ChoiceFilter( choices=Task.TaskType.choices,label='Type', widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    created_by = ModelChoiceFilter(queryset=User.objects.filter(is_superuser=True), label='Created By', widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))

    class Meta:
        model = Job
        fields = {}