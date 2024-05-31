from django.shortcuts import render
from apps.recipe_app.models import Recipe,Tag, NutritionInformation, RecipeIngredientQuantity
from apps.recipe_app.serializers import RecipeSerializer
# Create your views here.

class RecipeDetailView(APIView):
    def get(self, request):
        """
        Get a recipe with ID.
        """
        recipe_id = request.GET.get('id')
        try:
            recipe = Recipe.objects.get(id=recipe_id)
            serializer = RecipeSerializer(recipe)
            return Response(serializer.data)
        except Recipe.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data="Recipe does not exist...")

    def post(self, request):
        """
        Post a recipe by user.
        """
        serializer = RecipeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """
        Delete a recipe by ID.
        """
        recipe_id = request.GET.get('id')
        try:
            recipe = Recipe.objects.get(id=recipe_id)
            recipe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Recipe.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data="Recipe does not exist...")

    def put(self, request):
        """
        Update a recipe by recipe ID.
        """
        recipe_id = request.GET.get('id')
        try:
            recipe = Recipe.objects.get(id=recipe_id)
            serializer = RecipeSerializer(recipe, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Recipe.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data="Recipe does not exist...")