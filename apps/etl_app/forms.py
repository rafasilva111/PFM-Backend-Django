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
            task=task,
            defaults={
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
    
    parent_tasks_extract = forms.ModelChoiceField(label='Extract Tasks', queryset=Task.objects.filter(type=Task.TaskType.EXTRACT).order_by('-created_at'),
                                                  required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    parent_tasks_transform = forms.ModelChoiceField(label='Transform Tasks', queryset=Task.objects.filter(type=Task.TaskType.TRANSFORM).order_by('-created_at'),
                                                    required=False, widget=forms.Select(attrs={'class': 'form-select form-select-lg'}))
    
    class Meta:
        model = Task
        fields = ['type','company','debug_mode','process']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'process': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'debug_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter users based on company type

    def clean(self):
        cleaned_data = super().clean()
        
        # Enforce Process required for EXTRACT, TRANSFORM, LOAD
        company = cleaned_data.get('company')
        if cleaned_data.get('type') in [Task.TaskType.EXTRACT, Task.TaskType.TRANSFORM, Task.TaskType.LOAD]:
            if cleaned_data.get('process') not in company.processes:
                self.add_error('process', 'Process not found in company')
        
        # Enforce parent task or job required for TRANSFORM, LOAD
        parent_task = None
        if cleaned_data.get('type') == Task.TaskType.TRANSFORM:
            parent_task = cleaned_data.get('parent_tasks_extract')
            if not parent_task:
                self.add_error('parent_tasks_extract', 'Please choose a Parent Task.')
        
        if cleaned_data.get('type') == Task.TaskType.LOAD:
            parent_task = cleaned_data.get('parent_tasks_transform')
            if not parent_task:
                self.add_error('parent_tasks_transform', 'Please choose a Parent Task.')
        
        # Enforce parent task to be PAUSED or STOPPED
        if parent_task and parent_task.status not in [Task.Status.PAUSED, Task.Status.STOPPED]:
            self.add_error('parent_tasks_extract', 'Parent task must be PAUSED or STOPPED.')
        
        
        return cleaned_data
    
    def save(self, *args, **kwargs):
        instance = super(TaskForm, self).save(commit=False)
        if instance.type not in [Task.TaskType.EXTRACT, Task.TaskType.TRANSFORM, Task.TaskType.LOAD]:
            instance.process = None
        
        if self.cleaned_data['parent_tasks_extract']:
            instance.parent_task = self.cleaned_data['parent_tasks_extract']
            
        elif self.cleaned_data['parent_tasks_transform']:
            instance.parent_task = self.cleaned_data['parent_tasks_transform']
        
        instance.save()
        " Launch the task "
        instance.launch()
        return instance


class TaskEditForm(forms.ModelForm):
    
    job = forms.ModelChoiceField(
        queryset=Job.objects.all(),
        required=False,
        label='Job',
        help_text='Select the job.',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )

    class Meta:
        model = Task
        fields = ['log_path', 'job', 'debug_mode', 'step']
        widgets = {
            'log_path': forms.TextInput(attrs={'class': 'form-control'}),
            'debug_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'step': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Pass the user object to the form
        
        if user is None:
            raise ValueError("User must not be None")
        
        super(TaskEditForm, self).__init__(*args, **kwargs)

        # Edit Permissions
        if not user.is_staff:
            self.fields['log_path'].widget.attrs['readonly'] = 'readonly'
            self.fields['debug_mode'].widget.attrs['readonly'] = 'readonly'
            self.fields['job'].widget.attrs['readonly'] = 'readonly'
    
    def clean(self):
        cleaned_data = super().clean() 

        if self.instance.status in [Task.Status.WAITING, Task.Status.RUNNING]:
            if self.instance.debug_mode != cleaned_data.get('debug_mode'):
                self.add_error('debug_mode', "Cannot change debug_mode if current status is STARTING or RUNNING. Please change it to STOPPED first.")
            
            job = cleaned_data.get('job')
            if job and self.instance.job_id != job.id: # use get to avoid keyerrors
                self.add_error('job', "Cannot change job if current status is STARTING or RUNNING. Please change it to STOPPED first.")
            if self.instance.step != cleaned_data.get('step'):
                self.add_error('step', "Cannot change step if current status is STARTING or RUNNING. Please change it to STOPPED first.")
            if self.instance.log_path != cleaned_data.get('log_path'):
                self.add_error('log_path', "Cannot change log_path if current status is STARTING or RUNNING. Please change it to STOPPED first.")

        return cleaned_data
    
    def save(self,  *args, **kwargs):
        # Check if type has changed
        old_instance = Task.objects.get(pk=self.instance.pk)

        instance = super(TaskEditForm, self).save(commit=False)
        
        # Check if the status is STARTING or RUNNING
        if old_instance.status in [Task.Status.WAITING, Task.Status.RUNNING]:
            
            if old_instance.debug_mode != self.cleaned_data['debug_mode']:
                self.add_error('debug_mode', "Cannot change debug_mode if status is STARTING or RUNNING.")
            
            if old_instance.job_id != self.cleaned_data['job']:
                self.add_error('job', "Cannot change job if status is STARTING or RUNNING.")
            
            if old_instance.step != self.cleaned_data['step']:
                self.add_error('step', "Cannot change step if status is STARTING or RUNNING.")
            
            if old_instance.log_path != self.cleaned_data['log_path']:
                self.add_error('log_path', "Cannot change log_path if status is STARTING or RUNNING.")
            
            # Abort save if there are errors
            if self.errors:
                return old_instance
            
        instance.save()
        
        # Change the status if it has changed, to reflect the new status
        if self.instance.status != old_instance.status:
            self.instance.change_status(self.instance.status)
            
        return instance


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
                    elif stopping_condition_form.prefix == 'stopping_threshold_condition_form':
                        job.stopping_condition = stopping_condition_form.save()
                
                # Call the original save method
                job.save()
            
                return job
        except Exception as e:
            # Handle any exceptions (rollback will occur automatically)
            print(f"An error occurred: {e}")
            raise


class JobEditForm(forms.ModelForm):
    
    starting_condition_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(
            Q(app_label='task_app', model='timecondition')
        ),
        required=False,
        label='Starting Condition Type',
        help_text='Select the type of condition for starting.',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    
    stopping_condition_type = forms.ModelChoiceField(
        queryset = ContentType.objects.filter(
            Q(app_label='task_app', model='timecondition') | Q(app_label='etl_app', model='treshholdcondition')
        ),
        required=False,
        label='Stopping Condition Type',
        help_text='Select the type of condition for stopping.',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )

    class Meta:
        model = Job
        fields = ['name', 'type',  'starting_condition_type', 'stopping_condition_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter the name of the job'}),
            'type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'parent_task': forms.Select(attrs={'class': 'form-select form-select-lg'}),
        }           
    

    def save(self, starting_condition_form = None,stopping_condition_form = None, *args, **kwargs):
        
        
        # Create or update the Job instance
        job = super().save(commit=False)
        
        
        if starting_condition_form:
            job.starting_condition = starting_condition_form.save(job_id = job.id, name = f"Job Starting Condition: {job.name}")
            
        if stopping_condition_form:
            job.stopping_condition = stopping_condition_form.save(job_id = job.id, name = f"Job Stopping Condition: {job.name}")
        
        # Call the original save method
        job.save()
    
        return job