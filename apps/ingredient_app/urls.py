###
#       General imports
##

##
#   Django 
#

from django.urls import  path

##
#   Views 
#

from apps.ingredient_app.views import IngredientTableView,  IngredientDetailView,  ingredient_delete

###
#
#       Task App
#   
##

urlpatterns = [

    ###
    #   Ingredient
    ##

    path("ingredients", IngredientTableView.as_view(), name="ingredients"),
    path("ingredient/<int:id>", IngredientDetailView.as_view(), name="ingredient_detail"),
    path("ingredient/<int:id>/delete", ingredient_delete, name="ingredient_delete"),
    
]
