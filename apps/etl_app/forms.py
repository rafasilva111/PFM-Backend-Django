from django import forms
from django_celery_beat.models import CrontabSchedule,PeriodicTask
from .models import Task, Job,TaskType
from apps.user_app.models import User
import json

class TaskForm(forms.ModelForm):
    parent_tasks_extract = forms.ModelChoiceField(label='Extract Tasks', queryset=Task.objects.filter(type=TaskType.EXTRACT).order_by("-created_at"),
                                                  required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    parent_tasks_transform = forms.ModelChoiceField(label='Transform Tasks', queryset=Task.objects.filter(type=TaskType.TRANSFORM).order_by("-created_at"),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    class Meta:
        model = Task
        fields = ['company', 'type', 'max_records','parent_task']
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'max_records': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter the maximum number of records'}),
            'parent_task': forms.Select(attrs={'class': 'form-select form-select-lg'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter users based on company type

        
    def clean(self):
        cleaned_data = super().clean()
        task_type = cleaned_data.get('type')
        
        if task_type == TaskType.TRANSFORM:
            cleaned_data['parent_task'] = cleaned_data.get('parent_tasks_extract')
            
        elif task_type == TaskType.LOAD:
            cleaned_data['parent_task'] = cleaned_data.get('parent_tasks_transform')

        return cleaned_data


# Predefined options for cron fields
MINUTES_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(60)]
HOURS_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(24)]
DAY_OF_WEEK_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(7)]
DAY_OF_MONTH_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(1, 32)]
MONTH_OF_YEAR_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(1, 13)]
class JobForm(forms.ModelForm):

    parent_tasks_extract = forms.ModelChoiceField(label='Extract Tasks', queryset=Task.objects.filter(type=TaskType.EXTRACT).order_by("-created_at"),
                                                  required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_tasks_transform = forms.ModelChoiceField(label='Transform Tasks', queryset=Task.objects.filter(type=TaskType.TRANSFORM).order_by("-created_at"),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))

    minute = forms.ChoiceField(
        choices=MINUTES_CHOICES, 
        initial='*', 
        help_text='Cron minute field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    hour = forms.ChoiceField(
        choices=HOURS_CHOICES, 
        initial='*', 
        help_text='Cron hour field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    day_of_week = forms.ChoiceField(
        choices=DAY_OF_WEEK_CHOICES, 
        initial='*', 
        help_text='Cron day of week field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    day_of_month = forms.ChoiceField(
        choices=DAY_OF_MONTH_CHOICES, 
        initial='*', 
        help_text='Cron day of month field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    month_of_year = forms.ChoiceField(
        choices=MONTH_OF_YEAR_CHOICES, 
        initial='*', 
        help_text='Cron month of year field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )

    class Meta:
        model = Job
        fields = ['name','minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year','company', 'type', 'max_records','parent_task']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'max_records': forms.NumberInput(attrs={'class': 'form-control'}),
            'parent_task': forms.Select(attrs={'class': 'form-select form-select-lg'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Create or get the crontab schedule
        crontab, created = CrontabSchedule.objects.get_or_create(
            minute=self.cleaned_data['minute'],
            hour=self.cleaned_data['hour'],
            day_of_week=self.cleaned_data['day_of_week'],
            day_of_month=self.cleaned_data['day_of_month'],
            month_of_year=self.cleaned_data['month_of_year'],
        )


        instance.crontab = crontab

        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        task_type = cleaned_data.get('type')
        
        if task_type == TaskType.TRANSFORM:
            cleaned_data['parent_task'] = cleaned_data.get('parent_tasks_extract')
            
        elif task_type == TaskType.LOAD:
            cleaned_data['parent_task'] = cleaned_data.get('parent_tasks_transform')

        return cleaned_data