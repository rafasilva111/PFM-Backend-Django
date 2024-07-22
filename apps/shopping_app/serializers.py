from rest_framework import serializers
from apps.shopping_app.models import ShoppingList, ShoppingIngredient
from apps.recipe_app.serializers import IngredientSerializer

class ShoppingIngredientSerializer(serializers.ModelSerializer):
    
    ingredient = IngredientSerializer
    
    class Meta:
        model = ShoppingIngredient
        fields = '__all__'

class ShoppingListSerializer(serializers.ModelSerializer):
    shopping_ingredients = ShoppingIngredientSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = ['id', 'name', 'user', 'archived', 'shopping_ingredients']
