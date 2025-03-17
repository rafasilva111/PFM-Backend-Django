###
#       General imports
##


##
#   Default
#

from web_project import TemplateLayout

##
#   Django
#


from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.utils.safestring import mark_safe
from django.http import HttpResponse

##
#   Api Swagger
#


##
#   Extras
#

import re
from os import path

###
#       App specific imports
##


##
#   Models
#

from apps.etl_app.models import Job, Task

##
#   Serializers
#


##
#   Forms
#

from apps.etl_app.forms import  TaskForm, JobForm, TimeConditionForm,ThresholdConditionForm, TaskEditForm, JobEditForm


##
#   Filters
#

from apps.etl_app.filters import JobFilter, TaskFilter

##
#   Functions
#


##
#   Contants
#

from apps.common.constants import WEBSOCKET_HOST


###
#
#   Jobs
#
##


@method_decorator(login_required, name="dispatch")
class JobTableView(PermissionRequiredMixin, TemplateView):
    """
    A view class that displays a paginated table of jobs with filtering capabilities.
    This view requires user authentication and specific permission to view jobs.
    It extends TemplateView and implements PermissionRequiredMixin for access control.

    Attributes:
        template_name (str): Path to the template used to render the job table.
        page_size (int): Default number of items per page.
        permission_required (str): Permission required to access this view.

    Methods:
        get_context_data(**kwargs): Prepares and returns the context data for template rendering.
            - Initializes template layout.
            - Retrieves and orders all jobs.
            - Applies filtering based on request parameters.
            - Implements pagination.
            - Adds create job permission check.
    """

    template_name = "etl_app/job/table.html"
    permission_required = "task_app.can_view_jobs"
    page_size = 10

    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context data for template rendering.
        - Initializes template layout.
        - Retrieves and orders all jobs.
        - Applies filtering based on request parameters.
        - Implements pagination.
        - Adds create job permission check.

        Returns:
            dict: Context containing:
                - filter: Filtered queryset of jobs.
                - page_obj: Paginator object with job records.
                - can_create_job: Boolean indicating if user can create jobs.
                - can_edit_job: Boolean indicating if user can edit jobs.
                - can_view_job: Boolean indicating if user can view jobs.
                - can_delete_job: Boolean indicating if user can delete jobs.
        """
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        # Retrieve and order all jobs
        records = Job.objects.all().order_by("-id")
        
        # Apply filtering based on request parameters
        filter = JobFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs
        
        # Implement pagination
        page_size = int(self.request.GET.get("page_size", self.page_size))
        paginator = Paginator(filtered_records, page_size) 
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Add create job permission check
        context.update(
            {
                "filter": filter,
                "page_obj": page_obj,
                "can_create_job": self.request.user.has_perm(
                    "task_app.can_create_job"
                ),
                "can_edit_job": self.request.user.has_perm(
                    "task_app.can_edit_job"
                ),
                "can_view_job": self.request.user.has_perm(
                    "task_app.can_view_job"
                ),
                "can_delete_job": self.request.user.has_perm(
                    "task_app.can_delete_job"
                ),
            }
        )
        
        return context


@method_decorator(login_required, name='dispatch')
class JobDetailView(PermissionRequiredMixin, TemplateView):
    """
    A view class for displaying job details.

    This class handles the display of job-specific information and associated log files.
    Requires user authentication to access the view.

    Attributes:
        template_name (str): The template used for rendering the job detail view.
        page_size (int): Number of items to display per page.
        permission_required (str): The required permission to access this view.

    Methods:
        get_context_data(**kwargs): Prepares and returns the context data for template rendering.

    Parameters:
        kwargs["id"] (int): The ID of the job to be displayed.

    Returns:
        dict: Context dictionary containing:
            - record: Job object retrieved from database.
            - log: Content of the job's log file (if exists).
            - WEBSOCKET_HOST: WebSocket host configuration.
            - Additional template layout context data.
    """
    
    template_name = "etl_app/job/detail.html"
    permission_required = "task_app.can_view_job"
    page_size = 10

    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context data for template rendering.
        - Initializes template layout.
        - Retrieves the job by ID.
        - Reads the job's log file if it exists.
        - Adds WebSocket host configuration.

        Returns:
            dict: Context dictionary containing:
                - record: Job object retrieved from database.
                - log: Content of the job's log file (if exists).
                - WEBSOCKET_HOST: WebSocket host configuration.
        """
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Retrieve the Job by ID
        context["record"] = Job.objects.get(id=kwargs["id"])

        # Retrieve the Job's Tasks
        records = context["record"].tasks.all().order_by("-started_at")
        
        # Apply filtering based on request parameters
        filter = TaskFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs
        
        # Implement pagination
        page_size = int(self.request.GET.get("page_size", self.page_size))
        paginator = Paginator(filtered_records, page_size)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        
        # Read the job's log file if it exists
        log_path = context["record"].log_path
        if log_path and path.isfile(log_path):
            with open(log_path, "r") as log_file:
                context["log"] = log_file.read()
                
        # Create context
        context.update(
            {
                "WEBSOCKET_HOST": WEBSOCKET_HOST,
                "filter": filter,
                "page_obj": page_obj,
                "can_stop_job": self.request.user.has_perm(
                    "task_app.can_stop_job"
                ),
                "can_resume_job": self.request.user.has_perm(
                    "task_app.can_resume_job"
                ),
                "can_delete_job": self.request.user.has_perm(
                    "task_app.can_delete_job"
                ),
            }
        )

        return context


@method_decorator(login_required, name='dispatch')
class JobCreateView(PermissionRequiredMixin, TemplateView):
    """
    Class-based view for creating a new job.

    This view requires users to be authenticated and have the 'task_app.can_create_job' permission.
    It renders a form for job creation and handles both GET and POST requests.

    Attributes:
        template_name (str): Path to the template used for rendering the job creation form.
        permission_required (str): Permission required to access this view.

    Methods:
        get_context_data(**kwargs): Adds form and layout context to template context.
        post(request, *args, **kwargs): Handles form submission, saves job if valid, 
            and redirects to job detail view.

    Returns:
        GET: Rendered template with job creation form.
        POST: Redirects to job detail view on success, or re-renders form with errors.
    """
    
    template_name = "etl_app/job/create.html"
    permission_required = "task_app.can_create_job"
    form_class = JobForm
        
    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context data for template rendering.
        - Initializes template layout.
        - Adds job form and time condition forms to context.

        Returns:
            dict: Context dictionary containing:
                - form: JobForm instance.
                - starting_condition_time_form: TimeConditionForm instance for starting condition.
                - stopping_condition_time_form: TimeConditionForm instance for stopping condition.
        """
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context["form"] = self.form_class()
        context["starting_condition_time_form"] = TimeConditionForm(
            prefix="starting_condition_time_form"
        )
        context["stopping_condition_time_form"] = TimeConditionForm(
            prefix="stopping_condition_time_form"
        )
        context["stopping_condition_threshold_form"] = ThresholdConditionForm(
            prefix="stopping_threshold_condition_form"
        )
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles form submission for creating a new job.
        - Validates and saves the job form and time condition forms.
        - Redirects to job detail view on success, or re-renders form with errors.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponseRedirect: Redirects to job detail view on success.
            HttpResponse: Re-renders form with errors on failure.
        """

        job_form = self.form_class(request.POST)
        
        starting_time_condition_form = TimeConditionForm(
            request.POST, prefix="starting_condition_time_form"
        )
        stopping_time_condition_form = TimeConditionForm(
            request.POST, prefix="stopping_condition_time_form"
        )
        stopping_condition_threshold_form = ThresholdConditionForm(
            request.POST, prefix="stopping_threshold_condition_form"
        )
        
        
        if job_form.is_valid():
            starting_condition_form = None
            stopping_condition_form = None

            # Save the starting condition
            if job_form.instance.starting_condition_type:
                if job_form.instance.starting_condition_type.name == "time condition":
                    
                    starting_time_condition_form = TimeConditionForm(
                        request.POST, prefix="starting_condition_time_form"
                    )
                    if starting_time_condition_form.is_valid():
                        starting_condition_form = starting_time_condition_form
                    else:
                        # Collect all errors if any form is invalid
                        context = self.get_context_data()
                        context.update(
                            {
                                "form": job_form,
                                "starting_condition_time_form": starting_time_condition_form,
                                "stopping_condition_time_form": stopping_time_condition_form,
                            }
                        ) 
                        return self.render_to_response(context)

            # Save the stopping time condition
            if job_form.instance.stopping_condition_type:
                if job_form.instance.stopping_condition_type.name == "time condition":
                    if stopping_time_condition_form.is_valid():
                        stopping_condition_form = stopping_time_condition_form
                    else:
                        # Collect all errors if any form is invalid
                        context = self.get_context_data()
                        context.update(
                            {
                                "form": job_form,
                                "starting_condition_time_form": starting_time_condition_form,
                                "stopping_condition_time_form": stopping_time_condition_form,
                                "stopping_condition_threshold_form": stopping_condition_threshold_form,
                            }
                        ) 
                        return self.render_to_response(context)
                
                if job_form.instance.stopping_condition_type.name == "threshold condition":
                    if stopping_condition_threshold_form.is_valid():
                        stopping_condition_form = stopping_condition_threshold_form
                    else:
                        # Collect all errors if any form is invalid
                        context = self.get_context_data()
                        context.update(
                            {
                                "form": job_form,
                                "starting_condition_time_form": starting_time_condition_form,
                                "stopping_condition_time_form": stopping_time_condition_form,
                                "stopping_condition_threshold_form": stopping_condition_threshold_form,
                            }
                        ) 
                        return self.render_to_response(context)

            job = job_form.save(starting_condition_form, stopping_condition_form, request.user)
            return redirect(reverse("job_detail", args=[job.id]))

        # Create context
        context = self.get_context_data()
        context.update(
            {
                "form": job_form,
                "starting_condition_time_form": starting_time_condition_form,
                "stopping_condition_time_form": stopping_time_condition_form,
                "stopping_condition_threshold_form": stopping_condition_threshold_form,
            }
        )        
        return self.render_to_response(context)

@method_decorator(login_required, name='dispatch')
class JobEditView(PermissionRequiredMixin, TemplateView):
    """
    View for editing a user.

    Inherits from:
        PermissionRequiredMixin: Ensures the user has the required permissions.
        TemplateView: Renders a template.

    Attributes:
        template_name (str): The path to the template used for rendering the view.
        permission_required (str): The permission required to access this view.
        form_class (UserEditForm): The form class used for editing the user.

    Methods:
        get_object(): Retrieves the User object or raises a 404 error.
        get_context_data(**kwargs): Adds the UserEditForm to the context.
        post(request, *args, **kwargs): Handles form submission for editing a user.


        Returns:
            User: The user object retrieved by ID.


        Args:
            **kwargs: Additional context data.

        Returns:
            dict: The context data including the form.


        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The HTTP response object.
    """
    template_name = 'etl_app/job/edit.html'
    permission_required = 'auth.change_job'
    form_class = JobForm

    def get_object(self):
        """
        Retrieve the User object or raise a 404 error.
        """
        instance_id = self.kwargs.get('id')
        return get_object_or_404(Job, id=instance_id)

    
    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context data for template rendering.
        - Initializes template layout.
        - Adds job form and time condition forms to context.
    
        Returns:
            dict: Context dictionary containing:
                - form: JobForm instance.
                - starting_condition_time_form: TimeConditionForm instance for starting condition.
                - stopping_condition_time_form: TimeConditionForm instance for stopping condition.
        """
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        instance = self.get_object()
        context["form"] = self.form_class(instance=instance)
        
        context["starting_condition_time_form"] = TimeConditionForm(
            prefix="starting_condition_time_form",
            instance=instance.starting_condition if instance.starting_condition_type and instance.starting_condition_type.name == "time condition" else None
        )
        context["stopping_condition_time_form"] = TimeConditionForm(
            prefix="stopping_condition_time_form",
            instance=instance.stopping_condition if instance.stopping_condition_type and instance.stopping_condition_type.name == "time condition" else None
        )
        context["stopping_condition_threshold_form"] = ThresholdConditionForm(
            prefix="stopping_condition_threshold_form",
            instance=instance.stopping_condition if instance.stopping_condition_type and instance.stopping_condition_type.name == "threshold condition" else None
        )
    
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles form submission for creating a new job.
        - Validates and saves the job form and time condition forms.
        - Redirects to job detail view on success, or re-renders form with errors.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponseRedirect: Redirects to job detail view on success.
            HttpResponse: Re-renders form with errors on failure.
        """
        job_form = self.form_class(request.POST, instance=self.get_object())
        
        if job_form.is_valid():

            
            

            # Save the starting condition
            if job_form.instance.starting_condition_type:
                if job_form.instance.starting_condition_type.name == "time condition":
                
                    starting_time_condition_form = TimeConditionForm(
                        request.POST, prefix="starting_condition_time_form", instance = job_form.instance.starting_condition
                    )
                    
                    if starting_time_condition_form.is_valid():
                        starting_condition_form = starting_time_condition_form
                        
                    else:
                        # Collect all errors if any form is invalid
                        context = self.get_context_data()
                        context.update(
                            {
                                "form": job_form,
                                "starting_condition_time_form": starting_time_condition_form,
                            }
                        ) 
                        return self.render_to_response(context)
                    

            # Save the stopping time condition
            if job_form.instance.stopping_condition_type:
                if job_form.instance.stopping_condition_type.name == "time condition":
                    stopping_time_condition_form = TimeConditionForm(
                        request.POST, prefix="stopping_condition_time_form", instance = job_form.instance.stopping_condition
                    )
                    
                    if stopping_time_condition_form.is_valid():
                        stopping_condition_form = stopping_time_condition_form
                        
                    else:
                        # Collect all errors if any form is invalid
                        context = self.get_context_data()
                        context.update(
                            {
                                "form": job_form,
                                "stopping_condition_time_form": stopping_time_condition_form,
                            }
                        ) 
                        return self.render_to_response(context)
                
                if job_form.instance.stopping_condition_type.name == "threshold condition":
                    
                    stopping_condition_threshold_form = ThresholdConditionForm(
                        request.POST, prefix="stopping_condition_threshold_form", instance = job_form.instance.stopping_condition
                    )
                    if stopping_condition_threshold_form.is_valid():
                        stopping_condition_form = stopping_condition_threshold_form
                        
                    else:
                        # Collect all errors if any form is invalid
                        context = self.get_context_data()
                        context.update(
                            {
                                "form": job_form,
                                "stopping_condition_threshold_form": stopping_condition_threshold_form,
                            }
                        ) 
                        return self.render_to_response(context)                    
                        
            job_form.save(starting_condition_form = starting_condition_form, stopping_condition_form = stopping_condition_form)
            return redirect(reverse("job_detail", args=[job_form.instance.id]))
        
        # Create context
        context = self.get_context_data()
        context.update(
            {
                "form": job_form,
                "starting_condition_time_form": starting_time_condition_form,
                "stopping_condition_time_form": stopping_time_condition_form,
                "stopping_threshold_condition_form": stopping_condition_threshold_form,
            }
        )        
        return self.render_to_response(context)



###
#
#   Actions
#
##

@require_GET
def job_resume(request, id):
    """
    Resume a job instance and redirect to job detail page.
    This view requires user authentication and 'can_resume_job' permission.
    It retrieves a job by ID, calls its resume method, and redirects to the job detail page.

    Args:
        request: The HTTP request object.
        id (int): The ID of the job to resume.

    Returns:
        HttpResponseRedirect: Redirects to the job detail page.

    Raises:
        PermissionDenied: If user doesn't have 'can_resume_job' permission.
        Http404: If job with given ID is not found.

    Requires:
        - User must be logged in (@login_required).
        - Request method must be GET (@require_GET).
        - User must have 'task_app.can_resume_job' permission.
    """
    job = get_object_or_404(Job, id=id)
    job.resume()
    return redirect(reverse("job_detail", args=[job.id]))


@require_GET
def job_pause(request, id):
    """
    Pause a job instance and redirect to job detail page.
    This view requires user authentication and 'can_pause_job' permission.
    It retrieves a job by ID, calls its pause method, and redirects to the job detail page.

    Args:
        request: The HTTP request object.
        id (int): The ID of the job to pause.

    Returns:
        HttpResponseRedirect: Redirects to the job detail page.

    Raises:
        PermissionDenied: If user doesn't have 'can_pause_job' permission.
        Http404: If job with given ID is not found.

    Requires:
        - User must be logged in (@login_required).
        - Request method must be GET (@require_GET).
        - User must have 'task_app.can_pause_job' permission.
    """
    job = get_object_or_404(Job, id=id)
    job.pause()
    return redirect(reverse("job_detail", args=[job.id]))


@login_required
@require_GET
def job_delete(request, id):
    """
    Delete a job instance.
    This view function handles the deletion of a Job object. It requires the user to be
    authenticated and to have the 'can_delete_job' permission. If the job with the given ID
    exists, it will be deleted and the user will be redirected to the jobs list page.

    Args:
        request (HttpRequest): The HTTP request object.
        id (int): The ID of the job to be deleted.

    Returns:
        HttpResponseRedirect: Redirects to the jobs list page after successful deletion.

    Raises:
        PermissionDenied: If the user doesn't have the required permission.
        Http404: If the job with the given ID doesn't exist.
    """
    instance = get_object_or_404(Job, id=id)
    instance.delete()
    return redirect("jobs")

@login_required
@require_GET
def job_log_download(request, id):
    job = get_object_or_404(Job, id=id)  # Assuming you have a Task model

    if path.exists(job.log_path):
        # Open the log file in binary mode
        with open(job.log_path, 'rb') as log_file:
            response = HttpResponse(log_file.read(), content_type='text/plain')
            # Set the Content-Disposition header to indicate a file download
            response['Content-Disposition'] = f'attachment; filename="job_{id}_log.txt"'
            return response
    else:
        return HttpResponse('Log file not found.', status=404)

###
#
#   Tasks
#
##


@method_decorator(login_required, name="dispatch")
class TaskTableView(PermissionRequiredMixin, TemplateView):
    """
    A view class that displays a paginated table of tasks with filtering capabilities.
    This view requires user authentication and specific permission to view tasks.
    It extends TemplateView and implements PermissionRequiredMixin for access control.
    Attributes:
        template_name (str): Path to the template used to render the task table
        page_size (int): Default number of items per page
        permission_required (str): Permission required to access this view
        raise_exception (bool): Whether to raise exception for unauthorized access
    Methods:
        get_context_data(**kwargs): Prepares and returns the context data for template rendering
            - Initializes template layout
            - Retrieves and orders all tasks
            - Applies filtering based on request parameters
            - Implements pagination
            - Adds create task permission check
    Returns:
        dict: Context containing:
            - filter: Filtered queryset of tasks
            - page_obj: Paginator object with task records
            - can_create_task: Boolean indicating if user can create tasks
    """

    template_name = "etl_app/task/table.html"
    permission_required = "task_app.can_view_tasks"
    page_size = 10

    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context data for template rendering.
        - Initializes template layout
        - Retrieves and orders all tasks
        - Applies filtering based on request parameters
        - Implements pagination
        - Adds create task permission check

        Returns:
            dict: Context containing:
                - filter: Filtered queryset of tasks
                - page_obj: Paginator object with task records
                - can_create_task: Boolean indicating if user can create tasks
        """
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        # Retrieve and order all tasks
        records = Task.objects.all().order_by('-id')
        
        # Apply filtering based on request parameters
        filter = TaskFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs
        
        # Implement pagination
        page_size = int(self.request.GET.get('page_size', self.page_size))
        paginator = Paginator(filtered_records, page_size)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Add create task permission check
        context.update(
            {
                "filter": filter,
                "page_obj": page_obj,
                "can_create_task": self.request.user.has_perm(
                    "task_app.can_create_task"
                ),
                "can_edit_task": self.request.user.has_perm(
                    "task_app.can_edit_task"
                ),
                "can_view_task": self.request.user.has_perm(
                    "task_app.can_view_task"
                ),
                "can_delete_task": self.request.user.has_perm(
                    "task_app.can_delete_task"
                ),
            }
        )
        
        return context

@method_decorator(login_required, name="dispatch")
class TaskDetailView(PermissionRequiredMixin,TemplateView):
    """
    A view class for displaying task details.

    This class handles the display of task-specific information and associated log files.
    Requires user authentication to access the view.

    Attributes:
        template_name (str): The template used for rendering the task detail view.
        page_size (int): Number of items to display per page.
        permission_required (str): The required permission to access this view.

    Methods:
        get_context_data(**kwargs): Prepares and returns the context data for template rendering.

    Parameters:
        kwargs["id"] (int): The ID of the task to be displayed.

    Returns:
        dict: Context dictionary containing:
            - task: Task object retrieved from database
            - log: Content of the task's log file (if exists)
            - WEBSOCKET_HOST: WebSocket host configuration
            - Additional template layout context data
    """
    template_name = "etl_app/task/detail.html"
    permission_required = "task_app.can_view_task"
    page_size = 10

    def get_context_data(self, **kwargs):
        """
        Prepares and returns the context data for template rendering.
        - Initializes template layout
        - Retrieves the task by ID
        - Reads the task's log file if it exists
        - Adds WebSocket host configuration

        Returns:
            dict: Context dictionary containing:
                - task: Task object retrieved from database
                - log: Content of the task's log file (if exists)
                - WEBSOCKET_HOST: WebSocket host configuration
        """
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Retrieve the task by ID
        context["task"] = Task.objects.get(id=kwargs["id"])

        # Read the task's log file if it exists
        log_path = context["task"].log_path
        if log_path and path.isfile(log_path):
            with open(log_path, "r") as log_file:
                log_content = log_file.read()
                # Add color coding
                # Add color coding only to the log level, not the date or the rest of the message
                log_content = re.sub(r'(\[(INFO)\])', r'<span style="color: #4A90E2; font-weight: bold;">\1</span>', log_content)
                log_content = re.sub(r'(\[(WARNING)\])', r'<span style="color: #FDD835; font-weight: bold;">\1</span>', log_content)
                log_content = re.sub(r'(\[(ERROR)\])', r'<span style="color: #E57373; font-weight: bold;">\1</span>', log_content)

                context["log"] = mark_safe(log_content)
                
        # Create context
        context.update(
            {
                "WEBSOCKET_HOST": WEBSOCKET_HOST,
                "can_cancel_task": self.request.user.has_perm(
                    "task_app.can_cancel_task"
                ),
                "can_restart_task": self.request.user.has_perm(
                    "task_app.can_restart_task"
                ),
                "can_resume_task": self.request.user.has_perm(
                    "task_app.can_resume_task"
                ),
                "can_pause_task": self.request.user.has_perm(
                    "task_app.can_pause_task"
                ),
                "can_delete_task": self.request.user.has_perm(
                    "task_app.can_delete_task"
                ),
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class TaskCreateView(PermissionRequiredMixin, TemplateView):
    """
    Class-based view for creating a new task.

    This view requires users to be authenticated and have the 'task_app.can_create_task' permission.
    It renders a form for task creation and handles both GET and POST requests.

    Attributes:
        template_name (str): Path to the template used for rendering the task creation form.
        permission_required (str): Permission required to access this view.

    Methods:
        get_context_data(**kwargs): Adds form and layout context to template context.
        post(request, *args, **kwargs): Handles form submission, saves task if valid, 
            and redirects to task detail view.

    Returns:
        GET: Rendered template with task creation form
        POST: Redirects to task detail view on success, or re-renders form with errors
    """

    template_name = "etl_app/task/create.html"
    permission_required = "task_app.can_create_task"

    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context["form"] = TaskForm()

        return context

    def post(self, request, *args, **kwargs):

        form = TaskForm(request.POST)

        if form.is_valid():
            instance = form.save()
            return redirect(reverse("task_detail", args=[instance.id]))

        # Use get_context_data to include layout_path and other context variables
        context = self.get_context_data(**kwargs)
        context["form"] = form

        return render(request, self.template_name, context)


@method_decorator(login_required, name="dispatch")
class TaskEditView(PermissionRequiredMixin, TemplateView):
    """
    View for editing a user.

    Inherits from:
        PermissionRequiredMixin: Ensures the user has the required permissions.
        TemplateView: Renders a template.

    Attributes:
        template_name (str): The path to the template used for rendering the view.
        permission_required (str): The permission required to access this view.
        form_class (UserEditForm): The form class used for editing the user.

    Methods:
        get_object(): Retrieves the User object or raises a 404 error.
        get_context_data(**kwargs): Adds the UserEditForm to the context.
        post(request, *args, **kwargs): Handles form submission for editing a user.


        Returns:
            User: The user object retrieved by ID.


        Args:
            **kwargs: Additional context data.

        Returns:
            dict: The context data including the form.


        Args:
            request (HttpRequest): The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The HTTP response object.
    """
    template_name = 'etl_app/task/edit.html'
    permission_required = "task_app.change_task"
    permission_required = 'auth.change_user'
    form_class = TaskEditForm

    def get_object(self):
        """
        Retrieve the User object or raise a 404 error.
        """
        instance_id = self.kwargs.get('id')
        return get_object_or_404(Task, id=instance_id)

    def get_context_data(self, **kwargs):
        """
        Add the UserEditForm to the context.
        """
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        instance = self.get_object()
        context['form'] = self.form_class(instance=instance, user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        """
        Handle form submission for editing a user.
        """
        user = self.get_object()
        form = self.form_class(request.POST, instance=user, user=request.user)

        if form.is_valid():
            form.save()
            return redirect(reverse("task_detail", args=[user.id]))

        # Re-render the form with errors
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


###
#
#   Actions
#
##


@login_required
@require_GET
def task_restart(request, id):
    """
    Restart a task instance and redirect to task detail page.
    This view requires user authentication and 'can_restart_task' permission.
    It retrieves a task by ID, calls its restart method, and redirects to the task detail page.
    Args:
        request: The HTTP request object
        id (int): The ID of the task to restart
    Returns:
        HttpResponseRedirect: Redirects to the task detail page
    Raises:
        PermissionDenied: If user doesn't have 'can_restart_task' permission
        Http404: If task with given ID is not found
    Requires:
        - User must be logged in (@login_required)
        - Request method must be GET (@require_GET)
        - User must have 'task_app.can_restart_task' permission
    """

    if not request.user.has_perm("task_app.can_restart_task"):
        raise PermissionDenied

    instance = get_object_or_404(Task, id=id)
    instance.restart()

    
    return redirect(reverse("task_detail", args=[instance.id]))
    

@login_required
@require_GET
def task_cancel(request, id):
    """
    Cancel a task and redirect to task detail page.
    This view cancels a specific task and redirects to the task detail page. It requires login and GET method.
    Only users with 'can_cancel_task' permission can access this view.
    Args:
        request (HttpRequest): The HTTP request object
        id (int): The ID of the task to be cancelled
    Returns:
        HttpResponseRedirect: Redirects to the task detail page
    Raises:
        PermissionDenied: If user doesn't have required permission
        Http404: If task with given ID doesn't exist
    Required Permissions:
        - task_app.can_cancel_task
    Decorators:
        - @login_required
        - @require_GET
    """
    if not request.user.has_perm("task_app.can_cancel_task"):
        raise PermissionDenied

    instance = get_object_or_404(Task, id=id)
    instance.cancel()
    
    return redirect(reverse("task_detail", args=[instance.id]))
    

@login_required
@require_GET
def task_delete(request, id):
    """
    Delete a task instance.
    This view function handles the deletion of a Task object. It requires the user to be
    authenticated and to have the 'can_delete_task' permission. If the task with the given ID
    exists, it will be deleted and the user will be redirected to the tasks list page.
    Args:
        request (HttpRequest): The HTTP request object.
        id (int): The ID of the task to be deleted.
    Returns:
        HttpResponseRedirect: Redirects to the tasks list page after successful deletion.
    Raises:
        PermissionDenied: If the user doesn't have the required permission.
        Http404: If the task with the given ID doesn't exist.
    """
    if not request.user.has_perm("task_app.can_delete_task"):
        raise PermissionDenied

    instance = get_object_or_404(Task, id=id)
    instance.delete()
    return redirect("tasks")



@login_required
@require_GET
def task_pause(request, id):

    if not request.user.has_perm("task_app.can_pause_task"):
        raise PermissionDenied

    instance = get_object_or_404(Task, id=id)
    instance.pause()
    return redirect(reverse("task_detail", args=[instance.id]))

@login_required
@require_GET
def task_resume(request, id):

    if not request.user.has_perm("task_app.can_resume_task"):
        raise PermissionDenied

    instance = get_object_or_404(Task, id=id)
    instance.resume()
    return redirect(reverse("task_detail", args=[instance.id]))


@login_required
@require_GET
def download_log(request, id):
    task = get_object_or_404(Task, id=id)  # Assuming you have a Task model

    if path.exists(task.log_path):
        # Open the log file in binary mode
        with open(task.log_path, 'rb') as log_file:
            response = HttpResponse(log_file.read(), content_type='text/plain')
            # Set the Content-Disposition header to indicate a file download
            response['Content-Disposition'] = f'attachment; filename="task_{id}_log.txt"'
            return response
    else:
        return HttpResponse('Log file not found.', status=404)