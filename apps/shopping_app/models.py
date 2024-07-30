from django.db import models
from apps.user_app.models import User
from apps.recipe_app.models import Ingredient
from apps.common.models import BaseModel
from apps.group_app.models import Group

# Create your models here.


# Shopping List App models
class ShoppingList(BaseModel):
    """
    Model to store shopping lists.
    """
    name = models.CharField(max_length=255, null=False)
    user = models.ForeignKey(User, related_name='shopping_lists', on_delete=models.CASCADE,blank=True,  null=True)
    group = models.ForeignKey(Group, related_name='shopping_lists', on_delete=models.CASCADE, blank=True, null=True)
    archived = models.BooleanField(default=False)
    

class ShoppingIngredient(BaseModel):
    """
    Model to store ingredients in shopping lists.
    """
    ingredient = models.ForeignKey(Ingredient, related_name='shopping_ingredients', on_delete=models.CASCADE)
    shopping_list = models.ForeignKey(ShoppingList, related_name='shopping_ingredients', on_delete=models.CASCADE, blank=True, null=True) 
    checked = models.BooleanField(default=False)
    quantity = models.FloatField(null=False)
    extra_quantity = models.FloatField(null=True)
    units = models.CharField(default='G', max_length=255)
    extra_units = models.CharField(max_length=255, null=True)
    