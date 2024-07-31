from django.contrib import admin
from .models import ShoppingList, ShoppingIngredient

class ShoppingIngredientInline(admin.TabularInline):
    model = ShoppingIngredient
    extra = 1

class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'archived')
    list_filter = ('user', 'archived')
    search_fields = ('name', 'user__username')
    inlines = [ShoppingIngredientInline]

class ShoppingIngredientAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'shopping_list', 'checked', 'quantity', 'extra_quantity', 'units', 'extra_units')
    list_filter = ('shopping_list', 'checked')
    search_fields = ('ingredient__name', 'shopping_list__name')
    autocomplete_fields = ('ingredient', 'shopping_list')

admin.site.register(ShoppingList, ShoppingListAdmin)
admin.site.register(ShoppingIngredient, ShoppingIngredientAdmin)
