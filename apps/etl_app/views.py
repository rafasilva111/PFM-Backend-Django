from django.shortcuts import render,redirect,get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.views import View
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.generic import TemplateView

from web_project import TemplateLayout

from apps.etl_app.forms import TaskForm, JobForm
from apps.etl_app.filters import JobFilter,TaskFilter
from apps.etl_app.models import Job
from apps.recipe_app.models import Recipe
from apps.recipe_app.filters import RecipeFilter
from apps.common.constants import WEBSOCKET_HOST   
# Create your views here.



class JobTableView(TemplateView):
    template_name = 'etl_app/job/table.html'
    page_size = 10

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        records = Job.objects.all().order_by('-id')
        filter = JobFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs
        
        #

        page_size = int(self.request.GET.get('page_size',self.page_size))
            
        paginator = Paginator(filtered_records, page_size)  # Show 10 tasks per page
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['filter'] = filter
        context['page_obj'] = page_obj
        
        return context
    
#@method_decorator(login_required, name='dispatch')
class JobCreateView(TemplateView):
    template_name = 'etl_app/job/job_create.html'
    
    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['form'] = JobForm()
        
        return context

    def post(self, request, *args, **kwargs):
        form = JobForm(request.POST)
        if form.is_valid():
            instance =form.save()  
            return redirect(reverse('job_detail', args=[instance.id]))

        return render(request, self.template_name, {'form': form})
    

#@method_decorator(login_required, name='dispatch')
class JobDetailView(TemplateView):
    template_name = 'etl_app/job/job_detail.html'
    page_size = 10

    def get_context_data(self, **kwargs):
        
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['record'] = Job.objects.get(id=kwargs['id'])


        records = context['record'].tasks.all().order_by('-started_at')
        filter = TaskFilter(self.request.GET, queryset=records)
        filtered_records = filter.qs
        
        #

        page_size = int(self.request.GET.get('page_size',self.page_size))
            
        paginator = Paginator(filtered_records, page_size)  # Show 10 tasks per page
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['filter'] = filter
        context['page_obj'] = page_obj

        context['WEBSOCKET_HOST'] =  WEBSOCKET_HOST
        
        return context




###
#
#   Actions
#
## 


@require_GET
def job_resume(request, id):
    job = get_object_or_404(Job, id=id)
    job.resume_task()

    return redirect(reverse('job_detail', args=[job.id]))


@require_GET
def job_pause(request, id):
    job = get_object_or_404(Job, id=id)
    job.pause_task()

    return redirect(reverse('job_detail', args=[job.id]))

@login_required
@require_GET
def job_delete(request, id):
    instance = get_object_or_404(Job, id=id)
    instance.delete()
    
    return redirect('job')