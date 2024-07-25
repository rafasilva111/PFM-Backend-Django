###
#       Default imports
##


##
#   Default
#

from datetime import datetime, timedelta
from django.utils import timezone

from django.db.models.functions import Random
from django.db.models import Count, Avg, OuterRef, Subquery
from django.db.models import Q

##
#   Django Rest Framework
#

from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response




##
#   Api Swagger
#

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema



##
#   Extras
#

from django.core.paginator import Paginator




###
#       App specific imports
##


##
#   Models
#

from apps.recipe_app.models import Recipe,RecipeBackground, RecipeReport, Comment
from apps.user_app.models import User

##
#   Serializers
#

from apps.recipe_app.serializers import RecipeSerializer,RecipeReportSerializer,RecipeReportPatchSerializer,RecipePatchSerializer,CommentSerializer,CommentPatchSerializer,\
    RecipeBackgroundSerializer,SimpleRecipeSerializer
from apps.api.serializers import SuccessResponseSerializer,ErrorResponseSerializer,ListResponseSerializer


##
#   Functions
#


##
#   Contants
#


from apps.recipe_app.constants import RecipeSortingTypes,RecipesBackgroundType
from apps.api.constants import ERROR_TYPES
from apps.common.constants import MAX_USER_NORMAL_SAVED_RECIPES, MAX_USER_PREMIUM_SAVED_RECIPES



###
#
#   Recipe App
#
##


###
#   Recipe
##

class RecipeView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Recipe'],
        operation_summary="Get a recipe by ID",
        operation_description="Get a recipe by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                description="The ID of the recipe to retrieve.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description='The retrieved recipe data.',
                schema=RecipeSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self,request):
        # TODO user shouldnt be able to see private account recipes
        
        user = request.user
        # Get args
        id = int(request.query_params.get('id', -1))

        # Validate args
        if id == -1:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Recipe report Id not supplied.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Retrieve the instance
        try:
            recipe = Recipe.objects.get(id=id)  
        except Recipe.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data, status=status.HTTP_400_BAD_REQUEST)
    
        return Response(RecipeSerializer(recipe, context={'user': user}).data, status=status.HTTP_200_OK)
            
    @swagger_auto_schema(
        tags=['Recipe'],
        operation_summary="Create a new recipe",
        operation_description="Create a new recipe for the authenticated user.",
        request_body=RecipeSerializer,
        responses={
            201: openapi.Response(
                description='Recipe created successfully.',
                schema=RecipeSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided data is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def post(self, request):
        
        # Get authenticated user
        user = request.user
        
        # Validate and save the recipe
        serializer = RecipeSerializer(data=request.data, context={'user': user})
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

    @swagger_auto_schema(
        tags=['Recipe'],
        operation_summary="Delete a recipe by ID",
        operation_description="Delete a recipe by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                description="The ID of the recipe to delete.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description='The recipe was successfully deleted.',
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
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
    
    @swagger_auto_schema(
        tags=['Recipe'],
        operation_summary="Get a recipe by ID",
        operation_description="Get a recipe by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                name='id',
                in_=openapi.IN_QUERY,
                description="The ID of the recipe to retrieve.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                name='page',
                in_=openapi.IN_QUERY,
                description="The page number to retrieve. Defaults to 1.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name='page_size',
                in_=openapi.IN_QUERY,
                description="The number of recipes per page. Must be one of [5, 10, 20, 40]. Defaults to 5.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name='by',
                in_=openapi.IN_QUERY,
                description="The sorting method for the recipes. One of: random, date, verified, likes, saves, classification. Defaults to date.",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                name='user_id',
                in_=openapi.IN_QUERY,
                description="The ID of the user who created the recipes. Defaults to the authenticated user.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name='commented_by',
                in_=openapi.IN_QUERY,
                description="The ID of the user who commented on the recipes. Defaults to the authenticated user.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name='searchString',
                in_=openapi.IN_QUERY,
                description="The search string to filter the recipes by. Defaults to empty.",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                name='searchTag',
                in_=openapi.IN_QUERY,
                description="The tag to filter the recipes by. Defaults to empty.",
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description='The retrieved recipe data.',
                schema=ListResponseSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self,request):
        
        # Get user auth 
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
        if by and not RecipeSortingTypes.is_valid_choice(by):
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
            query = Recipe.objects.all().order_by('id')

        if search_string:
            
            if search_string.isdigit():
                query = query.filter(Q(id=search_string))
            else:
                print("here")
                query = query.filter(Q(title__icontains=search_string)|Q(tags__title__icontains=search_string))

        if search_tag:
            query = query.filter(tags__title__icontains=search_tag)

        # Apply sorting
        if by:
            if by == RecipeSortingTypes.DATE:
                query = query.order_by('created_at')
                
            elif by == RecipeSortingTypes.RANDOM:
                query = query.annotate(random_number=Random()).order_by('random_number')
                
            elif by == RecipeSortingTypes.VERIFIED:
                query = query.filter(verified=True)
                
            elif by == RecipeSortingTypes.LIKES:
                query = query.annotate(liked_count=Count('users_liked')).order_by('-liked_count')
                
            elif by == RecipeSortingTypes.SAVES:
                query = query.annotate(saved_count=Count('users_saved')).order_by('-saved_count')
                
            elif by == RecipeSortingTypes.CLASSIFICATION:
                query = query.annotate(avg_rating=Avg('ratings__rating')).order_by('avg_rating')
                

        # Paginate the results
        paginator = Paginator(query, page_size)

        # Get the requested page
        try:
            records_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.PAGINATION.value, message="Page does not exist.").data, status=status.HTTP_400_BAD_REQUEST)
        
        
        return Response(
                ListResponseSerializer.build_(
                    request,
                    page,
                    paginator,
                    serializer=SimpleRecipeSerializer(records_page, many=True, context={'user': user}),
                    endpoint_name="recipe_list"
                ).data,
                status=status.HTTP_200_OK
            )
        

###
#   Recipe Report
##

class RecipeReportView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Recipe Report'],
        operation_summary="Get a recipe report by ID",
        operation_description="Get a recipe report by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                description="The ID of the recipe report to retrieve.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description='The retrieved recipe report data.',
                schema=RecipeReportSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self,request):
        
        # TODO not really needed yet

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @swagger_auto_schema(
        tags=['Recipe Report'],
        operation_summary="Create a recipe report",
        operation_description="Create a recipe report for the authenticated user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'recipe_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='The ID of the recipe to report.'),
                'category': openapi.Schema(type=openapi.TYPE_STRING, description='The category of the issue.', enum=list(RecipeReport.Type)),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='The description of the issue.'),
                'verified': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Whether the issue is verified or not.'),
            },
            required=['recipe_id', 'category', 'description', 'verified']
        ),
        responses={
            201: openapi.Response(
                description='The created recipe report data.',
                schema=RecipeReportSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided data is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def post(self,request):
        
        # Get user authed
        user = request.user
        
        # Get args
        recipe_id = request.GET.get('recipe_id')

        # Validate args
        if not recipe_id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param RecipeId.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except User.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Validate serializer
        serializer = RecipeReportSerializer(data=request.data, context={'user': user,'recipe': recipe})
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return Response(serializer.data,status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        tags=['Recipe Report'],
        operation_summary="Update a recipe report",
        operation_description="Update a recipe report by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                description="The ID of the recipe report to update.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'category': openapi.Schema(type=openapi.TYPE_STRING, description='The category of the issue.', enum=list(RecipeReport.Type)),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='The description of the issue.'),
                'verified': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Whether the issue is verified or not.'),
            },
            required=['category', 'description', 'verified']
        ),
        responses={
            200: openapi.Response(
                description='The updated recipe report data.',
                schema=RecipeReportSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
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

    @swagger_auto_schema(
        tags=['Recipe Report'],
        operation_summary="Delete a recipe report",
        operation_description="Delete a recipe report by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                description="The ID of the recipe report to delete.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description='The deleted recipe report data.',
                schema=RecipeReportSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
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

        # Delete instance
        recipe_report.delete()

        return Response(status=status.HTTP_200_OK)

class RecipeReportListView(APIView):
    
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        tags=['Recipe Report'],
        operation_summary="Get a list of recipe reports",
        operation_description="List all recipe reports for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="The page number to retrieve.",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="The number of items per page.",
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Response(
                description='A list of recipe reports.',
                schema=ListResponseSerializer(many=True),
            ),
            400: openapi.Response(
                description='Bad request. The provided parameters are not valid, or other parameter issues.',
                schema=ErrorResponseSerializer,
            ),
        }
    )
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

        # Get the requested page
        try:
            records_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ListResponseSerializer.build_(request,page, paginator, serializer=RecipeReport(records_page, many=True), endpoint_name="calendar_list").data,
            status=status.HTTP_200_OK
        )


###
#   Comment
##

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
        except Comment.DoesNotExist:
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
        except Recipe.DoesNotExist:
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
        except Comment.DoesNotExist:
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
        except Comment.DoesNotExist:
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

        
        # Get the requested page
        try:
            records_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            ListResponseSerializer.build_(request,page,paginator,serializer = CommentSerializer(records_page, many=True),endpoint_name="comment_list").data,
            status=status.HTTP_200_OK)


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
        except Comment.DoesNotExist:
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
        except Comment.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.likes.remove(user)
        # Save model
        instance.save()

        return Response(CommentSerializer(instance).data,status=status.HTTP_201_CREATED)
    
###
#   Background
##


#   Liked recipes shound not be saved (on Frontend local memory)

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
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
            
            # Query building
            query = user_instance.liked_recipes.all()
            
        else:
            
            # Query building
            query = user.liked_recipes.all()
        

        # Paginate the results
        paginator = Paginator(query, page_size)

        # Get the requested page
        try:
            records_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ListResponseSerializer.build_(request,page, paginator, serializer=RecipeSerializer(records_page, many=True,context={'user':user}), endpoint_name="calendar_list").data,
            status=status.HTTP_200_OK
        )
    
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
        except Recipe.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.users_liked.add(user)
        # Save model
        instance.save()

        return Response(RecipeSerializer(instance,context={'user':user}).data,status=status.HTTP_201_CREATED)

    
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
        except Recipe.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.users_liked.remove(user)
        # Save model
        instance.save()

        return Response(RecipeSerializer(instance,context={'user':user}).data,status=status.HTTP_200_OK)


#   User Normal can only have 25 saved recipes (on Frontend local memory)
#   User Premium can have 100 saved recipes (on Frontend local memory)
  
class RecipesSavedView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    
    @swagger_auto_schema(
        tags=['Recipe Save'],
        operation_summary="Get a recipe report by ID",
        operation_description="Get a recipe report by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="The page number to retrieve. Defaults to 1.", required=False),
            openapi.Parameter('page_size', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="The number of recipes per page. Must be one of [5, 10, 20, 40]. Defaults to 5.", required=False),
            openapi.Parameter('user_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="The ID of the user to retrieve saved recipes for. If not provided, it will be the authenticated user.", required=False),
        ],
        responses={
            200: openapi.Response(description='A paginated list of saved recipes.', schema=ListResponseSerializer),
            400: openapi.Response(description='Bad request. The provided page does not exist or other parameter issues.', schema=ErrorResponseSerializer),
        }
    )
    def get(self,request):
        """
        Get a paginated list of saved recipes.

        :param page: The page number to retrieve. Defaults to 1.
        :param page_size: The number of recipes per page. Must be one of [5, 10, 20, 40]. Defaults to 5.
        :param user_id: The ID of the user to retrieve saved recipes for. If not provided, it will be the authenticated user.

        :return: A paginated list of saved recipes.
        :rtype: dict
        """
        # Get user auth id
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        user_id = request.GET.get('user_id')
        
        
        # Query building
        if user_id:
            
            try:
                user_instance = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
            
            
            query = user_instance.saved_recipes.all()
            
        else:
            
            # Query building
            query = user.saved_recipes.all()
            

        # Paginate the results
        paginator = Paginator(query, page_size)

        # Get the requested page
        try:
            records_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ListResponseSerializer.build_(request,page, paginator, serializer=RecipeSerializer(records_page, many=True,context={'user':user}), endpoint_name="calendar_list").data,
            status=status.HTTP_200_OK
        )
    
    @swagger_auto_schema(
        tags=['Recipe Save'],
        operation_summary="Get a recipe report by ID",
        operation_description="Get a recipe report by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                description="The ID of the recipe report to retrieve.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description='The retrieved recipe report data.',
                schema=RecipeReportSerializer
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def post(self, request):
        
        # Get user authed
        user = request.user
        
        # Get args
        id = request.GET.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.ARGS.value,message="Missing param Id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Validate User
        
        if user.user_type == User.UserType.PREMIUM:
            if user.saved_recipes.all().count() >= MAX_USER_PREMIUM_SAVED_RECIPES:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.RESOURCE_LIMIT.value,message=f"You can only save {MAX_USER_PREMIUM_SAVED_RECIPES} recipes.").data,status=status.HTTP_400_BAD_REQUEST)
        else:
            if user.saved_recipes.all().count() >= MAX_USER_NORMAL_SAVED_RECIPES:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.RESOURCE_LIMIT.value,message="You can only save {MAX_USER_NORMAL_SAVED_RECIPES} recipes.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get Instance
        try:
            instance = Recipe.objects.get(id=id)
        except Recipe.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.users_saved.add(user)
        # Save model
        instance.save()

        return Response(RecipeSerializer(instance,context={'user':user}).data,status=status.HTTP_201_CREATED)

    
    @swagger_auto_schema(
        tags=['Recipe Save'],
        operation_summary="Get a recipe report by ID",
        operation_description="Get a recipe report by ID for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_QUERY,
                description="The ID of the recipe report to retrieve.",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description='The retrieved recipe report data.',
                schema=RecipeReportSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided ID is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
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
        except Recipe.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Increment likes ( TODO idk if a many to many relation would be usefull to confirm likes )
        instance.users_saved.remove(user)
        # Save model
        instance.save()

        return Response(RecipeSerializer(instance,context={'user':user}).data,status=status.HTTP_200_OK)
 
#   All users should have access to all created recipes (on Frontend local memory)

class RecipesCreatedView(APIView):
    
    permission_classes = [IsAuthenticated]   
    @swagger_auto_schema(
        tags=['Recipe Creates'],
        operation_summary="Get recipes created by the authenticated user",
        operation_description="Get a paginated list of recipes created by the authenticated user. The results can be filtered and paginated using query parameters.",
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="The page number to retrieve. Defaults to 1.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="The number of recipes per page. Must be one of [5, 10, 20, 40]. Defaults to 5.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="The ID of the user to retrieve recipes for. If not provided, it will be the authenticated user.",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description='A paginated list of recipes created by the authenticated user.',
                schema=ListResponseSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided page does not exist or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self,request):
        
        # Get user auth
        user = request.user

        # Get args
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
        user_id = request.GET.get('user_id')
        
        # Validate args
        if user_id:
            
            # Get Instance
            try:
                user_instance = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Recipe Report couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
            
            # Query building
            query = user_instance.created_recipes.all()
            
        else:
            
            # Query building
            query = user.created_recipes.all()
            

        # Paginate the results
        paginator = Paginator(query, page_size)

        # Get the requested page
        try:
            records_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ListResponseSerializer.build_(request,page, paginator, serializer=RecipeSerializer(records_page, many=True), endpoint_name="recipes_created").data,
            status=status.HTTP_200_OK
        )



class RecipeBackgroundView(APIView):
    
    permission_classes = [IsAuthenticated]  
    
    def get(self,request):
        
        # Get user auth
        user = request.user
        
        return Response(RecipeBackgroundSerializer(user, context={'user':user}).data,status=status.HTTP_200_OK)
