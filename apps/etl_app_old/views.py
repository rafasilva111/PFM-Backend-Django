from django.shortcuts import render,redirect,get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.views import View
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.generic import TemplateView

from web_project import TemplateLayout

from apps.etl_app.forms import TaskForm, JobForm,MaxRecordsConditionForm,TimeConditionForm
from apps.etl_app.filters import JobFilter,TaskFilter
from apps.etl_app.models import Job
from apps.recipe_app.models import Recipe
from apps.recipe_app.filters import RecipeFilter
from apps.common.constants import WEBSOCKET_HOST   
# Create your views here.


#@method_decorator(login_required, name='dispatch')
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
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        context['form'] = JobForm()
        context['starting_condition_time_form'] = TimeConditionForm(prefix='starting_condition_time_form')
        context['stopping_condition_time_form'] = TimeConditionForm(prefix='stopping_condition_time_form')
        context['stopping_condition_max_records_form'] = MaxRecordsConditionForm(prefix='stopping_condition_max_records_form')
        return context

    def post(self, request, *args, **kwargs):
        job_form = JobForm(request.POST)
        starting_time_condition_form = TimeConditionForm(request.POST, prefix='starting_condition_time_form')
        stopping_time_condition_form = TimeConditionForm(request.POST, prefix='stopping_condition_time_form')
        stopping_condition_max_records_form = MaxRecordsConditionForm(request.POST, prefix='stopping_condition_max_records_form')

        if job_form.is_valid() :
            starting_condition_form = None
            stopping_condition_form = None
            
            teste = job_form.instance
            
            # Save the starting condition
            
            if job_form.instance.starting_condition_type and job_form.instance.starting_condition_type.name =='time condition': 
                if starting_time_condition_form.is_valid():
                
                    starting_condition_form = starting_time_condition_form
                else:
                    # Collect all errors if any form is invalid
                    context = self.get_context_data()
                    context['form'] = job_form
                    context['starting_condition_time_form'] = starting_time_condition_form
                    context['stopping_condition_time_form'] = stopping_time_condition_form
                    context['stopping_condition_max_records_form'] = stopping_condition_max_records_form
                    
                    return self.render_to_response(context)
                
            # Save the stopping time condition
            
            if job_form.instance.stopping_condition_type: 
                
                if job_form.instance.stopping_condition_type.name =='time condition':
                    if stopping_time_condition_form.is_valid():
                        stopping_condition_form = stopping_time_condition_form
                    else:
                        # Collect all errors if any form is invalid
                        context = self.get_context_data()
                        context['form'] = job_form
                        context['starting_condition_time_form'] = starting_time_condition_form
                        context['stopping_condition_time_form'] = stopping_time_condition_form
                        context['stopping_condition_max_records_form'] = stopping_condition_max_records_form
                        
                        return self.render_to_response(context)
                
                elif job_form.instance.stopping_condition_type.name =='max records condition':
                    stopping_condition_form = MaxRecordsConditionForm(request.POST, prefix='stopping_condition_max_records_form')
                    
                    if stopping_condition_max_records_form.is_valid():
                        stopping_condition_form = stopping_condition_max_records_form
                    # Collect all errors if any form is invalid
                    else:
                        context = self.get_context_data()
                        context['form'] = job_form
                        context['starting_condition_time_form'] = starting_time_condition_form
                        context['stopping_condition_time_form'] = stopping_time_condition_form
                        context['stopping_condition_max_records_form'] = stopping_condition_max_records_form
                        
                        return self.render_to_response(context)

                
            job = job_form.save(starting_condition_form,stopping_condition_form)
            
            return redirect(reverse('job_detail', args=[job.id]))

        # Collect all errors if any form is invalid
        context = self.get_context_data()
        context['form'] = job_form
        context['starting_condition_time_form'] = starting_time_condition_form
        context['stopping_condition_time_form'] = stopping_time_condition_form
        context['stopping_condition_max_records_form'] = stopping_condition_max_records_form

        return self.render_to_response(context)
    

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