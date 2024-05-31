from django.db import models
from apps.user_app.models import User
from apps.recipe_app.models import Ingredient

# Create your models here.


# Shopping List App models
class ShoppingList(models.Model):
    """
    Model to store shopping lists.
    """
    name = models.CharField(max_length=255, null=False)
    user = models.ForeignKey(User, related_name='shopping_lists', on_delete=models.CASCADE)
    archived = models.BooleanField(default=False)


class ShoppingIngredient(models.Model):
    """
    Model to store ingredients in shopping lists.
    """
    ingredient = models.ForeignKey(Ingredient, related_name='shopping_ingredients', on_delete=models.CASCADE)
    shopping_list = models.ForeignKey(ShoppingList, related_name='shopping_ingredients', on_delete=models.CASCADE)
    checked = models.BooleanField(default=False)
    quantity = models.FloatField(null=False)
    extra_quantity = models.FloatField(null=True)
    units = models.CharField(default='G', max_length=255)
    extra_units = models.CharField(max_length=255, null=True)