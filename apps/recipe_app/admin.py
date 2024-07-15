from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import (
    Ingredient, RecipeIngredientQuantity, NutritionInformation, Recipe,
    Tag,  RecipeRating, RecipeBackground, Comment, RecipeReport
)

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(RecipeIngredientQuantity)
class RecipeIngredientQuantityAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'recipe', 'quantity_original', 'quantity_normalized', 'units_normalized', 'extra_quantity', 'extra_units')
    search_fields = ('ingredient__name', 'recipe__title')

@admin.register(NutritionInformation)
class NutritionInformationAdmin(admin.ModelAdmin):
    list_display = ('energia', 'energia_perc', 'gordura', 'gordura_perc', 'gordura_saturada', 'gordura_saturada_perc', 'hidratos_carbonos', 'hidratos_carbonos_perc', 'hidratos_carbonos_acucares', 'hidratos_carbonos_acucares_perc', 'fibra', 'fibra_perc', 'proteina', 'proteina_perc')

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'verified', 'difficulty', 'portion', 'time', 'views', 'created_by', 'rating')
    search_fields = ('title', 'created_by__username')
    list_filter = ('verified', 'difficulty')

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('title',)
    search_fields = ('title',)

@admin.register(RecipeRating)
class RecipeRatingAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'rating')
    search_fields = ('recipe__title', 'user__username')

@admin.register(RecipeBackground)
class RecipeBackgroundAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'type')
    search_fields = ('user__username', 'recipe__title')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'recipe', 'user', 'parent_comment')
    search_fields = ('text', 'recipe__title', 'user__username')

@admin.register(RecipeReport)
class RecipeReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'message', 'recipe', 'user', 'status')
    search_fields = ('title', 'recipe__title', 'user__username')
    list_filter = ('status',)