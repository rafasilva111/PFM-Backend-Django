# === Imports ===
from django.db import models

# === Custom Functions and Constants ===
from apps.common.models import BaseModel

class Tag(BaseModel):
    # General
    text = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return self.text

class Ingredient(BaseModel):
    # General
    title = models.CharField(max_length=255, default="")
    brand = models.CharField(max_length=255, default="")
    description = models.TextField(default="", blank=True)
    company = models.CharField(max_length=255)
    category = models.JSONField(default=None, null=True, blank=True)
    source_link = models.CharField(max_length=500, default="", blank=True)

    # Size and Price
    old_size = models.CharField(max_length=255)
    size = models.CharField(max_length=255, null=True, blank=True)
    
    class SizeType(models.TextChoices):
        PACKAGE = "P","Package"
        BULK = "B","Bulk"
        
    size_type = models.CharField(
        choices=SizeType.choices,
        max_length=1,  # Adjust based on expected selections
        default=None,
        null=True,
    )

    portions = models.FloatField(null=True, blank=True)
    portion_size = models.IntegerField(null=True, blank=True)
    portion_unit = models.IntegerField(null=True, blank=True)
    portion_price = models.FloatField(null=True, blank=True)

    bulk_price = models.CharField(max_length=255)
    bulk_unit = models.CharField(max_length=255)

    size_type = models.CharField(max_length=255)
    minimum_size_for_bulk = models.IntegerField(null=True, blank=True)

    # About the Product
    about_the_product = models.TextField(null=True, blank=True)

    # Characteristics
    caracteristics = models.TextField(null=True, blank=True)

    # Other Information
    other_information = models.TextField(null=True, blank=True)

    # Nutritional Information
    nutrition_information = models.TextField(null=True, blank=True)

    # Legal Info
    legal_info = models.TextField(null=True, blank=True)
    
    # Tags
    tags = models.ManyToManyField(
        Tag,
        related_name="ingredients",
        blank=True
    )

    def __str__(self):
        return self.title


class Image(BaseModel):
    # General
    path = models.CharField(max_length=500, unique=True)
    ingredient = models.ForeignKey(
        Ingredient,
        related_name="images",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.path


