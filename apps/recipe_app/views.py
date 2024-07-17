from django.shortcuts import render,redirect,get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.views import View
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.generic import TemplateView

from web_project import TemplateLayout

from apps.etl_app.forms import TaskForm
from apps.etl_app.filters import TaskFilter
from apps.etl_app.models import Task
from apps.recipe_app.models import Recipe
from apps.recipe_app.filters import RecipeFilter
from apps.common.constants import WEBSOCKET_HOST   


from os import path





###
#
#   Views
#
##

@method_decorator(login_required, name='dispatch')
class RecipeTableView(TemplateView):
    template_name = 'recipe_app/recipe/table.html'
    page_size = 10

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        records = Recipe.objects.all().order_by('-id')
        filter = RecipeFilter(self.request.GET, queryset=records)
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
class RecipeTaskTableView(TemplateView):
    template_name = 'recipe_app/etl_recipe/table.html'
    page_size = 10

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        records = Task.objects.all().order_by('-id')
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
    
#@method_decorator(login_required, name='dispatch')
class RecipeTaskDetailView(TemplateView):
    template_name = 'recipe_app/etl_recipe/task_detail.html'
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
    
    
#@method_decorator(login_required, name='dispatch')
class RecipeTaskCreateView(TemplateView):
    template_name = 'recipe_app/etl_recipe/task_create.html'

    
    
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
 
 
###
#
#   Functions
#
##





###
#
#   Actions
#
##   

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

