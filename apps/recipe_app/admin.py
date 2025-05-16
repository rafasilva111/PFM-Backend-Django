from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import (
    Ingredient, IngredientQuantity, NutritionInformation, Recipe,
    Tag,  RecipeRating, Comment, RecipeReport, RecipeAuditLog
)

###
#   Recipe Models
##
@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',) 

@admin.register(IngredientQuantity)
class IngredientQuantityAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'recipe', 'quantity_original', 'quantity_normalized', 'units_normalized', 'extra_quantity', 'extra_units')
    search_fields = ('ingredient__name', 'recipe__title')

@admin.register(NutritionInformation)
class NutritionInformationAdmin(admin.ModelAdmin):
    list_display = (
        'energy_kcal', 'energy_perc', 'fat_g', 'fat_perc', 'saturates_g', 'saturates_perc',
        'carbohydrates_g', 'carbohydrates_perc', 'sugars_g', 'sugars_perc', 'fiber_g',
        'protein_g', 'protein_perc', 'salt_g', 'salt_perc'
    )
    search_fields = ('recipe__title',)

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'verified', 'difficulty', 'portion_lower', 'time', 'views', 'created_by', 'rating')
    search_fields = ('title', 'created_by__username')
    list_filter = ('verified', 'difficulty')

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('text',)
    search_fields = ('text',)

@admin.register(RecipeRating)
class RecipeRatingAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'rating')
    search_fields = ('recipe__title', 'user__username')

###
#   Recipe Comment
##

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'recipe', 'user', 'parent_comment')
    search_fields = ('text', 'recipe__title', 'user__username')

###
#   Recipe Report
##

@admin.register(RecipeReport)
class RecipeReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'message', 'recipe', 'user', 'status')
    search_fields = ('title', 'recipe__title', 'user__username')
    list_filter = ('status',)
    

###
#   Recipe Audit Log
##

@admin.register(RecipeAuditLog)
class RecipeAuditLogAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'task', 'reviewed_by', 'type')
    search_fields = ('recipe__title',)
    list_filter = ('type',)