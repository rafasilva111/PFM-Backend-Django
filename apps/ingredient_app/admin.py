from django.contrib import admin
from apps.ingredient_app.models import Ingredient

# Register your models here.

class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('name',)
    
admin.site.register(Ingredient, IngredientAdmin)