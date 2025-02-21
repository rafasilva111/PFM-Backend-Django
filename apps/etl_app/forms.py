from django import forms
from django_celery_beat.models import CrontabSchedule,PeriodicTask
from apps.etl_app.models import Task, Job,TaskType,ContentType, TimeCondition, MaxRecordsCondition
from apps.user_app.models import User
from django.db.models import Q
from django.core.exceptions import ValidationError
import json



# Predefined options for cron fields

MINUTES_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(60)]
HOURS_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(24)]
DAY_OF_WEEK_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(7)]
DAY_OF_MONTH_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(1, 32)]
MONTH_OF_YEAR_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(1, 13)]

class MaxRecordsConditionForm(forms.ModelForm):
    
    max_records = forms.IntegerField(
        required=True,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'The Job will stop after this number of records are processed'
        })
    )
    class Meta:
        model = MaxRecordsCondition
        fields = ['max_records']
    
    def clean(self):
        cleaned_data = super().clean()
        max_records = cleaned_data.get('max_records')

        if max_records == 0:
            self.add_error('max_records', 'Maximum records cannot be 0')


        return cleaned_data
        
    


class TimeConditionForm(forms.ModelForm):
    
    minute = forms.ChoiceField(
        choices=MINUTES_CHOICES, 
        initial='*', 
        required=False,
        help_text='Cron minute field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    hour = forms.ChoiceField(
        choices=HOURS_CHOICES, 
        initial='*', 
        required=False,
        help_text='Cron hour field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    day_of_week = forms.ChoiceField(
        choices=DAY_OF_WEEK_CHOICES, 
        initial='*', 
        required=False,
        help_text='Cron day of week field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    day_of_month = forms.ChoiceField(
        choices=DAY_OF_MONTH_CHOICES, 
        initial='*', 
        required=False,
        help_text='Cron day of month field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    month_of_year = forms.ChoiceField(
        choices=MONTH_OF_YEAR_CHOICES, 
        initial='*', 
        required=False,
        help_text='Cron month of year field', 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    class Meta:
        model = TimeCondition
        fields = ['minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year']
        
    def clean(self):
        cleaned_data = super().clean()
        minute = cleaned_data.get('minute')
        hour = cleaned_data.get('hour')

        if minute == '*':
            self.add_error('minute', 'Minute cannot be "*"')
        if hour == '*': 
            self.add_error('hour', 'Hour cannot be "*"')

        return cleaned_data
    
        
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


class TaskForm(forms.ModelForm):
    
    company = forms.ModelChoiceField(
        label='Company',
        queryset=User.objects.filter(user_type=User.UserType.COMPANY),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})  # Specify widget here
    )
    
    parent_tasks_extract = forms.ModelChoiceField(label='Extract Tasks', queryset=Task.objects.filter(type=TaskType.EXTRACT).order_by('-created_at'),
                                                  required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_tasks_transform = forms.ModelChoiceField(label='Transform Tasks', queryset=Task.objects.filter(type=TaskType.TRANSFORM).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    class Meta:
        model = Task
        fields = [ 'company', 'type', 'stopping_condition_max_records', 'parent_task', 'debug_mode']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'stopping_condition_max_records': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter the maximum number of records'}),
            'parent_task': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'debug_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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

class JobForm(forms.ModelForm):
    
    company = forms.ModelChoiceField(
        label='Company',
        queryset=User.objects.filter(user_type=User.UserType.COMPANY),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})  # Specify widget here
    )
    
    starting_condition_type = forms.ModelChoiceField(
        queryset=ContentType.objects.all().exclude(model__in=['maxrecordscondition']),
        required=False,
        label='Starting Condition Type',
        help_text='Select the type of condition for starting.',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    
    stopping_condition_type = forms.ModelChoiceField(
        queryset=ContentType.objects.all(),
        required=False,
        label='Stopping Condition Type',
        help_text='Select the type of condition for stopping.',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )

    parent_task_extract = forms.ModelChoiceField(label='Extract Tasks', queryset=Task.objects.filter(type=TaskType.EXTRACT).order_by('-created_at'),
                                                  required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_task_transform = forms.ModelChoiceField(label='Transform Tasks', queryset=Task.objects.filter(type=TaskType.TRANSFORM).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_task_load = forms.ModelChoiceField(label='Load Tasks', queryset=Task.objects.filter(type=TaskType.LOAD).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_job_extract = forms.ModelChoiceField(label='Extract Jobs', queryset=Job.objects.filter(type=TaskType.EXTRACT).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_job_transform = forms.ModelChoiceField(label='Transform Jobs', queryset=Job.objects.filter(type=TaskType.TRANSFORM).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_job_load = forms.ModelChoiceField(label='Load Jobs', queryset=Job.objects.filter(type=TaskType.LOAD).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    

    

    class Meta:
        model = Job
        fields = ['name','company', 'type','parent_task', 'parent_job','parent_task_extract', 'parent_task_transform', 'parent_task_load','parent_job_extract', 'parent_job_transform', 'parent_job_load', 'debug_mode', 'starting_condition_type', 'stopping_condition_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter the name of the job'}),
            'type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'parent_task': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'debug_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtering the ContentType queryset to show only types related to conditions
        # Adjust this if you want to filter specific content types for conditions.

        self.fields['starting_condition_type'].queryset = ContentType.objects.filter(
            Q(app_label='etl_app', model='timecondition')
        )
        self.fields['stopping_condition_type'].queryset = ContentType.objects.filter(
            Q(app_label='etl_app', model='timecondition') | Q(app_label='etl_app', model='maxrecordscondition')
        )
    
    def save(self,starting_condition_form = None,stopping_condition_form = None, *args, **kwargs):
        
        
        # Create or update the Job instance
        job = super().save(commit=False)
        
        
        if starting_condition_form:
            job.starting_condition = starting_condition_form.save()
            
        if stopping_condition_form:
            job.stopping_condition = stopping_condition_form.save()  
        
        

        # Call the original save method
        job.save()
    
        
        return job


    def clean(self):
        cleaned_data = super().clean()
        task_type = cleaned_data.get('type')
        
        if task_type == TaskType.TRANSFORM:
            cleaned_data['parent_task'] = cleaned_data.get('parent_task_extract')
            
        elif task_type == TaskType.LOAD:
            cleaned_data['parent_task'] = cleaned_data.get('parent_task_transform')
            
            
        if task_type == TaskType.TRANSFORM:
            cleaned_data['parent_job'] = cleaned_data.get('parent_job_extract')
            
            if cleaned_data['parent_job'] and cleaned_data['parent_task']:
                self.add_error('parent_task_extract', 'Parent job and parent task cannot be selected at the same time.')
                self.add_error('parent_job_extract', 'Parent job and parent task cannot be selected at the same time.')
            elif not cleaned_data['parent_job'] and not cleaned_data['parent_task']:
                self.add_error('parent_job_extract', 'Parent job and parent task cannot be empty at the same time.')
                self.add_error('parent_task_extract', 'Parent job and parent task cannot be empty at the same time.')
            
        elif task_type == TaskType.LOAD:
            cleaned_data['parent_job'] = cleaned_data.get('parent_job_transform')
            
            if cleaned_data['parent_job'] and cleaned_data['parent_task']:
                self.add_error('parent_task_transform', 'Parent job and parent task cannot be selected at the same time.')
                self.add_error('parent_job_transform', 'Parent job and parent task cannot be selected at the same time.')
            elif not cleaned_data['parent_job'] and not cleaned_data['parent_task']:
                self.add_error('parent_job_transform', 'Parent job and parent task cannot be empty at the same time.')
                self.add_error('parent_job_transform', 'Parent job and parent task cannot be empty at the same time.')
            
        return cleaned_data