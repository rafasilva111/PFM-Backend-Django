###
#       General imports
##


##
#   Default
#

from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
import markdown
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.http import JsonResponse

##
#   Extras
#

from web_project import TemplateLayout, TemplateHelper
from datetime import datetime, timedelta

###
#       App specific imports
##


##
#   Models
#

from apps.user_app.models import User
from apps.etl_app.models import Task, Job

##
#   Serializers
#


##
#   Forms
#

from apps.common.forms import LoginForm, RegisterForm, ResetForm, SetPasswordForm


##
#   Functions
#


##
#   Contants
#




###
#
#       Others Views 
#   
##



@method_decorator(login_required, name="dispatch")
class DashboardsView(TemplateView):
    template_name = "dashboard_analytics.html" 
    # Predefined function
    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context["user"] = self.request.user

        context["tasks_count_in_this_month"] = Task.objects.filter(created_at__month=datetime.now().month).count()
        context["jobs_count_in_this_month"] = Job.objects.filter(created_at__month=datetime.now().month).count()
        
        homologous_date = datetime.now() - timedelta(days=365)
        task_count_one_year_ago = Task.objects.filter(Q(created_at__month = homologous_date.month) & Q(created_at__year=homologous_date.year)).count() 
        task_count_one_year_ago = task_count_one_year_ago if task_count_one_year_ago > 0 else 1
        jobs_count_one_year_ago = Job.objects.filter(Q(created_at__month =homologous_date.month) & Q(created_at__year=homologous_date.year)).count()
        jobs_count_one_year_ago = jobs_count_one_year_ago if jobs_count_one_year_ago > 0 else 1

        context["tasks_count_growth"] = context["tasks_count_in_this_month"] / task_count_one_year_ago * 100
        context["jobs_count_growth"] = context["jobs_count_in_this_month"] / jobs_count_one_year_ago * 100
        
        #   Tasks Statistics
        
        context["tasks_count"] = Task.objects.all().count()
        context["jobs_count"] = Job.objects.all().count()
        
        task_counts = [
            (Task.objects.filter(type=Task.TaskType.EXTRACT).count(), "Extract Tasks"),
            (Task.objects.filter(type=Task.TaskType.TRANSFORM).count(), "Transform Tasks"),
            (Task.objects.filter(type=Task.TaskType.LOAD).count(), "Large Tasks"),
            (Task.objects.filter(type=Task.TaskType.FULL_PROCESS).count(), "Full Process Tasks"),
            (Task.objects.filter(type=Task.TaskType.TEST).count(), "Test Tasks"),
            (Task.objects.filter(type=Task.TaskType.FAILURE).count(), "Failure Tasks"),
            (Task.objects.filter(type=Task.TaskType.EMPTY).count(), "Empty Tasks"),
        ]

        # Sort the task counts by the count in descending order
        task_counts.sort(key=lambda x: x[0], reverse=True)

        context["task_counts_statistics"] = task_counts
        
        # Lastest Activities
        latest_tasks = list(Task.objects.all().order_by("-created_at",)[:10])
        latest_jobs = list(Job.objects.all().order_by("-created_at")[:10])
        latest_activities = sorted(latest_tasks + latest_jobs, key=lambda x: x.created_at, reverse=True)[:7]
        context["latest_activities"] = latest_activities
        
        return context


###
#
#   Error Views
#
##


class Custom403View(TemplateView):
    template_name = "common/page_error.html"
    status_code = 403

    def get(self, request, *args, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context.update({
            "layout_path": TemplateHelper.set_layout("layout_blank.html", context),
            "title": "403 Forbidden 🚫",
            "description": "Oops! You don’t have permission to access this page.\n\
              If you think this is a mistake, please contact support.",
        })
        
        return self.render_to_response(context, status=403)
    
class Custom500View(TemplateView):
    template_name = "common/page_error.html"
    status_code = 500 

    def __init__(self, **kwargs):
        self.status_code = kwargs.pop('status_code', self.status_code)
        super().__init__(**kwargs)

    def get(self, request, *args, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context.update({
            "layout_path": TemplateHelper.set_layout("layout_blank.html", context),
            "title": "Oops! Something went wrong. ⚠️",
            "description": "We're sorry, but it seems the page you're looking for cannot be found or there was an issue with your request.",
        })
        return self.render_to_response(context, status=self.status_code)


###
#
#   Miscellaneous
#
##

@method_decorator(login_required, name="dispatch")
class ReadMeView(TemplateView):
    template_name = "readme.html" 

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        
        with open("README.md", "r") as f:  # Adjust the file path as needed
            readme_content = f.read()
        html_content = markdown.markdown(readme_content)
        context.update({
            "layout_path": TemplateHelper.set_layout("layout_vertical.html", context),
            "html_content": html_content,
        })
        
    
        return context

class TermsAndConditionsView(TemplateView):
    template_name = "common/miscellaneous/terms_and_conditions.html"
    
    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['layout_path']  = TemplateHelper.set_layout("layout_blank.html", context)
        # Add previous page URL to context if available
        context['previous_page'] = self.request.META.get('HTTP_REFERER')
        return context
    
@login_required
@require_GET
def total_task_report_chart_data(request):
    """
    Generates chart data for total tasks report for a given year.

    Args:
        request (HttpRequest): The HTTP request object.
        year (int or str): The year for which the report is generated.

    Returns:
        JsonResponse: A JSON response containing the available years and datasets.
            The response structure is as follows:
                "available_years": [list of years with task data available],
                        "name": "current_year",
                        "data": [list of task counts for each month of the current year]
    """
    current_year =  datetime.now().year
    five_years_ago = datetime.now().year - 5
    
    available_years = list(
        Task.objects.filter(created_at__year__gte=five_years_ago)
        .dates('created_at', 'year')
        .distinct()
        .values_list('created_at__year', flat=True)
    )

    data = {
        "available_years": available_years,
        "datasets": [
            {
                "name": str(current_year),
                "data": [
                    Task.objects.filter(created_at__year=current_year, created_at__month=month).count()
                    for month in range(1, 13)
                ],
            }
        ]
    }
    return JsonResponse(data, safe=False)


@login_required
@require_GET 
def total_task_chart_data(request):
    
    one_week_ago = datetime.now() - timedelta(days=7)
    two_weeks_ago = datetime.now() - timedelta(days=14)
    task_count_last_week = Task.objects.filter(created_at__gte=two_weeks_ago, created_at__lt=one_week_ago).count()
    task_count_last_week = task_count_last_week if task_count_last_week > 0 else 1
    task_current_week = Task.objects.filter(created_at__gte=one_week_ago)
    task_count_current_week = Task.objects.filter(created_at__gte=one_week_ago).count()
    
    data = {
        "series": [
            task_current_week.filter(type=Task.TaskType.EXTRACT).count(),
            task_current_week.filter(type=Task.TaskType.TRANSFORM).count(),
            task_current_week.filter(type=Task.TaskType.LOAD).count(),
            task_current_week.filter(type=Task.TaskType.FULL_PROCESS).count(),
            task_current_week.filter(type=Task.TaskType.TEST).count(),
            task_current_week.filter(type=Task.TaskType.FAILURE).count(),
            task_current_week.filter(type=Task.TaskType.EMPTY).count()
            ],  # Example data, replace with actual data
        "total": task_current_week.count(),
        "growth": task_count_current_week / task_count_last_week * 100
        
           
    }
    return JsonResponse(data)