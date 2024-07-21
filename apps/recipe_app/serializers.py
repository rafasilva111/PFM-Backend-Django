from rest_framework import serializers
from django.db import transaction
from .models import Recipe, RecipeRating, RecipeBackground, Tag, Ingredient, RecipeIngredientQuantity, Comment, RecipeReport,NutritionInformation,Preparation
from apps.user_app.serializers import SimpleUserSerializer
from apps.user_app.models import User

###
#   Recipe 
##

class NutritionInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionInformation
        fields = '__all__'
        
class PrepationSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['step','description']
        model = Preparation

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['title']
        
class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'
           
class RecipeIngredientQuantitySerializer(serializers.ModelSerializer):
    
    ingredient = IngredientSerializer()
    
    class Meta:
        model = RecipeIngredientQuantity
        fields = '__all__'
        read_only_fields = [ 'user','recipe']


class RecipeSerializer(serializers.ModelSerializer):

    nutrition_information = NutritionInformationSerializer(required = False)
    created_by = SimpleUserSerializer(required = False)
    preparation = PrepationSerializer(many = True,required = False)
    ingredients = RecipeIngredientQuantitySerializer(many = True,required = False)
    tags = TagSerializer(many = True,required = False)
    likes = serializers.SerializerMethodField()
    saves = serializers.SerializerMethodField()
    
    class Meta:
        model = Recipe
        fields = ['id','title','description','img_source','verified','difficulty','ingredients','tags','portion','preparation','time','likes','saves','views','nutrition_information','rating','source_rating','source_link','created_at', 'updated_at','created_by']  # Include all fields
        read_only_fields = ['id', 'created_at', 'updated_at','created_by','ingredients','preparation','tags','nutrition_information']
        
        
    def create(self, validated_data):
        # Create is prepared to load full model
        # adding Recipe's created_by User by context
        
        preparation_data = validated_data.pop('preparation')
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        
        # Create the NutritionInformation instance
        nutrition_information = NutritionInformation.objects.create(**validated_data.pop('nutrition_information'))
        
        # Create the Recipe instance
        recipe_instance = Recipe.objects.create(
            created_by = self.context['user'],
            nutrition_information=nutrition_information,
            **validated_data
            )
        
        # Create Preparation instances and link them to the Recipe
        for prep_data in preparation_data:
            Preparation.objects.create(recipe=recipe_instance, **prep_data)
        
        # Create RecipeIngredientQuantity instances and link them to the Recipe
        for ing_data in ingredients_data:
            ingredient_data = ing_data.pop('ingredient')
            ingredient_intance, created = Ingredient.objects.get_or_create(**ingredient_data)
            RecipeIngredientQuantity.objects.create(recipe= recipe_instance, ingredient=ingredient_intance, **ing_data)
        
        # Create Tags instances and link them to the Recipe
        for tag_data in tags_data:
            tag_instance, created = Tag.objects.get_or_create(**tag_data)
            recipe_instance.tags.add(tag_instance)
            
        recipe_instance.save()
        return recipe_instance


    def get_likes(self, obj):
        return obj.users_liked.count()
    
    def get_saves(self, obj):
        return obj.users_saved.count()
    
class SimpleRecipeSerializer(serializers.ModelSerializer):

    created_by = SimpleUserSerializer(required = False)
    tags = TagSerializer(many = True)
    
    likes = serializers.SerializerMethodField()
    
    class Meta:
        model = Recipe
        fields = ['id','title','description','img_source','verified','difficulty','tags','portion','time','likes','views','rating','source_rating','created_by']  # Include all fields
    
    def get_likes(self, obj):
        return obj.users_liked.count()
    
class RecipePatchSerializer(RecipeSerializer):
    
    class Meta:
        model = Recipe
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at','created_by','ingredients','preparation','tags','nutrition_information','views','likes']
        
        extra_kwargs = {
            'id': {'required': False},
            'title': {'required': False},
            'description': {'required': False},
            'img_source': {'required': False},
            'verified': {'required': False},
            'difficulty': {'required': False},
            'ingredients': {'required': False},
            'tags': {'required': False},
            'portion': {'required': False},
            'preparation': {'required': False},
            'time': {'required': False},
            'likes': {'required': False},
            'views': {'required': False},
            'nutrition_information': {'required': False},
            'rating': {'required': False},
            'source_rating': {'required': False},
            'source_link': {'required': False},
            'created_by': {'required': False},
        }

class RecipeRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeRating
        fields = '__all__'

###
#   Backgrounds
##

class RecipeBackgroundSerializer(serializers.ModelSerializer):
    created_recipes = RecipeSerializer(many=True, read_only=True)
    saved_recipes = RecipeSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['created_recipes', 'saved_recipes']
###
#   Comments
##
        
class CommentSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(required = False)
    recipe = SimpleRecipeSerializer(required = False)
    likes = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = ['id','user','recipe','parent_comment','likes','created_at','updated_at']
        
    def create(self, validated_data):
        
        # Create the Recipe instance
        recipe_report_instance = Comment.objects.create(
            user = self.context['user'],
            recipe = self.context['recipe'],
            **validated_data
            )

        return recipe_report_instance
    
    def get_likes(self, obj):
        return obj.likes.count()


class CommentPatchSerializer(CommentSerializer):
    
    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = ['id','user','recipe','created_at','updated_at']
        
        extra_kwargs = {
            'text': {'required': False},
        }

###
#   Recipe Report
##

class RecipeReportSerializer(serializers.ModelSerializer):
    
    user = SimpleUserSerializer(required = False)
    recipe = SimpleRecipeSerializer(required = False)
    
    class Meta:
        model = RecipeReport
        fields = '__all__'
        read_only_fields = ['id','user','recipe','created_at','updated_at']
        
    def create(self, validated_data):
        
        # Create the Recipe instance
        recipe_report_instance = RecipeReport.objects.create(
            user = self.context['user'],
            recipe = self.context['recipe'],
            **validated_data
            )

        return recipe_report_instance

class RecipeReportPatchSerializer(RecipeReportSerializer):
    
    class Meta:
        model = RecipeReport
        fields = '__all__'
        read_only_fields = ['id','user','recipe','created_at','updated_at']
        
        extra_kwargs = {
            'title': {'required': False},
            'message': {'required': False},
            'status': {'required': False}
        }
        
