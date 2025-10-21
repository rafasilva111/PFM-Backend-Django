from django.db import models
from apps.common.models import BaseModel

class Ingredient(BaseModel):
    # General
    title = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    description = models.TextField(null=True)
    link = models.URLField(null=True)
    category = models.CharField(max_length=255, blank=True, default="")

    # Size and money
    size = models.CharField(max_length=100, blank=True, default="")
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_bulk = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bulk_unit = models.CharField(max_length=100, blank=True, default="")

    # About the Product
    about_the_product = models.TextField(null=True)

    # Characteristics
    characteristics = models.TextField(null=True)

    # Other Information
    other_information = models.TextField(null=True)

    # Nutritional Information
    nutrition_information = models.TextField(null=True)

    # Legal Info
    legal_info = models.TextField(null=True)

