from django.contrib import admin
from .models import Ingredient, Image, Tag


# ---------------------------------------
# IMAGE INLINE (for Ingredient admin)
# ---------------------------------------
class ImageInline(admin.TabularInline):
    model = Image
    extra = 1
    fields = ("path",)
    readonly_fields = ()


# ---------------------------------------
# INGREDIENT ADMIN
# ---------------------------------------
@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "brand",
        "company",
        "size",
        "bulk_price",
        "size_type",
    )
    list_filter = ("brand", "company", "size_type")
    search_fields = ("title", "brand", "company", "description")
    inlines = [ImageInline]

    filter_horizontal = ("tags",)   # ManyToMany

    fieldsets = (
        ("General", {
            "fields": (
                "title",
                "brand",
                "description",
                "company",
                "category",
                "source_link",
            )
        }),
        ("Size & Pricing", {
            "fields": (
                "old_size",
                "size",
                "portions",
                "portion_size",
                "portion_unit",
                "portion_price",
                "bulk_price",
                "bulk_unit",
                "size_type",
                "minimum_size_for_bulk",
            )
        }),
        ("Product Details", {
            "fields": (
                "about_the_product",
                "caracteristics",
                "other_information",
                "nutrition_information",
                "legal_info",
            )
        }),
        ("Tags", {
            "fields": ("tags",)
        })
    )


# ---------------------------------------
# IMAGE ADMIN
# ---------------------------------------
@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("id", "path", "ingredient")
    search_fields = ("path",)
    list_filter = ("ingredient",)


# ---------------------------------------
# TAG ADMIN
# ---------------------------------------
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "text", )
    search_fields = ("text",)