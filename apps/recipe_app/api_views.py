from django.db.models import Q
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.api.serializers import ErrorResponseSerializer
from django.core.paginator import Paginator
from apps.api.constants import ERROR_TYPES
from django.db.models.functions import Random
from django.db.models import Count, Avg, OuterRef, Subquery
from rest_framework.permissions import IsAuthenticated


from .models import Recipe,RecipeBackground, RecipeReport, Comment
from .serializers import RecipeSerializer,RecipeReportSerializer,RecipeReportPatchSerializer,RecipePatchSerializer,CommentSerializer,CommentPatchSerializer
from .constants import RECIPES_SORTING_TYPE, RECIPES_BACKGROUND_TYPE
from apps.user_app.models import User
from apps.api.serializers import PaginationMetadataSerializer


class RecipeView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        # TODO user shouldnt be able to see private account recipes
        
        # Get args
        id = int(request.GET.get('id', -1))
        
        # Validate args
        if id == -1:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Recipe report Id not supplied.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Retrieve the instance
        try:
            recipe = Recipe.objects.get(id=id)
        except Recipe.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data, status=status.HTTP_400_BAD_REQUEST)
    
        return Response(RecipeSerializer(recipe).data, status=200)
            
    
    def post(self,request):
        
         # Get user authed
        user = request.user
        
        # Validate serializer
        serializer = RecipeSerializer(data=request.data, context={'user': user})
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return Response(serializer.data,status=status.HTTP_201_CREATED)
    
    
    def patch(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = int(request.GET.get('id', -1))
        
        # Validate args
        if id == -1:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Recipe Report Id not supplied.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Retrieve the instance
        try:
            recipe = Recipe.objects.get(id=id, created_by = user)
        except RecipeReport.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report can't be found by this id.").data, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Deserialize the incoming data
        serializer = RecipePatchSerializer(recipe, data=request.data)
        
        # Validate and update the instance
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        
        serializer.save()
        return Response(serializer.data,status=status.HTTP_200_OK)


    

    def delete(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Retrieve the instance
        try:
            recipe = Recipe.objects.get(id=id,created_by = user)
        except Recipe.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        
        recipe.delete()

        return Response(status=status.HTTP_200_OK)
    
    


class RecipeListView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        by = request.GET.get('by')
        user_id = request.GET.get('user_id')
        commented_by = request.GET.get('commented_by')
        search_string = request.GET.get('searchString')
        search_tag = request.GET.get('searchTag')
        
        # Validate args
        if by and by not in RECIPES_SORTING_TYPE:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Sorting by is not in RECIPES_SORTING_TYPE list.").data,status=status.HTTP_400_BAD_REQUEST)


        # Query building
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data, status=status.HTTP_400_BAD_REQUEST)
            query = Recipe.objects.filter(created_by=user)
        elif commented_by:
            try:
                user = User.objects.get(id=commented_by)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data, status=status.HTTP_400_BAD_REQUEST)
            query = Recipe.objects.filter(comments__user=user).distinct()
        else:
            query = Recipe.objects.all()

        if search_string:
            query = query.filter(Q(title__icontains=search_string) | Q(id=search_string))

        if search_tag:
            query = query.filter(tags__title__icontains=search_tag)

        # Apply sorting
        if by:
            if by == RECIPES_SORTING_TYPE.DATE.value:
                query = query.order_by('created_date')
                
            elif by == RECIPES_SORTING_TYPE.RANDOM:
                query = query.annotate(random_number=Random()).order_by('random_number')
                
            elif by == RECIPES_SORTING_TYPE.VERIFIED:
                query = query.filter(verified=True)
                
            elif by == RECIPES_SORTING_TYPE.LIKES:
                likes_subquery = RecipeBackground.objects.filter(
                    recipe=OuterRef('pk'), type=RECIPES_BACKGROUND_TYPE.LIKED
                ).values('recipe').annotate(count=Count('id')).values('count')
                query = query.annotate(likes=Subquery(likes_subquery)).order_by('-likes')
                
            elif by == RECIPES_SORTING_TYPE.SAVES:
                saves_subquery = RecipeBackground.objects.filter(
                    recipe=OuterRef('pk'), type=RECIPES_BACKGROUND_TYPE.SAVED
                ).values('recipe').annotate(count=Count('id')).values('count')
                query = query.annotate(saves=Subquery(saves_subquery)).order_by('-saves')
                
            elif by == RECIPES_SORTING_TYPE.CLASSIFICATION:
                query = query.annotate(avg_rating=Avg('ratings__rating')).order_by('-avg_rating')

        # Paginate the results
        paginator = Paginator(query, page_size)
        total_items = paginator.count
        total_pages = paginator.num_pages

        try:
            recipes_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({ERROR_TYPES.PAGINATION.value:"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Build metadata
        metadata = PaginationMetadataSerializer.build_metadata(page, page_size, total_pages, total_items, "recipe_list")
        
        # Serialize the data
        serializer = RecipeSerializer(recipes_page, many=True)
        
        teste = query.first().ingredients.count()
        
        # Build response data
        response_data = {
            "_metadata": metadata,
            "result": serializer.data
        }
        

        return Response(response_data, status=200)

    
    
class RecipeReportView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    
    def get(self,request):
        
        # TODO not really needed yet

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def post(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            recipe = Recipe.objects.get(id=id)
        except User.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Validate serializer
        serializer = RecipeReportSerializer(data=request.data, context={'user': user,'recipe': recipe})
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return Response(serializer.data,status=status.HTTP_201_CREATED)
    

    def patch(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = int(request.GET.get('id', -1))
        
        # Validate args
        if id == -1:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Recipe Report Id not supplied.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Retrieve the instance
        try:
            recipe_report = RecipeReport.objects.get(id=id, user = user)
        except RecipeReport.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report can't be found by this id.").data, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Deserialize the incoming data
        
        serializer = RecipeReportPatchSerializer(recipe_report, data=request.data)
        
        # Validate and update the instance
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        
        serializer.save()
        return Response(serializer.data,status=status.HTTP_200_OK)

    
    def delete(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            recipe_report = RecipeReport.objects.get(id=id,user = user)
        except RecipeReport.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        
        recipe_report.delete()

        return Response(status=status.HTTP_200_OK)

class RecipeReportListView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        


        # Query building
        query = RecipeReport.objects.filter ( user = user)

        # Paginate the results
        paginator = Paginator(query, page_size)
        total_items = paginator.count
        total_pages = paginator.num_pages

        try:
            recipes_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({ERROR_TYPES.PAGINATION.value:"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Build metadata
        metadata = PaginationMetadataSerializer.build_metadata(page, page_size, total_pages, total_items, "recipe_list")
        
        # Serialize the data
        serializer = RecipeReportSerializer(recipes_page, many=True)
            
        # Build response data
        response_data = {
            "_metadata": metadata,
            "result": serializer.data
        }
        

        return Response(response_data, status=200)



class CommentView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    
    def get(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            comment = Comment.objects.get(id=id)
        except User.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Comment couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)


        return Response(CommentSerializer(comment).data,status=status.HTTP_201_CREATED)
    
    def post(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('recipe_id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            recipe = Recipe.objects.get(id=id)
        except User.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Validate serializer
        serializer = CommentSerializer(data=request.data, context={'user': user,'recipe': recipe})
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        # Save model
        serializer.save()

        return Response(serializer.data,status=status.HTTP_201_CREATED)
    

    def patch(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = int(request.GET.get('id', -1))
        
        # Validate args
        if id == -1:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Recipe Report Id not supplied.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Retrieve the instance
        try:
            instance = Comment.objects.get(id=id, user = user)
        except RecipeReport.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report can't be found by this id.").data, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Deserialize the incoming data
        
        serializer = CommentPatchSerializer(instance, data=request.data)
        
        # Validate and update the instance
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Save Instance
        serializer.save()
        return Response(serializer.data,status=status.HTTP_200_OK)

    
    def delete(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Comment.objects.get(id=id,user = user)
        except RecipeReport.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Delete Instance
        instance.delete()

        return Response(status=status.HTTP_200_OK)

class CommentListView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        recipe_id = request.GET.get('recipe_id')
        client_id = request.GET.get('client_id')
        
        
        # Query building
        query = Comment.objects.filter ( user = user).order_by("-created_at",)
        
        if recipe_id:
            query.filter(recipe= int(recipe_id))
        
        if client_id:
            query.filter(recipe= int(client_id))

        # Paginate the results
        paginator = Paginator(query, page_size)
        total_items = paginator.count
        total_pages = paginator.num_pages

        try:
            result = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({ERROR_TYPES.PAGINATION.value:"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Build metadata
        metadata = PaginationMetadataSerializer.build_metadata(page, page_size, total_pages, total_items, "recipe_list")
        
        # Serialize the data
        serializer = CommentSerializer(result, many=True)
            
        # Build response data
        response_data = {
            "_metadata": metadata,
            "result": serializer.data
        }
        

        return Response(response_data, status=200)


class CommentLikeView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Comment.objects.get(id=id)
        except User.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.likes.add(user)
        # Save model
        instance.save()

        return Response(CommentSerializer(instance).data,status=status.HTTP_201_CREATED)

    
    def delete(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Comment.objects.get(id=id)
        except User.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.likes.remove(user)
        # Save model
        instance.save()

        return Response(CommentSerializer(instance).data,status=status.HTTP_201_CREATED)
    


class RecipesLikedView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        user_id = request.GET.get('user_id')
        
        if user_id:
            
            # Get Instance
            try:
                user_instance = User.objects.get(id=user_id)
            except RecipeReport.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
            
            # Query building
            query = user_instance.liked_recipes.all()
            
        else:
            
            # Query building
            query = user.liked_recipes.all()
            

        # Paginate the results
        paginator = Paginator(query, page_size)
        total_items = paginator.count
        total_pages = paginator.num_pages

        try:
            result = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({ERROR_TYPES.PAGINATION.value:"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Build metadata
        metadata = PaginationMetadataSerializer.build_metadata(page, page_size, total_pages, total_items, "recipe_list")
        
        # Serialize the data
        serializer = RecipeSerializer(result, many=True)
            
        # Build response data
        response_data = {
            "_metadata": metadata,
            "result": serializer.data
        }
        

        return Response(response_data, status=200)
    
    def post(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Recipe.objects.get(id=id)
        except User.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.users_liked.add(user)
        # Save model
        instance.save()

        return Response(RecipeSerializer(instance).data,status=status.HTTP_201_CREATED)

    
    def delete(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Recipe.objects.get(id=id)
        except User.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.users_liked.remove(user)
        # Save model
        instance.save()

        return Response(RecipeSerializer(instance).data,status=status.HTTP_201_CREATED)
    
    
class RecipesSavedView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    
    def get(self,request):
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        user_id = request.GET.get('user_id')
        
        if user_id:
            
            # Get Instance
            try:
                user_instance = User.objects.get(id=user_id)
            except RecipeReport.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
            
            # Query building
            query = user_instance.saved_recipes.all()
            
        else:
            
            # Query building
            query = user.saved_recipes.all()
            

        # Paginate the results
        paginator = Paginator(query, page_size)
        total_items = paginator.count
        total_pages = paginator.num_pages

        try:
            result = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({ERROR_TYPES.PAGINATION.value:"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Build metadata
        metadata = PaginationMetadataSerializer.build_metadata(page, page_size, total_pages, total_items, "recipe_list")
        
        # Serialize the data
        serializer = RecipeSerializer(result, many=True)
            
        # Build response data
        response_data = {
            "_metadata": metadata,
            "result": serializer.data
        }
        

        return Response(response_data, status=200)
    
    def post(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Recipe.objects.get(id=id)
        except User.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.users_saved.add(user)
        # Save model
        instance.save()

        return Response(RecipeSerializer(instance).data,status=status.HTTP_201_CREATED)

    
    def delete(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Recipe.objects.get(id=id)
        except User.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.users_saved.remove(user)
        # Save model
        instance.save()

        return Response(RecipeSerializer(instance).data,status=status.HTTP_201_CREATED)
    
      
class RecipesCreatedView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        user_id = request.GET.get('user_id')
        
        if user_id:
            
            # Get Instance
            try:
                user_instance = User.objects.get(id=user_id)
            except RecipeReport.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
            
            # Query building
            query = user_instance.created_recipes.all()
            
        else:
            
            # Query building
            query = user.created_recipes.all()
            

        # Paginate the results
        paginator = Paginator(query, page_size)
        total_items = paginator.count
        total_pages = paginator.num_pages

        try:
            result = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({ERROR_TYPES.PAGINATION.value:"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Build metadata
        metadata = PaginationMetadataSerializer.build_metadata(page, page_size, total_pages, total_items, "recipe_list")
        
        # Serialize the data
        serializer = RecipeSerializer(result, many=True)
            
        # Build response data
        response_data = {
            "_metadata": metadata,
            "result": serializer.data
        }
        

        return Response(response_data, status=200)
    