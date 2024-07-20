from rest_framework import serializers
from .models import ShoppingList, ShoppingIngredient

class ShoppingIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingIngredient
        fields = ['id', 'ingredient', 'shopping_list', 'checked', 'quantity', 'extra_quantity', 'units', 'extra_units']

class ShoppingListSerializer(serializers.ModelSerializer):
    shopping_ingredients = ShoppingIngredientSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = ['id', 'name', 'user', 'archived', 'shopping_ingredients']
