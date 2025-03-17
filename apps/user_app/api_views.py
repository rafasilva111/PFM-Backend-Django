###
#       General imports
##


##
#   Default
#

from django.utils import timezone
from django.contrib.auth import login, logout, authenticate
from django.conf import settings
from django.db.models import Case, When, Value, BooleanField,Q

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

from apps.user_app.models import User


##
#   Serializers
#

from apps.user_app.serializers import UserSerializer,UserSimpleSerializer,UserPatchSerializer
from apps.api.serializers import LoginSerializer,LogoutSerializer,TokenSerializer,SuccessResponseSerializer,ErrorResponseSerializer,ListResponseSerializer,IdResponseSerializer


##
#   Functions
#


##
#   Contants
#


from apps.api.constants import ERROR_TYPES,RESPONSE_CODES




###
#
#   User App
#
##

###
#   Auth
##

class LoginView(APIView):
    """
    View for user login authentication.

    - Accepts POST requests with email and password.
    - Returns a token for successful authentication.
    """


    @swagger_auto_schema(
        tags=['Auth'], 
        operation_id="login", 
        request_body=LoginSerializer,
        responses={
            200: TokenSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
        }
    )
    def post(self, request):
        """
        Handle POST request for user login.

        Args:
            request: HTTP request object containing user login data.

        Returns:
            Response: HTTP response with token data or error message.
        """
        
        # Validate serializer
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        # Authenticate user
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = authenticate(request, username=email, password=password)
        
        if not user:
            return Response(ErrorResponseSerializer.from_dict({'auth': ['Invalid email or password']}).data, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate token and expiration time
        return Response(TokenSerializer.for_user(user).data, status=status.HTTP_200_OK)


class AuthView(APIView):
    """
    View for user authentication and registration.

    - GET: Returns user data if authenticated.
    - POST: Registers a new user.
    """
    
    def get_permissions(self):
        """
        Define permissions based on HTTP method.

        Returns:
            list: List of permissions for the request.
        """
        if self.request.method in ['GET', 'DELETE']:
            return [IsAuthenticated()]
        return []

    @swagger_auto_schema(
        tags=['Auth'],      
        operation_id="session",     
        responses={
            200: UserSerializer,
            401: ErrorResponseSerializer,
        }
    )
    def get(self, request):
        """
        Handle GET request for user authentication.

        Args:
            request: HTTP request object.

        Returns:
            Response: HTTP response with user data or authentication error.
        """
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=['Auth'],
        operation_id="register", 
        request_body=UserSerializer,
        responses={
            201: UserSerializer,
            400: ErrorResponseSerializer,
        }
    )
    def post(self, request):    
        """
        Handle POST request for user registration.

        Args:
            request: HTTP request object containing user registration data.

        Returns:
            Response: HTTP response with success message or error.
        """
        # Validate user input
        serializer = UserSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Save user data
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(ErrorResponseSerializer.from_dict({"exception": str(e)}).data, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        tags=['Auth'],
        operation_id="logout", 
        request_body=LogoutSerializer,
        responses={
            200: openapi.Response(description="Logout successful"),
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        }
    )
    def delete(self, request):
        """
        Handle DELETE request for user logout.

        Args:
            request: HTTP request object containing user token.

        Returns:
            Response: HTTP response with success message or error.
        """
        
        serializer = LogoutSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            
            
            # Retrieve the user's refresh token
            refresh_token = RefreshToken(serializer.validated_data['refresh'])
            
            # Blacklist the refresh token
            refresh_token.blacklist()
            
            return Response( status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response(ErrorResponseSerializer.from_params(type=ERROR_TYPES.INTERNAL.value, message= str(e)).data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from datetime import datetime
from django.utils import timezone

class CustomTokenRefreshView(TokenRefreshView):
    def get_serializer_class(self):
        # Use the existing TokenRefreshSerializer from simple_jwt
        return TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        # Call the parent class's post method to get the original response
        print(request.data)
        response = super().post(request, *args, **kwargs)

        
        # Extract expiration dates
        access_token_expires = timezone.now() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
        refresh_token_expires = timezone.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']


        # Add expiration details to the response data
        response.data ={
            'refresh_token': str(response.data['refresh']),            
            'refresh_token_expires': refresh_token_expires.isoformat(),
            'access_token': str(response.data['access']),
            'access_token_expires': access_token_expires.isoformat()
            
        }

        return response

###
#   User
##


class UserListView(APIView):

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
        string_to_search = request.query_params.get('string', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 5))
                
        # Build base query
        query = User.objects.exclude(user_type=User.UserType.ADMIN.value).order_by('created_at')
        
        # Perform search if string_to_search is provided
        if string_to_search:
            query = query.filter(
                Q(first_name__icontains=string_to_search) |
                Q(last_name__icontains=string_to_search) |
                Q(email__icontains=string_to_search)
            )
        
        # Paginate the results
        paginator = Paginator(query, page_size)

        
        # Get the requested page
        try:
            records_page = paginator.page(page)
        except Exception:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Page does not exist."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            ListResponseSerializer.build_(request,page,paginator,serializer = UserSimpleSerializer(records_page, many=True),endpoint_name="user_list").data,
            status=status.HTTP_200_OK)
    
    
class UserView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    """
    API endpoint for user operations.

    Supports GET, DELETE, and PATCH methods.
    Requires JWT authentication.
    """

    
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
        username = request.query_params.get('username')

        # Validate args
        if id:
            try:
                user = User.objects.get(id=id)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this id.").data,status=status.HTTP_400_BAD_REQUEST)
        elif username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return Response(ErrorResponseSerializer.from_params(type = ERROR_TYPES.MISSING_MODEL.value,message="User couldn't be found by this username.").data,status=status.HTTP_400_BAD_REQUEST)
        else:

            return Response(ErrorResponseSerializer.from_dict({"args":"Missing arguments."}).data,status=status.HTTP_400_BAD_REQUEST)

        # Check if user is following or pending
        #is_following = Follow.objects.filter(follower=user_logged_id, followed=user).exists()
        #is_pending = FollowRequest.objects.filter(follower=user_logged_id, followed=user).exists()

        # Set followed state based on user relationship
        #followed_state = FOLLOWED_STATE_SET.FOLLOWED.value if is_following else (
        #    FOLLOWED_STATE_SET.PENDING_FOLLOWED.value if is_pending else FOLLOWED_STATE_SET.NOT_FOLLOWED.value
        #)

        # Serialize user profile
        user_data = UserSerializer(user).data
        #user_data['followed_state'] = followed_state

        return Response(data = user_data, status=status.HTTP_200_OK)



    @swagger_auto_schema(
        tags=['User'],
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

        # Get user authed
        user = request.user

        # Serialize    
        serializer = UserPatchSerializer(data=request.data, partial=True)
        
        # Validate Serializer
        if not serializer.is_valid():
            return Response(ErrorResponseSerializer.from_serializer_errors(serializer).data, status=status.HTTP_400_BAD_REQUEST)

        # Update instance
        try:
            validated_data = serializer.validated_data
            
            if 'password' in validated_data:
                if not user.check_password(validated_data.pop('old_password', '')):
                    return Response(ErrorResponseSerializer.from_dict({"validation":"Old password is incorrect."}).data, status=status.HTTP_400_BAD_REQUEST)
                
                user.set_password(validated_data.pop('password'))
                
            for key, value in validated_data.items():
                setattr(user, key, value)

            user.updated_date = timezone.now()
            user.save()
            
        except Exception as e:
            return Response(ErrorResponseSerializer.from_dict({"exception":"Error updating user."}).data, status=status.HTTP_400_BAD_REQUEST)
        
        
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=['User'],
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

        # Get user authed
        user = request.user
        
        
        # Retrieve the user's refresh token
        refresh_token = RefreshToken.for_user(user)
        
        # Delete user instance
        user.delete()
        