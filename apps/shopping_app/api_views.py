###
#       Default imports
##


##
#   Default
#

from django.utils import timezone
from django.contrib.auth import login, logout, authenticate
from django.db.models import Q
from django.conf import settings

##
#   Django Rest Framework
#

from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView


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


from apps.shopping_app.models import ShoppingList,ShoppingIngredient
from apps.user_app.models import User, FollowRequest,Follow
from apps.group_app.models import Group



##
#   Serializers
#

from apps.shopping_app.serializers import ShoppingListSerializer, ShoppingIngredientSerializer,ShoppingIngredientPatchSerializer,ShoppingListSerializer,ShoppingListPatchSerializer
from apps.user_app.serializers import UserSerializer,UserSimpleSerializer,UserPatchSerializer,UserProfileSerializer
from apps.api.serializers import ErrorResponseSerializer,ListResponseSerializer,IdListInputSerializer


##
#   Functions
#


##
#   Contants
#

from apps.api.constants import ERROR_TYPES,RESPONSE_CODES
from apps.common.constants import MAX_USER_NORMAL_SHOPPING_LISTS,MAX_USER_PREMIUM_SHOPPING_LISTS,MAX_USER_NORMAL_SHOPPING_LISTS_GROUPS,MAX_USER_PREMIUM_SHOPPING_LISTS_GROUPS



###
#
#   Shopping App
#
##

###
#   Shopping
##


class ShoppingListView(APIView):
    """
    API endpoint for user operations.

    Supports GET, DELETE, and PATCH methods.
    Requires JWT authentication.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User'],
        operation_summary="Retrieve authenticated user profile",
        operation_description="Retrieve the authenticated user's profile by ID or username",
        manual_parameters=[
            openapi.Parameter('id', openapi.IN_QUERY, description="User ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('username', openapi.IN_QUERY, description="Username", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description='Successful operation',
                schema=UserSimpleSerializer
            ),
            400: openapi.Response(
                description='Bad request',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self, request):
        """
        Retrieve a user profile by ID or username.

        Args:
            request: Request object containing query parameters.

        Returns:
            Response: JSON response containing the user profile.
        """
        
        # Get query parameters
        id = request.query_params.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.ARGS.value,message="Id was not provided.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get the requested ShoppingList
        try:
            record = ShoppingList.objects.get(id=id,user=request.user)
        except ShoppingList.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Shopping list couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)


        return Response(data = ShoppingListSerializer(record).data, status=status.HTTP_200_OK)

    
    @swagger_auto_schema(
        tags=['Shopping List'],
        operation_summary="Create a new recipe",
        operation_description="Create a new recipe for the authenticated user.",
        request_body=ShoppingIngredientSerializer(),
        responses={
            201: openapi.Response(
                description='Recipe created successfully.',
                schema=ShoppingIngredientSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided data is not valid, or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def post(self, request):
        """
        Create a new recipe for the authenticated user.

        Args:
            request (HttpRequest): The request object containing the user data.

        Returns:
            Response: A response object that contains the serialized recipe data if the
            creation is successful, or an error message if the data is invalid.
        """

        # Get query parameters
        group_id = request.query_params.get('group_id')
        
        # Validate args
        if group_id:
            
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Group couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)

        else:
            group = None 

        # Validate and save the recipe
        serializer = ShoppingListSerializer(data=request.data, context={'user': request.user, 'group': group})

        # Check if the data is valid
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        
        return Response(data = serializer.data, status=status.HTTP_201_CREATED)
        
        
    

    @swagger_auto_schema(
        tags=['Shopping List'],
        operation_summary="Patch authenticated user",
        operation_description="Patch the authenticated user's profile",
        request_body=UserPatchSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description='User profile updated successfully',
                schema=UserSerializer
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description='Error updating user profile',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def patch(self, request):
        """
        Patch the authenticated user.

        Args:
            request: Request object containing user data.

        Returns:
            Response: JSON response containing the updated user profile or error message.
        """
        
        # Get query parameters
        id = request.query_params.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.ARGS.value,message="Id was not provided.").data,status=status.HTTP_400_BAD_REQUEST)
        
        # Get the requested Instance
        try:
            instance = ShoppingList.objects.get(id=id,user=request.user)
        except ShoppingList.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Shopping list couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)


        # Serialize
        serializer = ShoppingListPatchSerializer(instance ,data=request.data, partial=True,context = {'user': request.user})

        # Validate Serializer
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        # Update Instance
        
        serializer.save()
        
        
        return Response(data=ShoppingListSerializer(instance).data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=['Shopping List'],
        operation_summary="Delete authenticated user",
        operation_description="Delete the authenticated user",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description='User deleted successfully'
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description='Error deleting user',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def delete(self, request):
        
        """
        Delete the authenticated user.

        Args:
            request: Request object containing user ID.

        Returns:
            Response: JSON response indicating success or failure.
        """

        # Get query parameters
        id = request.query_params.get('id')

        # Validate args
        if not id:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.ARGS.value,message="Id was not provided.").data,status=status.HTTP_400_BAD_REQUEST)
        
        
        
        # Get Record instance
        try:
            record = ShoppingList.objects.get(user = request.user,id = id)
        except ShoppingList.DoesNotExist:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="Shopping list couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)

        record.delete()
        

        return Response( status=status.HTTP_200_OK)

class ShoppingListsView(APIView):

    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['User'],
        operation_summary="Retrieve a paginated list of users",
        operation_description="Retrieve a paginated list of users based on optional search criteria.",
        manual_parameters=[
            openapi.Parameter(
                'string',
                openapi.IN_QUERY,
                description="String to search for in users' first name, last name, or email address.",
                type=openapi.TYPE_STRING,
                default=""
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="The page number to retrieve.",
                type=openapi.TYPE_INTEGER,
                default=1
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="The number of users per page. Must be one of [5, 10, 20, 40].",
                type=openapi.TYPE_INTEGER,
                default=5
            ),
        ],
        responses={
            200: openapi.Response(
                description='A paginated list of users.',
                schema=ListResponseSerializer
            ),
            400: openapi.Response(
                description='Bad request. The provided page does not exist or other parameter issues.',
                schema=ErrorResponseSerializer
            ),
        }
    )
    def get(self, request):
        """
        Retrieve a paginated list of users based on optional search criteria.

        Search criteria:
            - string: A string to search for in users' first name, last name, or email address. Defaults to an empty string.
            - page: The page number to retrieve. Defaults to 1.
            - page_size: The number of users per page. Must be one of [5, 10, 20, 40]. Defaults to 5.

        Returns:
            Response: A JSON response containing the paginated list of users and metadata.
                The metadata includes information about the current page, page size, total pages, and total users.
        """
        
        # Get query parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 5))
        group_id = request.query_params.get('group_id')
        
                
        # Build base query
        if group_id:
            query = ShoppingList.objects.filter(group = group_id).order_by('created_at')
        else:
            query = request.user.shoppinglists.all().order_by('created_at') 
        
        
        # Paginate the results
        paginator = Paginator(query, page_size)

        
        # Get the requested page
        try:
            records_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.PAGINATION.value,message="Page does not exist.").data, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            ListResponseSerializer.build_(request,page,paginator,serializer = ShoppingListSerializer(records_page, many=True),endpoint_name="user_list").data,
            status=status.HTTP_200_OK)
    