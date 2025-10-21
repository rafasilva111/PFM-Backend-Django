from django.contrib import admin
from apps.ingredient_app.models import Ingredient

class IngredientAdmin(admin.ModelAdmin):
    # Columns shown in the changelist
    list_display = (
        "title",
        "brand",
        "category",
        "size",
        "price_per_unit",
        "price_bulk",
        "bulk_unit",
        "created_at",
    )

    # Make price fields editable directly from the list view
    list_editable = ("price_per_unit", "price_bulk")

    # Filters and search
    list_filter = ("category", "brand", "created_at")
    search_fields = ("title", "brand", "category", "description", "characteristics")
    ordering = ("title",)

    # Useful date navigation
    date_hierarchy = "created_at"

    # Readonly fields (timestamps should not be editable)
    readonly_fields = ("created_at", "updated_at")

    # Field grouping in the detail/edit view
    fieldsets = (
        ("General", {
            "fields": ("title", "brand", "category", "link")
        }),
        ("Pricing & Size", {
            "fields": ("size", ("price_per_unit", "price_bulk", "bulk_unit"))
        }),
        ("Product Info", {
            "fields": ("description", "about_the_product", "characteristics", "other_information")
        }),
        ("Nutrition & Legal", {
            "fields": ("nutrition_information", "legal_info")
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at",),
        }),
    )
    
admin.site.register(Ingredient, IngredientAdmin)