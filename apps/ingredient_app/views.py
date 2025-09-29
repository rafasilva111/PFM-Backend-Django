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
from django.views.decorators.http import require_GET
from django.views import View
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib import messages
from web_project import TemplateLayout

from apps.user_app.models import User
from django.contrib.auth.decorators import permission_required
from firebase_admin import  storage

from os import path

from apps.ingredient_app.models import Ingredient
from apps.ingredient_app.filters import IngredientFilter



from datetime import  timedelta


###
#
#   Views
#
##



###
#   Ingredient
##

@method_decorator(login_required, name='dispatch')
class IngredientTableView(PermissionRequiredMixin, TemplateView):
    template_name = 'ingredient_app/ingredient/table.html'
    permission_required = "ingredient_app.can_view_ingredients"
    page_size = 10

    def get_context_data(self, **kwargs):
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        # Retrieve and order all tasks
        records = Ingredient.objects.all().order_by('-id')
        
        # Company users should only see ingredients from their own company
        if self.request.user.type in [User.UserType.COMPANY_ADMIN, User.UserType.COMPANY_STAFF]:
            records = records.filter(company=self.request.user.company)
        
        # Apply filtering based on request parameters
        filter = IngredientFilter(self.request.GET, queryset=records)
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
                "can_view_ingredient": self.request.user.has_perm(
                    "ingredient_app.can_view_ingredient"
                ),
                "can_delete_ingredient": self.request.user.has_perm(
                    "ingredient_app.can_delete_ingredient"
                ),
            }
        )
        
        return context

@method_decorator(login_required, name='dispatch')
class IngredientDetailView(PermissionRequiredMixin, TemplateView):
    template_name = 'ingredient_app/ingredient/detail.html'
    permission_required = "ingredient_app.can_view_ingredient"
    page_size = 10

    def get_context_data(self, **kwargs):
        
        # Initialize template layout
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))
        
        # Retrieve Ingredient instance, if company user filter by company
        filters = {"id": kwargs["id"]}
        if self.request.user.type in [User.UserType.COMPANY_ADMIN, User.UserType.COMPANY_STAFF]:
            filters["company"] = self.request.user.company
        instance = get_object_or_404(Ingredient, **filters)

        # Image

        ## Reference to the image file in Firebase Storage
        if instance.image:
            bucket = storage.bucket()
            blob = bucket.blob(instance.image)
            
            # Get the download URL
            context['image_url'] = blob.generate_signed_url(timedelta(minutes=15))

        # Created context
        context.update(
            {
                "instance": instance,          
            }
        )
        
        return context

@login_required
@require_GET
@permission_required("ingredient_app.can_delete_ingredient",raise_exception=True)
def ingredient_delete(request, id):
    
    instance = get_object_or_404(Ingredient, id=id)
    instance.delete()

    return redirect('ingredients')

