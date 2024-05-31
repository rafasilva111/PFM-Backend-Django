from rest_framework import serializers
from .models import Recipe, RecipeRating, RecipeBackground, Tag, Ingredient, RecipeIngredientQuantity, Comment, RecipeReport

class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = '__all__'  # Include all fields


class RecipeRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeRating
        fields = '__all__'

class RecipeBackgroundSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeBackground
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientQuantitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeIngredientQuantity
        fields = '__all__'
        
class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'


class RecipeReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeReport
        fields = '__all__'
