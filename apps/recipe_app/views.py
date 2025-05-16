##
#       General imports
##


##
#   Default
#

from web_project import TemplateLayout

##
#   Django
#

from django.shortcuts import render,redirect,get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.views import View
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib import messages
from web_project import TemplateLayout

from apps.etl_app.forms import TaskForm
from apps.etl_app.filters import TaskFilter
from apps.etl_app.models import Task
from apps.recipe_app.models import Recipe, RecipeReport, RecipeAuditLog
from apps.recipe_app.filters import RecipeFilter, RecipeAuditLogFilter, RecipeAuditLogStatusHistoryFilter
from apps.recipe_app.forms import RecipeReportForm
from apps.common.constants import WEBSOCKET_HOST   

from firebase_admin import  storage

from os import path



from datetime import  timedelta


###
#
#   Views
#
##



###
#   General
##


@method_decorator(login_required, name='dispatch')
class RecipeTableView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/recipe/table.html'
    permission_required = "task_app.can_view_recipes"
    page_size = 10

    def get_context_data(self, **kwargs):
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        # Retrieve and order all tasks
        records = Recipe.objects.all().order_by('-id')
        
        # Apply filtering based on request parameters
        filter = RecipeFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs

        # Implement pagination 
        paginator = Paginator(
            filtered_records, 
            self.request.GET.get("page_size", self.page_size)
        )
        page_obj = paginator.get_page(self.request.GET.get("page"))
        
        # Created context
        context.update(
            {
                "filter": filter,
                "total_count": paginator.count,
                "page_obj": page_obj,
                "can_view_recipe": self.request.user.has_perm(
                    "recipe_app.can_view_recipe"
                ),
                "can_edit_recipe": self.request.user.has_perm(
                    "recipe_app.can_edit_recipe"
                ),
                "can_delete_recipe": self.request.user.has_perm(
                    "recipe_app.can_delete_recipe"
                ),
            }
        )
        
        return context

@method_decorator(login_required, name='dispatch')
class RecipeDetailView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/recipe/detail.html'
    permission_required = "task_app.can_view_recipe"
    page_size = 10

    def get_context_data(self, **kwargs):
        
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Retrieve and order all tasks
        instance = Recipe.objects.get(id=kwargs['id'])

        # Image

        ## Reference to the image file in Firebase Storage
        if instance.image:
            bucket = storage.bucket()
            blob = bucket.blob(instance.image)
            
            # Get the download URL
            context['image_url'] = blob.generate_signed_url(timedelta(minutes=15))

        # Retrieve and order all instances
        report_instances = instance.reports.all().order_by('-created_at')
        audit_log_instances = instance.audit_logs.all().order_by('-created_at')
        
        # Apply filtering based on request parameters
        audit_log_filter = RecipeAuditLogFilter(self.request.GET, queryset=audit_log_instances)
        filtered_audit_log_instances = audit_log_filter.qs
        report_filter = RecipeFilter(self.request.GET, queryset=report_instances)
        filtered_report_instances = report_filter.qs
        
        # Implement Pagination
        audit_log_paginator = Paginator(
            filtered_audit_log_instances,
            per_page=self.request.GET.get('page_size',self.page_size)
        )  
        audit_log_page_obj = audit_log_paginator.get_page(
            number = self.request.GET.get('page')
        )
        report_paginator = Paginator(
            filtered_report_instances,
            per_page=self.request.GET.get('page_size',self.page_size)
        )
        report_page_obj = report_paginator.get_page(
            number = self.request.GET.get('page')
        )
        
        # Created context
        context.update(
            {
                "instance": instance,
                "audit_log_filter": audit_log_filter,
                "audit_log_page_obj": audit_log_page_obj,
                "can_view_audit_log": self.request.user.has_perm(
                    "recipe_app.can_view_audit_log"
                ),
                "can_accept_audit_log": self.request.user.has_perm(
                    "recipe_app.can_accept_audit_log"
                ),
                "can_unaccept_audit_log": self.request.user.has_perm(
                    "recipe_app.can_unaccept_audit_log"
                ),
                "can_review_audit_log": self.request.user.has_perm(
                    "recipe_app.can_review_audit_log"
                ),
                "can_unreview_audit_log": self.request.user.has_perm(
                    "recipe_app.can_unreview_audit_log"
                ),
                "can_delete_audit_log": self.request.user.has_perm(
                    "recipe_app.can_delete_audit_log"
                ),
                "report_filter": report_filter,
                "report_page_obj": report_page_obj,            
            }
        )
        
        return context


@login_required
@require_GET
def recipe_edit(request, id):

    return redirect(request.path)

@login_required
@require_GET
def recipe_delete(request, id):
    
    instance = get_object_or_404(Task, id=id)
    instance.delete()

    return redirect('recipes')



###
#   ETL Tasks
##


@method_decorator(login_required, name='dispatch')
class RecipeTaskTableView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/etl_recipe/table.html'
    permission_required = "task_app.can_view_tasks"
    page_size = 10

    def get_context_data(self, **kwargs):
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Retrieve and order all instances
        records = Task.objects.all().order_by('-id')
        
        # Apply filtering based on request parameters
        filter = TaskFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs

        # Implement pagination 
        paginator = Paginator(
            filtered_records, 
            self.request.GET.get("page_size", self.page_size)
        )
        page_obj = paginator.get_page(self.request.GET.get("page"))
        
        
        # Add create task permission check
        context.update(
            {
                "filter": filter,
                "total_count": paginator.count,
                "page_obj": page_obj,
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
    
@method_decorator(login_required, name='dispatch')
class RecipeTaskDetailView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/etl_recipe/task_detail.html'
    permission_required = "task_app.can_view_task"
    page_size = 10

    def get_context_data(self, **kwargs):
        
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['task'] = Task.objects.get(id=kwargs['id'])
        
        log_path = context['task'].log_path

        if log_path and path.isfile(log_path):
            with open(log_path, 'r') as log_file:
                context['log'] = log_file.read()  # Read the entire content of the log file

        
        context['WEBSOCKET_HOST'] =  WEBSOCKET_HOST
        
        return context
    
    
@method_decorator(login_required, name='dispatch')
class RecipeTaskCreateView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/etl_recipe/task_create.html'
    permission_required = "task_app.can_create_task"
    
    
    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['form'] = TaskForm()
        
        return context

    def post(self, request, *args, **kwargs):
        
        form = TaskForm(request.POST)

        if form.is_valid():
            instance = form.save()
            return redirect(reverse('recipe_task_detail', args=[instance.id]))
        
        # Use get_context_data to include layout_path and other context variables
        context = self.get_context_data(**kwargs)
        context['form'] = form

        return render(request, self.template_name, context)
 
#@login_required
@require_GET
def recipe_task_restart(request, id):
    instance = get_object_or_404(Task, id=id)
    
    instance.restart()
    
    return redirect(reverse('recipe_task_detail', args=[instance.id])) 

@require_GET
def recipe_task_pause(request, id):
    instance = get_object_or_404(Task, id=id)
    
    instance.pause()
    
    return redirect(reverse('recipe_task_detail', args=[instance.id])) 

@require_GET
def recipe_task_resume(request, id):
    instance = get_object_or_404(Task, id=id)
    
    instance.resume()
    
    return redirect(reverse('recipe_task_detail', args=[instance.id])) 

@require_GET
def recipe_task_cancel(request, id):
    instance = get_object_or_404(Task, id=id)
    
    instance.cancel()
    
    return redirect(reverse('recipe_task_detail', args=[instance.id])) 

@login_required
@require_GET
def recipe_task_delete(request, id):
    instance = get_object_or_404(Task, id=id)
    
    instance.delete()
    
    return redirect('recipe_tasks')


###
#   Recipe Audit Logs
##


@method_decorator(login_required, name='dispatch')
class AuditLogTableView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/audit_log/table.html'
    permission_required = "task_app.can_view_audit_logs"
    page_size = 10

    def get_context_data(self, **kwargs):
        
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Retrieve and order all tasks
        records = RecipeAuditLog.objects.all().order_by('-id')
        
        # Apply filtering based on request parameters
        filter = RecipeAuditLogFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs
        
        # Implement pagination 
        paginator = Paginator(
            filtered_records, 
            self.request.GET.get("page_size", self.page_size)
        )
        page_obj = paginator.get_page(self.request.GET.get("page"))

        # Created context
        context.update(
            {
                "filter": filter,
                "total_count": paginator.count,
                "page_obj": page_obj,
                "can_view_audit_log": self.request.user.has_perm(
                    "recipe_app.can_view_audit_log"
                ),
                "can_accept_audit_log": self.request.user.has_perm(
                    "recipe_app.can_accept_audit_log"
                ),
                "can_unaccept_audit_log": self.request.user.has_perm(
                    "recipe_app.can_unaccept_audit_log"
                ),
                "can_review_audit_log": self.request.user.has_perm(
                    "recipe_app.can_review_audit_log"
                ),
                "can_unreview_audit_log": self.request.user.has_perm(
                    "recipe_app.can_unreview_audit_log"
                ),
                "can_delete_audit_log": self.request.user.has_perm(
                    "recipe_app.can_delete_audit_log"
                ),
            }
        )
        
        return context

@method_decorator(login_required, name='dispatch')
class AuditLogDetailView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/audit_log/detail.html'
    permission_required = "task_app.can_view_audit_log"
    page_size = 10

    def get_context_data(self, **kwargs):
        
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Retrieve the Job by ID
        instance = RecipeAuditLog.objects.get(id=kwargs["id"])
        
        # Apply filtering based on request parameters
        filter = RecipeAuditLogStatusHistoryFilter(self.request.GET, queryset=instance.status_history.all().order_by('-changed_at'))
        filtered_records = filter.queryset.order_by('-changed_at')
        
        # Implement pagination 
        paginator = Paginator(
            filtered_records, 
            self.request.GET.get("page_size", self.page_size)
        )
        page_obj = paginator.get_page(self.request.GET.get("page"))
        
        # Create context
        context.update(
            {
                "instance": instance,
                "filter": filter,
                "total_count": paginator.count,
                "page_obj": page_obj,
                "can_accept_audit_log": self.request.user.has_perm(
                    "recipe_app.can_accept_audit_log"
                ),
                "can_delete_audit_log": self.request.user.has_perm(
                    "recipe_app.can_delete_audit_log"
                ),
            }
        )
        
        return context
    
@login_required
@require_GET
def audit_log_delete(request, id):

    if not request.user.has_perm("recipe_app.can_delete_audit_log"):
        raise PermissionDenied

    instance = get_object_or_404(RecipeAuditLog, id=id)
    
    try:
        instance.delete()
    except ValueError as e:
        messages.error(request, str(e))
        
    return redirect(request.META.get('HTTP_REFERER', 'audit_logs'))

@login_required
@require_GET
def audit_log_accept(request, id):

    if not request.user.has_perm("recipe_app.can_accept_audit_log"):
        raise PermissionDenied

    instance = get_object_or_404(RecipeAuditLog, id=id)
    instance.accept(changed_by=request.user)
    return redirect(request.META.get('HTTP_REFERER', 'audit_logs'))

@login_required
@require_GET
def audit_log_unaccept(request, id):

    if not request.user.has_perm("recipe_app.can_unaccept_audit_log"):
        raise PermissionDenied

    instance = get_object_or_404(RecipeAuditLog, id=id)
    instance.unaccept(changed_by=request.user)
    return redirect(request.META.get('HTTP_REFERER', 'audit_logs'))

@login_required
@require_GET
def audit_log_review(request, id):

    if not request.user.has_perm("recipe_app.can_review_audit_log"):
        raise PermissionDenied

    instance = get_object_or_404(RecipeAuditLog, id=id)
    instance.review(changed_by=request.user)
    return redirect(request.META.get('HTTP_REFERER', 'audit_logs'))

@login_required
@require_GET
def audit_log_unreview(request, id):

    if not request.user.has_perm("recipe_app.can_unreview_audit_log"):
        raise PermissionDenied

    instance = get_object_or_404(RecipeAuditLog, id=id)
    instance.unreview(changed_by=request.user)
    return redirect(request.META.get('HTTP_REFERER', 'audit_logs'))


###
#   Recipe Reports
##



@method_decorator(login_required, name='dispatch')
class RecipeReportTableView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/report/table.html'
    permission_required = "task_app.can_view_recipe_reports"
    page_size = 10

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        records = RecipeReport.objects.all().order_by('-id')
        filter = TaskFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs
        
        #

        page_size = int(self.request.GET.get('page_size',self.page_size))
            
        paginator = Paginator(filtered_records, page_size)  # Show 10 tasks per page
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['filter'] = filter
        context['page_obj'] = page_obj
        
        return context



@method_decorator(login_required, name='dispatch')
class RecipeReportDetailView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/report/report_detail.html'
    permission_required = "task_app.can_view_recipe_report"
    page_size = 10

    def get_context_data(self, **kwargs):
        
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['task'] = RecipeReport.objects.get(id=kwargs['id'])
        
        
        return context

@method_decorator(login_required, name='dispatch')
class RecipeReportCreateView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/report/report_create.html'
    permission_required = "task_app.can_create_recipe_report"
    page_size = 10

    def get_context_data(self, **kwargs):
        
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['record'] = Recipe.objects.get(id=kwargs['id'])
        context['form'] = RecipeReportForm()
        
        return context
    
    
    def post(self, request, *args, **kwargs):

        form_data = request.POST.copy()
        form_data['recipe'] = kwargs.get('id') 
        form_data['user'] = request.user.id 
        print(form_data['user']  )
        print(form_data)
        form = RecipeReportForm(form_data) 

        if form.is_valid():
            instance = form.save()
            return redirect(reverse('recipe_report_detail', args=[instance.id]))

        
        # Use get_context_data to include layout_path and other context variables
        context = self.get_context_data(**kwargs)
        context['form'] = form

        return render(request, self.template_name, context)
    



