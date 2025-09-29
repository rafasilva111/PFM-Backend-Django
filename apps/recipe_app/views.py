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

from apps.user_app.models import User
from apps.etl_app.forms import TaskForm
from apps.etl_app.filters import TaskFilter
from apps.etl_app.models import Task
from apps.recipe_app.models import Recipe, RecipeReport, RecipeAuditLog
from apps.recipe_app.filters import RecipeFilter, RecipeAuditLogFilter, RecipeAuditLogStatusHistoryFilter, RecipeReportFilter
from apps.recipe_app.forms import RecipeReportForm
from apps.common.constants import WEBSOCKET_URL   
from django.contrib.auth.decorators import permission_required
from firebase_admin import  storage

from os import path



from datetime import  timedelta


###
#
#   Views
#
##



###
#   Recipe
##


@method_decorator(login_required, name='dispatch')
class RecipeTableView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/recipe/table.html'
    permission_required = "recipe_app.can_view_recipes"
    page_size = 10

    def get_context_data(self, **kwargs):
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        # Retrieve and order all tasks
        records = Recipe.objects.all().order_by('-id')
        
        # Company users should only see recipes from their own company
        if self.request.user.type in [User.UserType.COMPANY_ADMIN, User.UserType.COMPANY_STAFF]:
            records = records.filter(company=self.request.user.company)
        
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
        
        # Retrieve Recipe instance, if company user filter by company
        filters = {"id": kwargs["id"]}
        if self.request.user.type in [User.UserType.COMPANY_ADMIN, User.UserType.COMPANY_STAFF]:
            filters["company"] = self.request.user.company
        instance = get_object_or_404(Recipe, **filters)

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
@permission_required("recipe_app.can_delete_recipe",raise_exception=True)
def recipe_delete(request, id):
    
    instance = get_object_or_404(Recipe, id=id)
    instance.delete()

    return redirect('recipes')


###
#   Recipe Audit Logs
##


@method_decorator(login_required, name='dispatch')
class AuditLogTableView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/audit_log/table.html'
    permission_required = "recipe_app.can_view_audit_logs"
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
    permission_required = "recipe_app.can_view_audit_log"
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
@permission_required("recipe_app.can_delete_audit_log",raise_exception=True)
def audit_log_delete(request, id):

    instance = get_object_or_404(RecipeAuditLog, id=id)
    
    try:
        instance.delete()
    except ValueError as e:
        messages.error(request, str(e))
        
    return redirect(request.META.get('HTTP_REFERER', 'audit_logs'))

@login_required
@require_GET
@permission_required("recipe_app.can_accept_audit_log",raise_exception=True)
def audit_log_accept(request, id):


    instance = get_object_or_404(RecipeAuditLog, id=id)
    instance.accept(changed_by=request.user)
    return redirect(request.META.get('HTTP_REFERER', 'audit_logs'))

@login_required
@require_GET
@permission_required("recipe_app.can_unaccept_audit_log",raise_exception=True)
def audit_log_unaccept(request, id):

    instance = get_object_or_404(RecipeAuditLog, id=id)
    instance.unaccept(changed_by=request.user)
    return redirect(request.META.get('HTTP_REFERER', 'audit_logs'))

@login_required
@require_GET
@permission_required("recipe_app.can_review_audit_log",raise_exception=True)
def audit_log_review(request, id):

    instance = get_object_or_404(RecipeAuditLog, id=id)
    instance.review(changed_by=request.user)
    return redirect(request.META.get('HTTP_REFERER', 'audit_logs'))

@login_required
@require_GET
@permission_required("recipe_app.can_unreview_audit_log",raise_exception=True)
def audit_log_unreview(request, id):

    instance = get_object_or_404(RecipeAuditLog, id=id)
    instance.unreview(changed_by=request.user)
    return redirect(request.META.get('HTTP_REFERER', 'audit_logs'))


###
#   Recipe Reports
##



@method_decorator(login_required, name='dispatch')
class RecipeReportTableView(PermissionRequiredMixin, TemplateView):
    template_name = 'recipe_app/report/table.html'
    permission_required = "recipe_app.can_view_recipe_reports"
    page_size = 10

    def get_context_data(self, **kwargs):
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        # Retrieve and order all recipe reports
        records = RecipeReport.objects.all().order_by('-id')
        record = list(records)

        # Filter by company for company users
        if self.request.user.type in [User.UserType.COMPANY_ADMIN, User.UserType.COMPANY_STAFF]:
            records = records.filter(recipe__company=self.request.user.company)
        
        # Filter by user
        if self.request.user.type == User.UserType.NORMAL:
            records = records.filter(user=self.request.user)
        
        # Apply filtering based on request parameters
        filter = RecipeReportFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs

        # Implement pagination
        paginator = Paginator(
            filtered_records,
            self.request.GET.get("page_size", self.page_size)
        )
        page_obj = paginator.get_page(self.request.GET.get("page"))

        # Update context with filter, pagination, and permissions
        context.update(
            {
                "filter": filter,
                "total_count": paginator.count,
                "page_obj": page_obj,
                "can_view_recipe_report": self.request.user.has_perm(
                    "recipe_app.can_view_recipe_report"
                ),
                "can_create_recipe_report": self.request.user.has_perm(
                    "recipe_app.can_create_recipe_report"
                ),
                "can_review_recipe_report": self.request.user.has_perm(
                    "recipe_app.can_review_recipe_report"
                ),
                "can_unreview_recipe_report": self.request.user.has_perm(
                    "recipe_app.can_unreview_recipe_report"
                ),
                "can_delete_recipe_report": self.request.user.has_perm(
                    "recipe_app.can_delete_recipe_report"
                ),
            }
        )

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
        form = RecipeReportForm(form_data) 

        if form.is_valid():
            instance = form.save()
            return redirect(reverse('recipe_report_detail', args=[instance.id]))

        
        # Use get_context_data to include layout_path and other context variables
        context = self.get_context_data(**kwargs)
        context['form'] = form

        return render(request, self.template_name, context)

@login_required
@require_GET
@permission_required("recipe_app.can_delete_recipe_report",raise_exception=True)
def recipe_report_delete(request, id):
    
    instance = get_object_or_404(RecipeReport, id=id)
    instance.delete()
    return redirect('recipe_reports')

@login_required
@require_GET
@permission_required("recipe_app.can_review_recipe_report",raise_exception=True)
def recipe_report_review(request, id):

    instance = get_object_or_404(RecipeReport, id=id)
    instance.review(reviewed_by=request.user)
    return redirect(request.META.get('HTTP_REFERER', 'recipe_reports'))

@login_required
@require_GET
@permission_required("recipe_app.can_unreview_recipe_report",raise_exception=True)
def recipe_report_unreview(request, id):

    instance = get_object_or_404(RecipeReport, id=id)
    instance.unreview()
    return redirect(request.META.get('HTTP_REFERER', 'recipe_reports'))

