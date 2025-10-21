from apps.ingredient_app.models import Ingredient
from rest_framework import serializers

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'price', 'quantity']
        
        