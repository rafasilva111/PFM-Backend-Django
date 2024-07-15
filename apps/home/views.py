from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from web_project import TemplateLayout
from django.views import View
from django.shortcuts import render
from web_project.template_helpers.theme import TemplateHelper
import markdown
"""
This file is a view controller for multiple pages as a module.
Here you can override the page view layout.
Refer to dashboards/urls.py file for more pages.
"""

@method_decorator(login_required, name='dispatch')
class DashboardsView(TemplateView):
    template_name = 'dashboard_analytics.html' 
    # Predefined function
    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        return context

## TODO For dev usege LoginRequiredMixin is not required

@method_decorator(login_required, name='dispatch')
class ReadMeView(TemplateView):
    template_name = 'readme.html' 

    def get_context_data(self, **kwargs):
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        
        with open('README.md', 'r') as f:  # Adjust the file path as needed
            readme_content = f.read()
        html_content = markdown.markdown(readme_content)
        context.update({
            "layout_path": TemplateHelper.set_layout("layout_vertical.html", context),
            'html_content': html_content,
        })
        
    
        return context
