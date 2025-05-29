###
#       General imports
##

## 
#   Default
##
import json


##
#   Django
##
from django import forms
from django.db.models import Q
from django.core.exceptions import ValidationError
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from django.db import transaction

## 
#   Api Swagger
##


## 
#   Extras
##


###
#       App specific imports
##

##
#   Models
from apps.etl_app.models import Task, Job, ContentType, TimeCondition, ThresholdCondition
from apps.user_app.models import User, Company


# Predefined options for cron fields

MINUTES_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(60)]
HOURS_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(24)]
DAY_OF_WEEK_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(7)]
DAY_OF_MONTH_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(1, 32)]
MONTH_OF_YEAR_CHOICES = [('*', '*')] + [(str(i), str(i)) for i in range(1, 13)]


###
#
#   Conditions
#
##


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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Map instance crontab fields to form fields
        if self.instance and self.instance.periodic_task and self.instance.periodic_task.crontab:
            self.fields['minute'].initial = self.instance.periodic_task.crontab.minute
            self.fields['hour'].initial = self.instance.periodic_task.crontab.hour
            self.fields['day_of_week'].initial = self.instance.periodic_task.crontab.day_of_week
            self.fields['day_of_month'].initial = self.instance.periodic_task.crontab.day_of_month
            self.fields['month_of_year'].initial = self.instance.periodic_task.crontab.month_of_year
        # Filter users based on company type

    def clean(self):
        cleaned_data = super().clean()
        minute = cleaned_data.get('minute')

        if minute == '*':
            self.add_error('minute', 'Minute cannot be "*"')

        return cleaned_data
    
        
    def save(self,job_id, starting_condition, name, *args, **kwargs):
        
        instance = super().save(commit=False)

        # Create or get the crontab schedule
        crontab, created = CrontabSchedule.objects.get_or_create(
            minute=self.cleaned_data['minute'],
            hour=self.cleaned_data['hour'],
            day_of_week=self.cleaned_data['day_of_week'],
            day_of_month=self.cleaned_data['day_of_month'],
            month_of_year=self.cleaned_data['month_of_year'],
        )
        
        if starting_condition:
            task= 'apps.etl_app.tasks._launch_job'
        else:
            task= 'apps.etl_app.tasks._stop_job'
            
        
        instance.periodic_task, created = PeriodicTask.objects.update_or_create(
            name=name,
            defaults={
            'task': task,
            'crontab': crontab,
            'args': json.dumps([str(job_id)]),
            'enabled': True,
            }
        )

        instance.save()
        
        return instance


class ThresholdConditionForm(forms.ModelForm):
    
    threshold_value = forms.IntegerField(
        required=True,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'The Job will stop after this number of records are processed'
        })
    )
    class Meta:
        model = ThresholdCondition
        fields = ['threshold_value']
    
    def clean(self):
        cleaned_data = super().clean()
        threshold_value = cleaned_data.get('threshold_value')

        if threshold_value == 0:
            self.add_error('threshold_value', 'Maximum records cannot be 0')


        return cleaned_data



###
#
#   Tasks
#
##


class TaskForm(forms.ModelForm):
    company = forms.ModelChoiceField(
        label='Company',
        queryset=Company.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})  # Specify widget here
    )
    

    parent_task_extract = forms.ModelChoiceField(label='Extract Tasks', queryset=Task.objects.filter(type=Task.TaskType.EXTRACT).order_by('-created_at'),
                                                  required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_task_transform = forms.ModelChoiceField(label='Transform Tasks', queryset=Task.objects.filter(type=Task.TaskType.TRANSFORM).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_job_extract = forms.ModelChoiceField(label='Extract Jobs', queryset=Job.objects.filter(type=Job.TaskType.EXTRACT).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_job_transform = forms.ModelChoiceField(label='Transform Jobs', queryset=Job.objects.filter(type=Job.TaskType.TRANSFORM).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))

    class Meta:
        model = Task
        fields = [
            'type','company','process','debug_mode',
            'parent_task_extract', 'parent_task_transform',
            'parent_job_extract', 'parent_job_transform',
        ]
        widgets = {
            'process': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'parent_task': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'debug_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)

        " Set the initial values for the parent task or job fields based on the instance type "
        if instance:
            if instance.parent_task:
                if instance.type == Job.TaskType.TRANSFORM:
                    self.fields['parent_task_extract'].initial = instance.parent_task
                elif instance.type == Job.TaskType.LOAD:
                    self.fields['parent_task_transform'].initial = instance.parent_task
                    
            elif instance.parent_job:
                if instance.type == Job.TaskType.TRANSFORM:
                    self.fields['parent_job_extract'].initial = instance.parent_job
                elif instance.type == Job.TaskType.LOAD:
                    self.fields['parent_job_transform'].initial = instance.parent_job
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Prevent from saving a RUNNING task
        if self.instance.status in [Task.Status.RUNNING, Task.Status.PAUSED]:
            self.add_error(None, f'You cannot save a task with status {self.instance.status}.')
        
        # Enforce parent task or job required for TRANSFORM, LOAD
        if cleaned_data.get('type') == Job.TaskType.TRANSFORM:
            parent_task = cleaned_data.get('parent_task_extract')
            parent_job = cleaned_data.get('parent_job_extract')
            
            if not parent_task and not parent_job:
                self.add_error('parent_task_extract', 'Please choose either a Parent Task or Job.')
            elif parent_task and parent_job:
                self.add_error('parent_task_extract', 'Please choose only one: either a Parent Task or Job.')
            
        if cleaned_data.get('type') == Job.TaskType.LOAD:
            parent_task = cleaned_data.get('parent_task_transform')
            parent_job = cleaned_data.get('parent_job_transform')
            
            if not parent_task and not parent_job:
                self.add_error('parent_task_extract', 'Please choose either a Parent Task or Job.')
            elif parent_task and parent_job:
                self.add_error('parent_task_extract', 'Please choose only one: either a Parent Task or Job.')
                
        # Enforce process required for EXTRACT, TRANSFORM, LOAD
        if cleaned_data.get('type') in [Job.TaskType.EXTRACT, Job.TaskType.TRANSFORM, Job.TaskType.LOAD]:
            if cleaned_data.get('process') not in cleaned_data.get('company').processes:
                self.add_error('process', 'Process not found in company')
        
        return cleaned_data
    
    def save(self, created_by = None, *args, **kwargs):
        
        try:
            # Create or update the Job instance
            with transaction.atomic():
                
                # Save the job instance
                instance = super().save(commit=False)
                
                if created_by:
                    instance.created_by = created_by
                
                # We need to set the parent task or job ( we dont need to validate the Type here, because we already did it in the clean method )
                if self.cleaned_data['parent_task_extract']:
                    instance.parent_task = self.cleaned_data['parent_task_extract']
                elif self.cleaned_data['parent_task_transform']:
                    instance.parent_task = self.cleaned_data['parent_task_transform']
                elif self.cleaned_data['parent_job_extract']:
                    instance.parent_job = self.cleaned_data['parent_job_extract']
                elif self.cleaned_data['parent_job_transform']:
                    instance.parent_job = self.cleaned_data['parent_job_transform']
                
                
                instance.save()
                if instance.status == Task.Status.WAITING:
                    instance.launch()
                
            
                return instance
        except Exception as e:
            # Handle any exceptions (rollback will occur automatically)
            print(f"An error occurred: {e}")
            raise
###
#
#   Jobs
#
##


class JobForm(forms.ModelForm):
    
    company = forms.ModelChoiceField(
        label='Company',
        queryset=Company.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})  # Specify widget here
    )
    
    starting_condition_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(
            Q(app_label='etl_app', model='timecondition') | Q(app_label='etl_app', model='taskstatuscondition')
        ),
        required=False,
        label='Starting Condition Type',
        help_text='Select the type of condition for starting.',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    
    stopping_condition_type = forms.ModelChoiceField(
        queryset = ContentType.objects.filter(
            Q(app_label='etl_app', model='timecondition') | Q(app_label='etl_app', model='thresholdcondition')
        ),
        required=False,
        label='Stopping Condition Type',
        help_text='Select the type of condition for stopping.',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )

    parent_task_extract = forms.ModelChoiceField(label='Extract Tasks', queryset=Task.objects.filter(type=Task.TaskType.EXTRACT).order_by('-created_at'),
                                                  required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_task_transform = forms.ModelChoiceField(label='Transform Tasks', queryset=Task.objects.filter(type=Task.TaskType.TRANSFORM).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_job_extract = forms.ModelChoiceField(label='Extract Jobs', queryset=Job.objects.filter(type=Job.TaskType.EXTRACT).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_job_transform = forms.ModelChoiceField(label='Transform Jobs', queryset=Job.objects.filter(type=Job.TaskType.TRANSFORM).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))

    class Meta:
        model = Job
        fields = [
            'name', 'type','company','process',
            'parent_task_extract', 'parent_task_transform',
            'parent_job_extract', 'parent_job_transform',
            'starting_condition_type', 'stopping_condition_type',
        ]
        widgets = {
            'process': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter the name of the job'}),
            'type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'parent_task': forms.Select(attrs={'class': 'form-select form-select-lg'}),
        }
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)

        if instance:
            if instance.parent_task:
                if instance.type == Job.TaskType.TRANSFORM:
                    self.fields['parent_task_extract'].initial = instance.parent_task
                elif instance.type == Job.TaskType.LOAD:
                    self.fields['parent_task_transform'].initial = instance.parent_task
                    
            elif instance.parent_job:
                if instance.type == Job.TaskType.TRANSFORM:
                    self.fields['parent_job_extract'].initial = instance.parent_job
                elif instance.type == Job.TaskType.LOAD:
                    self.fields['parent_job_transform'].initial = instance.parent_job
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Enforce parent task or job required for TRANSFORM, LOAD
        if cleaned_data.get('type') == Job.TaskType.TRANSFORM:
            parent_task = cleaned_data.get('parent_task_extract')
            parent_job = cleaned_data.get('parent_job_extract')
            
            if not parent_task and not parent_job:
                self.add_error('parent_task_extract', 'Please choose either a Parent Task or Job.')
            elif parent_task and parent_job:
                self.add_error('parent_task_extract', 'Please choose only one: either a Parent Task or Job.')
            
        if cleaned_data.get('type') == Job.TaskType.LOAD:
            parent_task = cleaned_data.get('parent_task_transform')
            parent_job = cleaned_data.get('parent_job_transform')
            
            if not parent_task and not parent_job:
                self.add_error('parent_task_extract', 'Please choose either a Parent Task or Job.')
            elif parent_task and parent_job:
                self.add_error('parent_task_extract', 'Please choose only one: either a Parent Task or Job.')
                
        # Enforce process required for EXTRACT, TRANSFORM, LOAD
        if cleaned_data.get('type') in [Job.TaskType.EXTRACT, Job.TaskType.TRANSFORM, Job.TaskType.LOAD]:
            if cleaned_data.get('process') not in cleaned_data.get('company').processes:
                self.add_error('process', 'Process not found in company')
        
        return cleaned_data
    
    def save(self,starting_condition_form = None,stopping_condition_form = None, created_by = None, *args, **kwargs):
        
        try:
            # Create or update the Job instance
            with transaction.atomic():
                
                # Save the job instance
                job = super().save(commit=False)
                
                if created_by:
                    job.created_by = created_by
                
                # We need to set the parent task or job ( we dont need to validate the Type here, because we already did it in the clean method )
                if self.cleaned_data['parent_task_extract']:
                    job.parent_task = self.cleaned_data['parent_task_extract']
                elif self.cleaned_data['parent_task_transform']:
                    job.parent_task = self.cleaned_data['parent_task_transform']
                elif self.cleaned_data['parent_job_extract']:
                    job.parent_job = self.cleaned_data['parent_job_extract']
                elif self.cleaned_data['parent_job_transform']:
                    job.parent_job = self.cleaned_data['parent_job_transform']
                
                job.save()
                
                if starting_condition_form:
                    job.starting_condition = starting_condition_form.save(
                        job_id = job.id,
                        name = f"Job Starting Condition: {job.name}",
                        starting_condition = True
                    )
                    
                if stopping_condition_form:
                    if stopping_condition_form.prefix == 'stopping_condition_time_form':
                        job.stopping_condition = stopping_condition_form.save(
                            job_id = job.id,
                            name = f"Job Stopping Condition: {job.name}",
                            starting_condition = False
                        )
                    elif stopping_condition_form.prefix == 'stopping_condition_threshold_form':
                        job.stopping_condition = stopping_condition_form.save()
                
                # Call the original save method
                job.save()
            
                return job
        except Exception as e:
            # Handle any exceptions (rollback will occur automatically)
            print(f"An error occurred: {e}")
            raise



        
        
        # Create or update the Job instance
        job = super().save(commit=False)
        
        
        if starting_condition_form:
            job.starting_condition = starting_condition_form.save(job_id = job.id, name = f"Job Starting Condition: {job.name}")
            
        if stopping_condition_form:
            job.stopping_condition = stopping_condition_form.save(job_id = job.id, name = f"Job Stopping Condition: {job.name}")
        
        # Call the original save method
        job.save()
    
        return job