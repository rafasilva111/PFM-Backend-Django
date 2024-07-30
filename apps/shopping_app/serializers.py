from rest_framework import serializers
from apps.shopping_app.models import ShoppingList, ShoppingIngredient
from apps.recipe_app.serializers import IngredientSerializer
from apps.recipe_app.models import Ingredient

##
#   Contants
#

from apps.common.constants import MAX_USER_NORMAL_SHOPPING_LISTS,MAX_USER_PREMIUM_SHOPPING_LISTS,MAX_USER_NORMAL_SHOPPING_LISTS_GROUPS,MAX_USER_PREMIUM_SHOPPING_LISTS_GROUPS



class ShoppingIngredientSerializer(serializers.ModelSerializer):
    
    ingredient = IngredientSerializer()
    
    class Meta:
        model = ShoppingIngredient
        fields = '__all__'
        read_only_fields = ['id','name']


class ShoppingListSerializer(serializers.ModelSerializer):
    shopping_ingredients = ShoppingIngredientSerializer(many=True)
    
    class Meta:
        model = ShoppingList
        fields = '__all__'
        read_only_fields = ['id', 'user','group']   
    
    def create(self, validated_data):
        
        # Get context instances
        user = self.context.get('user')
        group =  self.context.get('group')
        
        # Validate context instances       
        if (not user and not group) and ( user and group):
            raise serializers.ValidationError("User or Group in context is required.")
        
        # Extract shopping ingredients data
        shopping_ingredients_data = validated_data.pop('shopping_ingredients')

        # Create the ShoppingList instance
        if group:
            shopping_list = ShoppingList.objects.create(group=group, **validated_data)
        else:
            shopping_list = ShoppingList.objects.create(user=user, **validated_data)
            

        # Create ShoppingIngredient instances
        for ingredient_data in shopping_ingredients_data:
            ingredient_data['shopping_list'] = shopping_list
            try:
                ingredient_instance = Ingredient.objects.get(**ingredient_data.pop('ingredient'))
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError("Ingredient does not exist.")
            ingredient_data['ingredient'] = ingredient_instance
            ShoppingIngredient.objects.create(**ingredient_data)

        
        
        return shopping_list

    
class ShoppingIngredientPatchSerializer(ShoppingIngredientSerializer):
    
    class Meta:
        model = ShoppingIngredient
        fields = '__all__'
        read_only_fields = ['id','ingredient', 'shopping_list']


class ShoppingListPatchSerializer(serializers.ModelSerializer):
    shopping_ingredients = ShoppingIngredientPatchSerializer(many=True, required=False, allow_null=True)
    
    class Meta:
        model = ShoppingList
        fields = ['id', 'name', 'user', 'archived', 'shopping_ingredients']
        read_only_fields = ['id', 'user']
        
    def validate(self, data):
        
        # Enforce Premium Priveleges
        
        # Get context instances
        user = self.context.get('user')
        group =  self.context.get('group')

        # Validate context instances       
        if (not user and not group) and ( user and group):
            raise serializers.ValidationError("User or Group in context is required.")
        
        # Call the parent class's validate method
        data = super().validate(data)
        
        # Custom validation logic
        if "archived" in data and not data["archived"]:
            if user:
                max_lists = MAX_USER_PREMIUM_SHOPPING_LISTS if user.user_type == user.UserType.PREMIUM else MAX_USER_NORMAL_SHOPPING_LISTS
                
                if user.shopping_lists.count() >= max_lists:
                    raise serializers.ValidationError({
                        "archived": f"Exceeded the maximum allowed shopping lists ({max_lists})."
                    })
            else:
                max_lists = MAX_USER_PREMIUM_SHOPPING_LISTS_GROUPS if user.user_type == user.UserType.PREMIUM else MAX_USER_NORMAL_SHOPPING_LISTS_GROUPS
                if group.shopping_lists.count() >= max_lists:
                    raise serializers.ValidationError({
                        "archived": f"Exceeded the maximum allowed shopping lists ({max_lists})."
                    })

        return data
        
    def update(self, instance, validated_data):
        # Extract nested data
        ingredients_data = validated_data.pop('shopping_ingredients', None)
        
        # Update the main instance
        instance = super().update(instance, validated_data)
        
        # Handle nested data
        if ingredients_data:
            # Clear existing ingredients
            instance.shopping_ingredients.all().delete()

            # Create new ingredients
            for ingredient_data in ingredients_data:
                ingredient_data['shopping_list'] = instance
                
                try:
                    ingredient_instance = Ingredient.objects.get(**ingredient_data.pop('ingredient'))
                except Ingredient.DoesNotExist:
                    raise serializers.ValidationError("Ingredient does not exist.")
                
                ingredient_data['ingredient'] = ingredient_instance 
                ShoppingIngredient.objects.create( **ingredient_data)
                
        return instance
    
